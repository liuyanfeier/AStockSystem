"""No-network regressions for the actual dedicated HTTP/SQL/file path."""

import copy
import json
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from astock.data import admission_metadata as proposal, admission_metadata_live as live
from astock.data.warehouse_lock import warehouse_connection

ROOT = Path(__file__).parents[1]
PLAN = ROOT / 'data/private/phase1c1-admission-a-evidence/2026-10-04/szse-metadata-plan-v1.json'
# CI has no private evidence: publish byte-identical pinned plan in the test temp root.
TOKEN = SecretStr('fixture-auth-value-not-a-real-credential')


class Clock(live.Clock):
    def __init__(self):
        self.wall = datetime(2031, 1, 1, tzinfo=timezone.utc)
        self.mono = 100.0
        self.boot_id = 'fixture-system-boot'
        self.sleeps = []

    def utc(self):
        self.wall += timedelta(microseconds=1)
        return self.wall

    def monotonic(self):
        return self.mono

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.wall += timedelta(seconds=seconds)
        self.mono += seconds

    def boot(self):
        return self.boot_id


def setup(tmp_path):
    plan = proposal.build_plan(ROOT)
    path = tmp_path / 'plan.json'
    # Original file uses sorted keys and indent=2, final newline.
    path.write_text(json.dumps(plan, sort_keys=True, indent=2)+'\n')
    assert live.sha256(path) == live.PLAN_BYTES
    license = live.license_template(ROOT, subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    t = datetime.now(timezone.utc).isoformat()
    license.update(namespace='CANDIDATE_REHEARSAL_ONLY', execution_license=True,
                   review_ref='CANDIDATE_REHEARSAL_ONLY:offline-test', reviewed_at=t,
                   user_authorization_ref='CANDIDATE_REHEARSAL_ONLY:synthetic', user_authorized_at=t)
    return plan, path, license, Clock()


def body(member):
    start = proposal._day(member['wire']['params']['start_date'])
    return dict(request_id='fixture-provider-receipt', code=0, msg='', data=dict(fields=proposal.FIELDS, items=[
        ['SZSE', (start+timedelta(days=i)).strftime('%Y%m%d'), 1,
         (start+timedelta(days=i-1)).strftime('%Y%m%d')]
        for i in range(member['expected_civil_rows'])]))


def send(db, store, state, *, i=0, handler=None, **kwargs):
    plan, path, license, clock = state
    return live.capture(ROOT, db, store, path, license, plan['requests'][i]['request_id'], TOKEN,
                        live=True, fixture=True, transport=httpx.MockTransport(handler or
                        (lambda req: httpx.Response(200, json=body(plan['requests'][i])))), clock=clock, **kwargs)


@pytest.mark.parametrize('pin', ['schema', 'plan_hash', 'plan_bytes_hash', 'membership_hash',
                                'contract_bytes_hash', 'implementation_sha', 'design_hash',
                                'namespace', 'review_ref', 'reviewed_at', 'user_authorization_ref',
                                'user_authorized_at', 'execution_license'])
def test_missing_or_wrong_license_stops_before_http(tmp_path, pin):
    state = setup(tmp_path); state[2][pin] = False if pin == 'execution_license' else None
    calls = []
    store = tmp_path / 'store'; store.mkdir()
    with warehouse_connection(store/'metadata.duckdb') as db:
        with pytest.raises((ValueError, TypeError)):
            send(db, store, state, handler=lambda req: calls.append(req))
    assert not calls
    assert not list(store.glob('*/*'))


def test_plan_mutation_unknown_member_and_no_explicit_live_stop(tmp_path):
    state = setup(tmp_path); store = tmp_path/'store'; store.mkdir(); calls=[]
    with warehouse_connection(store/'metadata.duckdb') as db:
        with pytest.raises(ValueError, match='UNKNOWN_EXACT_MEMBER'):
            live.capture(ROOT,db,store,state[1],state[2],'f'*64,TOKEN,live=True,fixture=True,
                         transport=httpx.MockTransport(lambda req:calls.append(req)))
        with pytest.raises(ValueError, match='LICENSE_REQUIRED'):
            live.capture(ROOT,db,store,state[1],state[2],state[0]['requests'][0]['request_id'],TOKEN,
                         fixture=True,transport=httpx.MockTransport(lambda req:calls.append(req)))
        state[1].write_text('{}')
        with pytest.raises(ValueError,match='PLAN_BYTES_CHANGED'):send(db,store,state,handler=lambda req:calls.append(req))
    assert not calls


def test_seven_exact_wire_sql_bytes_reopen_no_resend_and_distinct_times(tmp_path):
    state=setup(tmp_path); store=tmp_path/'store';store.mkdir();calls=[]
    def handler(req):
        calls.append(req)
        assert str(req.url)=='https://api.tushare.pro' and req.method=='POST'
        wire=json.loads(req.content);assert set(wire)=={'api_name','params','fields','token'}
        assert wire['token']==TOKEN.get_secret_value()
        member=next(m for m in state[0]['requests'] if m['wire']['params']==wire['params'])
        assert wire['api_name']=='trade_cal' and wire['fields']==','.join(proposal.FIELDS)
        return httpx.Response(200,json=body(member))
    with warehouse_connection(store/'metadata.duckdb') as db:
        for i in range(7):assert send(db,store,state,i=i,handler=handler)['status']=='COMPLETE'
        before=db.execute('SELECT * FROM metadata_event ORDER BY request_id,ordinal').fetchall()
        receipt=db.execute('SELECT * FROM metadata_receipt ORDER BY request_id').fetchall()
        assert len(receipt)==7 and len(before)==28
        for member in state[0]['requests']:
            directory=store/member['request_id'];source=json.loads((directory/'http-source.json').read_text())
            times=[source[k] for k in ('created_at','claimed_at','call_entered_at','finished_at','retrieved_at','available_at')]
            assert len(set(times))==6 and times==sorted(times)
            assert (directory/'response.body').read_bytes()!=live.canonical_json(json.loads((directory/'response.body').read_bytes())['data'])
        assert len(state[3].sleeps)==6 and sum(state[3].sleeps)>7.49
    hashes={str(p):live.sha256(p) for p in store.rglob('*') if p.is_file() and not p.name.endswith('.lock')}
    with warehouse_connection(store/'metadata.duckdb') as db:
        for i in range(7):assert send(db,store,state,i=i,handler=lambda req:pytest.fail('resend'))['status']=='ALREADY_VALID'
        assert db.execute('SELECT * FROM metadata_event ORDER BY request_id,ordinal').fetchall()==before
        assert db.execute('SELECT * FROM metadata_receipt ORDER BY request_id').fetchall()==receipt
    assert hashes=={str(p):live.sha256(p) for p in store.rglob('*') if p.is_file() and not p.name.endswith('.lock')}
    assert len(calls)==7
    for p in store.rglob('*'):
        if p.is_file():assert TOKEN.get_secret_value().encode() not in p.read_bytes()


@pytest.mark.parametrize('kind',['http','permission','redirect','timeout','malformed','partial','secret','escaped-secret','truncated','encoded'])
def test_errors_consume_one_attempt_stop_plan_and_no_cross_run_reset(tmp_path,kind):
    state=setup(tmp_path);store=tmp_path/'store';store.mkdir();calls=[]
    def handler(req):
        calls.append(req)
        if kind=='timeout':raise httpx.ReadTimeout('fixture error echoes '+TOKEN.get_secret_value())
        if kind=='http':return httpx.Response(503,content=b'provider unavailable')
        if kind=='redirect':return httpx.Response(302,headers={'location':'https://invalid.test/steal'},content=b'redirect')
        if kind=='malformed':return httpx.Response(200,content=b'{')
        value=body(state[0]['requests'][0]);headers={}
        if kind=='permission':value['code']=2002;value['msg']='permission denied'
        if kind=='partial':value['data']['items'].pop()
        if kind in ('secret','escaped-secret'):value['msg']=TOKEN.get_secret_value()
        content=json.dumps(value).encode()
        if kind=='escaped-secret':content=content.replace(TOKEN.get_secret_value().encode(),''.join('\\u%04x'%ord(c) for c in TOKEN.get_secret_value()).encode())
        if kind=='truncated':headers['content-length']=str(len(content)+1)
        if kind=='encoded':headers['content-encoding']='identity-wrong'
        return httpx.Response(200,content=content,headers=headers)
    with warehouse_connection(store/'metadata.duckdb') as db:
        with pytest.raises(ValueError):send(db,store,state,handler=handler)
        assert db.execute("SELECT count(*) FROM metadata_event WHERE state='CLAIMED'").fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM metadata_receipt').fetchone()[0]==0
        with pytest.raises(ValueError):send(db,store,state,handler=handler)
        with pytest.raises(ValueError,match='PLAN_STOPPED'):send(db,store,state,i=1,handler=handler)
    with warehouse_connection(store/'metadata.duckdb') as db:
        with pytest.raises(ValueError):send(db,store,state,handler=handler)
    assert len(calls)==1
    for p in store.rglob('*'):
        if p.is_file():assert TOKEN.get_secret_value().encode() not in p.read_bytes()


@pytest.mark.parametrize('stage', ['after_claim','after_call_entered','after_body','after_source','after_typed',
                                  'after_manifest','after_sidecar','after_registration','before_completion_commit'])
def test_fault_reopen_reconciles_exact_evidence_only_without_resend(tmp_path,stage):
    state=setup(tmp_path);store=tmp_path/'store';store.mkdir();calls=[]
    def fault(s):
        if s==stage:raise RuntimeError('synthetic crash')
    def handler(req):calls.append(req);return httpx.Response(200,json=body(state[0]['requests'][0]))
    with warehouse_connection(store/'metadata.duckdb') as db:
        with pytest.raises(RuntimeError):send(db,store,state,handler=handler,fault=fault)
    with warehouse_connection(store/'metadata.duckdb') as db:
        if stage in ('after_claim','after_call_entered','after_body'):
            with pytest.raises(ValueError):send(db,store,state,handler=lambda req:pytest.fail('resend'))
            with pytest.raises(ValueError):send(db,store,state,i=1,handler=lambda req:pytest.fail('resend'))
        else:
            assert send(db,store,state,handler=lambda req:pytest.fail('resend'))['status']=='COMPLETE'
            assert send(db,store,state,handler=lambda req:pytest.fail('resend'))['status']=='ALREADY_VALID'
    assert len(calls)==(0 if stage in ('after_claim','after_call_entered') else 1)


@pytest.mark.parametrize('kind',['body','source','uuid','manifest','zero-manifest','orphan','receipt','missing-sidecar','symlink','hardlink'])
def test_completed_evidence_tamper_cannot_validate_or_send_another_member(tmp_path,kind):
    state=setup(tmp_path);store=tmp_path/'store';store.mkdir()
    with warehouse_connection(store/'metadata.duckdb') as db:
        send(db,store,state)
        d=store/state[0]['requests'][0]['request_id']
        if kind=='body':(d/'response.body').write_bytes(b'{}')
        elif kind in ('source','uuid'):
            value=json.loads((d/'http-source.json').read_text());value['object_id' if kind=='uuid' else 'available_at']='different';(d/'http-source.json').write_text(json.dumps(value))
        elif kind=='manifest':(d/'manifest.json').write_text('{}')
        elif kind=='zero-manifest':(d/'manifest.json').write_bytes(b'')
        elif kind=='orphan':(d/'unexpected.part').write_bytes(b'orphan')
        elif kind=='receipt':db.execute("UPDATE metadata_receipt SET manifest_hash='faked'")
        elif kind=='missing-sidecar':(d/'metadata.json').unlink()
        elif kind=='symlink':
            p=d/'metadata.json';v=p.read_bytes();p.unlink();other=tmp_path/'other';other.write_bytes(v);p.symlink_to(other)
        elif kind=='hardlink':__import__('os').link(d/'metadata.json',tmp_path/'hardlinked')
        with pytest.raises(ValueError):send(db,store,state,handler=lambda req:pytest.fail('HTTP'))
        with pytest.raises(ValueError):send(db,store,state,i=1,handler=lambda req:pytest.fail('HTTP'))


def test_readonly_escaped_wrong_owner_and_fixture_production_refusal(tmp_path):
    state=setup(tmp_path);store=tmp_path/'store';store.mkdir()
    with warehouse_connection(store/'metadata.duckdb') as db:send(db,store,state)
    with pytest.raises(ValueError):send(db,store,state)
    with warehouse_connection(store/'metadata.duckdb',read_only=True) as ro:
        with pytest.raises(ValueError):send(ro,store,state)
    with warehouse_connection(tmp_path/'foreign.duckdb') as foreign:
        with pytest.raises(ValueError,match='STORE_OWNER'):send(foreign,store,state)
    with pytest.raises(ValueError):live.validate_license(ROOT,state[1],state[2],live=True,fixture=False)
    with warehouse_connection(store/'metadata.duckdb') as db:
        with pytest.raises(ValueError,match='INJECTED_TRANSPORT'):
            live.capture(ROOT,db,store,state[1],state[2],state[0]['requests'][0]['request_id'],TOKEN,
                         live=True,transport=httpx.MockTransport(lambda req:pytest.fail('HTTP')))


def test_competitor_cannot_claim_or_call_during_http(tmp_path):
    state=setup(tmp_path);store=tmp_path/'store';store.mkdir();errors=[]
    def competitor():
        try:
            with warehouse_connection(store/'metadata.duckdb') as db:send(db,store,state,i=1)
        except ValueError as e:errors.append(type(e).__name__)
    def handler(req):
        t=threading.Thread(target=competitor);t.start();t.join()
        assert errors
        return httpx.Response(200,json=body(state[0]['requests'][0]))
    with warehouse_connection(store/'metadata.duckdb') as db:
        send(db,store,state,handler=handler)
        assert db.execute("SELECT count(*) FROM metadata_event WHERE state='CLAIMED'").fetchone()[0]==1


@pytest.mark.parametrize('kind',['wall-back','mono-back','wall-fast','new-boot','no-sleep'])
def test_persistent_pacing_on_restart_and_clock_anomalies(tmp_path,kind):
    state=setup(tmp_path);store=tmp_path/'store';store.mkdir();calls=[]
    with warehouse_connection(store/'metadata.duckdb') as db:send(db,store,state)
    clock=state[3]
    if kind=='wall-back':clock.wall-=timedelta(seconds=10)
    elif kind=='mono-back':clock.mono-=20
    elif kind=='wall-fast':clock.wall+=timedelta(days=1)
    elif kind=='new-boot':clock.boot_id='new-boot';clock.mono=0
    elif kind=='no-sleep':clock.sleep=lambda seconds:None
    with warehouse_connection(store/'metadata.duckdb') as db:
        if kind in ('wall-back','mono-back','no-sleep'):
            with pytest.raises(ValueError):send(db,store,state,i=1,handler=lambda req:calls.append(req))
            assert not calls
        else:
            send(db,store,state,i=1)
            assert clock.sleeps[-1]>=1.249


def test_duplicate_json_and_nonfinite_provider_envelope_rejected(tmp_path):
    state=setup(tmp_path);store=tmp_path/'store';store.mkdir()
    with warehouse_connection(store/'metadata.duckdb') as db:
        value=json.dumps(body(state[0]['requests'][0])).replace('"code": 0','"code": 1, "code": 0')
        with pytest.raises(ValueError):send(db,store,state,handler=lambda req:httpx.Response(200,content=value.encode()))
        assert not db.execute('SELECT * FROM metadata_receipt').fetchall()
    with pytest.raises(ValueError):live.strict_json(b'{"data":NaN}')


def test_schema_constraints_and_store_namespace_cannot_reset_budget(tmp_path):
    state=setup(tmp_path);store=tmp_path/'store';store.mkdir()
    with warehouse_connection(store/'metadata.duckdb') as db:
        send(db,store,state)
        db.execute('ALTER TABLE metadata_receipt ADD COLUMN unexpected INTEGER')
        with pytest.raises(ValueError,match='STORE_SCHEMA'):send(db,store,state,i=1,handler=lambda req:pytest.fail('HTTP'))
    other=tmp_path/'other';other.mkdir()
    with warehouse_connection(other/'metadata.duckdb') as db:
        send(db,other,state)
        db.execute("UPDATE metadata_pin SET payload='{}'")
        with pytest.raises(ValueError,match='NO_BUDGET_RESET'):send(db,other,state,i=1,handler=lambda req:pytest.fail('HTTP'))


def test_original_destination_and_symlink_ancestors_refused_before_publish(tmp_path):
    store=tmp_path/'linked';other=tmp_path/'other';other.mkdir();store.symlink_to(other,target_is_directory=True)
    with pytest.raises(ValueError,match='SYMLINK'):live.safe_path(tmp_path,store/'metadata.duckdb')
    with pytest.raises(ValueError,match='ESCAPE'):live.safe_path(other,tmp_path/'outside')


def test_production_http_constructor_explicitly_disables_environment_and_retries(tmp_path,monkeypatch):
    state=setup(tmp_path);root=tmp_path/'project';root.mkdir()
    store=root/live.DESTINATION;store.mkdir(parents=True)
    license=copy.deepcopy(state[2]);license['namespace']='PRODUCTION'
    constructors=[]
    def http_transport(**kwargs):
        constructors.append(kwargs)
        assert kwargs==dict(retries=0,trust_env=False)
        return httpx.MockTransport(lambda req:httpx.Response(200,json=body(state[0]['requests'][0])))
    # Isolate only constructor/wire behavior; exact approval rejection has separate tests.
    monkeypatch.setattr(live,'validate_license',lambda *a,**k:state[0])
    monkeypatch.setattr(httpx,'HTTPTransport',http_transport)
    with warehouse_connection(store/'metadata.duckdb') as db:
        result=live.capture(root,db,store,state[1],license,state[0]['requests'][0]['request_id'],TOKEN,live=True,clock=state[3])
        assert result['status']=='COMPLETE'
    assert constructors==[dict(retries=0,trust_env=False)]
