import calendar
import json
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb
import httpx
import pytest
from pydantic import SecretStr
from typer.main import get_command
from typer.testing import CliRunner

from astock.cli import main
from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.probe import load_plan, run_probe
from astock.data.probe_audit import cross_audit, logical_fingerprint, table_audit
from astock.data.tushare_client import ProviderTable, TushareClient
from astock.paths import get_project_root
from astock.settings import Settings


NOW=datetime(2024,1,3,tzinfo=timezone.utc)
SECRET='synthetic-local-token-never-a-real-credential'


@pytest.fixture
def root(tmp_path):
    import shutil
    for name in ('config','sql'):
        shutil.copytree(get_project_root()/name,tmp_path/name)
    return tmp_path


def fake_client(permission=None,auth=False,redirect=False,native_anomaly=False):
    calls=[]
    def handler(request):
        req=json.loads(request.content);calls.append(req)
        dataset=req['api_name'];fields=req['fields'].split(',');params=req['params']
        if redirect:return httpx.Response(302,headers={'Location':'https://evil.example'})
        if auth:return httpx.Response(200,json={'code':40101,'msg':SECRET})
        if dataset==permission:return httpx.Response(200,json={'code':2002,'msg':SECRET})
        rows=[]
        if dataset=='trade_cal':
            for day in range(1,31):
                r=dict(exchange='SSE',cal_date=f'202609{day:02}',is_open=int(day==29),pretrade_date=None)
                rows.append([r[f] for f in fields])
        elif dataset=='stock_basic' and params=={'exchange':'SSE','list_status':'L'}:
            r=dict(ts_code='600001.SH',symbol='600001',name='Synthetic',market='Main',exchange='SSE',
                   list_status='L',list_date='20000101',delist_date=None)
            rows=[[r[f] for f in fields]]
        elif native_anomaly and dataset=='stock_basic' and params=={'exchange':'SSE','list_status':'D'}:
            r=dict(ts_code='T123456.SH',symbol='T123456',name='Synthetic predecessor',market=None,
                   exchange='SSE',list_status='D',list_date='20000101',delist_date='20061020')
            rows=[[r[f] for f in fields]]
        elif dataset in ('daily','daily_basic','adj_factor','stk_limit'):
            r=dict(ts_code='600001.SH',trade_date=params['trade_date'],open=10.0,high=11.0,low=9.0,
                   close=10.0,pre_close=10.0,change=0.0,pct_chg=0.0,vol=100.0,amount=1000.0,
                   turnover_rate=1.0,pe=10.0,pb=1.0,total_share=100.0,total_mv=1000.0,
                   adj_factor=1.0,up_limit=11.0,down_limit=9.0,asset_type='STK',exchange='SSE')
            rows=[[r[f] for f in fields]]
        return httpx.Response(200,json={'code':0,'data':{'fields':fields,'items':rows}})
    clock=[0.0]
    def sleep(seconds):clock[0]+=seconds
    return TushareClient(SecretStr(SECRET),transport=httpx.MockTransport(handler),
                         clock=lambda:clock[0],sleep=sleep),calls


def test_full_synthetic_probe_bounded_and_reconstructable(root,monkeypatch):
    monkeypatch.setattr('astock.data.probe._commit',lambda root:'a'*40)
    client,calls=fake_client()
    summary,path=run_probe(root,Settings(tushare_token=SecretStr(SECRET)),client=client)
    assert summary['status']=='PASS'
    assert len(calls)==47
    assert calls[0]['api_name']=='trade_cal'
    assert summary['resolved_recent_date']=='2026-09-29'
    assert summary['secret_scan']=='PASS'
    assert all(summary['repeat_consistency'].values())
    assert summary['lineage_reconciled'] and summary['raw_reconstruction_verified']
    assert summary['runs']['daily']['raw_object_count']==6
    assert summary['runs']['stock_basic']['raw_object_count']==15
    assert SECRET not in path.read_text()
    assert all(r['status']=='SUCCEEDED' for r in summary['runs'].values())
    with duckdb.connect(str(root/'data/warehouse/astock.duckdb')) as db:
        assert db.execute('SELECT count(*) FROM raw_object_manifest').fetchone()==(47,)
        assert db.execute("SELECT count(*) FROM ingestion_run WHERE mode='PROBE'").fetchone()==(8,)
        assert not db.execute("SELECT table_name FROM information_schema.tables WHERE table_name='daily_bar'").fetchall()
    assert not (root/'data/curated').exists()
    from astock.data.probe_review import export_review
    review, observed = export_review(root,summary,SecretStr(SECRET),'2026-10-01')
    assert SECRET not in review.read_text()+observed.read_text()
    assert '600001.SH' not in observed.read_text()
    assert json.loads(observed.read_bytes())['status']=='PASS'
    summary['captures'][0]['observed_fields'].append(SECRET)
    summary['batch_id']='00000000-0000-0000-0000-000000000099'
    with pytest.raises(ValueError,match='SECRET_SCAN: FAIL'):
        export_review(root,summary,SecretStr(SECRET),'2026-10-02')
    assert not (root/'docs/reviews/2026-10-02-phase1b-review.md').exists()


