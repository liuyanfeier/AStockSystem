"""Atomic manual facts and account declarations; no inferred fills or broker orders."""
from datetime import datetime, timezone
import json
from pathlib import Path

from astock.data.warehouse_lock import warehouse_connection
from astock.decision.daily import DailyObservation, load_daily_profile
from astock.portfolio.models import ManualInput, PositionScope
from astock.research.core import digest, instant, require
from astock.research.journal import (
    JournalEvent, active_events, append_events_in_transaction, position_events, unreconciled_trades,
)
from astock.research.store import ResearchStore


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def input_context(root: Path, profile_path: Path):
    profile, instruction = load_daily_profile(
        root, profile_path, DailyObservation(observed_at=now_utc()))
    mode = 'USER_MANUAL' if instruction.mode == 'REAL_EVIDENCE' else 'SIMULATED'
    return profile, mode


def _state(events: list[dict], mode: str) -> dict:
    positions, _ = position_events(events)
    positions = {code: value for code, value in positions.items() if value['shares'] > 0}
    relevant = [e for e in events if e['kind'] in ('POSITION', 'ACCOUNT', 'EXECUTION') or
                e['kind'] == 'INPUT' and e.get('manual_input', {}).get('kind') != 'NOTE']
    for event in events:
        require(event.get('input_mode') in (None, mode), 'MANUAL_MIXED_ACCOUNT_MODE')
    return dict(mode=mode, position_hash=digest(relevant),
                positions=[dict(code=code, shares=event['shares'], event_at=event['event_at'],
                                source_event=event['event_id']) for code, event in sorted(positions.items())],
                pending_reconciliation=unreconciled_trades(events))


def preview_positions(root: Path, profile_path: Path) -> dict:
    profile, mode = input_context(root, profile_path)
    if not profile.journal_store.exists():
        return _state([], mode)
    store = ResearchStore(profile.journal_store)
    with warehouse_connection(store.path, read_only=True) as db:
        store._check(db)
        _, events = active_events(db, now_utc().isoformat())
    return _state(events, mode)


def receipt_id(request_id: str, mode: str) -> str:
    return digest(['MANUAL_INPUT_V1', mode, request_id, 'INPUT'])


def _receipt_result(event: dict) -> dict:
    request = event['manual_input']
    quantity = request['shares'] if request['kind'] == 'POSITION' else request['remaining_shares']
    return dict(request_id=request['request_id'], receipt_id=event['event_id'],
                mode=request['mode'], kind=request['kind'], code=request['code'],
                recorded_at=event['recorded_at'], position_updated=quantity is not None,
                shares_after=quantity, orders_created=0)


def existing_input(root: Path, profile_path: Path, request_id: str) -> dict | None:
    profile, mode = input_context(root, profile_path)
    if not profile.journal_store.exists():
        return None
    store = ResearchStore(profile.journal_store)
    with warehouse_connection(store.path, read_only=True) as db:
        store._check(db)
        row = db.execute('SELECT payload FROM research_journal WHERE id=?', [receipt_id(request_id, mode)]).fetchone()
    return _receipt_result(json.loads(row[0])) if row else None


