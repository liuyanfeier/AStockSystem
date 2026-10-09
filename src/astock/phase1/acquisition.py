"""Managed unified consumption, bounded first-error runner and physical receipts."""
from __future__ import annotations

import hashlib
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import duckdb
import httpx
from pydantic import SecretStr

from astock.data.full_backfill_v1 import secret_present
from astock.data.warehouse_lock import require_writer, warehouse_connection
from astock.phase1 import PROTOCOL
from astock.phase1 import contracts, legacy
from astock.phase1.core import (ENDPOINT, PRODUCTION, Phase1Error, append_log, category,
    day, digest, encoded, file_hash, instant, logical_id, overlapping, publish, require, safe_path, stamp, strict_json)

DDL = "sql/offline/phase1_integrated_v1.sql"
OBJECT_FILES = {"response.body", "http-source.json", "typed.parquet", "manifest.json", "sidecar.json"}


def pins(root: Path) -> dict:
    names = [DDL, contracts.CATALOG, "docs/phase1/design.md"]
    names += [str(p.relative_to(root)) for p in sorted((root / "src/astock/phase1").glob("*.py"))]
    return {n: file_hash(root / n) for n in names}


def owner(root: Path, destination: Path, fixture: bool) -> dict:
    destination = destination.absolute()
    safe_path(destination.parent, destination)
    for p in legacy.ORIGINALS.values():
        original = (root / p).parent.resolve()
        require(not destination.resolve().is_relative_to(original), "ORIGINAL_STORE_IMMUTABLE")
    require(fixture != (destination.resolve() == (root / PRODUCTION).resolve()), "FIXTURE_PRODUCTION_SEPARATION")
    return dict(root=str(root.resolve()), destination=str(destination.resolve()),
                namespace="FIXTURE" if fixture else "PRODUCTION", protocol=PROTOCOL)


@contextmanager
def store(root: Path, destination: Path, *, fixture=True, read_only=False):
    identity = owner(root, destination, fixture)
    path = destination / "catalog.duckdb"
    if not read_only:
        destination.mkdir(parents=True, exist_ok=True)
    safe_path(destination, path, exists=read_only)
    with warehouse_connection(path, read_only=read_only) as db:
        if not read_only and not db.execute('SHOW TABLES').fetchall():
            db.execute((root / DDL).read_text())
            db.execute('INSERT INTO p1_meta VALUES (?,?)', ["owner", encoded(identity).decode()])
        row = db.execute('SELECT payload FROM p1_meta WHERE key=?', ["owner"]).fetchone()
        require(row == (encoded(identity).decode(),), "ROOT_STORE_NAMESPACE_CHANGED")
        with duckdb.connect(':memory:') as reference:
            reference.execute((root / DDL).read_text())
            from astock.data.full_backfill_v1 import layout
            require(layout(db) == layout(reference), "STORE_SCHEMA_CHANGED")
        yield db


def transaction(db, fn):
    require_writer(db)
    db.execute('BEGIN TRANSACTION')
    try:
        result = fn()
        db.execute('COMMIT')
        return result
    except BaseException:
        db.execute('ROLLBACK')
        raise


def local_consumption(db) -> list:
    result = []
    for mid, batch, request, origin, obj, at in db.execute('SELECT * FROM p1_attempt ORDER BY logical_id').fetchall():
        states = db.execute('SELECT state FROM p1_event WHERE logical_id=? ORDER BY ordinal', [mid]).fetchall()
        result.append(dict(logical_id=mid, batch_hash=batch, request=strict_json(request.encode()),
                           origin_id=origin, object_id=obj, claimed_at=stamp(at), states=[r[0] for r in states]))
    return result


