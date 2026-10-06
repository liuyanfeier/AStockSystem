"""Independent exact-plan capture. No original warehouse or bounded-client bypass."""

import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import UUID, uuid4

import duckdb
import httpx
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import SecretStr

from astock.data.admission_metadata_live import Clock, PATTERNS, instant, safe_path, stamp, strict_json
from astock.data.probe_audit import canonical_json
from astock.data.raw_validation import sha256
from astock.data.raw_writer import atomic_new_file
from astock.data.reconstruction import checksum, transaction
from astock.data.tushare_client import ProviderTable
from astock.data.warehouse_lock import require_writer, warehouse_connection

PROTOCOL = 'FULL_BACKFILL_CAPTURE_V1'
DESTINATION = 'data/private/full-backfill-v1'
DESIGN = 'docs/remediation/phase1c1/evidence-and-launch-preparation/full-backfill-runner-design-v1.md'
CATALOG = 'config/full_backfill_v1/catalog.json'
DDL = 'sql/offline/full_backfill_v1.sql'
SOURCE = 'src/astock/data/full_backfill_v1.py'
ENDPOINT = 'https://api.tushare.pro'
FILES = {'response.body', 'http-source.json', 'typed.parquet', 'manifest.json', 'sidecar.json'}


class BackfillError(ValueError):
    """Only fixed diagnostics cross the CLI/log boundary."""


def pins(root: Path) -> dict:
    return {p: sha256(root / p) for p in (SOURCE, DESIGN, CATALOG, DDL)}


def logical_id(request: dict) -> str:
    return checksum({k: request[k] for k in ('dataset', 'params', 'fields', 'contract_bytes_hash')})


def validate_plan(root: Path, plan: dict) -> dict:
    required = {'protocol', 'namespace', 'execution_license', 'requests', 'membership_hash',
                'max_attempts', 'budget', 'pins', 'historical_PIT_eligible', 'prior_failed_logical_members'}
    if (not isinstance(plan, dict) or set(plan) != required or plan['protocol'] != PROTOCOL
            or plan['namespace'] not in ('PROPOSED', 'FIXTURE', 'PRODUCTION')
            or plan['execution_license'] is not False or plan['historical_PIT_eligible'] is not False
            or plan['max_attempts'] != 1 or type(plan['max_attempts']) is not int
            or type(plan['budget']) is not int or plan['budget'] < 1 or plan['pins'] != pins(root)):
        raise BackfillError('PLAN_PIN_OR_SCOPE_INVALID')
    catalog = strict_json((root / CATALOG).read_bytes())
    requests = plan['requests']
    if (not isinstance(requests, list) or not requests or len(requests) > plan['budget']
            or plan['membership_hash'] != checksum(requests)
            or len({m['member_id'] for m in requests}) != len(requests)
            or not isinstance(plan['prior_failed_logical_members'], list)):
        raise BackfillError('MEMBERSHIP_OR_BUDGET_INVALID')
    for m in requests:
        if set(m) != {'member_id', 'dataset', 'params', 'fields', 'contract_bytes_hash',
                       'completeness_evidence', 'empty_evidence'} or m['dataset'] not in catalog:
            raise BackfillError('MEMBER_SCOPE_INVALID')
        c = catalog[m['dataset']]
        if (m['fields'] != c['required_fields'] or m['contract_bytes_hash'] != c['contract_bytes_hash']
                or sha256(root / c['contract_path']) != c['contract_bytes_hash']
                or m['member_id'] != logical_id(m) or not isinstance(m['params'], dict)):
            raise BackfillError('MEMBER_CONTRACT_INVALID')
        p = m['params']
        if m['dataset'] == 'trade_cal':
            if set(p) != {'exchange', 'start_date', 'end_date'} or p['exchange'] not in ('SSE', 'SZSE', 'BSE'):
                raise BackfillError('CALENDAR_SCOPE_INVALID')
            if p['start_date'] > p['end_date']:
                raise BackfillError('DATE_SCOPE_INVALID')
        elif m['dataset'] == 'stock_basic':
            if set(p) != {'exchange', 'list_status'} or p['exchange'] not in ('SSE', 'SZSE', 'BSE') or p['list_status'] not in ('L', 'D', 'P'):
                raise BackfillError('UNIVERSE_SCOPE_INVALID')
        elif set(p) not in ({'trade_date'}, {'trade_date', 'ts_code'}):
            raise BackfillError('MARKET_SCOPE_INVALID')
        for key, value in p.items():
            if key in ('trade_date', 'start_date', 'end_date'):
                if not isinstance(value, str) or not re.fullmatch(r'\d{8}', value):
                    raise BackfillError('DATE_SCOPE_INVALID')
                try:
                    datetime.strptime(value, '%Y%m%d')
                except ValueError:
                    raise BackfillError('DATE_SCOPE_INVALID') from None
            elif not isinstance(value, str) or not value or len(value) > 80:
                raise BackfillError('PARAM_SCOPE_INVALID')
        # Request renaming never licenses resending the old logical FAILED call.
        if m['member_id'] in plan['prior_failed_logical_members']:
            raise BackfillError('PRIOR_UNCERTAIN_NO_RESEND')
        for name in ('completeness_evidence', 'empty_evidence'):
            ev = m[name]
            if ev is not None:
                if set(ev) != {'path', 'sha256'} or not re.fullmatch(r'[0-9a-f]{64}', ev['sha256']):
                    raise BackfillError('MEMBER_EVIDENCE_INVALID')
                path = safe_path(root, root / ev['path'], exists=True)
                if sha256(path) != ev['sha256']:
                    raise BackfillError('MEMBER_EVIDENCE_CHANGED')
    return catalog


