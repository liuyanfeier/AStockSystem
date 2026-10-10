"""Raw-truth attacks, identity transitions and production-shaped CLOSED acceptance."""
from copy import deepcopy
from pathlib import Path
import json,shutil,socket
import httpx
import pytest
from pydantic import SecretStr
from astock.phase1 import acquisition as a,contracts as c,domains as d,fixtures as f,pipeline as p
from astock.phase1.core import PRODUCTION,Phase1Error,digest,encoded,file_hash,strict_json
from astock.phase1.__main__ import main
ROOT=Path(__file__).resolve().parents[1]
EMPTY=dict(records=[],original_paths={},original_hashes={})

@pytest.fixture(autouse=True)
def closed_network(monkeypatch):
    def deny(*a,**kw):raise AssertionError('REAL_NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket.socket,'connect',deny);monkeypatch.setattr(socket,'getaddrinfo',deny)

@pytest.fixture(scope='module')
def demo(tmp_path_factory):
    path=tmp_path_factory.mktemp('consolidated-demo')/'source'
    f.demo(ROOT,path)
    return path


def mutate_fact(db,kind):
    old=p.fact_rows(db);row=deepcopy(next(r for r in old if r['dataset']=='income' and r['payload']['ann_date']=='20250501'))
    if kind=='extra':row['payload']['basic_eps']=99.;row['available_at']=row['published_at']='2025-02-28T01:00:00+00:00'
    elif kind=='source_row':row['source_row']=99
    elif kind=='eligibility':row['eligibility']='PIT_APPROVED'
    elif kind=='time':row['available_at']=row['published_at']='2025-02-28T01:00:00+00:00'
    elif kind=='value':row['payload']['basic_eps']=99.
    else:assert kind=='delete'
    original=row.pop('fact_hash');row['fact_hash']=digest(row)
    if kind!='extra':
        a.transaction(db,lambda:db.execute('DELETE FROM p1_lineage WHERE fact_hash=?',[original]))
        a.transaction(db,lambda:db.execute('DELETE FROM p1_fact WHERE fact_hash=?',[original]))
    def tamper():
        if kind=='delete':pass
        else:
            keys=['fact_hash','dataset','domain','series_key','entity','event_date','valid_from','valid_to','published_at','available_at','retrieved_at','precision','knowledge_basis','source_object','source_row']
            values=[row[k] for k in keys]+[encoded(row['payload']).decode(),row['eligibility']]
            db.execute('INSERT INTO p1_fact VALUES ('+','.join('?' for _ in values)+')',values)
        remaining={r['fact_hash']:r for r in p.fact_rows(db)}
        for gh, in db.execute('SELECT generation_hash FROM p1_generation').fetchall():
            if kind!='delete':db.execute('INSERT INTO p1_lineage VALUES (?,?)',[gh,row['fact_hash']])
            hs=[h[0] for h in db.execute('SELECT fact_hash FROM p1_lineage WHERE generation_hash=? ORDER BY fact_hash',[gh]).fetchall()]
            db.execute('UPDATE p1_generation SET logical_content_hash=? WHERE generation_hash=?',[digest([remaining[h] for h in hs]),gh])
    a.transaction(db,tamper)

@pytest.mark.parametrize('kind',['extra','source_row','eligibility','time','value','delete'])
def test_self_consistent_mutations_block_all_consumers(demo,tmp_path,kind):
    dest=tmp_path/'derived';p.build(ROOT,dest,source_destination=demo)
    with a.store(ROOT,dest) as db:mutate_fact(db,kind)
    before=file_hash(dest/'catalog.duckdb')
    for fn in [lambda:p.query(ROOT,dest,'S1','2025-03-01','2025-03-01T10:00:00Z'),lambda:p.coverage(ROOT,dest),lambda:p.build(ROOT,dest),lambda:p.build(ROOT,tmp_path/'new',source_destination=dest)]:
        with pytest.raises(Phase1Error,match='SOURCE_DERIVED'):fn()
    for argv in [['audit'],['adjust','--native','000001.SZ','--event-date','2025-01-02','--anchor','2025-01-06','--as-of','2025-06-02T00:00:00Z'],['reference','--native','000300.SH','--event-date','2025-01-02','--as-of','2025-06-02T00:00:00Z']]:
        assert main(['--root',str(ROOT),argv[0],'--destination',str(dest),*argv[1:]])==1
    from astock.phase1.application import expand_market
    with pytest.raises(Phase1Error,match='SOURCE_DERIVED'):expand_market(ROOT,dest,EMPTY,start='2025-01-01',end='2025-01-10',budget=60)
    assert file_hash(dest/'catalog.duckdb')==before


def test_quality_rederived_and_old_generations_preserved(demo,tmp_path):
    dest=tmp_path/'derived';p.build(ROOT,dest,source_destination=demo)
    with a.store(ROOT,dest) as db:
        q=dict(dataset='income',entity='000001.SZ',event_date='2024-12-31',reason='AUTHOR_FAKE',source_object='none')
        a.transaction(db,lambda:db.execute('INSERT INTO p1_quality VALUES (?,?,?,?,?,?,?)',[digest(q),q['dataset'],q['entity'],q['event_date'],q['reason'],q['source_object'],encoded(q).decode()]))
    with pytest.raises(Phase1Error,match='SOURCE_DERIVED_QUALITY'):p.coverage(ROOT,dest)


def capture_fixture(dest,members,payloads,packages):
    def handler(q):
        w=strict_json(q.content);return httpx.Response(200,content=encoded(payloads[(w['api_name'],encoded(w['params']))]))
    plan=a.make_plan(ROOT,dest,members,EMPTY,fixture=True)
    run=a.run_batch(ROOT,dest,plan,EMPTY,token=SecretStr('closed-transition'),transport=httpx.MockTransport(handler),clock=f.FixtureClock())
    assert run['status']=='RAW_BATCH_VALID';p.import_evidence(ROOT,dest,packages);p.build(ROOT,dest)

@pytest.mark.parametrize('new_native',[False,True])
def test_four_financial_domains_cross_native_and_cutoffs(tmp_path,new_native):
    members,payloads,packages=f.sample_inputs(ROOT)
    for package in packages:
        if package['request']['dataset']=='security_identifiers':
            rows=c.decode(ROOT,package['request'],encoded(package['response']))['rows'];old=next(r for r in rows if r['security_id']=='S1');old['valid_to']='20250106'
            rows.append(dict(old,identifier='000777.SZ',valid_from='20250106',valid_to=None));package['response']=f.response(package['request'],rows)
    if new_native:
        rewritten={}
        for member in members:
            old_key=(member['dataset'],encoded(member['params']));value=payloads[old_key]
            if member['dataset'] in c.FINANCIAL:
                value=deepcopy(value);value['data']['items'][0][member['fields'].index('ts_code')]='000777.SZ';member['params']['ts_code']='000777.SZ'
                member['metadata']['financial_identity_basis']=dict(dataset=member['dataset'],source='TUSHARE',basis='PUBLICATION_NATIVE',evidence_hash='a'*64)
            rewritten[(member['dataset'],encoded(member['params']))]=value
        payloads=rewritten
    dest=tmp_path/'fixture';capture_fixture(dest,members,payloads,packages)
    for event in ('2025-01-02','2025-05-15'):
        assert len(p.query(ROOT,dest,'S1',event,'2025-03-31T10:00:00Z')['domains']['financial'])==0
        first=p.query(ROOT,dest,'S1',event,'2025-04-15T10:00:00Z')['domains']['financial'];second=p.query(ROOT,dest,'S1',event,'2025-05-15T10:00:00Z')['domains']['financial']
        assert {r['dataset'] for r in first}==c.FINANCIAL=={r['dataset'] for r in second}
        assert all(r['payload']['ann_date']=='20250401' for r in first) and all(r['payload']['ann_date']=='20250501' for r in second)


def test_default_coverage_and_frozen_target_staleness(demo,tmp_path):
    from astock.phase1 import coverage_targets as ct
    result=p.coverage(ROOT,demo);t=result['target_coverage']
    missing=[r for r in t['obligations'] if r['state']=='missing']
    assert any(r['dataset']=='daily' and r['event_date']=='2025-01-03' for r in missing)
    assert t['expected']>t['observed'] and t['uncertified']>0 and t['unknown_denominators']
    with a.store(ROOT,demo,read_only=True) as db:rows=p.fact_rows(db)
    custom=ct.target(rows,goals=[dict(dataset='income',entity='000001.SZ',event_date='2024-12-31',known_by='2025-03-01T00:00:00Z')]);assert ct.evaluate(rows,custom)['missing']>0
    vintage=ct.target(rows,goals=[dict(dataset='income',entity='000001.SZ',event_date='2024-12-31',known_by='2025-04-15T10:00:00Z',ann_date='20250401')])
    assert ct.evaluate(rows,vintage)['obligations'][-1]['state']=='observed'
    wrong=ct.target(rows,goals=[dict(dataset='income',entity='000001.SZ',event_date='2024-12-31',known_by='2025-04-15T10:00:00Z',ann_date='20250501')])
    assert ct.evaluate(rows,wrong)['obligations'][-1]['state']=='missing'
    custom['start']='2025-01-02'
    with pytest.raises(Phase1Error,match='TARGET_CHANGED'):ct.evaluate(rows,custom)
    stale=ct.target(rows);stale['facts_hash']='a'*64;stale['target_hash']=digest({k:v for k,v in stale.items() if k!='target_hash'})
    with pytest.raises(Phase1Error,match='TARGET_STALE'):ct.evaluate(rows,stale)
    out=tmp_path/'coverage.json';assert main(['--output',str(out),'coverage','--destination',str(demo)])==0
    assert strict_json(out.read_bytes())['target_coverage']['missing']>0


def test_frozen_v1_derivation_and_unregistered_version(demo):
    from astock.phase1 import versions
    v=versions.v1_registry(ROOT);cs,ds=versions.adapters(ROOT,v['pins'])
    assert cs is not c and ds is not d and cs.catalog(ROOT)==c.catalog(ROOT)
    with pytest.raises(Phase1Error,match='UNREGISTERED'):versions.validate(ROOT,{'fake':'a'*64})

@pytest.fixture(scope='module')
def production(tmp_path_factory):
    from astock.phase1.production_fixture import rehearsal
    root=tmp_path_factory.mktemp('test-production')/'root'
    return root,rehearsal(ROOT,root)


def test_closed_production_shape_rebuild_query_authorization(production):
    root,result=production
    assert result['closed_mock_calls']==35 and result['actual_market_API']==0 and result['original_SQL_writes']==0
    assert result['rebuild_a']['logical_content_hash']==result['rebuild_b']['logical_content_hash']==result['build']['logical_content_hash']
    assert len(result['financial_query']['domains']['financial'])==4 and result['source_bytes_unchanged']
    with a.store(root,root/PRODUCTION,read_only=True) as db:
        assert db.execute('SELECT count(*) FROM p1_authorization').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM p1_attempt WHERE authorization_hash IS NOT NULL').fetchone()[0]==35
        assert a.audit(root,root/PRODUCTION,db)['checked']==35
    derived=root/'derived-a'
    with a.store(root,derived,read_only=True) as db:
        owner=strict_json(db.execute("SELECT payload FROM p1_meta WHERE key='owner'").fetchone()[0].encode());assert owner['namespace']=='DERIVED_ONLY' and owner['source']['namespace']=='PRODUCTION'
    with pytest.raises(Phase1Error):a.owner(root,derived,False)


def test_authorization_registration_failure_prevents_all_http(tmp_path):
    from astock.phase1.production_fixture import rehearsal
    def fault(stage):
        if stage=='authorization_registered':raise RuntimeError('TEST_AUTH_STORE_FAILURE')
    root=tmp_path/'test-root'
    with pytest.raises(RuntimeError):rehearsal(ROOT,root,fault=fault)
    with a.store(root,root/PRODUCTION,read_only=True) as db:
        assert db.execute('SELECT count(*) FROM p1_plan').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM p1_authorization').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM p1_attempt').fetchone()[0]==0