def make_plan(root: Path, destination: Path, members: list, legacy_snapshot: dict, *,
              fixture=False, prior_consumption: list | None = None, resume_from: str | None = None,
              protected_history: dict | None = None) -> dict:
    identity = owner(root, destination, fixture)
    require(members and len({logical_id(m) for m in members}) == len(members), "PLAN_MEMBERS_REQUIRED")
    for m in members:
        candidate = contracts.request(root, m['dataset'], m['params'], fields=m['fields'],
                                      empty_evidence=m.get('empty_evidence'), metadata=m.get('metadata'))
        require(all(m.get(k) == v for k, v in candidate.items()), "EXACT_REQUEST_CONTRACT")
        legacy.check_unconsumed(m, legacy_snapshot)
    for i, m in enumerate(members):
        require(not any(overlapping(m, other) for other in members[:i]), 'OVERLAPPING_NEW_BATCH_MEMBERS')
    return dict(**identity, execution_license=False, members=members,
                membership_hash=digest(members), budget=len(members), max_attempts=1,
                spacing_seconds=1.25, retry=0, redirects=0, pins=pins(root),
                legacy_hash=digest(legacy_snapshot), prior_consumption=prior_consumption or [],
                prior_consumption_hash=digest(prior_consumption or []), resume_from=resume_from,
                protected_history=protected_history,
                research_admitted=False)


def validate_plan(root: Path, destination: Path, plan: dict, baseline: dict, db, *, fixture: bool) -> None:
    expected = make_plan(root, destination, plan['members'], baseline, fixture=fixture,
                         prior_consumption=plan['prior_consumption'], resume_from=plan['resume_from'],
                         protected_history=plan['protected_history'])
    require(plan == expected, "PLAN_SCOPE_PIN_CHANGED")
    current = local_consumption(db)
    require(current == plan['prior_consumption'], "FROZEN_CONSUMPTION_CHANGED")
    prior_stops = [r for r in current if r['states'][-1:] not in (['COMPLETE'], ['RAW_RETAINED'])]
    if prior_stops:
        require(plan['resume_from'] == digest(current), "MATCHED_RECOVERY_REQUIRED")
    for m in plan['members']:
        require(logical_id(m) not in {r['logical_id'] for r in current}, "CONSUMED_NEW_REQUEST")
        for previous in current:
            if overlapping(m, previous['request']):
                require(m['dataset'] == 'trade_cal' and previous['states'][-1] == 'COMPLETE', 'OVERLAPPING_LOCAL_SCOPE_HOLD')


def authorize(root: Path, destination: Path, plan: dict, baseline: dict, approval: dict | None,
              human: dict | None, *, live: bool, transport) -> None:
    fixture = plan['namespace'] == 'FIXTURE'
    if fixture:
        require(not live and type(transport) is httpx.MockTransport, "CLOSED_MOCK_ONLY")
        return
    require(live and transport is None and plan['namespace'] == 'PRODUCTION', "EXPLICIT_LIVE_REQUIRED")
    require(isinstance(approval, dict) and isinstance(human, dict), "MATCHED_INDEPENDENT_HUMAN_REQUIRED")
    expected = dict(protocol=PROTOCOL, namespace='PRODUCTION', plan_hash=digest(plan),
                    root=str(root.resolve()), destination=str(destination.resolve()),
                    pins=pins(root), legacy_hash=digest(baseline), budget=plan['budget'])
    require(all(approval.get(k) == v for k, v in expected.items()), "APPROVAL_SCOPE_CHANGED")
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    require(approval.get('implementation_sha') == sha and not subprocess.check_output(
            ['git', 'status', '--porcelain'], cwd=root), "CLEAN_REVIEWED_SHA_REQUIRED")
    require(approval.get('execution_license') is True and approval.get('reviewer')
            and approval.get('review_ref') and approval.get('approved_at'), "INDEPENDENT_APPROVAL_REQUIRED")
    require(human.get('execution_license') is True and human.get('review_hash') == digest(approval)
            and human.get('source') == 'DIRECT_USER' and human.get('instruction'), "ACTUAL_HUMAN_REQUIRED")
    require(instant(approval['approved_at']) <= instant(human['authorized_at']) <= datetime.now(timezone.utc), "AUTHORIZATION_TIME")
    for evidence in (approval.get('evidence'), human.get('evidence')):
        require(isinstance(evidence, dict) and set(evidence) == {'path', 'sha256'}, "ACTUAL_LICENSE_BYTES_REQUIRED")
        p = safe_path(root, root / evidence['path'], exists=True)
        require(file_hash(p) == evidence['sha256'], "LICENSE_EVIDENCE_CHANGED")
    require(baseline == legacy.snapshot(root), 'ACTUAL_GLOBAL_CONSUMPTION_REQUIRED')
    for m in plan['members']:
        if m.get('empty_evidence'):
            ref = m.get('metadata', {}).get('empty_policy_evidence')
            require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'EMPTY_POLICY_BYTES_REQUIRED')
            require(ref['sha256'] == m['empty_evidence']['evidence_hash'] and
                    file_hash(safe_path(root, root / ref['path'], exists=True)) == ref['sha256'], 'EMPTY_POLICY_CHANGED')


