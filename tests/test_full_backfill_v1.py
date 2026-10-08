"""Closed fake HTTP on the new runner, not the accepted synthetic-only transport."""
import copy
import json
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pyarrow.parquet as pq
import pytest
from pydantic import SecretStr

from astock.data import full_backfill_v1 as run
from astock.data.warehouse_lock import warehouse_connection

ROOT = Path(__file__).parents[1]
TOKEN = SecretStr('closed-test-value-no-real-account')


class Clock(run.Clock):
    def __init__(self):
        self.wall = datetime.now(timezone.utc) + timedelta(seconds=1)
        self.mono = 100.0
        self.sleeps = []
        self.boot_id = 'test-boot'

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


@pytest.fixture(autouse=True)
def no_real_sockets(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('Real socket forbidden in runner tests')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def setup(tmp_path, dataset='daily', count=2):
    c = json.loads((ROOT / run.CATALOG).read_bytes())[dataset]
    requests = []
    for day in range(1, count + 1):
        m = dict(dataset=dataset, params={'trade_date': f'202501{day:02}'}, fields=c['required_fields'],
                 contract_bytes_hash=c['contract_bytes_hash'], completeness_evidence=None, empty_evidence=None)
        m['member_id'] = run.logical_id(m); requests.append(m)
    plan = dict(protocol=run.PROTOCOL, namespace='FIXTURE', execution_license=False,
                requests=requests, membership_hash=run.checksum(requests), max_attempts=1,
                budget=count, pins=run.pins(ROOT), approval_descriptors=None, historical_PIT_eligible=False, prior_failed_logical_members=[])
    now = datetime.now(timezone.utc).isoformat()
    approval = dict(protocol=run.PROTOCOL, namespace='FIXTURE', plan_hash=run.checksum(plan), membership_hash=plan['membership_hash'],
                    pins=plan['pins'], budget=count, implementation_sha='fixture-code', review_ref='FIXTURE:review',
                    reviewed_at=now, execution_license=True)
    human = dict(protocol=run.PROTOCOL, namespace='FIXTURE', approval_hash=run.checksum(approval),
                 authorization_ref='FIXTURE:human', authorized_at=now, execution_license=True)
    store = tmp_path / 'store'; store.mkdir()
    return plan, approval, human, store, Clock()


def envelope(m, rows=1):
    catalog = json.loads((ROOT / run.CATALOG).read_bytes())[m['dataset']]
    fields = m['fields']; items = []
    for i in range(rows):
        values = {f: float(i + 1) if f in catalog['numeric_fields'] else i+1 if f in catalog['integer_fields'] else 'N' for f in fields}
        values.update(ts_code=f'T{i:05}.SH', trade_date=m['params']['trade_date'])
        if 'pre_close' in fields: values['pre_close'] = None
        items.append([values[f] for f in fields])
    return dict(request_id='closed-http-response-id', code=0, msg='', data=dict(fields=fields, items=items))


def send(db, state, index=0, handler=None, fault=lambda stage: None):
    p, a, h, s, clock = state
    handler = handler or (lambda req: httpx.Response(200, json=envelope(p['requests'][index])))
    return run.capture(ROOT, db, s, p, a, h, p['requests'][index]['member_id'], TOKEN,
                       fixture=True, live=True, transport=httpx.MockTransport(handler), clock=clock, fault=fault)


def test_plan_persistence_costs_zero_then_durable_calls_nonempty_native_and_null_reopen(tmp_path):
    state = setup(tmp_path); p, a, h, s, clock = state; observed = []
    with warehouse_connection(s / 'capture.duckdb') as db:
        run.initialize(ROOT, db, s, p)
        assert db.execute('SELECT count(*) FROM backfill_event').fetchone()[0] == 0
        def handler(req):
            observed.append(db.execute('SELECT state FROM backfill_event ORDER BY ordinal').fetchall())
            assert req.url == run.ENDPOINT and req.headers['accept-encoding'] == 'identity'
            return httpx.Response(200, json=envelope(p['requests'][0]))
        assert send(db, state, handler=handler)['status'] == 'COMPLETE'
    with warehouse_connection(s / 'capture.duckdb') as db:
        assert send(db, state, handler=lambda req: pytest.fail('resend'))['status'] == 'ALREADY_VALID'
        assert send(db, state, 1)['status'] == 'COMPLETE'
    assert observed == [[('CLAIMED',), ('CALL_ENTERED',)]] and sum(clock.sleeps) >= 1.25
    t = pq.read_table(s / p['requests'][0]['member_id'] / 'typed.parquet').to_pylist()
    assert t[0]['ts_code'] == 'T00000.SH' and t[0]['pre_close'] is None


@pytest.mark.parametrize('kind', ['cap', 'truncated', 'empty', 'permission', 'fields', 'type', 'date', 'duplicate', 'redirect', 'gzip', 'credential', 'encoded-credential'])
def test_bad_responses_terminal_global_stop_reopen_no_resend(tmp_path, kind):
    state = setup(tmp_path); p, a, h, s, clock = state; calls = []
    def handler(req):
        calls.append(1); body = envelope(p['requests'][0], 6000 if kind == 'cap' else 0 if kind == 'empty' else 1)
        headers = {}; status = 200
        if kind == 'truncated': headers['content-length'] = '1'
        if kind == 'permission': body['code'] = 2002
        if kind == 'fields': body['data']['fields'][0] = 'not_code'
        if kind == 'type': body['data']['items'][0][2] = 'not-a-number'
        if kind == 'date': body['data']['items'][0][1] = '20200101'
        if kind == 'duplicate': body['data']['items'] *= 2
        if kind == 'redirect': status = 302
        if kind == 'gzip': headers['content-encoding'] = 'gzip'; return httpx.Response(200, headers=headers, content=b'')
        if kind == 'credential': body['msg'] = TOKEN.get_secret_value()
        if kind == 'encoded-credential': body['msg'] = __import__('base64').b64encode(TOKEN.get_secret_value().encode()).decode()
        return httpx.Response(status, json=body, headers=headers)
    with warehouse_connection(s / 'capture.duckdb') as db:
        with pytest.raises(ValueError): send(db, state, handler=handler)
        assert db.execute('SELECT count(*) FROM backfill_receipt').fetchone()[0] == 0
    with warehouse_connection(s / 'capture.duckdb') as db:
        for index in (0, 1):
            with pytest.raises(ValueError): send(db, state, index, handler=lambda req: pytest.fail('resend'))
    assert calls == [1]


def test_unknown_remote_is_not_provider_rejection_and_consumed(tmp_path):
    state = setup(tmp_path); s = state[3]
    def handler(req): raise httpx.ReadTimeout('synthetic ambiguous delivery')
    with warehouse_connection(s / 'capture.duckdb') as db:
        with pytest.raises(ValueError, match='TRANSPORT_UNKNOWN_NO_RESEND'): send(db, state, handler=handler)
        assert run.events(db, state[0]['requests'][0]['member_id'])[-1][0] == 'UNCERTAIN'
    with warehouse_connection(s / 'capture.duckdb') as db:
        with pytest.raises(ValueError): send(db, state, handler=lambda req: pytest.fail('resend'))


@pytest.mark.parametrize('stage', ['after_claim', 'after_call_entered', 'after_body', 'after_source', 'after_typed', 'after_manifest', 'after_sidecar', 'after_registration', 'after_promotion'])
def test_publication_registration_promotion_failure_resume_without_http(tmp_path, stage):
    state = setup(tmp_path); s = state[3]; calls = []
    def fault(value):
        if value == stage: raise RuntimeError('fixture-local-fault')
    def handler(req): calls.append(1); return httpx.Response(200, json=envelope(state[0]['requests'][0]))
    with warehouse_connection(s / 'capture.duckdb') as db:
        with pytest.raises(RuntimeError): send(db, state, handler=handler, fault=fault)
        assert db.execute('SELECT count(*) FROM backfill_receipt').fetchone()[0] == 0
    with warehouse_connection(s / 'capture.duckdb') as db:
        if stage in ('after_claim', 'after_call_entered', 'after_body'):
            with pytest.raises(ValueError): send(db, state, handler=lambda req: pytest.fail('resend'))
            with pytest.raises(ValueError): send(db, state, 1, handler=lambda req: pytest.fail('resend'))
        else:
            assert send(db, state, handler=lambda req: pytest.fail('resend'))['status'] == 'COMPLETE'
            assert send(db, state, handler=lambda req: pytest.fail('resend'))['status'] == 'ALREADY_VALID'
    assert len(calls) == (0 if stage in ('after_claim', 'after_call_entered') else 1)


@pytest.mark.parametrize('kind', ['body', 'source', 'uuid', 'typed', 'manifest', 'zero-manifest', 'sidecar', 'orphan', 'receipt', 'promotion', 'missing', 'symlink', 'hardlink'])
def test_tampered_complete_blocks_existing_and_next_member(tmp_path, kind):
    state = setup(tmp_path); p, a, h, s, clock = state
    with warehouse_connection(s / 'capture.duckdb') as db:
        send(db, state); d = s / p['requests'][0]['member_id']
        if kind == 'body': (d / 'response.body').write_bytes(b'{}')
        elif kind in ('source', 'uuid'):
            v = json.loads((d / 'http-source.json').read_bytes()); v['object_id' if kind == 'uuid' else 'available_at'] = 'changed'; (d / 'http-source.json').write_text(json.dumps(v))
        elif kind in ('typed', 'manifest', 'zero-manifest', 'sidecar'): (d / {'typed':'typed.parquet','manifest':'manifest.json','zero-manifest':'manifest.json','sidecar':'sidecar.json'}[kind]).write_bytes(b'' if kind == 'zero-manifest' else b'bad')
        elif kind == 'orphan': (d / 'unexpected').write_bytes(b'orphan')
        elif kind == 'receipt': db.execute("UPDATE backfill_receipt SET manifest_hash='fake'")
        elif kind == 'promotion': db.execute("UPDATE backfill_event SET payload='{}' WHERE state='COMPLETE'")
        elif kind == 'missing': (d / 'manifest.json').unlink()
        elif kind == 'symlink':
            x = tmp_path / 'elsewhere'; x.write_bytes((d / 'sidecar.json').read_bytes()); (d / 'sidecar.json').unlink(); (d / 'sidecar.json').symlink_to(x)
        elif kind == 'hardlink': __import__('os').link(d / 'sidecar.json', tmp_path / 'hardlink')
        for index in (0, 1):
            with pytest.raises(ValueError): send(db, state, index, handler=lambda req: pytest.fail('HTTP forbidden'))


@pytest.mark.parametrize('kind', ['budget', 'pins', 'human', 'review', 'fixture-label', 'run-renaming', 'prior-failed', 'contract', 'production-injection'])
def test_licenses_membership_pins_budget_and_rename_cannot_escape(tmp_path, kind):
    state = setup(tmp_path); p, a, h, s, clock = state
    with warehouse_connection(s / 'capture.duckdb') as db:
        run.initialize(ROOT, db, s, p)
        if kind == 'budget': p['budget'] = 1
        elif kind == 'pins': p['pins'][run.SOURCE] = '0' * 64
        elif kind == 'human': h['approval_hash'] = 'fake'
        elif kind == 'review': a['execution_license'] = False
        elif kind == 'fixture-label': a['review_ref'] = 'actual reviewer'
        elif kind == 'run-renaming': p['run_name'] = 'try again'
        elif kind == 'prior-failed': p['prior_failed_logical_members'] = [p['requests'][0]['member_id']]
        elif kind == 'contract': p['requests'][0]['contract_bytes_hash'] = '0' * 64
        elif kind == 'production-injection': p['namespace'] = 'PRODUCTION'
        with pytest.raises(ValueError): send(db, state, handler=lambda req: pytest.fail('HTTP forbidden'))
        assert db.execute('SELECT count(*) FROM backfill_event').fetchone()[0] == 0


def test_changed_persisted_plan_and_orphan_cannot_reset_budget(tmp_path):
    state = setup(tmp_path); p, a, h, s, clock = state
    with warehouse_connection(s / 'capture.duckdb') as db:
        send(db, state)
        db.execute("UPDATE backfill_pin SET payload='{}'")
        with pytest.raises(ValueError): send(db, state, 1, handler=lambda req: pytest.fail('HTTP'))


def test_production_authorization_branch_closed_mock_with_exact_sha_pins_store_and_no_socket(tmp_path, monkeypatch):
    """Synthetic approvals in temp root ONLY: this is no actual production approval."""
    import shutil
    root = tmp_path / 'root'; root.mkdir()
    for rel in (run.SOURCE, run.DESIGN, run.CATALOG, run.DDL, 'config/contracts/v2/trade_cal.yaml'):
        dest = root / rel; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / rel, dest)
    state = setup(tmp_path); p, a, h, _, clock = state
    for m in p['requests']:
        rel = f"config/contracts/v2/{m['dataset']}.yaml"; dest = root / rel; dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / rel, dest)
    descriptors = [dict(request=m, purpose='ISOLATED_TEST_ONLY') for m in p['requests']]
    path = root / 'isolated-descriptors.json'; path.write_bytes(run.canonical_json(descriptors))
    p['approval_descriptors'] = dict(path=path.name, sha256=run.sha256(path), descriptor_hash=run.checksum(sorted(descriptors,key=lambda d:d['request']['member_id'])))
    p['namespace'] = a['namespace'] = h['namespace'] = 'PRODUCTION'
    a.update(plan_hash=run.checksum(p), pins=run.pins(root), implementation_sha='isolated-test-reviewed-SHA', review_ref='ISOLATED_TEST_NOT_REAL_REVIEW')
    h.update(approval_hash=run.checksum(a), authorization_ref='ISOLATED_TEST_NOT_REAL_HUMAN_LICENSE')
    store = root / run.DESTINATION; store.mkdir(parents=True)
    monkeypatch.setattr(run.subprocess, 'check_output', lambda cmd, **kw: 'isolated-test-reviewed-SHA\n' if cmd[1]=='rev-parse' else b'')
    calls = []
    def handler(req):
        calls.append(req)
        return httpx.Response(200, stream=httpx.ByteStream(run.canonical_json(envelope(p['requests'][0]))))
    def transport(**kwargs):
        assert kwargs == dict(retries=0, verify=True, trust_env=False)
        return httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, 'HTTPTransport', transport)
    with warehouse_connection(store / 'capture.duckdb') as db:
        result = run.capture(root, db, store, p, a, h, p['requests'][0]['member_id'], TOKEN, live=True, clock=clock)
        assert result['status'] == 'COMPLETE'
        assert run.capture(root, db, store, p, a, h, p['requests'][0]['member_id'], TOKEN, live=True, clock=clock)['status'] == 'ALREADY_VALID'
        with pytest.raises(ValueError): run.capture(root, db, store, p, a, h, p['requests'][1]['member_id'], TOKEN, live=False, clock=clock)
    assert len(calls) == 1


