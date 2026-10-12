"""Bounded research capture: dry-run first, immutable claims, one attempt per member."""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
from pathlib import Path
import subprocess
import time
from typing import Literal

import httpx
from pydantic import AwareDatetime, Field, SecretStr, model_validator

from astock.data.full_backfill_v1 import secret_present
from astock.data.warehouse_lock import warehouse_lock
from astock.research.core import code_fingerprint, digest, encoded, instant, market_day, private_path, read_json, require
from astock.research.inputs import Bundle, SourceFile, StrictModel, records
from astock.research.publication import publish_bytes
from astock.research.tushare import DATASETS, decode_response, validate_member

ENDPOINT = 'https://api.tushare.pro'


class CapturePlan(StrictModel):
    protocol: Literal['RESEARCH_CAPTURE_V1_1']
    purpose: Literal['CURRENT_OBSERVATION']
    execution_authorized: Literal[False] = False
    endpoint: Literal['https://api.tushare.pro'] = ENDPOINT
    destination: str
    window_start: date
    window_end: date
    not_before: AwareDatetime
    universe: list[str] = Field(min_length=1)
    benchmarks: list[str]
    benchmark_calendars: dict[str, Literal['SSE', 'SZSE']]
    expected_min_sessions: int = Field(ge=60, le=250)
    members: list[dict] = Field(min_length=1, max_length=100)
    maximum_requests: int = Field(ge=1, le=100)
    maximum_attempts: int = Field(ge=1, le=100)
    max_body_bytes: int = Field(ge=1024, le=2 * 1024**2)
    max_total_body_bytes: int = Field(ge=1024, le=100 * 1024**2)
    max_added_disk_bytes: int = Field(ge=1024**2, le=256 * 1024**2)
    min_spacing_seconds: float = Field(ge=1.25, le=60, allow_inf_nan=False)
    retries: Literal[0] = 0
    redirects: Literal[0] = 0

    @model_validator(mode='after')
    def scope(self):
        require(self.window_start <= self.window_end and market_day(self.not_before) >= self.window_end, 'PLAN_WINDOW')
        codes = self.universe + self.benchmarks
        require(len(set(codes)) == len(codes) and all(c and c.strip() == c for c in codes), 'PLAN_IDENTITIES')
        require(set(self.benchmark_calendars) == set(self.benchmarks), 'PLAN_BENCHMARK_CALENDAR')
        require(len(self.members) == self.maximum_requests == self.maximum_attempts, 'PLAN_COUNT')
        require(len({digest(m) for m in self.members}) == len(self.members), 'PLAN_MEMBER_DUPLICATE')
        require(self.max_total_body_bytes <= self.maximum_requests * self.max_body_bytes and
                self.max_added_disk_bytes >= 2 * self.max_total_body_bytes + 32 * 1024**2, 'PLAN_PEAK_BUDGET')
        for member in self.members:
            validate_member(member)
            p = member['params']
            if 'start_date' in p:
                require(self.window_start <= date_from(p['start_date']) <= date_from(p['end_date']) <= self.window_end, 'PLAN_MEMBER_WINDOW')
            if 'trade_date' in p:
                require(self.window_start <= date_from(p['trade_date']) <= self.window_end, 'PLAN_MEMBER_DATE')
            if 'ts_code' in p:
                expected = self.benchmarks if member['api'].startswith('index_') else self.universe
                require(set(p['ts_code'].split(',')) <= set(expected), 'PLAN_MEMBER_UNIVERSE')
        return self


def implementation_hash() -> str:
    package = Path(__file__).resolve().parents[1]
    root = package.parents[1]
    dependencies = [package / p for p in ('data/raw_writer.py', 'data/raw_validation.py',
                    'data/full_backfill_v1.py', 'data/warehouse_lock.py', 'cli/research.py', 'settings.py', 'paths.py')]
    return digest(dict(research=code_fingerprint(), dependencies={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [*dependencies, root / 'uv.lock']}))