def event(db, mid: str, state: str, at: datetime, payload: dict) -> None:
    history = db.execute('SELECT state,recorded_at FROM p1_event WHERE logical_id=? ORDER BY ordinal', [mid]).fetchall()
    previous = history[-1][0] if history else None
    allowed = {None: {'CLAIMED'}, 'CLAIMED': {'CALL_ENTERED', 'UNCERTAIN'},
               'CALL_ENTERED': {'COMPLETE', 'RAW_RETAINED', 'FAILED', 'UNCERTAIN'}}
    require(state in allowed.get(previous, set()), "INVALID_TERMINAL_TRANSITION")
    require(not history or instant(at) >= instant(history[-1][1]), "CLOCK_ROLLBACK")
    db.execute('INSERT INTO p1_event VALUES (?,?,?,?,?)', [mid, len(history), state, instant(at), encoded(payload).decode()])


def physical_validate(root: Path, destination: Path, db, mid: str) -> dict:
    row = db.execute('SELECT * FROM p1_attempt WHERE logical_id=?', [mid]).fetchone()
    require(row is not None, "ORPHAN_OBJECT")
    _, batch, payload, origin, obj, at = row
    m = strict_json(payload.encode())
    directory = safe_path(destination, destination / 'objects' / obj)
    require(directory.is_dir() and {p.name for p in directory.iterdir()} == OBJECT_FILES, "OBJECT_MEMBERSHIP")
    paths = {n: safe_path(destination, directory / n, exists=True) for n in OBJECT_FILES}
    source = strict_json(paths['http-source.json'].read_bytes())
    body = paths['response.body'].read_bytes()
    require(source['request'] == m and source['logical_id'] == mid and source['object_id'] == obj
            and source['batch_hash'] == batch and source['origin_id'] == origin
            and source['claimed_at'] == stamp(at) and source['body_hash'] == file_hash(paths['response.body'])
            and source['complete_body'] is True and source['http_status'] == 200
            and source['body_bytes'] == len(body) and source['content_encoding'] in ('', 'identity')
            and (source['content_length'] is None or source['content_length'] == len(body)), "SOURCE_BINDING_CHANGED")
    times = [instant(source[k]) for k in ('claimed_at', 'call_entered_at', 'retrieved_at')]
    require(times == sorted(times), "SOURCE_TIME_ORDER")
    decoded = contracts.decode(root, m, body)
    require(source['protocol'] == PROTOCOL and source['fixture_only'] ==
            (strict_json(db.execute("SELECT payload FROM p1_meta WHERE key='owner'").fetchone()[0].encode())['namespace'] == 'FIXTURE'), 'SOURCE_NAMESPACE_CHANGED')
    if m['dataset'] == 'trade_cal':
        cross_calendar(root, destination, db, mid, m, decoded['rows'])
    manifest = dict(protocol=PROTOCOL, logical_id=mid, object_id=obj, request_hash=digest(m),
                    body_hash=file_hash(paths['response.body']), source_hash=digest(source),
                    typed_hash=file_hash(paths['typed.parquet']), rows=len(decoded['rows']),
                    schema_hash=decoded['schema_hash'], completeness=decoded['completeness'],
                    envelope_profile=decoded['envelope_profile'], research_admitted=False)
    require(paths['typed.parquet'].read_bytes() == decoded['typed'], "TYPED_BYTES_CHANGED")
    require(paths['manifest.json'].read_bytes() == encoded(manifest), "MANIFEST_CHANGED")
    sidecar = dict(protocol=PROTOCOL, logical_id=mid, object_id=obj, manifest_hash=digest(manifest), source_hash=digest(source))
    require(paths['sidecar.json'].read_bytes() == encoded(sidecar), "SIDECAR_CHANGED")
    receipt = db.execute('SELECT object_id,manifest_hash,source_hash,completed_at,completeness FROM p1_receipt WHERE logical_id=?', [mid]).fetchone()
    require(receipt is not None and receipt[:3] == (obj, digest(manifest), digest(source))
            and receipt[4] == decoded['completeness'], "EXACT_RECEIPT_REQUIRED")
    history = db.execute('SELECT state,recorded_at,payload FROM p1_event WHERE logical_id=? ORDER BY ordinal', [mid]).fetchall()
    require([r[0] for r in history] in (['CLAIMED', 'CALL_ENTERED', 'COMPLETE'], ['CLAIMED', 'CALL_ENTERED', 'RAW_RETAINED']), "EXACT_SUCCESS_HISTORY")
    require(stamp(history[1][1]) == source['call_entered_at'] and times[-1] <= instant(receipt[3]) <= instant(history[-1][1]), "RECEIPT_TIME_CHANGED")
    require(strict_json(history[-1][2].encode()) == dict(manifest_hash=digest(manifest), source_hash=digest(source)), "COMPLETION_BINDING_CHANGED")
    return dict(logical_id=mid, object_id=obj, rows=len(decoded['rows']), status='VALID', completeness=decoded['completeness'])


