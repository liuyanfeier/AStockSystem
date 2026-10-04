"""Exact unlicensed SZSE metadata proposal and closed synthetic validation only."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from astock.data import admission_offline as offline
from astock.data.raw_validation import sha256
from astock.data.raw_writer import atomic_new_file
from astock.data.reconstruction import checksum
from astock.data.warehouse_lock import require_writer

PROTOCOL = 'ADMISSION_SZSE_METADATA_PROPOSAL_V1'
CONTRACT_BYTES = 'f1d8cc3b7147df703443c7fbff5669be0aaf3cf9d973a93fb0618e821c1cef11'
WINDOWS = (('20130104', '20130108'), ('20200821', '20200825'),
           ('20211112', '20211116'), ('20250430', '20250507'),
           ('20250930', '20251010'), ('20260703', '20260707'),
           ('20260928', '20260930'))
FIELDS = ['exchange', 'cal_date', 'is_open', 'pretrade_date']


def _day(value: str):
    if type(value) is not str or not re.fullmatch(r'[0-9]{8}', value):
        raise ValueError('Expected YYYYMMDD string')
    return datetime.strptime(value, '%Y%m%d').date()


def build_plan(root: Path) -> dict:
    path = root / 'config/contracts/v2/trade_cal.yaml'
    if sha256(path) != CONTRACT_BYTES:
        raise ValueError('Reviewed contract bytes changed')
    contract = yaml.safe_load(path.read_text())
    requests = []
    for start, end in WINDOWS:
        wire = dict(method='POST', endpoint='https://api.tushare.pro',
                    api_name='trade_cal', params=dict(exchange='SZSE', start_date=start, end_date=end),
                    fields=','.join(FIELDS), contract_version='2.0',
                    contract_bytes_sha256=CONTRACT_BYTES, contract_canonical_hash=checksum(contract))
        requests.append(dict(request_id=checksum(dict(protocol=PROTOCOL, wire=wire)), wire=wire,
                             expected_civil_rows=(_day(end)-_day(start)).days+1, max_attempts=1))
    return dict(protocol=PROTOCOL, execution_license=False, requests=requests,
                membership_hash=checksum(sorted(r['request_id'] for r in requests)),
                market_request_budget=7, min_start_interval_seconds=1.25,
                unknown_call='STOP_NO_AUTOMATIC_RETRY', provider_cap='UNKNOWN',
                destination='data/private/phase1c1-admission-metadata/<independently-approved-run>',
                context_integration='EXTERNAL_EVIDENCE_ONLY_REQUIRES_SEPARATE_APPROVAL_NOT_133_INPUTS')


def validate_plan(root: Path, plan: dict) -> None:
    if plan != build_plan(root):
        raise ValueError('Exact unlicensed metadata plan differs')


def validate_response(request: dict, payload: bytes) -> list[dict]:
    table = json.loads(payload)
    if not isinstance(table, dict) or set(table) != {'fields', 'items'} or table['fields'] != FIELDS:
        raise ValueError('Calendar response fields differ')
    start, end = (_day(request['wire']['params'][k]) for k in ('start_date', 'end_date'))
    expected = {(start+timedelta(days=i)).strftime('%Y%m%d') for i in range((end-start).days+1)}
    rows, seen = [], set()
    if not isinstance(table['items'], list):
        raise ValueError('Invalid calendar row collection')
    for values in table['items']:
        if not isinstance(values, list) or len(values) != len(FIELDS):
            raise ValueError('Invalid calendar row width')
        row = dict(zip(FIELDS, values))
        day, previous = _day(row['cal_date']), _day(row['pretrade_date'])
        if (row['exchange'] != 'SZSE' or type(row['is_open']) is not int or row['is_open'] not in (0, 1)
                or previous >= day or row['cal_date'] not in expected or row['cal_date'] in seen):
            raise ValueError('Invalid calendar value or duplicate/outside membership')
        seen.add(row['cal_date'])
        rows.append(row)
    if seen != expected:
        raise ValueError('Calendar civil-date completeness unknown')
    return rows


def capture_fake(root: Path, db, destination: Path, plan: dict, request_id: str,
                 transport: offline.FakeTransport, *, observe_claim=lambda: None) -> str:
    """Reuse durable lifecycle, never accept a callable or live transport adapter."""
    require_writer(db)
    validate_plan(root, plan)
    if type(transport) is not offline.FakeTransport:
        raise ValueError('Closed fake transport required')
    requests = [r for r in plan['requests'] if r['request_id'] == request_id]
    if len(requests) != 1:
        raise ValueError('Unknown exact metadata member')
    request = requests[0]
    plan_id = checksum(dict(membership=plan['membership_hash'], request=request))
    if not db.execute('SELECT 1 FROM offline_plan WHERE plan_id=?', [plan_id]).fetchone():
        offline.plan(db, plan_id)
    history = offline.events(db, plan_id)
    if history:
        if history[-1][0] != 'COMPLETE':
            raise ValueError('Consumed/uncertain metadata claim; no resend')
        result = offline.complete_capture(db, destination, plan_id)
    else:
        if not transport.fail:
            validate_response(request, transport.payload)
        result = offline.capture(db, destination, plan_id, transport, observe_claim=observe_claim)
    row = db.execute('SELECT * FROM offline_raw_manifest WHERE plan_id=?', [plan_id]).fetchone()
    path = destination / row[2]
    rows = validate_response(request, path.read_bytes())
    metadata = dict(protocol=PROTOCOL, synthetic=True, execution_license=False, request=request,
                    membership_hash=plan['membership_hash'], object_id=str(row[1]),
                    bytes_sha256=sha256(path), rows=len(rows), retrieved_at=row[4].isoformat(),
                    available_at=row[5].isoformat(), verified_at=row[6].isoformat(),
                    session_certification='NONE_SYNTHETIC_ONLY')
    sidecar = destination / (checksum(plan_id)+'.metadata.json')
    if sidecar.exists():
        if sidecar.is_symlink() or json.loads(sidecar.read_text()) != metadata:
            raise ValueError('Metadata sidecar changed')
    else:
        atomic_new_file(sidecar, lambda p: p.write_text(json.dumps(metadata, sort_keys=True)+'\n'))
    return result


def full_history_budget(verified_reuse: int) -> dict:
    if type(verified_reuse) is not int or not 0 <= verified_reuse <= 126:
        raise ValueError('Exact verified reuse must be in0..126')
    gross = 5021 * 6
    net = gross - verified_reuse
    return dict(gross_base= gross, reuse_candidates=126, verified_reuse=verified_reuse,
                net_base=net, net_if_all_candidates_verified=30000, reserve=0,
                pacing_start_span_lower_bound_seconds=max(net-1, 0)*1.25,
                response_latency_and_runtime='UNKNOWN', additional_splits='UNKNOWN_NOT_INCLUDED',
                future_annual_calendar_requests=28, bounded_metadata_requests=7, execution_license=False)


def validate_packet(packet: dict, context: dict, checklist: dict, context_ref: dict) -> None:
    """Fail closed on stale proposal entry points; never grant approval."""
    if packet['context_proposal'] != context_ref or context_ref['canonical_hash'] != checksum(context):
        raise ValueError('Final Context pointer/hash differs')
    if not re.fullmatch(r'[0-9a-f]{40}', context.get('implementation_sha') or ''):
        raise ValueError('Missing implementation pin')
    for name in ('implementation_sha', 'design_hash', 'policy_hash', 'input_set_hash', 'candidate_resolver_hash', 'delta_hash'):
        if packet['pins'].get(name) != context.get(name):
            raise ValueError('Context pin differs: '+name)
    for proposal in (packet, context):
        if any(proposal.get(k) is not None for k in ('approved_at', 'review_ref', 'reviewed_sha')):
            raise ValueError('Author cannot populate production approval')
        if proposal.get('execution_license') is not False:
            raise ValueError('Proposal is not explicitly unlicensed')
    preservation = [i for i in checklist['items'] if i['condition']=='Original preservation']
    if len(preservation)!=1 or preservation[0]['status']!='AUTHOR_VERIFIED_PASS' or not preservation[0]['evidence']:
        raise ValueError('Final preservation proof missing/pending')