def record_manual_input(root: Path, profile_path: Path, request: ManualInput) -> dict:
    profile, mode = input_context(root, profile_path)
    require(request.mode == mode, 'MANUAL_PROFILE_MODE')
    require(request.event_at <= now_utc(), 'MANUAL_FUTURE_FACT')
    store = ResearchStore(profile.journal_store)
    store.initialize()
    key = receipt_id(request.request_id, mode)
    with warehouse_connection(store.path) as db:
        store._check(db)
        db.execute('BEGIN')
        try:
            old = db.execute('SELECT payload FROM research_journal WHERE id=?', [key]).fetchone()
            if old:
                prior = JournalEvent.model_validate_json(old[0])
                require(prior.manual_input == request, 'MANUAL_REQUEST_ID_CONFLICT')
                db.execute('COMMIT')
                return _receipt_result(json.loads(old[0]))
            recorded = now_utc()
            _, active = active_events(db, recorded.isoformat())
            state = _state(active, mode)
            receipts = [e for e in active if e['kind'] == 'INPUT']
            require(all(instant(e['recorded_at']) < recorded for e in receipts), 'MANUAL_CLOCK_NOT_ADVANCING')
            if request.kind != 'NOTE':
                require(request.expected_position_hash == state['position_hash'], 'MANUAL_PREVIEW_CHANGED')
            base = dict(code=request.code, event_at=request.event_at, recorded_at=recorded,
                        input_mode=mode, confirmed=True)
            events = [JournalEvent(event_id=key, kind='INPUT', manual_input=request, **base)]
            role = lambda name: digest(['MANUAL_INPUT_V1', mode, request.request_id, name])
            positions, _ = position_events(active)
            quantity = request.shares if request.kind == 'POSITION' else request.remaining_shares
            if request.kind == 'NOTE':
                events.append(JournalEvent(event_id=role('NOTE'), kind='REVIEW', notes=request.note, **base))
            if request.kind == 'EXECUTION':
                events.append(JournalEvent(event_id=role('EXECUTION'), kind='EXECUTION', shares=request.shares,
                                           price_cny=float(request.price_cny),
                                           notes=f'{request.side}；用户补录实际成交；{request.note}', **base))
            if quantity is not None:
                prior_position = positions.get(request.code)
                require(prior_position is None or instant(prior_position['event_at']) <= request.event_at,
                        'MANUAL_POSITION_BEFORE_LATEST')
                inherited = {name: prior_position.get(name) if prior_position else None for name in (
                    'research_report_id', 'thesis', 'invalidation', 'exit_conditions', 'review_due', 'risk_plan')}
                for name in ('thesis', 'invalidation', 'exit_conditions'):
                    if getattr(request, name) is not None:
                        inherited[name] = getattr(request, name)
                position = JournalEvent(event_id=role('POSITION'), kind='POSITION', shares=quantity,
                                        notes=request.note, **inherited, **base)
                events.append(position)
                positions[request.code] = position.model_dump(mode='json')
            projected = sorted([*active, *[e.model_dump(mode='json') for e in events]],
                               key=lambda e: (instant(e['event_at']), instant(e['recorded_at']), e['event_id']))
            if request.kind != 'NOTE':
                require(not request.complete_positions_confirmed or not unreconciled_trades(projected),
                        'MANUAL_UNRECONCILED_ACCOUNT')
                scope = PositionScope(mode=mode, snapshot_at=recorded.isoformat(),
                                      position_event_ids=sorted(e['event_id'] for e in positions.values() if e['shares'] > 0),
                                      complete_positions_confirmed=request.complete_positions_confirmed,
                                      cash_cny=request.cash_cny, cash_confirmed=request.cash_confirmed)
                events.append(JournalEvent(event_id=role('ACCOUNT'), kind='ACCOUNT', code='__ACCOUNT__',
                                           event_at=recorded, recorded_at=recorded, input_mode=mode,
                                           position_scope=scope, confirmed=True,
                                           notes='本次用户对已报列表的范围声明；非券商同步，不继承旧现金/完整性确认'))
            append_events_in_transaction(db, events)
            db.execute('COMMIT')
            return _receipt_result(events[0].model_dump(mode='json'))
        except Exception:
            db.execute('ROLLBACK')
            raise


def resolve_position_scope(store: ResearchStore, as_of: str, mode: str,
                           fallback: PositionScope | None = None) -> PositionScope | None:
    expected = 'USER_MANUAL' if mode == 'REAL_EVIDENCE' else 'SIMULATED'
    with warehouse_connection(store.path, read_only=True) as db:
        store._check(db)
        _, events = active_events(db, as_of)
    _state(events, expected)
    accounts = [JournalEvent.model_validate(e) for e in events if e['kind'] == 'ACCOUNT']
    selected = max(accounts, key=lambda e: (e.recorded_at, e.event_id)).position_scope if accounts else None
    if selected and fallback and instant(fallback.snapshot_at) > instant(selected.snapshot_at):
        selected = fallback
    selected = selected or fallback
    require(selected is None or selected.mode == expected, 'MANUAL_ACCOUNT_SCOPE_MODE')
    return selected