def capture_status(destination: Path) -> dict:
    plan, receipts = read_capture(destination)
    states = {'COMPLETE': 0, 'FAILED': 0, 'UNKNOWN': 0, 'UNATTEMPTED': 0}
    for m in plan.members:
        key = digest(m)
        claim, terminal = destination / f'{key}.claim.json', destination / f'{key}.result.json'
        state = read_json(terminal)['state'] if terminal.exists() else 'UNKNOWN' if claim.exists() else 'UNATTEMPTED'
        states[state] += 1
    return dict(plan_hash=digest(plan.model_dump(mode='json')), states=states, verified_receipts=len(receipts),
                remaining_member_ids=[digest(m) for m in plan.members if not (destination / f'{digest(m)}.claim.json').exists()])


def date_from(value: str) -> date:
    from astock.research.core import day
    return day(value)


def payload_rows(plan: CapturePlan, member: dict, body: bytes, captured: str) -> list[dict]:
    api = member['api']
    spec = SourceFile(path='unused', sha256=hashlib.sha256(body).hexdigest(), dataset=DATASETS[api],
                      format='json', adapter='tushare-response-v1', request=member, source='capture validation',
                      retrieved_at=captured, available_at=captured,
                      calendar_exchange=plan.benchmark_calendars.get(member['params'].get('ts_code')),
                      volume_unit='lots100' if api in {'daily', 'index_daily'} else None,
                      amount_unit='thousand_CNY' if api in {'daily', 'index_daily'} else None)
    bundle = Bundle(protocol='RESEARCH_INPUT_V1', purpose='CURRENT_OBSERVATION', window_start=plan.window_start,
                    window_end=plan.window_end, universe=plan.universe, benchmarks=plan.benchmarks,
                    universe_scope='WATCHLIST', files=[spec])
    parsed = records(spec, body, bundle)
    if api == 'trade_cal':
        start, end = date_from(member['params']['start_date']), date_from(member['params']['end_date'])
        require(len(parsed) == (end - start).days + 1, 'CAPTURE_CALENDAR_INCOMPLETE')
    if api in {'stock_basic', 'index_basic'}:
        require(len(parsed) == 1 and parsed[0]['code'] == member['params']['ts_code'], 'CAPTURE_IDENTITY_INCOMPLETE')
    return parsed


def disk_bytes(destination: Path) -> int:
    total = 0
    for path in destination.rglob('*'):
        require(not path.is_symlink(), 'CAPTURE_SYMLINK')
        if path.is_file():
            total += path.stat().st_size
    return total


def read_capture(destination: Path) -> tuple[CapturePlan, list[dict]]:
    plan = CapturePlan.model_validate(read_json(destination / 'plan.json'))
    receipts = []
    for member in plan.members:
        key = digest(member)
        claim, terminal = destination / f'{key}.claim.json', destination / f'{key}.result.json'
        if not claim.exists():
            require(not terminal.exists(), 'CAPTURE_RESULT_WITHOUT_CLAIM')
            continue
        require(not claim.is_symlink() and not terminal.is_symlink(), 'CAPTURE_SYMLINK')
        c = read_json(claim)
        require(c['plan_hash'] == digest(plan.model_dump(mode='json')) and c['member'] == member, 'CAPTURE_CLAIM_CHANGED')
        approval_path = destination / f"{c['approval_hash']}.approval.json"
        require(approval_path.is_file() and not approval_path.is_symlink(), 'CAPTURE_APPROVAL_MISSING')
        a = read_json(approval_path)
        require(digest(a) == c['approval_hash'] and a['plan_hash'] == c['plan_hash'] and key in a['member_ids'], 'CAPTURE_APPROVAL_CHANGED')
        if not terminal.exists():
            continue  # durable UNKNOWN; never eligible for resend
        r = read_json(terminal)
        require(r['member'] == member and r['claim_hash'] == hashlib.sha256(claim.read_bytes()).hexdigest(), 'CAPTURE_RESULT_CHANGED')
        require(r['state'] in {'COMPLETE', 'FAILED', 'UNKNOWN'}, 'CAPTURE_STATE')
        require(r['transport'] == ('MOCK' if a['fixture_only'] else 'HTTPS_TLS'), 'CAPTURE_TRANSPORT_BINDING')
        if r['state'] != 'COMPLETE':
            continue
        require(r['object'] == f'{key}.response.json', 'CAPTURE_OBJECT_PATH')
        path = destination / r['object']
        require(path.is_file() and not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == r['sha256'], 'CAPTURE_OBJECT_CHANGED')
        require(instant(r['available_at']) >= instant(r['retrieved_at']) >= instant(c['claimed_at']), 'CAPTURE_TIME_ORDER')
        payload_rows(plan, member, path.read_bytes(), r['retrieved_at'])
        receipts.append({**r, 'receipt_file': terminal.name, 'receipt_hash': hashlib.sha256(terminal.read_bytes()).hexdigest()})
    return plan, receipts