def cross_calendar(root: Path, destination: Path, db, mid: str, member: dict, rows: list[dict]) -> None:
    known = {}
    for other, obj, payload in db.execute('SELECT a.logical_id,a.object_id,a.request FROM p1_attempt a JOIN p1_receipt r USING(logical_id) WHERE a.logical_id<>?', [mid]).fetchall():
        m = strict_json(payload.encode())
        if m['dataset'] != 'trade_cal' or m['params']['exchange'] != member['params']['exchange']:
            continue
        body = safe_path(destination, destination / 'objects' / obj / 'response.body', exists=True).read_bytes()
        for r in contracts.decode(root, m, body)['rows']:
            k = r['cal_date']
            require(k not in known or known[k] == r, 'CALENDAR_OVERLAP_CONFLICT')
            known[k] = r
    for r in rows:
        require(r['cal_date'] not in known or known[r['cal_date']] == r, 'CALENDAR_OVERLAP_CONFLICT')
    first = min(rows, key=lambda r: r['cal_date'])
    before = (day(first['cal_date']) - timedelta(days=1)).strftime('%Y%m%d')
    if before in known:
        previous = known[before]['cal_date'] if known[before]['is_open'] else known[before]['pretrade_date']
        require(first['pretrade_date'] == previous, 'CROSS_WINDOW_PRETRADE_CONFLICT')