def authorize(root: Path, plan: dict, approval: dict, human: dict, *, fixture: bool, live: bool) -> None:
    validate_plan(root, plan)
    namespace = 'FIXTURE' if fixture else 'PRODUCTION'
    base = dict(protocol=PROTOCOL, namespace=namespace, plan_hash=checksum(plan),
                membership_hash=plan['membership_hash'], pins=pins(root), budget=plan['budget'])
    if (not isinstance(approval, dict) or set(approval) != set(base) | {'implementation_sha', 'review_ref', 'reviewed_at', 'execution_license'}
            or any(approval.get(k) != v for k, v in base.items())
            or approval['execution_license'] is not True or plan['namespace'] != namespace):
        raise BackfillError('MATCHED_REVIEW_REQUIRED')
    if (not isinstance(human, dict) or set(human) != {'protocol', 'namespace', 'approval_hash', 'authorization_ref', 'authorized_at', 'execution_license'}
            or human['protocol'] != PROTOCOL or human['namespace'] != namespace
            or human['approval_hash'] != checksum(approval) or human['execution_license'] is not True):
        raise BackfillError('MATCHED_HUMAN_AUTHORIZATION_REQUIRED')
    if not live or any(not isinstance(v, str) or not v.strip() for v in
                       (approval['review_ref'], human['authorization_ref'])):
        raise BackfillError('EXECUTION_NOT_AUTHORIZED')
    if not instant(approval['reviewed_at']) <= instant(human['authorized_at']) <= datetime.now(timezone.utc):
        raise BackfillError('APPROVAL_TIME_INVALID')
    if fixture:
        if not approval['review_ref'].startswith('FIXTURE:') or not human['authorization_ref'].startswith('FIXTURE:'):
            raise BackfillError('FIXTURE_LABEL_REQUIRED')
    else:
        if any('FIXTURE' in v or 'PROPOSED' in v for v in (approval['review_ref'], human['authorization_ref'])):
            raise BackfillError('FIXTURE_CANNOT_AUTHORIZE_PRODUCTION')
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        if approval['implementation_sha'] != head or subprocess.check_output(['git', 'status', '--porcelain'], cwd=root):
            raise BackfillError('IMPLEMENTATION_NOT_REVIEWED')
        # Require an exhaustive historical consumption inventory from the matched review.
        # A newly authored plan cannot bypass the fixed FAILED metadata member by omitting it.
        from astock.data.admission_metadata import build_plan
        old = build_plan(root)['requests'][0]['wire']
        for m in plan['requests']:
            if (m['dataset'], m['params'], ','.join(m['fields'])) == (old['api_name'], old['params'], old['fields']):
                raise BackfillError('OLD_METADATA_CALL_REQUIRES_EXTERNAL_RECONCILIATION')
        catalog = strict_json((root / CATALOG).read_bytes())
        if any(catalog[m['dataset']]['max_rows'] is None and m['completeness_evidence'] is None for m in plan['requests']):
            raise BackfillError('UNDOCUMENTED_COMPLETENESS')