def test_test_license_cannot_run_at_real_root(production):
    from astock.phase1.authorization import test_scope
    with pytest.raises(Phase1Error,match='CANONICAL_ROOT'):test_scope(ROOT,dict(test_only=True))

@pytest.mark.parametrize('mutation',['missing','false_license','evidence','attempt','event'])
def test_production_authorization_chain_tampering_fails(production,tmp_path,mutation):
    root,_=production
    # Copies are data mutation simulations bound to the original owner/root;
    # move only the catalog bytes back to a managed temporary connection.
    from astock.data.warehouse_lock import warehouse_connection
    dest=root/PRODUCTION;clone=tmp_path/'catalog.duckdb';shutil.copyfile(dest/'catalog.duckdb',clone)
    with warehouse_connection(clone) as db:
        if mutation=='missing':db.execute('DELETE FROM p1_authorization')
        elif mutation=='attempt':db.execute("UPDATE p1_attempt SET authorization_hash='changed'")
        elif mutation=='event':db.execute("UPDATE p1_event SET payload='{}' WHERE state='CLAIMED'")
        else:
            h,ph,payload=db.execute('SELECT * FROM p1_authorization').fetchone();record=strict_json(payload.encode())
            if mutation=='false_license':record['approval']['execution_license']=False
            else:record['approval']['evidence']['sha256']='b'*64
            db.execute('UPDATE p1_authorization SET payload=?',[encoded(record).decode()])
        with pytest.raises(Phase1Error):a.audit(root,dest,db)

