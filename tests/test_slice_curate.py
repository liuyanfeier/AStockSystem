from datetime import date, datetime, timezone
from uuid import UUID

from astock.data.warehouse_lock import warehouse_connection
import duckdb
import pyarrow.parquet as pq
import pytest

from astock.data.curation import load_curation_specs
from astock.data.identity import IdentifierHistory, IdentityHistory
from astock.data.slice_capture import capture_slices, SliceStop
from astock.data.slice_curate import FrozenResolver, convert, curate_slices, cast_field, logical_hash
from astock.data.tushare_client import ProviderTable
from test_slice_capture import slice_root, settings, SyntheticCaptureClient, ROOT


NOW=datetime(2026,1,1,tzinfo=timezone.utc)


def resolver():
    def row(code,start,end):
        return IdentifierHistory(security_id='same-bse',source='tushare',identifier_type='ts_code',
            identifier=code,exchange='BSE',valid_from=start,valid_to=end,available_at=NOW,retrieved_at=NOW,evidence_source='synthetic')
    history=IdentityHistory([row('835305.BJ',date(2021,11,15),date(2025,10,9)),
                             row('920305.BJ',date(2025,10,9),None)])
    venue=dict(security_id='same-bse',venue='BSE',effective_from=date(2021,11,15),effective_to=None,available_at=NOW)
    return FrozenResolver(history,[venue],NOW)


def test_exact_bse_boundary_and_no_suffix_guessing():
    r=resolver()
    assert r.resolve('835305.BJ',date(2025,9,30))==('same-bse',None)
    assert r.resolve('920305.BJ',date(2025,10,9))==('same-bse',None)
    assert r.resolve('835305.BJ',date(2025,10,9))[1]=='OUTSIDE_IDENTIFIER_INTERVAL'
    assert r.resolve('920305.BJ',date(2025,9,30))[1]=='OUTSIDE_IDENTIFIER_INTERVAL'
    assert r.resolve('835305.BJ',date(2021,11,12))[1]=='PRE_BSE_LEGACY'
    assert r.resolve('830305.BJ',date(2025,10,9))[1]=='NO_IDENTIFIER_MAPPING'
    with pytest.raises(SliceStop):r.resolve('920305.BJ',date(2025,10,9),provider_exchange='SZSE')


def test_native_anomaly_and_unknown_preserved_in_quarantine():
    spec=next(s for s in load_curation_specs(ROOT,spec_version='v2') if s.dataset=='adj_factor')
    table=ProviderTable(fields=[f.source_column for f in spec.fields],
        items=[['T600018.SH','20251009',1.0],['830305.BJ','20251009',1.0],['920305.BJ','20251009',2.0]],retrieved_at=NOW)
    arrow,q=convert(table,{'object_id':'raw-synthetic'},spec,resolver())
    assert arrow.num_rows==1 and arrow['security_id'].to_pylist()==['same-bse']
    assert q[0]['provider_identifier']=='T600018.SH' and q[0]['raw_row_number']==0
    assert q[0]['reason']=='NON_NORMALIZED_IDENTIFIER'
    assert q[1]['reason']=='NO_IDENTIFIER_MAPPING'
    assert arrow['raw_row_number'].to_pylist()==[2]


def test_empty_typed_schema_and_strict_values():
    for spec in load_curation_specs(ROOT,spec_version='v2'):
        arrow,q=convert(ProviderTable(fields=[f.source_column for f in spec.fields],items=[],retrieved_at=NOW),
                        {'object_id':'empty'},spec,resolver())
        assert arrow.num_rows==0 and q==[] and str(arrow.schema.field('trade_date').type)=='date32[day]'
        assert not arrow.schema.field('security_id').nullable
        assert logical_hash(arrow)==logical_hash(arrow)
    spec=next(s for s in load_curation_specs(ROOT,spec_version='v2') if s.dataset=='stk_limit')
    assert str(spec.arrow_schema().field('exchange').type)=='string'
    f=next(f for f in spec.fields if f.source_column=='pre_close')
    for value in ('1.00',True,float('nan'),2**53+1):
        with pytest.raises(SliceStop):cast_field(value,f)
    assert cast_field(None,f) is None


class MarketClient(SyntheticCaptureClient):
    def fetch_slice(self,contract,params):
        table=super().fetch_slice(contract,params)
        if contract.dataset=='trade_cal':return table
        specs={s.dataset:s for s in load_curation_specs(ROOT,spec_version='v2')}
        spec=specs[contract.dataset];row={}
        for f in spec.fields:
            row[f.source_column]={'string':'synthetic','float64':1.0,'int64':1,'date32':params.trade_date.strftime('%Y%m%d')}[f.logical_type]
        row.update(ts_code='000001.SZ',asset_type='STK',exchange='SZSE',change=0.0,pct_chg=0.0)
        return table.model_copy(update={'items':[[row[f] for f in table.fields]]})


def test_rebuild_after_deleted_outputs_and_lineage_reconstruction(slice_root):
    result=capture_slices(slice_root,settings(),live=True,client=MarketClient(),commit='a'*40)
    batch=UUID(result['batch_id'])
    first=curate_slices(slice_root,batch,commit='a'*40)
    assert first['curated_objects']==126 and first['resolved_rows']==126
    with warehouse_connection(str(slice_root/'data/warehouse/astock.duckdb')) as db:
        rows=db.execute('''SELECT c.relative_path,r.relative_path FROM slice_curated_binding b
            JOIN curated_object_manifest c ON c.object_id=b.curated_object_id
            JOIN raw_object_manifest r ON r.object_id=b.raw_object_id''').fetchall()
        for curated,raw in rows:
            derived=pq.ParquetFile(slice_root/curated).read().to_pylist()[0]
            original=pq.ParquetFile(slice_root/raw).read().to_pylist()[derived['raw_row_number']]
            assert derived['ts_code']==original['ts_code']
            (slice_root/curated).unlink()
    rebuilt=curate_slices(slice_root,batch,rebuild=True,commit='a'*40)
    assert rebuilt['generation']==1 and rebuilt['rebuild_hash_match']
    with warehouse_connection(str(slice_root/'data/warehouse/astock.duckdb')) as db:
        assert db.execute('SELECT count(*) FROM raw_object_manifest').fetchone()==(133,)
        assert db.execute('SELECT count(DISTINCT logical_hash) FROM slice_curated_binding GROUP BY request_id HAVING count(DISTINCT logical_hash)>1').fetchall()==[]