def owner(db, store: Path) -> None:
    require_writer(db)
    paths = [Path(p).absolute() for _, _, p in db.execute('PRAGMA database_list').fetchall() if p]
    if paths != [(store / 'capture.duckdb').absolute()]:
        raise BackfillError('STORE_OWNER_MISMATCH')
    safe_path(store, store / 'capture.duckdb', exists=True)


def layout(db) -> list:
    return db.execute("SELECT table_name,sql FROM duckdb_tables() WHERE schema_name='main' ORDER BY table_name").fetchall()


def initialize(root: Path, db, store: Path, plan: dict) -> None:
    owner(db, store)
    validate_plan(root, plan)
    schema = (root / DDL).read_text()
    with duckdb.connect(':memory:') as memory:
        memory.execute(schema)
        expected = layout(memory)
    current = layout(db)
    if not current:
        if any(p.name not in ('capture.duckdb', 'capture.duckdb.lock', 'capture.duckdb.wal') for p in store.iterdir()):
            raise BackfillError('ORPHAN_BEFORE_PLAN')
        def create():
            db.execute(schema)
            db.execute('INSERT INTO backfill_pin VALUES (1,?)', [canonical_json(plan).decode()])
            for m in plan['requests']:
                db.execute('INSERT INTO backfill_member VALUES (?,?,?,?)',
                           [m['member_id'], uuid4(), datetime.now(timezone.utc).isoformat(), canonical_json(m).decode()])
        transaction(db, create)
    if layout(db) != expected or db.execute('SELECT payload FROM backfill_pin').fetchall() != [(canonical_json(plan).decode(),)]:
        raise BackfillError('STORE_PINS_CHANGED_NO_RESET')
    members = db.execute('SELECT member_id,payload FROM backfill_member ORDER BY member_id').fetchall()
    if members != sorted((m['member_id'], canonical_json(m).decode()) for m in plan['requests']):
        raise BackfillError('STORE_MEMBERS_CHANGED')
    allowed = {'capture.duckdb', 'capture.duckdb.lock', 'capture.duckdb.wal'} | {m['member_id'] for m in plan['requests']}
    if any(p.name not in allowed for p in store.iterdir()):
        raise BackfillError('ORPHAN_STORE_EVIDENCE')
    for mid, in db.execute('SELECT member_id FROM backfill_member').fetchall():
        history = events(db, mid)
        directory = safe_path(store, store / mid)
        if directory.exists() and not history:
            raise BackfillError('ORPHAN_UNCLAIMED_MEMBER')
        states = [v[0] for v in history]
        if states not in ([], ['CLAIMED'], ['CLAIMED', 'CALL_ENTERED'],
                          ['CLAIMED', 'CALL_ENTERED', 'COMPLETE'],
                          ['CLAIMED', 'CALL_ENTERED', 'FAILED'],
                          ['CLAIMED', 'CALL_ENTERED', 'UNCERTAIN'], ['CLAIMED', 'UNCERTAIN']):
            raise BackfillError('EVENT_HISTORY_CHANGED')
        ordinals = [o for o, in db.execute('SELECT ordinal FROM backfill_event WHERE member_id=? ORDER BY ordinal', [mid]).fetchall()]
        if ordinals != list(range(len(history))) or [instant(v[1]) for v in history] != sorted(instant(v[1]) for v in history):
            raise BackfillError('EVENT_ORDER_CHANGED')