@pytest.mark.parametrize('ambiguous',[False,True])
def test_reused_native_and_identity_conflict_keep_episode_boundary(tmp_path,ambiguous):
    members,payloads,packages=f.sample_inputs(ROOT)
    for package in packages:
        ds=package['request']['dataset'];rows=c.decode(ROOT,package['request'],encoded(package['response']))['rows']
        if ds=='security_identifiers':
            old=next(r for r in rows if r['security_id']=='S1');old['valid_to']='20250106'
            rows += [dict(old,identifier='000777.SZ',valid_from='20250106',valid_to=None),dict(old,security_id='S4',episode_id='E4',identifier='000777.SZ' if ambiguous else '000001.SZ',valid_from='20250107' if ambiguous else '20250106',valid_to=None)]
        if ds=='listing_episodes':
            ep=next(r for r in rows if r['security_id']=='S1');rows += [dict(ep,security_id='S4',episode_id='E4',list_date='20250106',valid_from='20250106')]
        package['response']=f.response(package['request'],rows)
    dest=tmp_path/'store';capture_fixture(dest,members,payloads,packages)
    queried=p.query(ROOT,dest,'S1','2025-05-15','2025-05-15T10:00:00Z')
    if ambiguous:
        assert not queried['domains']['financial'] and any('CONFLICT' in q['reason'] for q in queried['unknowns'])
    else:
        assert len(queried['domains']['financial'])==4
        assert not p.query(ROOT,dest,'S4','2025-05-15','2025-05-15T10:00:00Z')['domains']['financial']
        coverage=p.coverage(ROOT,dest)['target_coverage']
        assert any(r.get('security_id')=='S4' and r['state']=='missing' for r in coverage['obligations'])
        assert not any(r.get('security_id')=='S4' and r['event_date']<'2025-01-06' for r in coverage['obligations'])


