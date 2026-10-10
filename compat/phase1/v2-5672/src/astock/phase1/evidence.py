"""Read-only legacy compatibility, failed-body derivative and bounded rehearsal."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

import httpx
from pydantic import SecretStr

from astock.data.warehouse_lock import warehouse_connection
from astock.phase1 import acquisition, contracts, fixtures, legacy
from astock.phase1.core import digest, encoded, file_hash, instant, publish, require, safe_path, stamp, strict_json


def failed_calendar_candidate(root: Path, destination: Path, directory: Path, baseline: dict) -> dict:
    legacy.check_snapshot(baseline)
    source_path = safe_path(root, directory / 'http-source.json', exists=True)
    body_path = safe_path(root, directory / 'response.body', exists=True)
    source = strict_json(source_path.read_bytes())
    m = source['member']
    old = [r for r in baseline['records'] if r['store'] == 'capture' and r['origin_id'] == m['member_id']]
    require(len(old) == 1 and old[0]['state'] == 'FAILED' and old[0]['consumed'], 'ORIGINAL_FAILED_FACT_REQUIRED')
    diagnostic = source['diagnostic']
    require(source['complete_body'] is True and source['fixture_only'] is False and source['http_status'] == 200
            and source['body_hash'] == file_hash(body_path) and source['body_bytes'] == body_path.stat().st_size
            and source['content_encoding'] in ('', 'identity')
            and source['content_length'] in (None, body_path.stat().st_size)
            and diagnostic['eof'] is True and diagnostic['error_type'] == 'NONE'
            and diagnostic['body_bytes'] == source['body_bytes'] and diagnostic['phase'] == 'COMPLETE', 'ORIGINAL_COMPLETE_HTTP_EVIDENCE_REQUIRED')
    require(instant(source['claimed_at']) <= instant(source['call_entered_at']) <= instant(source['retrieved_at'])
            <= instant(source['available_at']), 'ORIGINAL_TIME_ORDER')
    member = contracts.request(root, m['dataset'], m['params'], fields=m['fields'])
    decoded = contracts.decode(root, member, body_path.read_bytes())
    result = dict(protocol='PHASE1_FAILED_BODY_DERIVATIVE_CANDIDATE_V1', original_request_id=m['member_id'],
                  original_state='FAILED', original_object_id=source['object_id'], original_origin_plan=source['origin_plan'],
                  body_hash=file_hash(body_path), source_hash=file_hash(source_path), contract_hash=member['contract_hash'],
                  implementation_pins=acquisition.pins(root),
                  new_validation_time=stamp(), rows=len(decoded['rows']), completeness=decoded['completeness'],
                  envelope_profile=decoded['envelope_profile'], diagnostic_semantics=decoded['diagnostic_semantics'],
                  leading_previous_certified=False, old_receipt_created=False, original_state_rewritten=False,
                  execution_license=False, production_adopted=False, research_admitted=False)
    h = digest(result)
    with acquisition.store(root, destination) as db:
        def append():
            require(file_hash(body_path) == result['body_hash'] and file_hash(source_path) == result['source_hash'], 'DERIVATIVE_INPUT_CHANGED')
            db.execute('INSERT INTO p1_derivative_validation VALUES (?,?,?,?,?,?,?,?,false)', [h,
                       m['member_id'], 'FAILED', result['body_hash'], result['source_hash'], member['contract_hash'],
                       result['new_validation_time'], encoded(result).decode()])
        acquisition.transaction(db, append)
    legacy.check_snapshot(baseline)
    return dict(result, validation_hash=h)


def compatible_identity(root: Path) -> tuple:
    from astock.data.provider_identity import ProviderResolver
    data = legacy.approved_identity_export(root)
    tables = data['tables']
    for rows in tables.values():
        for row in rows:
            if isinstance(row.get('evidence_ids'), str):
                row['evidence_ids'] = strict_json(row['evidence_ids'].encode())
    bindings = []
    for row in tables['provider_native_binding']:
        b = dict(row)
        b['observations'] = [{k: r[k] for k in ('raw_object_id', 'raw_row_number', 'event_date')}
                             for r in tables['provider_binding_observation'] if r['binding_id'] == b['binding_id']]
        bindings.append(b)
    resolver = ProviderResolver(tables['listing_episode'], tables['official_exchange_code'], bindings)
    at = max([e.available_at for e in resolver.episodes] + [c.available_at for c in resolver.codes] + [b.available_at for b in resolver.bindings])
    reasons = {}
    resolved = 0
    for b in resolver.bindings:
        episode = resolver._episodes[b.episode_id]
        for o in b.observations:
            result = resolver.resolve(provider=b.provider, dataset=b.dataset, native_identifier=b.native_identifier,
                      event_date=o.event_date, raw_object_id=o.raw_object_id, raw_row_number=o.raw_row_number,
                      knowledge_as_of=at, provider_exchange=episode.venue, provider_asset_type=episode.asset_type)
            if result.reason is None: resolved += 1
            else: reasons[result.reason] = reasons.get(result.reason, 0) + 1
    return resolver, dict(warehouse_hash=data['warehouse_hash'], episodes=len(resolver.episodes),
                          codes=len(resolver.codes), bindings=len(resolver.bindings),
                          observations=sum(len(b.observations) for b in resolver.bindings),
                          compatibility='ORIGINAL_VALIDATED_RESOLVER_WITH_EXACT_OBSERVATIONS', wider_aliases_created=0,
                          checked_knowledge_at=stamp(at), resolved_exact_observations=resolved, unresolved_reasons=reasons)


def stopped27(root: Path, destination: Path, selection_path: Path, baseline: dict) -> dict:
    selection = strict_json(selection_path.read_bytes())
    validate_selection(root, selection, baseline)
    legacy.check_snapshot(baseline)
    original = Path(baseline['original_paths']['capture'])
    destination.mkdir(parents=True, exist_ok=True)
    copied = destination / 'stopped-original-copy'
    require(not copied.exists(), 'FRESH_STOPPED_COPY_REQUIRED')
    # Copy existing bytes under a read lock. This copy never changes production.
    with warehouse_connection(original, read_only=True) as db:
        names = [r[0] for r in db.execute('SHOW TABLES').fetchall()]
        from astock.data.receipt_integrity import serial
        before = digest({n: serial(db.execute('SELECT * FROM "' + n + '" ORDER BY ALL').fetchall()) for n in names})
        shutil.copytree(original.parent, copied, ignore=shutil.ignore_patterns('*.lock', '*.wal'))
        require(file_hash(original) == file_hash(copied / original.name), 'COPY_BYTES_CHANGED')
    with warehouse_connection(copied / original.name, read_only=True) as db:
        after = digest({n: serial(db.execute('SELECT * FROM "' + n + '" ORDER BY ALL').fetchall()) for n in names})
        require(before == after and len(names) == 11, 'STOPPED11_ROWSETS_CHANGED')
    members = []
    for original_member in selection['members']:
        m = original_member['request']
        request = contracts.request(root, m['dataset'], m['params'], fields=m['fields'])
        request.update(origin_id=original_member['member_id'], object_id=original_member['object_id'], origin_plan=original_member['origin_plan'],
                       legacy_request_hash=digest(m), legacy_request=m)
        members.append(request)
    new = destination / 'unified-27'
    plan = acquisition.make_plan(root, new, members, baseline, fixture=True)
    ordered, calls = list(members), []
    def handler(request):
        wire = strict_json(request.content)
        m = ordered[len(calls)]
        require(wire['api_name'] == m['dataset'] and wire['params'] == m['params'], 'EXACT27_WIRE_ORDER')
        calls.append(m['origin_id'])
        return httpx.Response(200, content=encoded(fixtures.response(m, fixtures.calendar_rows(m['params']))))
    result = acquisition.run_batch(root, new, plan, baseline, token=SecretStr('closed-exact27'),
                                   transport=httpx.MockTransport(handler), clock=fixtures.FixtureClock('2026-10-09T12:00:00+00:00'))
    require(result['primary_error'] is None and len(calls) == 27 and result['final_audit']['checked'] == 27, 'EXACT27_REHEARSAL_FAILED')
    legacy.check_snapshot(baseline)
    require(file_hash(copied / original.name) == baseline['original_hashes']['capture'], 'STOPPED_COPY_CHANGED')
    return dict(status='OFFLINE_EXACT27_VALID', selection_hash=file_hash(selection_path), original_tables=len(names),
                copied11_rowsets_hash=before, original_hashes=baseline['original_hashes'], mock_calls=27,
                exact_origin_ids=calls, preserved_consumed_ids=[r['origin_id'] for r in baseline['records'] if r['consumed']],
                resends=0, original_SQL_writes=0, real_market_API=0, research_admitted=False,
                new_audit=result['final_audit'], source_copy_immutable=True)


def validate_selection(root: Path, selection: dict, baseline: dict) -> None:
    require(selection['execution_license'] is False and len(selection['members']) == 27
            and selection['canonical_root'] == str(root.resolve())
            and selection['original_capture_hash'] == baseline['original_hashes']['capture'], 'FROZEN_EXACT27_REQUIRED')
    unused = {r['origin_id']: r for r in baseline['records'] if r['store'] == 'capture' and not r['consumed']}
    require({m['member_id'] for m in selection['members']} == set(unused), 'EXACT27_GLOBAL_PENDING_MEMBERSHIP')
    for member in selection['members']:
        m = member['request']
        r = unused[member['member_id']]
        require(r['request'] == dict(dataset=m['dataset'], params=legacy.normalized_params(m['params']))
                and r['object_id'] == member['object_id'] and r['origin_plan'] == member['origin_plan'], 'EXACT27_ORIGIN_CHANGED')


def protection_benchmark(destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    for i in range(48):
        p = destination / f'{i:02}.fixture'
        publish(p, (f'SYNTHETIC-{i}-' * 1024).encode())
        files.append(p)
    started = time.perf_counter()
    expected = {p.name: file_hash(p) for p in files}
    scan = time.perf_counter() - started
    started = time.perf_counter()
    for _ in range(6):
        require({p.name: file_hash(p) for p in files} == expected, 'CONTROLLED_PROTECTION_CHANGED')
    repeated = time.perf_counter() - started
    p = files[0]
    import os
    st, body = p.stat(), p.read_bytes()
    p.write_bytes(b'X' + body[1:])
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
    detected = file_hash(p) != expected[p.name]
    require(detected and p.stat().st_size == st.st_size and p.stat().st_mtime_ns == st.st_mtime_ns, 'SAME_METADATA_TAMPER_MISSED')
    return dict(files=48, byte_count=sum(p.stat().st_size for p in files), scans=7, hashes=48 * 7,
                full_scan_seconds=scan, repeated_six_seconds=repeated, same_size_mtime_tamper_detected=detected,
                production_full_hash_policy_retained=True, cheaper_equivalence_not_claimed=True,
                detection='FULL_SCAN_BEFORE_EACH_PRODUCTION_CALL_AND_FINAL_SCAN')