def events(db, member: str) -> list:
    return db.execute('SELECT state,recorded_at,payload FROM backfill_event WHERE member_id=? ORDER BY ordinal', [member]).fetchall()


def event(db, member: str, state: str, clock, payload: dict) -> str:
    history = events(db, member)
    previous = history[-1][0] if history else None
    if state not in {None: {'CLAIMED'}, 'CLAIMED': {'CALL_ENTERED', 'UNCERTAIN'},
                      'CALL_ENTERED': {'COMPLETE', 'FAILED', 'UNCERTAIN'}}.get(previous, set()):
        raise BackfillError('TERMINAL_OR_INVALID_TRANSITION')
    recorded = stamp(clock)
    if history and instant(recorded) < instant(history[-1][1]):
        raise BackfillError('CLOCK_ROLLBACK')
    if state == 'CALL_ENTERED':
        payload = dict(payload, wall=recorded)
    db.execute('INSERT INTO backfill_event VALUES (?,?,?,?,?)', [member, len(history), state, recorded, canonical_json(payload).decode()])
    return recorded


def pace(db, clock) -> None:
    calls = [json.loads(p) for p, in db.execute("SELECT payload FROM backfill_event WHERE state='CALL_ENTERED'").fetchall()]
    if not calls:
        return
    last = max(calls, key=lambda p: instant(p['wall']))
    wall_delta = (clock.utc() - instant(last['wall'])).total_seconds()
    if wall_delta < 0:
        raise BackfillError('CLOCK_ROLLBACK')
    delta = clock.monotonic() - last['monotonic'] if clock.boot() == last['boot'] else 0
    if delta < 0:
        raise BackfillError('MONOTONIC_ROLLBACK')
    clock.sleep(max(0, 1.25 - wall_delta, 1.25 - delta))
    if (clock.utc() - instant(last['wall'])).total_seconds() < 1.25 or (clock.boot() == last['boot'] and clock.monotonic() - last['monotonic'] < 1.25):
        raise BackfillError('PACING_CLOCK_FAILED')


def secret_present(body: bytes, token: str) -> bool:
    values = [body]
    try:
        values.append(canonical_json(strict_json(body)))
    except ValueError:
        pass
    spellings = [token.encode(), base64.b64encode(token.encode()), token.encode().hex().encode(), quote(token, safe='').encode()]
    return any(any(s and s in v for s in spellings) or any(re.search(p, v) for p in PATTERNS) for v in values)