@pytest.mark.parametrize('kind', ['call-pacing', 'fake-db-uuid', 'event-gap', 'unknown-member', 'clock-rollback', 'boot-change'])
def test_durable_history_pacing_owner_and_unknown_member_boundaries(tmp_path, kind):
    state = setup(tmp_path); p, a, h, s, clock = state
    with warehouse_connection(s / 'capture.duckdb') as db:
        send(db, state)
        mid = p['requests'][0]['member_id']
        if kind == 'call-pacing':
            payload = json.loads(run.events(db, mid)[1][2]); payload['wall']='2000-01-01T00:00:00+00:00'; db.execute("UPDATE backfill_event SET payload=? WHERE state='CALL_ENTERED'", [json.dumps(payload)])
        elif kind == 'fake-db-uuid': db.execute("UPDATE backfill_receipt SET object_id='00000000-0000-0000-0000-000000000000' WHERE member_id=?", [mid])
        elif kind == 'event-gap': db.execute("UPDATE backfill_event SET ordinal=4 WHERE state='COMPLETE'")
        elif kind == 'unknown-member':
            with pytest.raises(ValueError): run.capture(ROOT, db, s, p, a, h, '0'*64, TOKEN, live=True, fixture=True, transport=httpx.MockTransport(lambda req: pytest.fail('HTTP')), clock=clock)
            return
        elif kind == 'clock-rollback': clock.wall -= timedelta(days=1)
        elif kind == 'boot-change':
            clock.boot_id = 'rebooted-test'; assert send(db, state, 1)['status']=='COMPLETE'; assert clock.sleeps[-1]>=1.25; return
        with pytest.raises(ValueError): send(db, state, 1, handler=lambda req: pytest.fail('HTTP'))


