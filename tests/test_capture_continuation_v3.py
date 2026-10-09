"""New capability only: stopped ledger copies, durable single attempts, safe facts."""

import copy
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx
import pytest
import socket

from astock.data import capture_continuation_v3 as run
from astock.data import transport_diagnostics as diag
from astock.data.warehouse_lock import warehouse_connection, WarehouseLockError
from test_full_backfill_v1 import ROOT, TOKEN, Clock, envelope, no_real_sockets, setup, send


def stopped(tmp_path,dataset='daily',count=3):
    state=setup(tmp_path,dataset=dataset,count=count);store=state[3]
    def fail(request):raise httpx.ReadTimeout('closed synthetic exception')
    with warehouse_connection(store/'capture.duckdb') as db:
        with pytest.raises(ValueError):send(db,state,handler=fail)
    before=run.old.sha256(store/'capture.duckdb')
    with warehouse_connection(store/'capture.duckdb') as db:
        base=run.freeze_baseline(ROOT,db,store,before)
        run.upgrade_copy(ROOT,db,store,base)
        app=run.application(ROOT,db,base,fixture=True)
    review,human=license_for(app)
    return base,app,review,human,store,state[4]


def license_for(app):
    now=datetime.now(timezone.utc).isoformat()
    review=dict(protocol=run.PROTOCOL,namespace='FIXTURE',application_hash=run.old.checksum(app),
                pins=app['pins'],baseline_hash=app['baseline_hash'],membership_hash=app['membership_hash'],
                production_destination=app['production_destination'],budget=app['budget'],
                implementation_sha='closed-fixture-code',review_ref='FIXTURE:independent',
                reviewed_at=now,execution_license=True,human_evidence='FIXTURE:actual-human')
    human=dict(protocol=run.PROTOCOL,review_hash=run.old.checksum(review),instruction_ref=review['human_evidence'],
               authorization_ref='FIXTURE:human',authorized_at=now,execution_license=True)
    return review,human


def capture(db,state,index=0,handler=None,fault=lambda stage:None):
    base,app,review,human,store,clock=state;m=app['members'][index]
    handler=handler or (lambda request:httpx.Response(200,json=envelope(m['request'])))
    return run.capture_mock(ROOT,db,store,base,app,review,human,m['member_id'],TOKEN,
                            transport=httpx.MockTransport(handler),clock=clock,fault=fault)


def test_upgrade_exact_origin_preserved_attempt_new_authorization_and_reopen(tmp_path):
    state=stopped(tmp_path);base,app,_,_,store,_=state;assert len(app['members'])==2
    with warehouse_connection(store/'capture.duckdb') as db:
        assert run.rowsets(db)==base['legacy_rows']
        assert capture(db,state)['status']=='COMPLETE'
        assert capture(db,state,1)['status']=='COMPLETE'
        assert run.rowsets(db)==base['legacy_rows']
        assert db.execute('SELECT count(*) FROM continuation_attempt').fetchone()[0]==2
        assert db.execute('SELECT count(*) FROM continuation_authorization').fetchone()[0]==1
        assert run.upgrade_copy(ROOT,db,store,base)['old_history_unchanged']
    with warehouse_connection(store/'capture.duckdb') as db:
        run.audit(ROOT,db,store,base)
        assert capture(db,state,handler=lambda r:pytest.fail('no resend'))['status']=='ALREADY_VALID'
        assert run.rowsets(db)==base['legacy_rows']


