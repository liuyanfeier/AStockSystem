"""Exact-seven, separately licensed metadata capture; no generic ingestion path.

The CLI never admits fixtures. MockTransport tests exercise the same persisted
claim, HTTP wire, immutable response and completion path without network access.
"""

import argparse
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import duckdb
import httpx
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import SecretStr

from astock.data import admission_metadata as proposal
from astock.data.probe_audit import canonical_json
from astock.data.raw_validation import sha256
from astock.data.raw_writer import atomic_new_file
from astock.data.reconstruction import checksum, transaction
from astock.data.warehouse_lock import require_writer, warehouse_connection

PROTOCOL = 'ADMISSION_SZSE_METADATA_LIVE_V1'
DESIGN = 'docs/remediation/phase1c1/combined-remediation-b-rehearsal/concrete-design-v1.md'
DESTINATION = 'data/private/phase1c1-admission-metadata-live-v1'
PLAN_BYTES = 'bf8280a25a1f0456b30f79b2da5c5115e0c2bb6a09c3589bcf24911616fd0ec2'
PLAN_HASH = 'fb2c0792fdb6548c5849df398a56206e52802ca4bfab78da6f4ca3cdf5553a35'
LICENSE_FIELDS = {'schema', 'namespace', 'plan_hash', 'plan_bytes_hash', 'membership_hash',
                  'contract_bytes_hash', 'implementation_sha', 'design_hash', 'review_ref',
                  'reviewed_at', 'user_authorization_ref', 'user_authorized_at', 'execution_license'}
SCHEMA = pa.schema([('exchange', pa.string()), ('cal_date', pa.string()),
                    ('is_open', pa.int64()), ('pretrade_date', pa.string())])