def audit(root: Path, destination: Path, db) -> dict:
    registered = {r['object_id'] for r in local_consumption(db)}
    objects = destination / 'objects'
    require(not objects.exists() or {p.name for p in objects.iterdir()} <= registered, "ORPHAN_OBJECT_DIRECTORY")
    outcomes = []
    for ph, payload in db.execute('SELECT * FROM p1_plan').fetchall():
        plan = strict_json(payload.encode())
        require(digest(plan) == ph and plan['root'] == str(root.resolve()) and
                plan['destination'] == str(destination.resolve()) and plan['pins'] == pins(root), 'PLAN_OWNER_OR_PINS_CHANGED')
        attempted = {r['logical_id']: r for r in local_consumption(db) if r['batch_hash'] == ph}
        prefix = [logical_id(m) for m in plan['members']][:len(attempted)]
        require(set(attempted) == set(prefix), 'BATCH_ORDER_PREFIX_CHANGED')
        for mid in prefix[:-1]:
            require(attempted[mid]['states'][-1] in ('COMPLETE', 'RAW_RETAINED'), 'FIRST_ERROR_STOP_VIOLATED')
    for r in local_consumption(db):
        stored = db.execute('SELECT payload FROM p1_plan WHERE plan_hash=?', [r['batch_hash']]).fetchone()
        require(stored is not None, "ATTEMPT_PLAN_MISSING")
        plan = strict_json(stored[0].encode())
        require(digest(plan) == r['batch_hash'] and r['request'] in plan['members'], "ATTEMPT_PLAN_CHANGED")
        require(db.execute('SELECT count(*) FROM p1_attempt WHERE batch_hash=?', [r['batch_hash']]).fetchone()[0] <= plan['budget'], "BUDGET_CHANGED")
        states = r['states']
        require(states in (['CLAIMED'], ['CLAIMED', 'CALL_ENTERED'], ['CLAIMED', 'UNCERTAIN'],
                          ['CLAIMED', 'CALL_ENTERED', 'FAILED'], ['CLAIMED', 'CALL_ENTERED', 'UNCERTAIN'],
                          ['CLAIMED', 'CALL_ENTERED', 'COMPLETE'], ['CLAIMED', 'CALL_ENTERED', 'RAW_RETAINED']), "EVENT_HISTORY_CHANGED")
        require(r['logical_id'] == logical_id(r['request']), "REQUEST_ID_CHANGED")
        histories = db.execute('SELECT ordinal,recorded_at FROM p1_event WHERE logical_id=? ORDER BY ordinal', [r['logical_id']]).fetchall()
        require([v[0] for v in histories] == list(range(len(histories))) and [instant(v[1]) for v in histories] == sorted(instant(v[1]) for v in histories), "EVENT_ORDER_CHANGED")
        if states[-1] in ('COMPLETE', 'RAW_RETAINED'):
            outcomes.append(physical_validate(root, destination, db, r['logical_id']))
        else:
            require(not db.execute('SELECT 1 FROM p1_receipt WHERE logical_id=?', [r['logical_id']]).fetchone(), "FAILED_SUCCESS_RECEIPT")
    return dict(status='VALID', checked=len(outcomes), attempts=len(registered), results=outcomes, research_admitted=False)


class Clock:
    def utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, value: float) -> None:
        time.sleep(value)

    def boot(self) -> str:
        from astock.data.full_backfill_v1 import Clock as LegacyClock
        return LegacyClock().boot()