@pytest.mark.parametrize('kind',['review','human','oldSHA','members','budget','pins','order','clone','dependencies','consumed'])
def test_no_license_changed_scope_or_clone_never_calls(tmp_path,kind):
    state=stopped(tmp_path);base,app,review,human,store,_=state
    if kind=='review':review['execution_license']=False
    if kind=='human':human['instruction_ref']='FIXTURE:forged'
    if kind=='oldSHA':review['implementation_sha']='old';review['namespace']='PRODUCTION'
    if kind=='members':app['members'][0]['request']['fields']=[]
    if kind=='budget':app['budget']=99
    if kind=='pins':app['pins'][run.SOURCE]='0'*64
    if kind=='order':app['members'].reverse()
    if kind=='consumed':app['members'][0]['member_id']=next(mid for mid,h in base['consumption'].items() if h)
    if kind=='dependencies':
        app['members'][0]['dependencies']=[next(mid for mid,h in base['consumption'].items() if h)]
        app['membership_hash']=run.old.checksum(app['members']);state=(base,app,*license_for(app),store,state[-1])
    with warehouse_connection(store/'capture.duckdb') as db:
        with pytest.raises(ValueError):
            if kind=='clone':run.authorize(tmp_path,db,base,app,review,human,fixture=True)
            else:capture(db,state,handler=lambda r:pytest.fail('no call'))
        assert db.execute('SELECT count(*) FROM continuation_attempt').fetchone()[0]==0


@pytest.mark.parametrize('stage',['after_claim','after_call_entered'])
def test_crash_boundary_consumes_once_and_stops_other_member(tmp_path,stage):
    state=stopped(tmp_path);store=state[4]
    def crash(value):
        if value==stage:raise KeyboardInterrupt()
    with warehouse_connection(store/'capture.duckdb') as db:
        with pytest.raises(KeyboardInterrupt):capture(db,state,fault=crash,handler=lambda r:pytest.fail('no call'))
    with warehouse_connection(store/'capture.duckdb') as db:
        for index in [0,1]:
            with pytest.raises(ValueError):capture(db,state,index,handler=lambda r:pytest.fail('no retry'))
        assert db.execute('SELECT count(*) FROM continuation_attempt').fetchone()[0]==1
        assert run.rowsets(db)==state[0]['legacy_rows']


def test_process_death_after_durable_claim_no_network_or_new_attempt(tmp_path):
    state=stopped(tmp_path);store=state[4]
    pid=os.fork()
    if pid==0:
        with warehouse_connection(store/'capture.duckdb') as db:
            capture(db,state,fault=lambda stage:os._exit(73) if stage=='after_claim' else None)
        os._exit(74)
    _,status=os.waitpid(pid,0);assert os.waitstatus_to_exitcode(status)==73
    with warehouse_connection(store/'capture.duckdb') as db:
        with pytest.raises(ValueError):capture(db,state,1,handler=lambda r:pytest.fail('no send'))
        assert db.execute('SELECT count(*) FROM continuation_attempt').fetchone()[0]==1


def test_new_unknown_safe_error_and_no_retry_or_later_member(tmp_path):
    state=stopped(tmp_path);calls=[]
    def fail(request):calls.append(1);raise httpx.ReadTimeout('password secret token arbitrary repr')
    with warehouse_connection(state[4]/'capture.duckdb') as db:
        with pytest.raises(ValueError):capture(db,state,handler=fail)
        for index in [0,1]:
            with pytest.raises(ValueError):capture(db,state,index,handler=lambda r:pytest.fail('no retry'))
        payload=json.dumps(run.rowsets(db,run.NEW_TABLES));assert 'password secret' not in payload
        assert 'READ_TIMEOUT' in payload and len(calls)==1
        assert run.rowsets(db)==state[0]['legacy_rows']


@pytest.mark.parametrize('stage',['after_sidecar','after_registration','after_promotion'])
@pytest.mark.parametrize('file',sorted(run.old.FILES))
def test_final_five_file_mutation_rolls_back_then_reopen_blocks_resend(tmp_path,stage,file):
    state=stopped(tmp_path);store=state[4];mid=state[1]['members'][0]['member_id'];calls=[]
    def mutate(value):
        if value==stage:(store/mid/file).write_bytes(b'{}')
    def handler(request):calls.append(1);return httpx.Response(200,json=envelope(state[1]['members'][0]['request']))
    with warehouse_connection(store/'capture.duckdb') as db:
        with pytest.raises((ValueError,KeyError)):capture(db,state,handler=handler,fault=mutate)
        assert db.execute('SELECT count(*) FROM continuation_receipt').fetchone()[0]==0
    with warehouse_connection(store/'capture.duckdb') as db:
        with pytest.raises(ValueError):capture(db,state,handler=lambda r:pytest.fail('no resend'))
        assert run.rowsets(db)==state[0]['legacy_rows']
    assert len(calls)==1