def decoded_table(root: Path, member: dict, body: bytes, retrieved: str) -> pa.Table:
    envelope = strict_json(body)
    if (not isinstance(envelope, dict) or set(envelope) != {'request_id', 'code', 'msg', 'data'}
            or type(envelope['code']) is not int or envelope['code'] != 0
            or not isinstance(envelope['request_id'], str) or not envelope['request_id']
            or envelope['msg'] is not None and not isinstance(envelope['msg'], str)):
        raise BackfillError('PROVIDER_PERMISSION_OR_ENVELOPE_REJECTED')
    data = envelope['data']
    if not isinstance(data, dict) or set(data) != {'fields', 'items'}:
        raise BackfillError('PROVIDER_SCHEMA_REJECTED')
    table = ProviderTable(fields=data['fields'], items=data['items'], retrieved_at=instant(retrieved))
    if table.fields != member['fields']:
        raise BackfillError('PROVIDER_FIELDS_CHANGED')
    c = strict_json((root / CATALOG).read_bytes())[member['dataset']]
    cap = c['max_rows']
    if cap is not None and len(table.items) >= cap:
        raise BackfillError('CAP_OR_TRUNCATION_STOPPED')
    if not table.items and member['empty_evidence'] is None:
        raise BackfillError('UNEXPLAINED_EMPTY_STOPPED')
    numeric = set(c['numeric_fields']); integers = set(c['integer_fields'])
    keys = set(); arrays = {f: [] for f in table.fields}
    for row in table.items:
        values = dict(zip(table.fields, row))
        key = tuple(values[f] for f in c['natural_key'])
        if any(v is None or v == '' for v in key):
            raise BackfillError('MISSING_NATURAL_KEY')
        if key in keys:
            raise BackfillError('DUPLICATE_NATURAL_KEY')
        keys.add(key)
        p = member['params']
        if 'trade_date' in p and values.get('trade_date') != p['trade_date']:
            raise BackfillError('RESPONSE_OUTSIDE_DATE_SCOPE')
        if 'ts_code' in p and values.get('ts_code') != p['ts_code']:
            raise BackfillError('RESPONSE_OUTSIDE_NATIVE_SCOPE')
        if member['dataset'] == 'trade_cal' and (values.get('exchange') != p['exchange'] or not p['start_date'] <= values.get('cal_date', '') <= p['end_date'] or values.get('is_open') not in (0, 1)):
            raise BackfillError('RESPONSE_OUTSIDE_CALENDAR_SCOPE')
        if member['dataset'] == 'stock_basic' and (values.get('exchange') != p['exchange'] or values.get('list_status') != p['list_status']):
            raise BackfillError('RESPONSE_OUTSIDE_UNIVERSE_SCOPE')
        for f, v in values.items():
            if v is not None and ((f in numeric and type(v) not in (int, float)) or (f in integers and type(v) is not int) or (f not in numeric | integers and not isinstance(v, str))):
                raise BackfillError('SOURCE_TYPE_REJECTED')
            arrays[f].append(v)
    if member['dataset'] == 'trade_cal':
        from datetime import timedelta
        first = datetime.strptime(member['params']['start_date'], '%Y%m%d').date()
        last = datetime.strptime(member['params']['end_date'], '%Y%m%d').date()
        expected_dates = {(first + timedelta(days=i)).strftime('%Y%m%d') for i in range((last-first).days + 1)}
        if set(arrays['cal_date']) != expected_dates:
            raise BackfillError('INCOMPLETE_CIVIL_CALENDAR')
    schema = pa.schema([(f, pa.float64() if f in numeric else pa.int64() if f in integers else pa.string()) for f in table.fields])
    return pa.table(arrays, schema=schema)


def publish(path: Path, body: bytes) -> None:
    if path.exists():
        if path.read_bytes() != body:
            raise BackfillError('IMMUTABLE_EVIDENCE_CHANGED')
    else:
        atomic_new_file(path, lambda p: p.write_bytes(body))


