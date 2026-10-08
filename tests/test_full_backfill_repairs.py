"""Review F1-F4 regressions, actual file faults and sequential closed-mock plans."""
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest

from astock.data import acquisition_proposal as proposal
from astock.data import full_backfill_v1 as run
from astock.data.warehouse_lock import warehouse_connection
from test_full_backfill_v1 import ROOT, Clock, TOKEN, envelope, no_real_sockets, send, setup


def repin(state):
    p,a,h,_,_=state
    p['membership_hash']=run.checksum(p['requests'])
    a.update(plan_hash=run.checksum(p),membership_hash=p['membership_hash'],budget=p['budget'])
    h['approval_hash']=run.checksum(a)
    return state


@pytest.mark.parametrize('kind',['full-day','intraday','missing-code','missing-type','missing-date','duplicate-null','two-timings'])
def test_f1_nullable_component_exact_tuple_and_required_keys(tmp_path,kind):
    state=setup(tmp_path,dataset='suspend_d',count=1);m=state[0]['requests'][0]
    body=envelope(m);fields=m['fields']; row=body['data']['items'][0]
    row[fields.index('suspend_timing')]=None if kind!='intraday' else '09:30-10:00'
    if kind.startswith('missing-'):
        row[fields.index({'missing-code':'ts_code','missing-type':'suspend_type','missing-date':'trade_date'}[kind])]=None
    if kind=='duplicate-null':body['data']['items']*=2
    if kind=='two-timings':
        other=row.copy();other[fields.index('suspend_timing')]='10:00-11:00';body['data']['items'].append(other)
    ok=kind in ('full-day','intraday','two-timings');calls=[]
    def handler(req):calls.append(1);return httpx.Response(200,json=body)
    with warehouse_connection(state[3]/'capture.duckdb') as db:
        if ok:assert send(db,state,handler=handler)['status']=='COMPLETE'
        else:
            with pytest.raises(ValueError):send(db,state,handler=handler)
        assert db.execute('SELECT count(*) FROM backfill_receipt').fetchone()[0]==int(ok)
    with warehouse_connection(state[3]/'capture.duckdb') as db:
        if ok:assert send(db,state,handler=lambda req:pytest.fail('resend'))['status']=='ALREADY_VALID'
        else:
            with pytest.raises(ValueError):send(db,state,handler=lambda req:pytest.fail('resend'))
    assert len(calls)==1
    if ok:
        rows=pq.read_table(state[3]/m['member_id']/'typed.parquet').to_pylist()
        assert rows[0]['suspend_timing']==row[fields.index('suspend_timing')]


@pytest.mark.parametrize('stage',['after_sidecar','after_registration','after_promotion'])
@pytest.mark.parametrize('file',['response.body','http-source.json','typed.parquet','manifest.json','sidecar.json'])
def test_f2_final_physical_readback_rolls_back_success_before_commit(tmp_path,stage,file):
    state=setup(tmp_path,count=1);mid=state[0]['requests'][0]['member_id'];calls=[]
    def fault(value):
        if value==stage:(state[3]/mid/file).write_bytes(b'{}')
    def handler(req):calls.append(1);return httpx.Response(200,json=envelope(state[0]['requests'][0]))
    with warehouse_connection(state[3]/'capture.duckdb') as db:
        with pytest.raises(ValueError):send(db,state,handler=handler,fault=fault)
        assert db.execute('SELECT count(*) FROM backfill_receipt').fetchone()[0]==0
        assert [e[0] for e in run.events(db,mid)]==['CLAIMED','CALL_ENTERED']
    damaged=(state[3]/mid/file).read_bytes()
    with warehouse_connection(state[3]/'capture.duckdb') as db:
        with pytest.raises(ValueError):send(db,state,handler=lambda req:pytest.fail('resend'))
        assert db.execute('SELECT count(*) FROM backfill_receipt').fetchone()[0]==0
    assert damaged==b'{}' and (state[3]/mid/file).read_bytes()==damaged and len(calls)==1


def calendar_state(tmp_path,start='20250101',end='20250102',venue='SSE'):
    state=setup(tmp_path,count=1);c=json.loads((ROOT/run.CATALOG).read_bytes())['trade_cal']
    m=dict(dataset='trade_cal',params=dict(exchange=venue,start_date=start,end_date=end),fields=c['required_fields'],contract_bytes_hash=c['contract_bytes_hash'],empty_evidence=None,completeness_evidence=None)
    m['member_id']=run.logical_id(m);state[0]['requests']=[m]
    return repin(state)


