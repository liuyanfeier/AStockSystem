from datetime import date
from uuid import UUID

from astock.data.warehouse_lock import warehouse_connection
import duckdb
import pytest

from astock.data.slice_dq import causal_audit, audit_tables, dq_slices
from astock.data.slice_capture import capture_slices, SliceStop
from astock.data.slice_curate import curate_slices, FrozenResolver
from astock.data.slice_plan import APPROVED
from astock.data.identity import IdentityHistory
from test_slice_capture import slice_root,settings, ROOT
from test_slice_curate import MarketClient, NOW


def bar(day,close,pre,pct):
    return dict(security_id='synthetic',trade_date=day,open=close,high=close,low=close,close=close,pre_close=pre,pct_chg=pct)


def test_causal_ex_right_chain_and_future_prefix_invariance():
    d1,d2,d3=date(2025,5,6),date(2025,5,7),date(2025,5,8)
    bars=[bar(d1,10.0,10.0,0.0),bar(d2,5.5,5.0,10.0)]
    previous={d2:d1,d3:d2};factors={('synthetic',d1):1.0,('synthetic',d2):2.0}
    first,prefix=causal_audit(bars,factors,previous)
    assert first['adjacent_pairs']==1 and first['causal_mismatch']==first['factor_mismatch']==0
    assert prefix[1]['scale']==2 and prefix[1]['causal_close']==11.0
    extended,series=causal_audit([*bars,bar(d3,2.2,2.2,0.0)],{**factors,('synthetic',d3):5.0},previous)
    assert series[:2]==prefix and extended['factor_mismatch']==0
    # An incompatible later reconstruction factor is an audit error, never an earlier price rewrite.
    incorrect,changed=causal_audit([*bars,bar(d3,2.2,2.2,0.0)],{**factors,('synthetic',d3):99.0},previous)
    assert changed[:2]==prefix and incorrect['factor_mismatch']==1


def test_causal_skips_sparse_gaps_and_flags_corruption():
    d1,d2=date(2025,5,6),date(2025,10,9)
    stats,series=causal_audit([bar(d1,10,10,0),bar(d2,5,5,0)],{}, {d2:date(2025,9,30)})
    assert stats['adjacent_pairs']==0 and stats['gap_resets']==1 and series[-1]['scale']==1
    invalid,_=causal_audit([bar(d1,10,10,0),bar(d2,5.5,5,9)],{('synthetic',d1):1,('synthetic',d2):2},{d2:d1})
    assert invalid['causal_mismatch']==invalid['factor_mismatch']==1


def test_missing_daily_requires_explicit_suspension_or_boundary_explanation():
    venue=dict(security_id='synthetic',venue='SZSE',effective_from=date(1990,1,1),effective_to=None,
               provider_list_date=date(1990,1,1),provider_delist_date=None,available_at=NOW)
    resolver=FrozenResolver(IdentityHistory([]),[venue],NOW)
    tables={}
    for days in APPROVED.values():
        for text in days:
            day=date.fromisoformat(text)
            tables[('suspend_d',day)]=[dict(security_id='synthetic',trade_date=day,suspend_type='S',suspend_timing=None)]
    result,_=audit_tables(tables,[],resolver,{})
    assert result['errors']['unexplained_missing_daily']==0
    day=date(2025,5,6);tables[('suspend_d',day)]=[]
    result,_=audit_tables(tables,[],resolver,{})
    assert result['errors']['unexplained_missing_daily']==1 and result['status']=='BLOCKED'
    venue['provider_delist_date']=day
    result,private=audit_tables(tables,[],FrozenResolver(IdentityHistory([]),[venue],NOW),{})
    assert result['errors']['unexplained_missing_daily']==0
    assert private['delist_boundary_review'][0]['effective_to'] is None
    assert private['delist_boundary_review'][0]['classification']=='BOUNDARY_REVIEW'


def test_offline_dq_reconstructs_every_row_and_detects_curated_corruption(slice_root):
    result=capture_slices(slice_root,settings(),live=True,client=MarketClient(),commit='a'*40)
    batch=UUID(result['batch_id']);curate_slices(slice_root,batch,commit='a'*40)
    summary=dq_slices(slice_root,batch)
    assert summary['lineage']=='PASS' and summary['schema']=='PASS' and summary['error_count']==0
    assert summary['raw_objects']==133 and summary['curated_objects']==126
    assert summary['causal']['adjacent_pairs']==14
    with warehouse_connection(str(slice_root/'data/warehouse/astock.duckdb')) as db:
        relative=db.execute('SELECT relative_path FROM curated_object_manifest LIMIT 1').fetchone()[0]
    (slice_root/relative).write_bytes(b'synthetic corruption')
    with pytest.raises(SliceStop):dq_slices(slice_root,batch)


def test_cross_table_errors_and_unresolved_traded_rows_cannot_pass():
    day=date(2025,5,6)
    resolver=FrozenResolver(IdentityHistory([]),[],NOW)
    daily={**bar(day,10,10,0),'security_id':'synthetic'}
    tables={('daily',day):[daily],('daily_basic',day):[{**daily,'close':12}],
            ('stk_limit',day):[{**daily,'pre_close':13}],('adj_factor',day):[{**daily,'adj_factor':-1}]}
    q=[dict(dataset='daily',reason='NO_IDENTIFIER_MAPPING')]
    result,_=audit_tables(tables,q,resolver,{})
    assert result['errors']['daily_basic_price_mismatch']==1
    assert result['errors']['stk_limit_price_mismatch']==1
    assert result['errors']['nonpositive_factor']==1
    assert result['errors']['unresolved_traded_identity']==1
    assert result['status']=='BLOCKED'


def test_secret_scan_supports_typed_curated_dates_and_compressed_tokens(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from pydantic import SecretStr
    from astock.data.raw_writer import secret_scan
    secret='synthetic-hidden-credential-test-value'
    path=tmp_path/'typed.parquet'
    safe=pa.table({'trade_date':[date(2025,5,6)],'retrieved_at':[NOW],'native':['000001.SZ']})
    pq.write_table(safe,path,compression='gzip',write_statistics=False)
    assert secret_scan(SecretStr(secret),[path])
    unsafe=pa.table({'trade_date':[date(2025,5,6)],'retrieved_at':[NOW],'native':[secret]})
    pq.write_table(unsafe,path,compression='gzip',write_statistics=False)
    assert secret.encode() not in path.read_bytes()
    assert not secret_scan(SecretStr(secret),[path])