def reconcile(root: Path, db, store: Path, plan: dict, member: dict, approval: dict, human: dict,
              *, clock=None, fault=lambda stage: None) -> dict:
    owner(db, store)
    clock = clock or Clock()
    mid = member['member_id']; directory = safe_path(store, store / mid)
    h = events(db, mid)
    if not h or h[-1][0] in ('FAILED', 'UNCERTAIN'):
        raise BackfillError('TERMINAL_NO_RESEND')
    if not directory.is_dir() or {p.name for p in directory.iterdir()} - FILES:
        raise BackfillError('MISSING_OR_ORPHAN_EVIDENCE')
    files = {name: safe_path(store, directory / name) for name in FILES}
    for name in ('response.body', 'http-source.json'):
        safe_path(store, files[name], exists=True)
    source = strict_json(files['http-source.json'].read_bytes())
    obj, created = db.execute('SELECT object_id,created_at FROM backfill_member WHERE member_id=?', [mid]).fetchone()
    calls = [e for e in h if e[0] == 'CALL_ENTERED']
    expected = {'protocol', 'fixture_only', 'member', 'object_id', 'created_at', 'claimed_at', 'call_entered_at', 'retrieved_at', 'available_at', 'http_status', 'content_length', 'content_encoding', 'body_hash', 'body_bytes', 'approval_hash', 'human_hash', 'complete_body'}
    if (set(source) != expected or len(calls) != 1 or h[0][0] != 'CLAIMED'
            or source['protocol'] != PROTOCOL or source['member'] != member or source['object_id'] != str(obj)
            or source['created_at'] != created or source['claimed_at'] != h[0][1] or source['call_entered_at'] != calls[0][1]
            or source['approval_hash'] != checksum(approval) or source['human_hash'] != checksum(human)
            or source['fixture_only'] != (plan['namespace'] == 'FIXTURE') or source['complete_body'] is not True
            or source['body_hash'] != sha256(files['response.body']) or source['body_bytes'] != files['response.body'].stat().st_size
            or source['http_status'] != 200 or source['content_encoding'] not in ('', 'identity')
            or source['content_length'] is not None and source['content_length'] != source['body_bytes']):
        raise BackfillError('SOURCE_BINDING_OR_HTTP_CHANGED')
    call = strict_json(calls[0][2].encode())
    if (set(call) != {'wall', 'monotonic', 'boot', 'object_id', 'plan_hash', 'approval_hash', 'human_hash'}
            or call['wall'] != calls[0][1] or call['object_id'] != str(obj)
            or call['plan_hash'] != checksum(plan) or call['approval_hash'] != checksum(approval)
            or call['human_hash'] != checksum(human)):
        raise BackfillError('DURABLE_CALL_BINDING_CHANGED')
    times = [instant(source[k]) for k in ('created_at', 'claimed_at', 'call_entered_at', 'retrieved_at', 'available_at')]
    if times != sorted(times):
        raise BackfillError('SOURCE_TIME_ORDER_INVALID')
    table = decoded_table(root, member, files['response.body'].read_bytes(), source['retrieved_at'])
    buf = io.BytesIO(); pq.write_table(table, buf); typed = buf.getvalue()
    manifest = dict(protocol=PROTOCOL, object_id=str(obj), member_id=mid, rows=table.num_rows,
                    body_hash=source['body_hash'], source_hash=checksum(source), typed_hash=hashlib.sha256(typed).hexdigest(),
                    schema_hash=hashlib.sha256(table.schema.serialize().to_pybytes()).hexdigest(),
                    retrieved_at=source['retrieved_at'], available_at=source['available_at'], research_admitted=False)
    sidecar = dict(protocol=PROTOCOL, object_id=str(obj), member_id=mid, manifest_hash=checksum(manifest),
                   plan_hash=checksum(plan), membership_hash=plan['membership_hash'])
    receipt = db.execute('SELECT object_id,manifest_hash,source_hash,completed_at FROM backfill_receipt WHERE member_id=?', [mid]).fetchone()
    if h[-1][0] == 'COMPLETE' or receipt:
        if not receipt or h[-1][0] != 'COMPLETE' or {p.name for p in directory.iterdir()} != FILES:
            raise BackfillError('COMPLETE_MEMBERSHIP_INVALID')
        for name, data in [('typed.parquet', typed), ('manifest.json', canonical_json(manifest)), ('sidecar.json', canonical_json(sidecar))]:
            safe_path(store, files[name], exists=True)
            if files[name].read_bytes() != data:
                raise BackfillError('COMPLETE_EVIDENCE_CHANGED')
        if (str(receipt[0]), receipt[1], receipt[2]) != (str(obj), checksum(manifest), checksum(source)) or strict_json(h[-1][2].encode()) != dict(manifest_hash=checksum(manifest), source_hash=checksum(source)) or instant(receipt[3]) < times[-1]:
            raise BackfillError('COMPLETE_RECEIPT_CHANGED')
        return dict(status='ALREADY_VALID', member_id=mid, rows=table.num_rows)
    if h[-1][0] != 'CALL_ENTERED':
        raise BackfillError('NO_EXACT_CALL_ENTRY')
    for name, data in [('typed.parquet', typed), ('manifest.json', canonical_json(manifest)), ('sidecar.json', canonical_json(sidecar))]:
        publish(files[name], data); fault('after_' + name.split('.')[0])
    completed = stamp(clock)
    if instant(completed) < times[-1]:
        raise BackfillError('COMPLETION_BEFORE_SOURCE')
    def complete():
        db.execute('INSERT INTO backfill_receipt VALUES (?,?,?,?,?)', [mid, UUID(str(obj)), checksum(manifest), checksum(source), completed])
        fault('after_registration')
        event(db, mid, 'COMPLETE', clock, dict(manifest_hash=checksum(manifest), source_hash=checksum(source)))
        fault('after_promotion')
    transaction(db, complete)
    return dict(status='COMPLETE', member_id=mid, rows=table.num_rows)