def calendar_body(state,items=None):
    m=state[0]['requests'][0]
    return dict(request_id='closed-calendar',code=0,msg='',data=dict(fields=m['fields'],items=items or [['SSE','20250101',1,'20241231'],['SSE','20250102',0,'20250101']]))


def rowsets(db):
    return {n:db.execute(f'SELECT * FROM {n} ORDER BY ALL').fetchall() for n, in db.execute("SELECT table_name FROM duckdb_tables() WHERE schema_name='main'").fetchall()}


def test_f3_calendar_market_next_shard_same_store_original_provenance_budget_preserved(tmp_path):
    for name in ('A','B','C'):(tmp_path/name).mkdir()
    a=calendar_state(tmp_path/'A');store=a[3]
    b=setup(tmp_path/'B',count=1);b=(*b[:3],store,a[4])
    c=setup(tmp_path/'C',count=1);c[0]['requests'][0]['params']['trade_date']='20250103';c[0]['requests'][0]['member_id']=run.logical_id(c[0]['requests'][0]);repin(c);c=(*c[:3],store,a[4])
    old_files={};old=None
    for state in (a,b,c):
        with warehouse_connection(store/'capture.duckdb') as db:
            if old:
                for table,rows in old.items():assert all(row in db.execute(f'SELECT * FROM {table}').fetchall() for row in rows)
            handler=(lambda req:httpx.Response(200,json=calendar_body(a))) if state is a else None
            assert send(db,state,handler=handler)['status']=='COMPLETE'
            old=rowsets(db)
            for path,body in old_files.items():assert path.read_bytes()==body
            old_files.update({p:p.read_bytes() for p in store.rglob('*') if p.is_file() and p.name in run.FILES})
    with warehouse_connection(store/'capture.duckdb') as db:
        assert db.execute('SELECT count(*) FROM backfill_pin').fetchone()[0]==3
        assert db.execute("SELECT count(*) FROM backfill_event WHERE state='CALL_ENTERED'").fetchone()[0]==3
        for state in (a,b,c):assert send(db,state,handler=lambda req:pytest.fail('reuse HTTP'))['status']=='ALREADY_VALID'
        assert rowsets(db)==old
    # Separate independently reviewed plan reuses the exact COMPLETE and original pins.
    d=copy.deepcopy(c[:3]);d[0]['budget']=2;state=(*d,store,Clock());repin(state)
    with warehouse_connection(store/'capture.duckdb') as db:
        assert send(db,state,handler=lambda req:pytest.fail('cross-plan resend'))['status']=='ALREADY_VALID'
        assert db.execute('SELECT count(*) FROM backfill_receipt').fetchone()[0]==3
        assert db.execute("SELECT count(*) FROM backfill_event WHERE state='CLAIMED'").fetchone()[0]==3


@pytest.mark.parametrize('terminal',['FAILED','UNCERTAIN'])
def test_f3_cross_plan_terminal_overlap_and_new_members_never_resend(tmp_path,terminal):
    (tmp_path/'A').mkdir();(tmp_path/'B').mkdir();a=setup(tmp_path/'A',count=1)
    def handler(req):
        if terminal=='UNCERTAIN':raise httpx.ReadTimeout('closed')
        return httpx.Response(403,json={})
    with warehouse_connection(a[3]/'capture.duckdb') as db:
        with pytest.raises(ValueError):send(db,a,handler=handler)
    b=setup(tmp_path/'B',count=1);b=(*b[:3],a[3],b[4]);b[0]['budget']=2;repin(b)
    with warehouse_connection(a[3]/'capture.duckdb') as db:
        with pytest.raises(ValueError):send(db,b,handler=lambda req:pytest.fail('crossplan resend'))
        b[0]['requests'][0]['params']['trade_date']='20250103';b[0]['requests'][0]['member_id']=run.logical_id(b[0]['requests'][0]);repin(b)
        with pytest.raises(ValueError,match='PLAN_STOPPED'):send(db,b,handler=lambda req:pytest.fail('new member send'))
        assert db.execute("SELECT count(*) FROM backfill_event WHERE state='CALL_ENTERED'").fetchone()[0]==1