def capture(root: Path, destination: Path, db, member: dict, batch_hash: str, token: SecretStr,
            *, transport=None, clock=None, fault=lambda stage: None) -> dict:
    clock = clock or Clock()
    mid, obj = logical_id(member), member.get('object_id') or str(uuid4())
    require(not db.execute('SELECT 1 FROM p1_attempt WHERE logical_id=?', [mid]).fetchone(), "NO_RESEND")
    fixture = type(transport) is httpx.MockTransport
    require(isinstance(token, SecretStr) and bool(token.get_secret_value()), "TOKEN_REQUIRED")
    require(not fixture or token.get_secret_value().startswith('closed-'), "FIXTURE_TOKEN_REQUIRED")
    require(contracts.catalog(root)[member['dataset']]['source'] == 'TUSHARE', "OFFLINE_EVIDENCE_IMPORT_ONLY")
    entered_rows = db.execute("SELECT recorded_at,payload FROM p1_event WHERE state='CALL_ENTERED' ORDER BY recorded_at DESC LIMIT 1").fetchall()
    if entered_rows:
        last, timing = entered_rows[0]
        require(instant(clock.utc()) >= instant(last), "CLOCK_ROLLBACK")
        elapsed = (instant(clock.utc()) - instant(last)).total_seconds()
        timing = strict_json(timing.encode())
        boot = clock.boot() if hasattr(clock, 'boot') else 'FIXTURE'
        mono_delta = clock.monotonic() - timing['monotonic'] if timing['boot'] == boot else 0
        require(mono_delta >= 0, "MONOTONIC_ROLLBACK")
        clock.sleep(max(0, 1.25 - elapsed, 1.25 - mono_delta))
        require((instant(clock.utc()) - instant(last)).total_seconds() >= 1.25, "PACING_FAILED")
        require(timing['boot'] != boot or clock.monotonic() - timing['monotonic'] >= 1.25, "MONOTONIC_PACING_FAILED")
    directory = safe_path(destination, destination / 'objects' / obj)
    require(not directory.exists(), "ORPHAN_BEFORE_CLAIM")
    claimed = instant(clock.utc())
    def claim():
        db.execute('INSERT INTO p1_attempt VALUES (?,?,?,?,?,?)', [mid, batch_hash, encoded(member).decode(), member.get('origin_id', mid), obj, claimed])
        event(db, mid, 'CLAIMED', claimed, dict(batch_hash=batch_hash))
    transaction(db, claim)
    fault('after_claim')
    entered = instant(clock.utc())
    transaction(db, lambda: event(db, mid, 'CALL_ENTERED', entered, dict(monotonic=clock.monotonic(),
                boot=clock.boot() if hasattr(clock, 'boot') else 'FIXTURE', batch_hash=batch_hash)))
    fault('after_call_entered')
    try:
        with httpx.Client(transport=transport or httpx.HTTPTransport(retries=0, verify=True, trust_env=False),
                          trust_env=False, verify=True, follow_redirects=False, timeout=20) as client:
            with client.stream('POST', ENDPOINT, headers={'Accept-Encoding': 'identity'}, json=dict(
                    api_name=member['dataset'], params=member['params'], fields=','.join(member['fields']), token=token.get_secret_value())) as response:
                chunks, size = [], 0
                for chunk in ((response.content,) if response.is_stream_consumed else response.iter_raw()):
                    size += len(chunk)
                    require(size <= 16 * 1024 * 1024, 'RESPONSE_BYTE_BOUND_EXCEEDED')
                    chunks.append(chunk)
                body = b''.join(chunks)
    except Exception:
        transaction(db, lambda: event(db, mid, 'UNCERTAIN', clock.utc(), dict(reason='TRANSPORT_UNKNOWN_NO_RESEND')))
        raise Phase1Error('TRANSPORT_UNKNOWN_NO_RESEND') from None
    if secret_present(body, token.get_secret_value()):
        transaction(db, lambda: event(db, mid, 'FAILED', clock.utc(), dict(reason='UNSAFE_BODY_SUPPRESSED')))
        raise Phase1Error('UNSAFE_BODY_SUPPRESSED')
    length = response.headers.get('content-length')
    source = dict(protocol=PROTOCOL, request=member, logical_id=mid, object_id=obj,
                  origin_id=member.get('origin_id', mid), batch_hash=batch_hash, claimed_at=stamp(claimed),
                  call_entered_at=stamp(entered), retrieved_at=stamp(clock.utc()), http_status=response.status_code,
                  content_length=int(length) if length and length.isdecimal() else None if not length else -1,
                  content_encoding=response.headers.get('content-encoding', ''), body_hash=hashlib.sha256(body).hexdigest(),
                  body_bytes=len(body), complete_body=True, fixture_only=fixture)
    safe_path(destination, directory)
    directory.mkdir(parents=True)
    def put(name, content):
        publish(safe_path(destination, directory / name), content)
    put('response.body', body)
    put('http-source.json', encoded(source))
    try:
        require(response.status_code == 200 and source['content_encoding'] in ('', 'identity') and
                (source['content_length'] is None or source['content_length'] == len(body)), "HTTP_OR_TRUNCATION")
        decoded = contracts.decode(root, member, body)
        fault('after_decode')
        put('typed.parquet', decoded['typed'])
        manifest = dict(protocol=PROTOCOL, logical_id=mid, object_id=obj, request_hash=digest(member),
                        body_hash=source['body_hash'], source_hash=digest(source), typed_hash=file_hash(directory / 'typed.parquet'),
                        rows=len(decoded['rows']), schema_hash=decoded['schema_hash'], completeness=decoded['completeness'],
                        envelope_profile=decoded['envelope_profile'], research_admitted=False)
        put('manifest.json', encoded(manifest))
        put('sidecar.json', encoded(dict(protocol=PROTOCOL, logical_id=mid, object_id=obj,
                    manifest_hash=digest(manifest), source_hash=digest(source))))
        fault('after_publish')
        status = 'COMPLETE' if decoded['completeness'] == 'CIVIL_WINDOW_VALID' else 'RAW_RETAINED'
        def complete():
            db.execute('INSERT INTO p1_receipt VALUES (?,?,?,?,?,?)', [mid, obj, digest(manifest), digest(source), clock.utc(), decoded['completeness']])
            event(db, mid, status, clock.utc(), dict(manifest_hash=digest(manifest), source_hash=digest(source)))
            fault('before_readback')
            physical_validate(root, destination, db, mid)
        transaction(db, complete)
        return dict(logical_id=mid, status=status, rows=len(decoded['rows']), research_admitted=False)
    except Exception as error:
        transaction(db, lambda: event(db, mid, 'FAILED', clock.utc(), dict(reason=category(error))))
        raise Phase1Error(category(error)) from None