def capture(root: Path, db, store: Path, plan: dict, approval: dict, human: dict,
            member_id: str, token: SecretStr, *, live=False, fixture=False,
            transport=None, clock=None, fault=lambda stage: None) -> dict:
    owner(db, store)
    authorize(root, plan, approval, human, fixture=fixture, live=live)
    if fixture:
        if type(transport) is not httpx.MockTransport:
            raise BackfillError('CLOSED_MOCK_REQUIRED')
    elif transport is not None or store.absolute() != (root / DESTINATION).absolute():
        raise BackfillError('FIXED_PRODUCTION_STORE_REQUIRED')
    if not isinstance(token, SecretStr) or not token.get_secret_value():
        raise BackfillError('LOCAL_TOKEN_REQUIRED')
    initialize(root, db, store, plan)
    selected = [m for m in plan['requests'] if m['member_id'] == member_id]
    if len(selected) != 1:
        raise BackfillError('UNKNOWN_EXACT_MEMBER')
    member = selected[0]; clock = clock or Clock()
    # Validate ALL durable completions before any further send.
    for m in plan['requests']:
        if db.execute('SELECT 1 FROM backfill_receipt WHERE member_id=?', [m['member_id']]).fetchone():
            reconcile(root, db, store, plan, m, approval, human, clock=clock)
    h = events(db, member_id)
    if h:
        return reconcile(root, db, store, plan, member, approval, human, clock=clock, fault=fault)
    if db.execute("SELECT count(*) FROM backfill_event WHERE state IN ('FAILED','UNCERTAIN')").fetchone()[0] or db.execute("SELECT member_id FROM backfill_event WHERE state='CLAIMED' EXCEPT SELECT member_id FROM backfill_receipt").fetchall():
        raise BackfillError('PLAN_STOPPED_NO_RESEND')
    if db.execute("SELECT count(*) FROM backfill_event WHERE state='CLAIMED'").fetchone()[0] >= plan['budget']:
        raise BackfillError('BUDGET_EXHAUSTED')
    directory = safe_path(store, store / member_id)
    if directory.exists():
        raise BackfillError('ORPHAN_BEFORE_CLAIM')
    pace(db, clock)
    claimed = transaction(db, lambda: event(db, member_id, 'CLAIMED', clock, {})); fault('after_claim')
    object_id = db.execute('SELECT object_id FROM backfill_member WHERE member_id=?', [member_id]).fetchone()[0]
    entered = transaction(db, lambda: event(db, member_id, 'CALL_ENTERED', clock,
                                           dict(monotonic=clock.monotonic(), boot=clock.boot(), object_id=str(object_id),
                                                plan_hash=checksum(plan), approval_hash=checksum(approval), human_hash=checksum(human))))
    fault('after_call_entered')
    try:
        with httpx.Client(transport=transport if fixture else httpx.HTTPTransport(retries=0, verify=True, trust_env=False),
                          verify=True, trust_env=False, follow_redirects=False, timeout=20) as client:
            with client.stream('POST', ENDPOINT, headers={'Accept-Encoding': 'identity'}, json=dict(
                    api_name=member['dataset'], params=member['params'], fields=','.join(member['fields']), token=token.get_secret_value())) as response:
                body = response.content if fixture and response.is_stream_consumed else b''.join(response.iter_raw())
    except Exception:
        transaction(db, lambda: event(db, member_id, 'UNCERTAIN', clock, dict(reason='TRANSPORT_UNKNOWN_NO_RESEND')))
        raise BackfillError('TRANSPORT_UNKNOWN_NO_RESEND') from None
    if response.headers.get('content-encoding', '') not in ('', 'identity') or secret_present(body, token.get_secret_value()):
        transaction(db, lambda: event(db, member_id, 'FAILED', clock, dict(reason='UNSAFE_RESPONSE_SUPPRESSED', body_hash=hashlib.sha256(body).hexdigest())))
        raise BackfillError('UNSAFE_RESPONSE_SUPPRESSED')
    obj, created = db.execute('SELECT object_id,created_at FROM backfill_member WHERE member_id=?', [member_id]).fetchone()
    length = response.headers.get('content-length')
    source = dict(protocol=PROTOCOL, fixture_only=fixture, member=member, object_id=str(obj), created_at=created,
                  claimed_at=claimed, call_entered_at=entered, retrieved_at=stamp(clock), available_at=stamp(clock),
                  http_status=response.status_code, content_length=int(length) if length and length.isdecimal() else -1 if length else None,
                  content_encoding=response.headers.get('content-encoding', ''), body_hash=hashlib.sha256(body).hexdigest(),
                  body_bytes=len(body), approval_hash=checksum(approval), human_hash=checksum(human), complete_body=True)
    directory.mkdir(parents=True, exist_ok=False)
    publish(directory / 'response.body', body); fault('after_body')
    publish(directory / 'http-source.json', canonical_json(source)); fault('after_source')
    try:
        if source['http_status'] != 200 or source['content_length'] is not None and source['content_length'] != len(body):
            raise BackfillError('HTTP_OR_TRUNCATED_BODY')
        decoded_table(root, member, body, source['retrieved_at'])
    except (ValueError, TypeError, KeyError, UnicodeError):
        transaction(db, lambda: event(db, member_id, 'FAILED', clock, dict(reason='HTTP_OR_CONTRACT_STOPPED')))
        raise BackfillError('HTTP_OR_CONTRACT_STOPPED') from None
    return reconcile(root, db, store, plan, member, approval, human, clock=clock, fault=fault)


def main() -> None:
    parser = argparse.ArgumentParser(description='Independent exact-plan backfill v1; disabled without matched external approvals')
    parser.add_argument('action', choices=('validate-plan', 'capture'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--human-authorization', type=Path)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    try:
        root = args.root.absolute(); plan = strict_json(args.plan.read_bytes())
        validate_plan(root, plan)
        if args.action == 'validate-plan':
            print(json.dumps(dict(status='PLAN_VALID_NOT_LICENSED', members=len(plan['requests']), attempts=0)))
            return
        approval = strict_json(args.review.read_bytes()); human = strict_json(args.human_authorization.read_bytes())
        authorize(root, plan, approval, human, fixture=False, live=args.live)
        store = safe_path(root, root / DESTINATION); store.mkdir(parents=True, exist_ok=True)
        from astock.settings import load_settings
        token = load_settings(root).tushare_token
        with warehouse_connection(store / 'capture.duckdb') as db:
            for member in plan['requests']:
                print(json.dumps(capture(root, db, store, plan, approval, human, member['member_id'], token, live=args.live)))
    except Exception:
        print('BACKFILL_STOPPED_REVIEW_LOCAL_EVIDENCE')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