@pytest.mark.parametrize('kind',['plan','license','origin','new-evidence','namespace','new-store'])
def test_f3_origin_tamper_and_renames_fail_closed(tmp_path,kind):
    state=setup(tmp_path,count=1)
    with warehouse_connection(state[3]/'capture.duckdb') as db:
        send(db,state)
        if kind=='plan':db.execute("UPDATE backfill_pin SET payload='{}'")
        elif kind=='license':db.execute("UPDATE backfill_authorization SET approval_hash='fake'")
        elif kind=='origin':db.execute("UPDATE backfill_member SET payload='{}'")
        elif kind=='new-evidence':
            state[0]['requests'][0]['empty_evidence']={'path':'AGENTS.md','sha256':run.sha256(ROOT/'AGENTS.md')};repin(state)
        elif kind=='namespace':state[0]['namespace']='PRODUCTION';repin(state)
        elif kind=='new-store':
            other=tmp_path/'other';other.mkdir()
            with pytest.raises(ValueError,match='STORE_OWNER_MISMATCH'):run.owner(db,other)
            return
        with pytest.raises(ValueError):send(db,state,handler=lambda req:pytest.fail('HTTP'))


def test_f3_old_v1_schema_rejected_unchanged(tmp_path):
    state=setup(tmp_path)
    with warehouse_connection(state[3]/'capture.duckdb') as db:
        db.execute((ROOT/'sql/offline/full_backfill_v1.sql').read_text());before=rowsets(db)
        with pytest.raises(ValueError,match='STORE_PROTOCOL_CHANGED'):send(db,state,handler=lambda req:pytest.fail('HTTP'))
        assert rowsets(db)==before


@pytest.mark.parametrize('kind',['valid','missing','extra','duplicate','venue','previous','previous-self','empty','type'])
def test_calendar_civil_and_previous_rules_on_new_capture_path(tmp_path,kind):
    state=calendar_state(tmp_path);body=calendar_body(state);items=body['data']['items']
    if kind=='missing':items.pop()
    elif kind=='extra':items.append(['SSE','20250103',1,'20250101'])
    elif kind=='duplicate':items.append(items[0].copy())
    elif kind=='venue':items[0][0]='SZSE'
    elif kind=='previous':items[1][3]='20241231'
    elif kind=='previous-self':items[0][3]='20250101'
    elif kind=='empty':items.clear()
    elif kind=='type':items[0][2]=True
    with warehouse_connection(state[3]/'capture.duckdb') as db:
        if kind=='valid':assert send(db,state,handler=lambda req:httpx.Response(200,json=body))['status']=='COMPLETE'
        else:
            with pytest.raises(ValueError):send(db,state,handler=lambda req:httpx.Response(200,json=body))
            assert db.execute('SELECT count(*) FROM backfill_receipt').fetchone()[0]==0


def test_calendar_adjacent_windows_must_match_last_open(tmp_path):
    (tmp_path/'A').mkdir();(tmp_path/'B').mkdir();a=calendar_state(tmp_path/'A');b=calendar_state(tmp_path/'B',start='20250103',end='20250103');b=(*b[:3],a[3],b[4])
    with warehouse_connection(a[3]/'capture.duckdb') as db:send(db,a,handler=lambda req:httpx.Response(200,json=calendar_body(a)))
    with warehouse_connection(a[3]/'capture.duckdb') as db:
        with pytest.raises(ValueError,match='CROSS_WINDOW'):send(db,b,handler=lambda req:httpx.Response(200,json=calendar_body(b,[['SSE','20250103',1,'20241231']])))
        assert db.execute('SELECT count(*) FROM backfill_receipt').fetchone()[0]==1


def test_f4_descriptor_set_hash_reorder_and_every_field_delta():
    a={'request':{'member_id':'a'},'purpose':'p','storage':'x'};b={'request':{'member_id':'b'},'purpose':'q','storage':'y'}
    h=proposal.descriptor_hash([a,b]);assert h==proposal.descriptor_hash([b,a])
    for field in ('purpose','storage','applicability'):
        changed=copy.deepcopy(a);changed[field]='new';assert proposal.descriptor_hash([changed,b])!=h
    assert run.checksum([a,b])!=run.checksum([b,a])
    with pytest.raises(ValueError):proposal.descriptor_hash([a,a])