def capture(root: Path, plan_file: Path, *, live: bool = False, approval_file: Path | None = None,
            transport: httpx.MockTransport | None = None, token: SecretStr | None = None,
            now=None, sleep=time.sleep) -> dict:
    plan = CapturePlan.model_validate(read_json(plan_file))
    public = plan.model_dump(mode='json')
    plan_hash = digest(public)
    if not live:
        return dict(mode='DRY_RUN', plan_hash=plan_hash, implementation_hash=implementation_hash(), plan=public, market_requests=0)
    require(approval_file is not None, 'HUMAN_APPROVAL_REQUIRED')
    destination = private_path(root, root / plan.destination)
    clock = now or (lambda: datetime.now(timezone.utc))
    approval = read_json(approval_file)
    fixture = transport is not None
    require(not fixture or isinstance(transport, httpx.MockTransport), 'MOCK_TRANSPORT_REQUIRED')
    require(set(approval) == {'protocol', 'plan_hash', 'destination', 'implementation_hash', 'authorized_by',
                             'approved_at', 'expires_at', 'member_ids', 'fixture_only', 'execution_authorized'}, 'APPROVAL_SHAPE')
    require(approval['protocol'] == 'RESEARCH_CAPTURE_APPROVAL_V1_1' and approval['plan_hash'] == plan_hash and
            approval['destination'] == str(destination) and approval['implementation_hash'] == implementation_hash() and
            approval['execution_authorized'] is True and approval['fixture_only'] is fixture and
            approval['authorized_by'] == ('SYNTHETIC_TEST' if fixture else 'HUMAN'), 'APPROVAL_MISMATCH')
    require(instant(approval['approved_at']) <= clock() <= instant(approval['expires_at']) and
            clock() >= instant(plan.not_before), 'APPROVAL_TIME')
    if not fixture:
        # Real execution is reproducible at a clean, committed implementation.
        require(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root) == b'', 'LIVE_DIRTY_WORKTREE')
        from astock.settings import load_settings
        token = load_settings(root).tushare_token
    require(token is not None and bool(token.get_secret_value()), 'TOKEN_REQUIRED')
    secret = token.get_secret_value()
    destination.mkdir(parents=True, exist_ok=True)
    with warehouse_lock(destination / 'capture'):
        publish_bytes(destination / 'plan.json', encoded(public))
        read_capture(destination)  # inspect all existing consumption before any new claim
        remaining = [m for m in plan.members if not (destination / f'{digest(m)}.claim.json').exists()]
        require(approval['member_ids'] == [digest(m) for m in remaining] and bool(remaining), 'APPROVAL_UNATTEMPTED_MEMBERS')
        publish_bytes(destination / f'{digest(approval)}.approval.json', encoded(approval))
        consumed = sum((destination / f'{digest(m)}.claim.json').exists() for m in plan.members)
        # Failed/unknown transfer sizes are unknowable: reserve their entire cap.
        charged = consumed * plan.max_body_bytes
        completed, stopped = 0, None
        latest_observed = max([instant(plan.not_before), instant(approval['approved_at']),
                               *[instant(read_json(p)['claimed_at']) for p in destination.glob('*.claim.json')],
                               *[instant(r['retrieved_at']) for r in read_capture(destination)[1]]])
        with httpx.Client(transport=transport, verify=True, follow_redirects=False, trust_env=False,
                          timeout=httpx.Timeout(30), limits=httpx.Limits(max_connections=1)) as client:
            for member in remaining:
                claim_time = instant(clock())
                require(latest_observed <= claim_time <= instant(approval['expires_at']), 'APPROVAL_EXPIRED_OR_CLOCK_ROLLBACK')
                require(consumed < plan.maximum_attempts and charged + plan.max_body_bytes <= plan.max_total_body_bytes, 'CAPTURE_BUDGET')
                # Two body copies plus derivation/headroom; no call when local peak cannot fit.
                require(disk_bytes(destination) + 2 * plan.max_body_bytes + 32 * 1024**2 <= plan.max_added_disk_bytes, 'CAPTURE_DISK_BUDGET')
                key = digest(member)
                claim_path = destination / f'{key}.claim.json'
                claim = dict(plan_hash=plan_hash, member=member, claimed_at=claim_time.isoformat(), approval_hash=digest(approval))
                publish_bytes(claim_path, encoded(claim))  # irrevocable UNKNOWN BEFORE transport
                consumed += 1
                charged += plan.max_body_bytes
                state, code, body, captured = 'UNKNOWN', 'TRANSPORT_UNCERTAIN', b'', None
                try:
                    with client.stream('POST', ENDPOINT, json=dict(api_name=member['api'], token=secret,
                                      params=member['params'], fields=','.join(member['fields']))) as response:
                        require(response.status_code == 200, 'HTTP_STATUS')
                        chunks, size = [], 0
                        # Raw transfer cap prevents compressed-body amplification bypass.
                        require(response.headers.get('content-encoding', 'identity') == 'identity', 'COMPRESSED_BODY_REJECTED')
                        for chunk in response.iter_raw(chunk_size=16384):
                            size += len(chunk)
                            require(size <= plan.max_body_bytes, 'CAPTURE_BODY_CAP')
                            chunks.append(chunk)
                        body = b''.join(chunks)
                    captured = instant(clock()).isoformat()
                    require(instant(captured) >= instant(claim['claimed_at']), 'CAPTURE_CLOCK_ROLLBACK')
                    require(not secret_present(body, secret), 'CAPTURE_SECRET')
                    payload_rows(plan, member, body, captured)
                    publish_bytes(destination / f'{key}.response.json', body)
                    state, code = 'COMPLETE', None
                except Exception as error:
                    from astock.research.core import ResearchError
                    if isinstance(error, ResearchError):
                        state, code = 'FAILED', str(error)
                    # Native exception bodies can contain credential/request context: never retain them.
                result = dict(member=member, claim_hash=hashlib.sha256(claim_path.read_bytes()).hexdigest(),
                              state=state, error=code, transport='MOCK' if fixture else 'HTTPS_TLS')
                if state == 'COMPLETE':
                    result.update(object=f'{key}.response.json', sha256=hashlib.sha256(body).hexdigest(),
                                  retrieved_at=captured, available_at=captured)
                publish_bytes(destination / f'{key}.result.json', encoded(result))
                if state != 'COMPLETE':
                    stopped = state
                    break
                latest_observed = instant(captured)
                completed += 1
                if completed < len(remaining):
                    sleep(plan.min_spacing_seconds)
        return dict(mode='MOCK' if fixture else 'LIVE', plan_hash=plan_hash, complete_this_run=completed,
                    consumed_total=consumed, stopped=stopped, unattempted=plan.maximum_requests - consumed)
