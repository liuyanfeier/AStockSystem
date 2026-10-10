"""Approved offline interpretation of existing raw; no API, retry or old rewrite."""
from __future__ import annotations

from pathlib import Path

from astock.phase1 import acquisition, contracts, legacy
from astock.phase1.core import digest, file_hash, instant, require, safe_path, strict_json


def validate(root: Path, package: dict, *, destination: Path | None = None, db=None) -> dict:
    ref = package.get('raw_reference')
    require(isinstance(ref, dict) and set(ref) == {'kind', 'body_path', 'body_hash', 'source_path', 'source_hash'}, 'EXACT_RAW_REFERENCE_REQUIRED')
    fixture = package['namespace'] == 'FIXTURE'
    body, source_path = Path(ref['body_path']).absolute(), Path(ref['source_path']).absolute()
    require(body.name == 'response.body' and source_path.name == 'http-source.json' and body.parent == source_path.parent, 'RAW_REFERENCE_PAIR_REQUIRED')
    for path in (body, source_path):
        safe_path(path.parent if fixture else root, path, exists=True)
    require(file_hash(body) == ref['body_hash'] and file_hash(source_path) == ref['source_hash'], 'RAW_REFERENCE_CHANGED')
    source = strict_json(source_path.read_bytes())
    member = source.get('request') or source.get('member')
    require(source['fixture_only'] == fixture and source['complete_body'] is True and source['http_status'] == 200
            and source['body_hash'] == ref['body_hash'] and source['body_bytes'] == body.stat().st_size
            and source['content_length'] in (None, body.stat().st_size) and source['content_encoding'] in ('', 'identity'), 'RAW_COMPLETE_SOURCE_REQUIRED')
    require(strict_json(body.read_bytes()) == package['response'], 'INTERPRETATION_VALUE_CHANGED')
    require(instant(package['retrieved_at']) >= instant(source['retrieved_at']), 'INTERPRETATION_RETRIEVAL_ORDER')
    request = package['request']
    require(all(request[k] == member[k] for k in ('dataset', 'params', 'fields')), 'INTERPRETATION_SCOPE_CHANGED')
    require(contracts.catalog(root)[request['dataset']]['source'] == 'TUSHARE', 'RAW_PROVIDER_DATASET_REQUIRED')
    if ref['kind'] == 'CAPTURE':
        store = body.parents[2]
        require(body.parent.name == source['object_id'], 'RAW_CAPTURE_OBJECT_SCOPE')
        if destination is not None and store.resolve() == destination.resolve() and db is not None:
            acquisition.physical_validate(root, store, db, source['logical_id'])
        else:
            with acquisition.store(root, store, fixture=fixture, read_only=True) as original:
                acquisition.physical_validate(root, store, original, source['logical_id'])
        original_state = 'RAW_RETAINED_OR_COMPLETE_UNCHANGED'
    elif ref['kind'] == 'FAILED_CALENDAR':
        require(not fixture and request['dataset'] == 'trade_cal'
                and body.parent == root / 'data/private/full-backfill-v1' / member['member_id'], 'FAILED_CALENDAR_EXACT_SOURCE_REQUIRED')
        baseline = legacy.snapshot(root)
        matches = [r for r in baseline['records'] if r['store'] == 'capture' and r['origin_id'] == member['member_id']]
        diagnostic = source['diagnostic']
        require(len(matches) == 1 and matches[0]['state'] == 'FAILED' and matches[0]['consumed']
                and diagnostic['eof'] is True and diagnostic['error_type'] == 'NONE'
                and diagnostic['body_bytes'] == source['body_bytes'], 'FAILED_CALENDAR_CONSUMPTION_REQUIRED')
        original_state = 'FAILED_UNCHANGED_NO_NEW_RECEIPT'
    else:
        require(False, 'UNKNOWN_RAW_INTERPRETATION_KIND')
    contracts.decode(root, request, body.read_bytes())
    return dict(original_state=original_state, original_source_object=source['object_id'],
                original_request_hash=digest(member), original_retrieved_at=source['retrieved_at'],
                raw_reference=ref, original_receipt_changed=False, market_API=0)