def test_f4_index_file_reference_drift_rejected(tmp_path):
    p=tmp_path/'proposal.json';p.write_bytes(b'original');ref={'path':p.name,'sha256':run.sha256(p),'bytes':8}
    assert proposal.validate_references(tmp_path,ref)==1
    p.write_bytes(b'modified')
    with pytest.raises(ValueError):proposal.validate_references(tmp_path,ref)


def application_fixture(tmp_path):
    import shutil
    root=tmp_path/'root';root.mkdir()
    for rel in (run.SOURCE,run.DESIGN,run.CATALOG,run.DDL,'config/contracts/v2/trade_cal.yaml'):
        p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,p)
    c=json.loads((root/run.CATALOG).read_bytes())['trade_cal'];inventory=[]
    for venue,years in [('SSE',range(2013,2027)),('SZSE',range(2013,2027)),('BSE',range(2021,2027))]:
        windows=[(str(y)+'0101','20260930' if y==2026 else str(y)+'1231') for y in years]
        if venue in ('SSE','SZSE'):windows.insert(0,('20121201','20121231'))
        for start,end in windows:
            m=dict(dataset='trade_cal',params=dict(exchange=venue,start_date=start,end_date=end),fields=c['required_fields'],contract_bytes_hash=c['contract_bytes_hash'],completeness_evidence=None,empty_evidence=None);m['member_id']=run.logical_id(m)
            held=venue=='BSE' or venue=='SZSE' and start=='20130101'
            if not held:
                p=root/(m['member_id']+'.json');p.write_bytes(run.canonical_json(run.calendar_rule(m)));m['completeness_evidence']={'path':p.name,'sha256':run.sha256(p)}
            inventory.append(dict(request=m,group='HOLD' if held else 'CANDIDATE',execution_license=False,max_attempts=1,call_start_spacing_seconds=1.25,purpose='Exact civil evidence, unlicensed',wire=dict(endpoint=run.ENDPOINT,method='POST',api_name='trade_cal',params=m['params'],fields=','.join(m['fields'])),storage_paths={n:f"{run.DESTINATION}/{m['member_id']}/{n}" for n in run.FILES}))
    candidates=[d for d in inventory if d['group']=='CANDIDATE'];hold=[d for d in inventory if d['group']=='HOLD']
    requests=[d['request'] for d in candidates]
    descriptor_file=root/'candidate-descriptors.json';descriptor_file.write_bytes(run.canonical_json(candidates))
    descriptor_ref=dict(path=descriptor_file.name,sha256=run.sha256(descriptor_file),descriptor_hash=proposal.descriptor_hash(candidates))
    plan=dict(protocol=run.PROTOCOL,namespace='PROPOSED',execution_license=False,requests=requests,membership_hash=run.checksum(requests),max_attempts=1,budget=29,pins=run.pins(root),approval_descriptors=descriptor_ref,historical_PIT_eligible=False,prior_failed_logical_members=[])
    a=dict(inventory=inventory,candidates=candidates,hold=hold,execution_license=False,approved_at=None,review_ref=None,budget=29,runtime_membership_hash=plan['membership_hash'],runtime_plan_hash=run.checksum(plan),**{n+'_descriptor_hash':proposal.descriptor_hash(d) for n,d in [('inventory',inventory),('candidates',candidates),('hold',hold)]})
    return root,a,plan


@pytest.mark.parametrize('kind',['valid','purpose','reorder','runtime-reorder','member','partition','rule','index'])
def test_f4_actual36_29_7_application_semantics_and_final_hash_domains(tmp_path,kind):
    root,a,p=application_fixture(tmp_path)
    if kind=='purpose':a['candidates'][0]['purpose']='changed after hash'
    elif kind=='reorder':a['inventory'].reverse();a['hold'].reverse()
    elif kind=='runtime-reorder':p['requests'].reverse();p['membership_hash']=run.checksum(p['requests'])
    elif kind=='member':a['candidates'][0]['request']['params']['exchange']='BSE'
    elif kind=='partition':a['candidates'][0]['group']='HOLD'
    elif kind=='rule':
        e=p['requests'][0]['completeness_evidence'];(root/e['path']).write_bytes(b'{}');e['sha256']=run.sha256(root/e['path'])
    elif kind=='index':
        f=root/'final.json';f.write_bytes(run.canonical_json(a));ref={'path':f.name,'sha256':run.sha256(f)};f.write_bytes(b'{}')
        with pytest.raises(ValueError):proposal.validate_references(root,ref)
        return
    if kind in ('valid','reorder'):assert proposal.validate_application(root,a,p)['candidates']==29
    else:
        with pytest.raises(ValueError):proposal.validate_application(root,a,p)


