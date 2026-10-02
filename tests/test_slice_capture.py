from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
import shutil

import duckdb
import httpx
import pytest
from pydantic import SecretStr

from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.raw_writer import migrate,RawWriter,verify_batch
from astock.data.slice_capture import capture_slices,identity_state,SliceStop,publish_capture_metadata,batch_requests
from astock.data.receipt_migration import apply_receipt_integrity_upgrade
from astock.data.slice_plan import APPROVED,create_batch,claim_request
from astock.data.tushare_client import TushareClient,ProviderFailure,ProviderTable
from astock.settings import Settings
from astock.paths import get_project_root

ROOT=get_project_root()


@pytest.fixture
def slice_root(tmp_path):
    shutil.copytree(ROOT/'config',tmp_path/'config');shutil.copytree(ROOT/'sql',tmp_path/'sql')
    (tmp_path/'data/warehouse').mkdir(parents=True)
    with duckdb.connect(str(tmp_path/'data/warehouse/astock.duckdb')) as db:
        migrate(db,tmp_path)
        apply_receipt_integrity_upgrade(tmp_path,db,verification_sha='a'*40)
        now=datetime(2026,1,1,tzinfo=timezone.utc)
        db.execute('INSERT INTO security_identifier_history VALUES (?,?,?,?,?,?,?,?,?,?,?)',[
            'synthetic-security','tushare','ts_code','000001.SZ','SZSE',date(1990,1,1),None,None,now,now,'synthetic-evidence'])
        db.execute('INSERT INTO security_venue_history VALUES (?,?,?,?,?,?,?,?,?,?)',[
            'synthetic-security','SZSE',date(1990,1,1),None,date(1990,1,1),None,'tushare',now,now,'synthetic-evidence'])
    return tmp_path


class SyntheticCaptureClient:
    def __init__(self):self.calls=[]
    def fetch_slice(self,contract,params):
        self.calls.append((contract.dataset,params.public_dict()))
        fields=contract.required_fields
        items=[]
        if contract.dataset=='trade_cal':
            approved={d.replace('-','') for days in APPROVED.values() for d in days}
            d=params.start_date;previous=d-timedelta(days=1)
            while d<=params.end_date:
                is_open=int(d.strftime('%Y%m%d') in approved)
                r={'exchange':'SSE','cal_date':d.strftime('%Y%m%d'),'is_open':is_open,'pretrade_date':previous.strftime('%Y%m%d')}
                items.append([r[f] for f in fields])
                if is_open:previous=d
                d+=timedelta(days=1)
        return ProviderTable(fields=fields,items=items,retrieved_at=datetime.now(timezone.utc))


def settings():return Settings(_env_file=None,tushare_token=SecretStr('synthetic-local-placeholder'))


def test_real_capture_requires_live_and_fixed_scope():
    contract=next(c for c in load_contracts(ROOT,catalog_version='v2') if c.dataset=='daily')
    calls=[]
    def response(req):calls.append(req);return httpx.Response(503)
    client=TushareClient(SecretStr('synthetic-token'),transport=httpx.MockTransport(response))
    with pytest.raises(ValueError):client.fetch_slice(contract,RequestParams(trade_date=date(2012,1,1)))
    assert not calls
    with pytest.raises(ProviderFailure):client.fetch_slice(contract,RequestParams(trade_date=date(2013,1,4)))
    assert len(calls)==1
    with pytest.raises(SliceStop):capture_slices(Path('/synthetic-missing'),settings(),live=False)


def test_intentional_interrupt_resume_and_no_duplicate_raw(slice_root):
    client=SyntheticCaptureClient()
    first=capture_slices(slice_root,settings(),live=True,stop_after=8,client=client,commit='a'*40)
    assert first['status']=='INTERRUPTED' and len(client.calls)==8
    batch=UUID(first['batch_id'])
    result=capture_slices(slice_root,settings(),live=True,batch_id=batch,client=client,commit='a'*40)
    assert result['status']=='CAPTURED' and len(client.calls)==133
    again=capture_slices(slice_root,settings(),live=True,batch_id=batch,client=client,commit='a'*40)
    assert again['status']=='CAPTURED' and len(client.calls)==133
    with duckdb.connect(str(slice_root/'data/warehouse/astock.duckdb')) as db:
        assert db.execute('SELECT count(*),count(DISTINCT object_id) FROM raw_object_manifest').fetchone()==(133,133)
        assert verify_batch(slice_root,db,[r[0] for r in db.execute('SELECT run_id FROM ingestion_run').fetchall()])
    with pytest.raises(SliceStop):capture_slices(slice_root,settings(),live=True,client=client,commit='a'*40)


def test_crash_after_registered_raw_recovers_without_refetch(slice_root):
    with duckdb.connect(str(slice_root/'data/warehouse/astock.duckdb')) as db:
        identity,_,_=identity_state(db)
        batch=create_batch(slice_root,db,commit='a'*40,identity_hash=identity,knowledge_as_of=datetime.now(timezone.utc))
        claim_request(db,batch,0)
        run=db.execute('SELECT run_id FROM slice_request WHERE ordinal=0').fetchone()[0]
        c=next(c for c in load_contracts(slice_root,catalog_version='v2') if c.dataset=='trade_cal')
        p=RequestParams(exchange='SSE',start_date=date(2013,1,4),end_date=date(2013,1,8))
        table=SyntheticCaptureClient().fetch_slice(c,p)
        raw=RawWriter(slice_root,db).write(run,'trade_cal',0,table,p)
        req=batch_requests(db,batch)[0]
        publish_capture_metadata(slice_root,db,req,c,dict(object_id=str(raw.object_id),relative_path=raw.relative_path,sha256=raw.sha256))
    client=SyntheticCaptureClient()
    result=capture_slices(slice_root,settings(),live=True,batch_id=batch,stop_after=1,client=client,commit='a'*40)
    assert result['status']=='INTERRUPTED' and client.calls[0][0]=='daily'
    with duckdb.connect(str(slice_root/'data/warehouse/astock.duckdb')) as db:
        assert db.execute("SELECT count(*) FROM slice_request WHERE status='COMPLETE'").fetchone()==(2,)


def test_uncertain_network_receipt_never_replayed(slice_root):
    with duckdb.connect(str(slice_root/'data/warehouse/astock.duckdb')) as db:
        identity,_,_=identity_state(db)
        batch=create_batch(slice_root,db,commit='a'*40,identity_hash=identity,knowledge_as_of=datetime.now(timezone.utc))
        claim_request(db,batch,0)
    client=SyntheticCaptureClient()
    result=capture_slices(slice_root,settings(),live=True,batch_id=batch,client=client,commit='a'*40)
    assert result['status']=='BLOCKED' and result['failure']=='UNCERTAIN_CAPTURE' and not client.calls
    assert list((slice_root/f'data/private/phase1c1/{batch}').glob('operation-block-*.json'))


def test_lineage_corruption_stops_resume(slice_root):
    first=capture_slices(slice_root,settings(),live=True,stop_after=1,client=SyntheticCaptureClient(),commit='a'*40)
    with duckdb.connect(str(slice_root/'data/warehouse/astock.duckdb')) as db:
        relative=db.execute('SELECT relative_path FROM raw_object_manifest').fetchone()[0]
    (slice_root/relative).write_bytes(b'synthetic corruption')
    client=SyntheticCaptureClient()
    result=capture_slices(slice_root,settings(),live=True,batch_id=UUID(first['batch_id']),client=client,commit='a'*40)
    assert result['failure']=='FILE_CHECKSUM' and not client.calls