def test_unknown_cap_raw_retained_and_native_null_not_research_complete(tmp_path):
    state=stopped(tmp_path,dataset='adj_factor')
    with warehouse_connection(state[4]/'capture.duckdb') as db:
        result=capture(db,state);assert result['status']=='RAW_RETAINED'
        assert result['completeness']=='RAW_UNCERTIFIED' and result['research_admitted'] is False
        run.audit(ROOT,db,state[4],state[0])
    (tmp_path/'null').mkdir();other=stopped(tmp_path/'null',dataset='stk_limit')
    with warehouse_connection(other[4]/'capture.duckdb') as db:
        assert capture(db,other)['status']=='COMPLETE'
        path=other[4]/other[1]['members'][0]['member_id']/'typed.parquet'
        assert run.pq.read_table(path).to_pylist()[0]['pre_close'] is None


def test_managed_concurrent_claims_one_attempt(tmp_path):
    state=stopped(tmp_path)
    def work():
        try:
            with warehouse_connection(state[4]/'capture.duckdb',wait_seconds=5) as db:return capture(db,state)['status']
        except WarehouseLockError:return 'LOCKED'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:work(),range(2)))
    assert results.count('COMPLETE')==1
    with warehouse_connection(state[4]/'capture.duckdb') as db:
        assert db.execute('SELECT count(*) FROM continuation_attempt').fetchone()[0]==1


def test_diag_allowlist_never_evaluates_exception_repr_or_string():
    class Dangerous(Exception):
        def __str__(self):pytest.fail('exception str leaked')
        def __repr__(self):pytest.fail('exception repr leaked')
    at=diag.utc();v=diag.observation(phase='READ_BODY',started_at=at,ended_at=at,
                                    headers_received=True,body_bytes=7,eof=False,error=Dangerous())
    assert v['error_type']=='OTHER_EXCEPTION' and v['body_bytes']==7 and v['TLS_verify']
    assert not any(k in v for k in ['request','headers','token','exception','proxy','certificate'])


@pytest.mark.parametrize('failed',['DNS','TCP','TLS',None])
def test_one_shot_connection_phases_dependency_failure_no_HTTP(monkeypatch,failed):
    calls=[];records=[]
    def lookup(*a,**k):
        calls.append('DNS')
        if failed=='DNS':raise socket.gaierror('unsafe raw exception string')
        return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('192.0.2.1',443))]
    class Sock:
        def settimeout(self,t):assert t==10
        def connect(self,addr):
            calls.append('TCP')
            if failed=='TCP':raise PermissionError('unsafe token')
        def close(self):pass
        def do_handshake(self):
            calls.append('TLS')
            if failed=='TLS':raise diag.ssl.SSLError('unsafe secret')
    class Context:
        def wrap_socket(self,s,**kw):
            assert kw=={'server_hostname':diag.HOST,'do_handshake_on_connect':False};return s
    monkeypatch.setattr(socket,'getaddrinfo',lookup)
    monkeypatch.setattr(socket,'socket',lambda *a,**k:Sock())
    monkeypatch.setattr(diag.ssl,'create_default_context',lambda **kw:Context())
    result=diag.connection_probe(records.append)
    assert calls==['DNS','TCP','TLS'][:{'DNS':1,'TCP':2,'TLS':3,None:3}[failed]]
    assert result['HTTP_calls']==0 and result['token_sent'] is False
    assert not any(word in json.dumps(records) for word in ['unsafe','secret'])