def test_no_live_or_approval_cannot_consume_proposed29_plan(tmp_path):
    root,a,p=application_fixture(tmp_path);store=root/run.DESTINATION;store.mkdir(parents=True)
    with warehouse_connection(store/'capture.duckdb') as db:
        for live in (False,True):
            with pytest.raises(ValueError):run.capture(root,db,store,p,{}, {},p['requests'][0]['member_id'],TOKEN,live=live)
        assert run.layout(db)==[]


def test_consumption_identity_fields_contract_and_budget_cannot_create_new_call():
    m={'dataset':'daily','params':{'trade_date':'20130109'},'fields':['x'],'contract_bytes_hash':'a'}
    changed=copy.deepcopy(m);changed.update(fields=['new'],contract_bytes_hash='b',plan_name='new',budget=100)
    assert run.logical_id(m)==run.logical_id(changed)


def test_concurrent_managed_claim_can_only_enter_one_closed_http(tmp_path):
    import threading
    from astock.data.warehouse_lock import WarehouseLockError
    state=setup(tmp_path,count=1);entered=threading.Event();release=threading.Event();errors=[];calls=[]
    def worker():
        try:
            with warehouse_connection(state[3]/'capture.duckdb') as db:
                def handler(req):
                    calls.append(1);entered.set();assert release.wait(10)
                    return httpx.Response(200,json=envelope(state[0]['requests'][0]))
                assert send(db,state,handler=handler)['status']=='COMPLETE'
        except BaseException as e:errors.append(e);entered.set()
    thread=threading.Thread(target=worker);thread.start()
    try:
        assert entered.wait(10) and not errors
        with pytest.raises(WarehouseLockError):
            with warehouse_connection(state[3]/'capture.duckdb') as db:send(db,state,handler=lambda req:pytest.fail('second HTTP'))
    finally:release.set();thread.join(10)
    assert not thread.is_alive() and not errors and len(calls)==1
    with warehouse_connection(state[3]/'capture.duckdb') as db:
        assert send(db,state,handler=lambda req:pytest.fail('reopen HTTP'))['status']=='ALREADY_VALID'
        assert db.execute("SELECT count(*) FROM backfill_event WHERE state='CLAIMED'").fetchone()[0]==1


def test_production_new_store_cannot_bypass_fixed_ledger(tmp_path,monkeypatch):
    import shutil
    state=setup(tmp_path,count=1);p,a,h,s,clock=state
    root=tmp_path/'root';root.mkdir()
    for rel in (run.SOURCE,run.DESIGN,run.CATALOG,run.DDL,'config/contracts/v2/daily.yaml','config/contracts/v2/trade_cal.yaml'):
        dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
    descriptors=[dict(request=m,purpose='ISOLATED_TEST_ONLY') for m in p['requests']]
    path=root/'descriptors.json';path.write_bytes(run.canonical_json(descriptors))
    p['approval_descriptors']=dict(path=path.name,sha256=run.sha256(path),descriptor_hash=proposal.descriptor_hash(descriptors))
    p['namespace']=a['namespace']=h['namespace']='PRODUCTION'
    a.update(implementation_sha='ISOLATED_TEST_SHA',review_ref='ISOLATED_TEST_REVIEW',production_destination=str((root/run.DESTINATION).resolve()))
    h['authorization_ref']='ISOLATED_TEST_HUMAN';repin(state)
    monkeypatch.setattr(run.subprocess,'check_output',lambda cmd,**kw:'ISOLATED_TEST_SHA\n' if cmd[1]=='rev-parse' else b'')
    with warehouse_connection(s/'capture.duckdb') as db:
        with pytest.raises(ValueError,match='FIXED_PRODUCTION_STORE_REQUIRED'):
            run.capture(root,db,s,p,a,h,p['requests'][0]['member_id'],TOKEN,live=True,clock=clock)
        assert run.layout(db)==[]