def test_calendar_incomplete_even_nonempty_is_rejected(tmp_path):
    c = json.loads((ROOT/run.CATALOG).read_bytes())['trade_cal']
    m = dict(dataset='trade_cal',params=dict(exchange='SZSE',start_date='20250101',end_date='20250102'),fields=c['required_fields'],contract_bytes_hash=c['contract_bytes_hash'],empty_evidence=None,completeness_evidence=None)
    m['member_id']=run.logical_id(m)
    body=dict(request_id='fixture',code=0,msg='',data=dict(fields=m['fields'],items=[['SZSE','20250101',0,'20241231']]))
    with pytest.raises(ValueError,match='INCOMPLETE_CIVIL_CALENDAR'):
        run.decoded_table(ROOT,m,run.canonical_json(body),datetime.now(timezone.utc).isoformat())


@pytest.mark.parametrize('dataset', ['daily','daily_basic','adj_factor','stk_limit','stock_st','suspend_d'])
def test_all_six_nonempty_source_scalar_types_native_ids_and_nullable_fields(tmp_path, dataset):
    state=setup(tmp_path,dataset=dataset,count=1)
    with warehouse_connection(state[3]/'capture.duckdb') as db:
        assert send(db,state)['status']=='COMPLETE'
    table=pq.read_table(state[3]/state[0]['requests'][0]['member_id']/'typed.parquet')
    assert table.num_rows==1 and table.to_pylist()[0]['ts_code']=='T00000.SH'
    if dataset=='stk_limit':assert str(table.schema.field('asset_type').type)=='string'
    if dataset=='stock_st':assert str(table.schema.field('type_name').type)=='string'
    if dataset=='daily_basic':assert str(table.schema.field('limit_status').type)=='int64'


def test_unclaimed_peer_directory_stops_plan_before_another_members_claim(tmp_path):
    state=setup(tmp_path);p,a,h,s,clock=state
    with warehouse_connection(s/'capture.duckdb') as db:
        run.initialize(ROOT,db,s,p)
        (s/p['requests'][1]['member_id']).mkdir()
        with pytest.raises(ValueError,match='ORPHAN_UNCLAIMED_MEMBER'):
            send(db,state,0,handler=lambda req:pytest.fail('No HTTP for another member'))
        assert db.execute('SELECT count(*) FROM backfill_event').fetchone()[0]==0