def run_batch(root: Path, destination: Path, plan: dict, baseline: dict, *, token: SecretStr,
              transport=None, live=False, approval=None, human=None, clock=None,
              log=append_log, output=publish, fault=lambda stage: None, protect=None) -> dict:
    authorize(root, destination, plan, baseline, approval, human, live=live, transport=transport)
    fixture = plan['namespace'] == 'FIXTURE'
    require(fixture or clock is None, "PRODUCTION_SYSTEM_CLOCK_ONLY")
    if fixture:
        protect = protect or (lambda: None)
    else:
        # A caller cannot replace mandatory production preservation with a noop.
        from astock.data.capture_continuation_v3 import protected_history_check
        frozen = plan.get('protected_history')
        require(isinstance(frozen, dict), 'PROTECTED_HISTORY_REQUIRED')
        extra = protect or (lambda: None)
        def protect():
            legacy.check_snapshot(baseline)
            protected_history_check(root, {'protected_history': frozen})
            extra()
    primary, secondary = None, []
    with store(root, destination, fixture=fixture) as db:
        validate_plan(root, destination, plan, baseline, db, fixture=fixture)
        audit(root, destination, db)
        protect()
        ph = digest(plan)
        transaction(db, lambda: db.execute('INSERT INTO p1_plan VALUES (?,?)', [ph, encoded(plan).decode()]))
        try:
            for member in plan['members']:
                try:
                    log(destination / 'driver.ndjson', dict(stage='MEMBER_ENTER', logical_id=logical_id(member)))
                    if not fixture:
                        authorize(root, destination, plan, baseline, approval, human, live=live, transport=None)
                        protect()
                    capture(root, destination, db, member, ph, token, transport=transport, clock=clock, fault=fault)
                    log(destination / 'driver.ndjson', dict(stage='MEMBER_COMPLETE', logical_id=logical_id(member)))
                except Exception as error:
                    primary = category(error)
                    try:
                        log(destination / 'driver.ndjson', dict(stage='STOP', recorded_at=stamp(), reason=primary))
                    except Exception as logging_error:
                        secondary.append(category(logging_error))
                    break
        finally:
            summary = dict(protocol=PROTOCOL, namespace=plan['namespace'], plan_hash=ph,
                           status='STOPPED' if primary or secondary else 'RAW_BATCH_VALID',
                           primary_error=primary, secondary_errors=secondary,
                           consumption=local_consumption(db), research_admitted=False,
                           real_market_API=0 if fixture else 'DURABLE_CALL_ENTERED_NOT_TRANSPORT_SUCCESS_COUNT')
            try:
                protect()
                summary['final_audit'] = audit(root, destination, db)
                output(destination / ('summary-' + ph + '.json'), encoded(summary))
            except Exception as reporting_error:
                secondary.append(category(reporting_error))
                summary['status'] = 'STOPPED'
    return summary