def test_no_bar_full_suspension_and_missing_rule_industry_are_distinct(tmp_path):
    members,payloads,packages=f.sample_inputs(ROOT)
    members=[m for m in members if not (m['dataset']=='daily' and m['params']['trade_date']=='20250102')]
    packages=[p for p in packages if p['request']['dataset']!='rule_history']
    for package in packages:
        if package['request']['dataset']=='industry_membership':
            rows=c.decode(ROOT,package['request'],encoded(package['response']))['rows'];package['response']=f.response(package['request'],rows[:1])
    dest=tmp_path/'fixture';capture_fixture(dest,members,payloads,packages)
    report=p.coverage(ROOT,dest)['target_coverage']
    assert any(r['dataset']=='daily' and r['event_date']=='2025-01-02' and r['state']=='source_backed_not_applicable' for r in report['obligations'])
    assert any(r['dataset']=='daily' and r['event_date']=='2025-01-03' and r['state']=='missing' for r in report['obligations'])
    assert any(r['dataset']=='industry_membership' and r['event_date']=='2025-01-06' and r['state']=='missing' for r in report['obligations'])
    assert any(r['dataset']=='rule_history' and r['event_date']=='2025-01-06' and r['state']=='missing' for r in report['obligations'])


def test_frozen_v1_store_read_only_rebuild_and_reproof(tmp_path):
    import subprocess,sys,os
    from astock.phase1 import versions
    root=tmp_path/'v1-root';v=versions.v1_registry(ROOT)
    for name in v['pins']:
        dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/v['archive']/name,dest)
        archived=root/v['archive']/name;archived.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dest,archived)
    shutil.copyfile(ROOT/'config/phase1/frozen-v1.json',root/'config/phase1/frozen-v1.json')
    (root/'src/astock/__init__.py').write_text('__path__.append('+repr(str(ROOT/'src/astock'))+')\n')
    script="import socket; deny=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN')); socket.socket.connect=deny; socket.getaddrinfo=deny; from pathlib import Path; from astock.phase1.fixtures import demo; r=Path("+repr(str(root))+"); assert demo(r,r/'fixture')['build']['facts']==62"
    env=dict(os.environ,PYTHONPATH=str(root/'src'),TUSHARE_TOKEN='',PYTHONDONTWRITEBYTECODE='1')
    subprocess.run([sys.executable,'-c',script],env=env,cwd=root,check=True,capture_output=True)
    for name in a.pins(ROOT):
        dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    path=root/'fixture';before=file_hash(path/'catalog.duckdb')
    with a.store(root,path,read_only=True) as db:
        p.verify_generation_inputs(root,path,db);assert p.validate_lineage(db)['facts']==62
    rebuilt=p.build(root,root/'v2-derived',source_destination=path)
    assert rebuilt['facts']==62 and p.build(root,root/'v2-derived')['status']=='ALREADY_VALID'
    assert file_hash(path/'catalog.duckdb')==before
    with pytest.raises(Phase1Error,match='LEGACY_STORE_READ_ONLY'):
        with a.store(root,path):pass