@pytest.mark.parametrize('condition',['auth','redirect'])
def test_handshake_stops_immediately(root,monkeypatch,condition):
    monkeypatch.setattr('astock.data.probe._commit',lambda root:'a'*40)
    client,calls=fake_client(**{condition:True})
    summary,_=run_probe(root,Settings(tushare_token=SecretStr(SECRET)),client=client)
    assert summary['status']=='BLOCKED'
    assert len(calls)==1
    assert summary['runs']['trade_cal']['status']=='FAILED'


def test_native_capture_passes_source_dq_but_identity_gate_remains_partial(root,monkeypatch):
    monkeypatch.setattr('astock.data.probe._commit',lambda root:'a'*40)
    client,_=fake_client(native_anomaly=True)
    summary,_=run_probe(root,Settings(tushare_token=SecretStr(SECRET)),client=client)
    assert all(c['dq_status']=='PASS' for c in summary['captures'])
    findings=[c for c in summary['captures'] if c['identity_status']=='REVIEW_REQUIRED']
    assert len(findings)==1 and findings[0]['invalid_source_identifier_count']==0
    assert findings[0]['non_normalized_identifier_count']==1
    assert summary['status']=='PARTIAL'


def test_permission_failure_keeps_other_captures_and_cannot_pass(root,monkeypatch):
    monkeypatch.setattr('astock.data.probe._commit',lambda root:'a'*40)
    client,calls=fake_client(permission='stock_st')
    summary,_=run_probe(root,Settings(tushare_token=SecretStr(SECRET)),client=client)
    assert summary['status']=='PARTIAL'
    assert len(calls)==47
    assert summary['runs']['stock_st']['status']=='FAILED'
    assert summary['runs']['daily']['raw_object_count']==6
    assert summary['errors'][0]['error']['category']=='PERMISSION'


def test_missing_token_creates_no_files_or_requests(root):
    before=set(root.rglob('*'))
    with pytest.raises(ValueError,match='not configured'):run_probe(root,Settings())
    assert set(root.rglob('*'))==before


def test_stk_contract_enriched():
    contracts={c.dataset:c for c in load_contracts(get_project_root())}
    assert contracts['stk_limit'].required_fields==[
        'trade_date','ts_code','pre_close','up_limit','down_limit','asset_type','exchange']


def test_fingerprint_column_and_row_reordering_preserves_nulls():
    contract={c.dataset:c for c in load_contracts(get_project_root())}['adj_factor']
    a=ProviderTable(fields=['ts_code','trade_date','adj_factor'],
        items=[['600001.SH','20240103',None],['600002.SH','20240103',1.0]],retrieved_at=NOW)
    b=ProviderTable(fields=['adj_factor','trade_date','ts_code'],
        items=[[1.0,'20240103','600002.SH'],[None,'20240103','600001.SH']],retrieved_at=NOW)
    assert logical_fingerprint(a,contract)==logical_fingerprint(b,contract)
    b.items[1][0]=0.0
    assert logical_fingerprint(a,contract)!=logical_fingerprint(b,contract)


def test_dq_cap_duplicates_null_factor_and_cross_close_mismatch():
    contracts={c.dataset:c for c in load_contracts(get_project_root())}
    client,_=fake_client()
    daily=client.fetch(contracts['daily'],RequestParams(trade_date=date(2019,6,25)))
    basic=client.fetch(contracts['daily_basic'],RequestParams(trade_date=date(2019,6,25)))
    factor=client.fetch(contracts['adj_factor'],RequestParams(trade_date=date(2019,6,25)))
    audit=table_audit(daily,contracts['daily'].model_copy(update={'max_rows':1}))
    assert audit['potential_truncation'] and audit['dq_status']=='ERROR'
    daily.items.append(daily.items[0].copy())
    assert table_audit(daily,contracts['daily'])['natural_key_duplicates']==1
    daily.items.pop()
    basic.items[0][basic.fields.index('close')]=20.0
    factor.items[0][factor.fields.index('adj_factor')]=None
    cross=cross_audit({'daily':daily,'daily_basic':basic,'adj_factor':factor},{'600001.SH'})
    assert cross['daily_basic']['close_mismatch']==1
    assert cross['adj_factor']['null_nonpositive_factor']==1
    daily.items[0][daily.fields.index('high')]=1.0
    assert table_audit(daily,contracts['daily'])['daily']['ohlc_invalid']==1


def test_cli_live_gate_plan_status_and_missing_token(root,monkeypatch):
    monkeypatch.setattr(main,'get_project_root',lambda:root)
    runner=CliRunner()
    before=set(root.rglob('*'))
    assert runner.invoke(main.app,['data','probe','plan']).exit_code==0
    assert runner.invoke(main.app,['data','probe','status']).exit_code==0
    result=runner.invoke(main.app,['data','probe','run'])
    assert result.exit_code==1 and '--live' in result.output
    result=runner.invoke(main.app,['data','probe','run','--live'])
    assert result.exit_code==1 and 'outside the chat/model input' in result.output
    assert set(root.rglob('*'))==before
    assert set(get_command(main.app).commands['data'].commands['probe'].commands)=={'plan','run','status'}


def test_plan_cannot_be_extended(root):
    import yaml
    path=root/'config/probes/phase1b.yaml'
    obj=yaml.safe_load(path.read_text());obj['stock_statuses'].append('extra')
    path.write_text(yaml.safe_dump(obj))
    with pytest.raises(ValueError):load_plan(root)