@pytest.mark.parametrize('repin_descriptor',[False,True])
def test_final_descriptor_change_invalidates_file_or_matched_license_before_http(tmp_path,repin_descriptor):
    root,a,p=application_fixture(tmp_path);p['namespace']='FIXTURE';now=datetime.now(timezone.utc).isoformat()
    review=dict(protocol=run.PROTOCOL,namespace='FIXTURE',plan_hash=run.checksum(p),membership_hash=p['membership_hash'],pins=p['pins'],budget=p['budget'],implementation_sha='FIXTURE:code',review_ref='FIXTURE:review',reviewed_at=now,production_destination=None,execution_license=True)
    human=dict(protocol=run.PROTOCOL,namespace='FIXTURE',approval_hash=run.checksum(review),authorization_ref='FIXTURE:human',authorized_at=now,execution_license=True)
    path=root/p['approval_descriptors']['path'];descriptors=json.loads(path.read_text());descriptors[0]['new_purpose']='changed after independent approval';path.write_bytes(run.canonical_json(descriptors))
    if repin_descriptor:p['approval_descriptors'].update(sha256=run.sha256(path),descriptor_hash=proposal.descriptor_hash(descriptors))
    store=root/'store';store.mkdir()
    with warehouse_connection(store/'capture.duckdb') as db:
        with pytest.raises(ValueError,match='MATCHED_REVIEW_REQUIRED' if repin_descriptor else 'APPROVAL_DESCRIPTOR_FILE_CHANGED'):
            run.capture(root,db,store,p,review,human,p['requests'][0]['member_id'],TOKEN,fixture=True,live=True,transport=httpx.MockTransport(lambda req:pytest.fail('HTTP')))
        assert run.layout(db)==[]


def test_same_external_review_cannot_relocate_fixed_ledger_by_cloning_root(tmp_path,monkeypatch):
    import shutil
    state=setup(tmp_path,count=1);p,a,h,_,clock=state;roots=[]
    for name in ('A','B'):
        root=tmp_path/name;root.mkdir();roots.append(root)
        for rel in (run.SOURCE,run.DESIGN,run.CATALOG,run.DDL,'config/contracts/v2/daily.yaml','config/contracts/v2/trade_cal.yaml'):
            dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
        path=root/'descriptors.json';descriptors=[dict(request=m,purpose='ISOLATED_TEST_ONLY') for m in p['requests']];path.write_bytes(run.canonical_json(descriptors))
    p['approval_descriptors']=dict(path=path.name,sha256=run.sha256(path),descriptor_hash=proposal.descriptor_hash(descriptors))
    p['namespace']=a['namespace']=h['namespace']='PRODUCTION'
    a.update(implementation_sha='ISOLATED_TEST_SHA',review_ref='ISOLATED_TEST_REVIEW',production_destination=str((roots[0]/run.DESTINATION).resolve()));h['authorization_ref']='ISOLATED_TEST_HUMAN';repin(state)
    monkeypatch.setattr(run.subprocess,'check_output',lambda cmd,**kw:'ISOLATED_TEST_SHA\n' if cmd[1]=='rev-parse' else b'')
    calls=[]
    def transport(**kwargs):
        def handler(req):calls.append(1);return httpx.Response(200,stream=httpx.ByteStream(run.canonical_json(envelope(p['requests'][0]))))
        return httpx.MockTransport(handler)
    monkeypatch.setattr(httpx,'HTTPTransport',transport)
    clock.wall+=timedelta(hours=1)
    for root in roots:
        store=root/run.DESTINATION;store.mkdir(parents=True)
        with warehouse_connection(store/'capture.duckdb') as db:
            if root is roots[0]:assert run.capture(root,db,store,p,a,h,p['requests'][0]['member_id'],TOKEN,live=True,clock=clock)['status']=='COMPLETE'
            else:
                with pytest.raises(ValueError,match='MATCHED_REVIEW_REQUIRED'):run.capture(root,db,store,p,a,h,p['requests'][0]['member_id'],TOKEN,live=True,clock=clock)
                assert run.layout(db)==[]
    assert len(calls)==1