PATTERNS = (rb'gh[pousr]_[A-Za-z0-9]{30,}', rb'github_pat_[A-Za-z0-9_]{40,}',
            rb'AKIA[A-Z0-9]{16}', rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
DDL = '''
CREATE TABLE metadata_pin (id INTEGER PRIMARY KEY CHECK(id=1), payload VARCHAR NOT NULL);
CREATE TABLE metadata_member (request_id VARCHAR PRIMARY KEY, object_id UUID UNIQUE NOT NULL,
 created_at VARCHAR NOT NULL, request_json VARCHAR NOT NULL);
CREATE TABLE metadata_event (request_id VARCHAR REFERENCES metadata_member(request_id),
 ordinal INTEGER, state VARCHAR CHECK(state IN ('CLAIMED','CALL_ENTERED','RECEIVED','COMPLETE','FAILED')),
 recorded_at VARCHAR NOT NULL, payload VARCHAR NOT NULL, PRIMARY KEY(request_id,ordinal));
CREATE TABLE metadata_receipt (request_id VARCHAR PRIMARY KEY REFERENCES metadata_member(request_id),
 object_id UUID UNIQUE NOT NULL, manifest_hash VARCHAR NOT NULL, source_hash VARCHAR NOT NULL,
 verified_at VARCHAR NOT NULL);
'''


class MetadataError(ValueError):
    """Stable diagnostics only; never include HTTP/auth/exception payloads."""


class Clock:
    def utc(self):
        return datetime.now(timezone.utc)

    def monotonic(self):
        return time.monotonic()

    def sleep(self, seconds):
        time.sleep(seconds)

    def boot(self):
        if sys.platform.startswith('linux'):
            return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if sys.platform == 'darwin':
            return subprocess.check_output(['sysctl', '-n', 'kern.boottime'], text=True).strip()
        raise MetadataError('BOOT_ID_UNAVAILABLE')


def stamp(clock):
    value = clock.utc()
    if value.tzinfo is None:
        raise MetadataError('NAIVE_CLOCK')
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds')


def instant(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise MetadataError('NAIVE_INSTANT')
    return result


def license_template(root: Path, implementation_sha: str) -> dict:
    plan = proposal.build_plan(root)
    return dict(schema=PROTOCOL, namespace='PRODUCTION', plan_hash=PLAN_HASH,
                plan_bytes_hash=PLAN_BYTES, membership_hash=plan['membership_hash'],
                contract_bytes_hash=proposal.CONTRACT_BYTES, implementation_sha=implementation_sha,
                design_hash=sha256(root / DESIGN), review_ref=None, reviewed_at=None,
                user_authorization_ref=None, user_authorized_at=None, execution_license=False)


def validate_license(root, plan_path, license, *, live, fixture):
    if not live or not isinstance(license, dict) or set(license) != LICENSE_FIELDS:
        raise MetadataError('LICENSE_REQUIRED')
    if plan_path.is_symlink() or sha256(plan_path) != PLAN_BYTES:
        raise MetadataError('PLAN_BYTES_CHANGED')
    plan = json.loads(plan_path.read_bytes())
    proposal.validate_plan(root, plan)
    if checksum(plan) != PLAN_HASH:
        raise MetadataError('PLAN_HASH_CHANGED')
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    template = license_template(root, actual)
    for name in ('schema', 'plan_hash', 'plan_bytes_hash', 'membership_hash',
                 'contract_bytes_hash', 'implementation_sha', 'design_hash'):
        if license[name] != template[name]:
            raise MetadataError('LICENSE_PIN_CHANGED')
    namespace = 'CANDIDATE_REHEARSAL_ONLY' if fixture else 'PRODUCTION'
    if license['namespace'] != namespace or license['execution_license'] is not True:
        raise MetadataError('LICENSE_NAMESPACE_OR_PERMISSION')
    for name in ('review_ref', 'user_authorization_ref'):
        if not isinstance(license[name], str) or not license[name].strip():
            raise MetadataError('LICENSE_APPROVAL_REQUIRED')
    if fixture and not license['review_ref'].startswith('CANDIDATE_REHEARSAL_ONLY:'):
        raise MetadataError('FIXTURE_NAMESPACE_REQUIRED')
    if not fixture:
        if any('CANDIDATE_REHEARSAL_ONLY' in license[n] for n in ('review_ref', 'user_authorization_ref')):
            raise MetadataError('FIXTURE_CANNOT_ENTER_PRODUCTION')
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root):
            raise MetadataError('UNCOMMITTED_CHECKOUT')
    current = datetime.now(timezone.utc)
    if not instant(license['reviewed_at']) <= instant(license['user_authorized_at']) <= current:
        raise MetadataError('LICENSE_TIME_INVALID')
    return plan


def safe_path(root: Path, path: Path, *, exists=False):
    root = root.absolute()
    path = path.absolute()
    if not path.is_relative_to(root):
        raise MetadataError('STORE_PATH_ESCAPE')
    # Check ancestors too, before any resolve/open/mkdir.
    for component in (root, *root.parents, path, *path.parents):
        if component.is_symlink():
            raise MetadataError('STORE_SYMLINK')
    if exists and not path.is_file():
        raise MetadataError('MISSING_EVIDENCE')
    if path.exists() and path.is_file() and path.stat().st_nlink != 1:
        raise MetadataError('STORE_HARDLINK')
    if path.exists() and not (path.is_dir() or path.is_file()):
        raise MetadataError('STORE_NOT_REGULAR')
    return path


def owner(db, store):
    require_writer(db)
    paths = [Path(p).resolve() for _, _, p in db.execute('PRAGMA database_list').fetchall() if p]
    if paths != [(store / 'metadata.duckdb').resolve()]:
        raise MetadataError('STORE_OWNER_MISMATCH')
    safe_path(store, store / 'metadata.duckdb', exists=True)


def _events(db, request_id):
    return [dict(state=s, recorded_at=t, payload=json.loads(p)) for s, t, p in db.execute(
        'SELECT state,recorded_at,payload FROM metadata_event WHERE request_id=? ORDER BY ordinal',
        [request_id]).fetchall()]


def _event(db, request_id, state, clock, payload=None):
    previous = _events(db, request_id)
    recorded = stamp(clock)
    if previous and instant(recorded) < instant(previous[-1]['recorded_at']):
        raise MetadataError('CLOCK_ROLLBACK')
    db.execute('INSERT INTO metadata_event VALUES (?,?,?,?,?)',
               [request_id, len(previous), state, recorded, canonical_json(payload or {}).decode()])
    return recorded


def _layout(db):
    return db.execute("SELECT table_name,sql FROM duckdb_tables() WHERE schema_name='main' ORDER BY table_name").fetchall()


@functools.lru_cache(maxsize=1)
def _expected_layout():
    with duckdb.connect(':memory:') as db:
        db.execute(DDL)
        return _layout(db)


def initialize(root, db, store, plan, license, *, fixture):
    owner(db, store)
    pins = {n: license[n] for n in ('schema', 'namespace', 'plan_hash', 'plan_bytes_hash',
                                   'membership_hash', 'contract_bytes_hash', 'implementation_sha', 'design_hash')}
    pins['fixture_only'] = fixture
    names = {n for n, in db.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()}
    expected = {'metadata_pin', 'metadata_member', 'metadata_event', 'metadata_receipt'}
    if not names:
        clock = Clock()
        def create():
            db.execute(DDL)
            db.execute('INSERT INTO metadata_pin VALUES (1,?)', [canonical_json(pins).decode()])
            for member in plan['requests']:
                db.execute('INSERT INTO metadata_member VALUES (?,?,?,?)',
                           [member['request_id'], uuid4(), stamp(clock), canonical_json(member).decode()])
        transaction(db, create)
    elif names != expected:
        raise MetadataError('STORE_SCHEMA_CHANGED')
    saved = db.execute('SELECT payload FROM metadata_pin WHERE id=1').fetchone()
    if not saved or json.loads(saved[0]) != pins:
        raise MetadataError('STORE_PINS_CHANGED_NO_BUDGET_RESET')
    members = db.execute('SELECT request_id,request_json FROM metadata_member ORDER BY request_id').fetchall()
    if members != sorted((m['request_id'], canonical_json(m).decode()) for m in plan['requests']):
        raise MetadataError('STORE_MEMBERS_CHANGED')
    if _layout(db) != _expected_layout():
        raise MetadataError('STORE_SCHEMA_CHANGED')
    # Schema evolution here is forbidden: compare actual column and constraint descriptions.
    for table, count in [('metadata_pin', 2), ('metadata_member', 4), ('metadata_event', 5), ('metadata_receipt', 5)]:
        if len(db.execute('SELECT * FROM '+table+' LIMIT 0').description) != count:
            raise MetadataError('STORE_SCHEMA_CHANGED')


def pace(db, clock):
    calls = [json.loads(p) for p, in db.execute(
        "SELECT payload FROM metadata_event WHERE state='CALL_ENTERED'").fetchall()]
    if not calls:
        return
    calls += [json.loads(p)['pacing'] for p, in db.execute(
        "SELECT payload FROM metadata_event WHERE state='COMPLETE'").fetchall()]
    last = max(calls, key=lambda p: p['wall'])
    now = clock.utc()
    wall_delta = (now - instant(last['wall'])).total_seconds()
    if wall_delta < 0:
        raise MetadataError('CLOCK_ROLLBACK')
    mono = clock.monotonic()
    if clock.boot() == last['boot']:
        elapsed = mono - last['monotonic']
        if elapsed < 0:
            raise MetadataError('MONOTONIC_ROLLBACK')
        wait = max(0.0, 1.25-wall_delta, 1.25-elapsed)
    else:
        wait = max(1.25, 1.25-wall_delta)
    if wait:
        clock.sleep(wait)
    if (clock.utc()-instant(last['wall'])).total_seconds() < 1.25:
        raise MetadataError('PACING_CLOCK_FAILED')
    if clock.boot() == last['boot'] and clock.monotonic()-last['monotonic'] < 1.25:
        raise MetadataError('PACING_CLOCK_FAILED')


def _secret(body: bytes, token: str):
    values = [body]
    try:
        decoded = json.loads(body)
        def strings(v):
            if isinstance(v, str): values.append(v.encode())
            elif isinstance(v, dict):
                for key, val in v.items(): strings(key); strings(val)
            elif isinstance(v, list):
                for val in v: strings(val)
        strings(decoded)
    except (ValueError, UnicodeError):
        pass
    return any((token and token.encode() in value) or any(re.search(p, value) for p in PATTERNS) for value in values)


def _files(store, request_id):
    directory = safe_path(store, store / request_id)
    return directory, {n: safe_path(store, directory / n) for n in
                       ('response.body', 'http-source.json', 'typed.parquet', 'manifest.json', 'metadata.json')}


def _publish(path, body):
    if path.exists():
        if path.read_bytes() != body:
            raise MetadataError('IMMUTABLE_EVIDENCE_CHANGED')
    else:
        atomic_new_file(path, lambda p: p.write_bytes(body))


def strict_json(body):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise MetadataError('DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def constant(value):
        raise MetadataError('NONFINITE_JSON')
    return json.loads(body, object_pairs_hook=pairs, parse_constant=constant)


def _source(root, db, store, request, license):
    request_id = request['request_id']
    directory, files = _files(store, request_id)
    if not directory.is_dir() or {p.name for p in directory.iterdir()} - files.keys():
        raise MetadataError('ORPHAN_LOCAL_EVIDENCE')
    for name in ('response.body', 'http-source.json'):
        safe_path(store, files[name], exists=True)
    source = json.loads(files['http-source.json'].read_bytes())
    member = db.execute('SELECT object_id,created_at FROM metadata_member WHERE request_id=?', [request_id]).fetchone()
    history = _events(db, request_id)
    call = [e for e in history if e['state'] == 'CALL_ENTERED']
    if len(call) != 1:
        raise MetadataError('MISSING_EXACT_CALL')
    expected = {'schema', 'fixture_only', 'request', 'object_id', 'created_at', 'claimed_at',
                'call_entered_at', 'finished_at', 'retrieved_at', 'available_at', 'http',
                'body_sha256', 'body_bytes', 'license_hash', 'implementation_sha', 'design_hash', 'complete_body'}
    if set(source) != expected or (source['request'] != request or source['object_id'] != str(member[0])
            or source['created_at'] != member[1] or source['schema'] != PROTOCOL
            or source['license_hash'] != checksum(license) or source['fixture_only'] != (license['namespace'] != 'PRODUCTION')
            or source['claimed_at'] != history[0]['recorded_at']
            or source['call_entered_at'] != call[0]['recorded_at']
            or source['implementation_sha'] != license['implementation_sha'] or source['design_hash'] != license['design_hash']
            or source['complete_body'] is not True or source['body_sha256'] != sha256(files['response.body'])
            or source['body_bytes'] != files['response.body'].stat().st_size):
        raise MetadataError('SOURCE_BINDING_CHANGED')
    times = [instant(source[n]) for n in ('created_at', 'claimed_at', 'call_entered_at',
                                         'finished_at', 'retrieved_at', 'available_at')]
    if times != sorted(times):
        raise MetadataError('SOURCE_TIMES_CHANGED')
    http = source['http']
    if set(http) != {'status', 'content_type', 'content_length', 'content_encoding'} or http['status'] != 200:
        raise MetadataError('HTTP_REJECTED')
    if http['content_encoding'] not in ('', 'identity'):
        raise MetadataError('ENCODED_BODY_REJECTED')
    if http['content_length'] is not None and http['content_length'] != source['body_bytes']:
        raise MetadataError('TRUNCATED_BODY')
    envelope = strict_json(files['response.body'].read_bytes())
    if (not isinstance(envelope, dict) or set(envelope) != {'request_id', 'code', 'msg', 'data'}
            or type(envelope['code']) is not int or envelope['code'] != 0
            or not isinstance(envelope['request_id'], str) or not envelope['request_id']
            or envelope['msg'] is not None and not isinstance(envelope['msg'], str)):
        raise MetadataError('PROVIDER_ENVELOPE_REJECTED')
    rows = proposal.validate_response(request, canonical_json(envelope['data']))
    return source, rows, files


def reconcile(root, db, store, request, license, *, clock=None, fault=lambda stage: None):
    owner(db, store)
    clock = clock or Clock()
    source, rows, files = _source(root, db, store, request, license)
    request_id = request['request_id']
    prior = _events(db, request_id)
    if prior and prior[-1]['state'] == 'COMPLETE' and any(not f.is_file() for f in files.values()):
        raise MetadataError('COMPLETE_EVIDENCE_MISSING')
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    import io
    stream = io.BytesIO()
    pq.write_table(table, stream)
    typed = stream.getvalue()
    _publish(files['typed.parquet'], typed)
    fault('after_typed')
    manifest = dict(schema=PROTOCOL, object_id=source['object_id'], request=request,
                    rows=len(rows), full_response_sha256=source['body_sha256'],
                    typed_sha256=hashlib.sha256(typed).hexdigest(),
                    schema_hash=hashlib.sha256(SCHEMA.serialize().to_pybytes()).hexdigest(),
                    source_hash=checksum(source), retrieved_at=source['retrieved_at'], available_at=source['available_at'],
                    session_certification='NONE_REQUIRES_INDEPENDENT_FACT_REVIEW')
    _publish(files['manifest.json'], canonical_json(manifest))
    fault('after_manifest')
    sidecar = dict(schema=PROTOCOL, request_id=request_id, object_id=source['object_id'],
                   manifest_hash=checksum(manifest), source_hash=checksum(source),
                   membership_hash=license['membership_hash'], plan_hash=PLAN_HASH)
    _publish(files['metadata.json'], canonical_json(sidecar))
    fault('after_sidecar')
    if set(p.name for p in files['manifest.json'].parent.iterdir()) != set(files):
        raise MetadataError('ORPHAN_LOCAL_EVIDENCE')
    receipt = db.execute('SELECT object_id,manifest_hash,source_hash,verified_at FROM metadata_receipt WHERE request_id=?', [request_id]).fetchone()
    history = _events(db, request_id)
    if receipt:
        if (str(receipt[0]), receipt[1], receipt[2]) != (source['object_id'], checksum(manifest), checksum(source)) or history[-1]['state'] != 'COMPLETE':
            raise MetadataError('RECEIPT_BINDING_CHANGED')
        return dict(status='ALREADY_VALID', request_id=request_id, rows=len(rows), verified_at=receipt[3])
    if history[-1]['state'] in ('COMPLETE', 'FAILED'):
        raise MetadataError('TERMINAL_WITHOUT_RECEIPT')
    verified = stamp(clock)
    if instant(verified) < instant(source['available_at']):
        raise MetadataError('VERIFICATION_PRECEDES_SOURCE')
    def complete():
        if not any(e['state'] == 'RECEIVED' for e in history):
            _event(db, request_id, 'RECEIVED', clock, dict(source_hash=checksum(source)))
        db.execute('INSERT INTO metadata_receipt VALUES (?,?,?,?,?)',
                   [request_id, UUID(source['object_id']), checksum(manifest), checksum(source), verified])
        fault('after_registration')
        _event(db, request_id, 'COMPLETE', clock, dict(manifest_hash=checksum(manifest), verified_at=verified,
            pacing=dict(wall=stamp(clock), monotonic=clock.monotonic(), boot=clock.boot())))
        fault('before_completion_commit')
    transaction(db, complete)
    return dict(status='COMPLETE', request_id=request_id, rows=len(rows), verified_at=verified)


def capture(root: Path, db, store: Path, plan_path: Path, license: dict, request_id: str,
            token: SecretStr, *, live=False, fixture=False, transport=None, clock=None,
            fault=lambda stage: None):
    """Call at most once; all uncertain outcomes retain their consumed reservation."""
    owner(db, store)
    if fixture:
        if type(transport) is not httpx.MockTransport:
            raise MetadataError('CLOSED_MOCK_REQUIRED')
    elif transport is not None:
        raise MetadataError('INJECTED_TRANSPORT_FORBIDDEN')
    plan = validate_license(root, plan_path, license, live=live, fixture=fixture)
    if not fixture and store.absolute() != (root / DESTINATION).absolute():
        raise MetadataError('FIXED_STORE_REQUIRED')
    initialize(root, db, store, plan, license, fixture=fixture)
    requests = [m for m in plan['requests'] if m['request_id'] == request_id]
    if len(requests) != 1:
        raise MetadataError('UNKNOWN_EXACT_MEMBER')
    request = requests[0]
    clock = clock or Clock()
    if not isinstance(token, SecretStr) or not token.get_secret_value():
        raise MetadataError('LOCAL_TOKEN_REQUIRED')
    history = _events(db, request_id)
    if history:
        if history[-1]['state'] == 'FAILED':
            raise MetadataError('TERMINAL_FAILURE_NO_RESEND')
        return reconcile(root, db, store, request, license, clock=clock, fault=fault)
    # A changed run UUID cannot hide a prior consumed/unknown/error attempt.
    incomplete = db.execute("SELECT DISTINCT request_id FROM metadata_event WHERE state='CLAIMED' EXCEPT SELECT request_id FROM metadata_receipt").fetchall()
    if incomplete:
        raise MetadataError('PLAN_STOPPED_CONSUMED_ATTEMPT')
    if db.execute("SELECT count(*) FROM metadata_event WHERE state='CLAIMED'").fetchone()[0] >= 7:
        raise MetadataError('ATTEMPT_BUDGET_EXHAUSTED')
    for previous in plan['requests']:
        if db.execute('SELECT 1 FROM metadata_receipt WHERE request_id=?', [previous['request_id']]).fetchone():
            reconcile(root, db, store, previous, license, clock=clock)
    directory, files = _files(store, request_id)
    if directory.exists():
        raise MetadataError('ORPHAN_BEFORE_CLAIM')
    pace(db, clock)
    claimed = transaction(db, lambda: _event(db, request_id, 'CLAIMED', clock))
    fault('after_claim')
    wall = stamp(clock)
    call_payload = dict(wall=wall, monotonic=clock.monotonic(), boot=clock.boot())
    entered = transaction(db, lambda: _event(db, request_id, 'CALL_ENTERED', clock, call_payload))
    fault('after_call_entered')
    secret = token.get_secret_value()
    wire = request['wire']
    try:
        with httpx.Client(transport=transport if fixture else httpx.HTTPTransport(retries=0),
                          timeout=httpx.Timeout(20.0, connect=10.0), trust_env=False,
                          follow_redirects=False) as client:
            response = client.post('https://api.tushare.pro',
                headers={'Accept-Encoding': 'identity'}, json=dict(api_name=wire['api_name'],
                token=secret, params=wire['params'], fields=wire['fields']))
            body = response.content
        finished, retrieved, available = stamp(clock), stamp(clock), stamp(clock)
    except Exception:
        transaction(db, lambda: _event(db, request_id, 'FAILED', clock, dict(reason='TRANSPORT_UNKNOWN_NO_RESEND')))
        raise MetadataError('TRANSPORT_UNKNOWN_NO_RESEND') from None
    if _secret(body, secret):
        transaction(db, lambda: _event(db, request_id, 'FAILED', clock,
            dict(reason='SECRET_RESPONSE_SUPPRESSED', body_sha256=hashlib.sha256(body).hexdigest(), body_bytes=len(body))))
        raise MetadataError('SECRET_RESPONSE_SUPPRESSED')
    length = response.headers.get('content-length')
    length = int(length) if length is not None and length.isdecimal() else (-1 if length is not None else None)
    member = db.execute('SELECT object_id,created_at FROM metadata_member WHERE request_id=?', [request_id]).fetchone()
    source = dict(schema=PROTOCOL, fixture_only=fixture, request=request, object_id=str(member[0]),
                  created_at=member[1], claimed_at=claimed, call_entered_at=entered,
                  finished_at=finished, retrieved_at=retrieved, available_at=available,
                  http=dict(status=response.status_code, content_type=response.headers.get('content-type', '')[:100],
                            content_length=length, content_encoding=response.headers.get('content-encoding', '')),
                  body_sha256=hashlib.sha256(body).hexdigest(), body_bytes=len(body), complete_body=True,
                  license_hash=checksum(license), implementation_sha=license['implementation_sha'], design_hash=license['design_hash'])
    # Safe HTTP fields must not echo auth either.
    if _secret(canonical_json(source), secret):
        transaction(db, lambda: _event(db, request_id, 'FAILED', clock, dict(reason='SECRET_METADATA_SUPPRESSED')))
        raise MetadataError('SECRET_METADATA_SUPPRESSED')
    directory.mkdir(parents=True, exist_ok=False)
    _publish(files['response.body'], body)
    fault('after_body')
    _publish(files['http-source.json'], canonical_json(source))
    fault('after_source')
    try:
        _source(root, db, store, request, license)
    except (ValueError, KeyError, TypeError, UnicodeError):
        transaction(db, lambda: _event(db, request_id, 'FAILED', clock, dict(reason='HTTP_OR_CONTRACT_REJECTED')))
        raise MetadataError('HTTP_OR_CONTRACT_REJECTED') from None
    return reconcile(root, db, store, request, license, clock=clock, fault=fault)


def main():
    parser = argparse.ArgumentParser(description='Licensed exact-seven SZSE metadata only')
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--license', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    try:
        root = args.root.absolute()
        license = json.loads(args.license.read_bytes())
        plan = validate_license(root, args.plan, license, live=args.live, fixture=False)
        store = safe_path(root, root / DESTINATION)
        store.mkdir(parents=True, exist_ok=True)
        from astock.settings import load_settings
        token = load_settings(root).tushare_token
        with warehouse_connection(store / 'metadata.duckdb') as db:
            for request in plan['requests']:
                result = capture(root, db, store, args.plan, license, request['request_id'], token, live=args.live)
                print(json.dumps(result, sort_keys=True))
    except Exception:
        # CLI never prints exception repr, auth/body or a potentially secret path.
        print('METADATA_STOPPED_REVIEW_LOCAL_EVIDENCE', file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