def test_production_durable_authorized_claim_process_death(tmp_path):
    import os
    if not hasattr(os,'fork'):pytest.skip('POSIX lifecycle')
    from astock.phase1.production_fixture import rehearsal,licenses
    root=tmp_path/'death-root'
    pid=os.fork()
    if pid==0:
        def exit_after_claim(stage):
            if stage=='after_claim':os._exit(97)
        rehearsal(ROOT,root,fault=exit_after_claim)
        os._exit(98)
    _,status=os.waitpid(pid,0);assert os.waitstatus_to_exitcode(status)==97
    with a.store(root,root/PRODUCTION) as db:
        current=a.local_consumption(db);assert len(current)==1 and current[0]['states']==['CLAIMED']
        assert a.audit(root,root/PRODUCTION,db)['checked']==0
        assert db.execute('SELECT count(*) FROM p1_authorization').fetchone()[0]==1
    members,_,_=f.sample_inputs(root)
    for m in members:m['metadata'].pop('knowledge',None)
    consumed=current[0]['logical_id']
    remaining=[m for m in members if __import__('astock.phase1.core',fromlist=['logical_id']).logical_id(m)!=consumed]
    plan=a.make_plan(root,root/PRODUCTION,remaining,EMPTY,prior_consumption=current,resume_from=digest(current))
    review,human=licenses(root,root/PRODUCTION,plan)
    wrong=dict(review,plan_hash='changed')
    with pytest.raises(Phase1Error,match='APPROVAL_SCOPE_CHANGED'):
        a.run_batch(root,root/PRODUCTION,plan,EMPTY,token=SecretStr('closed-death'),approval=wrong,human=human,transport=httpx.MockTransport(lambda q:None),clock=f.FixtureClock())