def test_calendar_leading_unknown_and_new_cross_window_conflict(tmp_path):
    from test_full_backfill_repairs import repin
    state=setup(tmp_path,count=3);p=state[0];c=json.loads((ROOT/run.old.CATALOG).read_text())['trade_cal'];members=[]
    for day in ['20241231','20250101','20250102']:
        m=dict(dataset='trade_cal',params=dict(exchange='SSE',start_date=day,end_date=day),fields=c['required_fields'],contract_bytes_hash=c['contract_bytes_hash'],completeness_evidence=None,empty_evidence=None)
        m['member_id']=run.old.logical_id(m);members.append(m)
    p['requests']=members;repin(state);store=state[3]
    with warehouse_connection(store/'capture.duckdb') as db:
        with pytest.raises(ValueError):send(db,state,handler=lambda req:(_ for _ in ()).throw(httpx.ReadTimeout('closed')))
    before=run.old.sha256(store/'capture.duckdb')
    with warehouse_connection(store/'capture.duckdb') as db:
        base=run.freeze_baseline(ROOT,db,store,before);run.upgrade_copy(ROOT,db,store,base)
        app=run.application(ROOT,db,base,fixture=True);review,human=license_for(app);new=(base,app,review,human,store,state[-1])
        def body(index,previous):
            m=app['members'][index]['request'];return dict(request_id='closed-calendar',code=0,msg='',data=dict(fields=m['fields'],items=[['SSE',m['params']['start_date'],1,previous]]))
        assert capture(db,new,handler=lambda req:httpx.Response(200,json=body(0,'20241230')))['status']=='COMPLETE'
        manifest=json.loads((store/app['members'][0]['member_id']/'manifest.json').read_text());assert not manifest['leading_previous_certified'] and not manifest['research_admitted']
        with pytest.raises(ValueError):capture(db,new,1,handler=lambda req:httpx.Response(200,json=body(1,'20241230')))
        assert db.execute('SELECT count(*) FROM continuation_receipt').fetchone()[0]==1


def test_production_entry_rejects_copy_and_missing_explicit_intent(tmp_path):
    state=stopped(tmp_path);base,app,review,human,store,_=state
    with warehouse_connection(store/'capture.duckdb') as db:
        for live in [False,True]:
            with pytest.raises(ValueError):run.capture_production(ROOT,db,store,base,app,review,human,app['members'][0]['member_id'],TOKEN,live=live)
            with pytest.raises(ValueError):run.upgrade_production(ROOT,db,store,base,app,review,human,live=live)
        assert db.execute('SELECT count(*) FROM continuation_attempt').fetchone()[0]==0


def test_stale_clock_cannot_register_or_claim_before_human(tmp_path,monkeypatch):
    from datetime import timedelta
    state=stopped(tmp_path);base,app,review,human,store,clock=state
    clock.wall=run.old.instant(human['authorized_at'])-timedelta(seconds=1)
    # Isolate the authorization boundary from the already-tested older pacing clock.
    monkeypatch.setattr(run.old,'pace',lambda *a:None)
    with warehouse_connection(store/'capture.duckdb') as db:
        with pytest.raises(ValueError,match='CLAIM_BEFORE_ACTUAL_AUTHORIZATION'):
            capture(db,state,handler=lambda r:pytest.fail('no call'))
        assert db.execute('SELECT count(*) FROM continuation_attempt').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM continuation_authorization').fetchone()[0]==0


def test_protected_history_manifest_and_files_fail_closed(tmp_path):
    root=tmp_path/'root';root.mkdir();data=root/'data/warehouse/astock.duckdb';meta=root/'data/private/phase1c1-admission-metadata-live-v1/metadata.duckdb'
    for p in [data,meta]:
        p.parent.mkdir(parents=True,exist_ok=True)
        with warehouse_connection(p) as db:db.execute('CREATE TABLE closed_fixture(v INTEGER)')
    artifact=root/'historical.txt';artifact.write_text('immutable synthetic history')
    inventory=dict(original_hash=run.old.sha256(data),metadata_hash=run.old.sha256(meta),files={'historical.txt':run.old.sha256(artifact)},accepted171={})
    manifest=root/'manifest.json';manifest.write_text(json.dumps(inventory));base={'protected_history':{'path':'manifest.json','sha256':run.old.sha256(manifest)}}
    run.protected_history_check(root,base)
    artifact.write_text('changed')
    with pytest.raises(ValueError,match='PROTECTED_HISTORY_CHANGED'):run.protected_history_check(root,base)
    with pytest.raises(ValueError,match='PROTECTED_HISTORY_REQUIRED'):run.protected_history_check(root,{})
