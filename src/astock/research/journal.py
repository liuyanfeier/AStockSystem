"""Append-only manual plans/positions/executions/exits/reviews, never broker integration."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from astock.data.warehouse_lock import warehouse_connection
from astock.research.core import day, digest, encoded, instant, market_day, read_json, require
from astock.research.inputs import StrictModel
from astock.research.store import ResearchStore
from astock.portfolio.models import ManualInput, PositionScope
from astock.decision.plan_models import PlanRecord


class JournalEvent(StrictModel):
    event_id: str = Field(min_length=1, max_length=100)
    kind: Literal["PLAN", "POSITION", "EXECUTION", "EXIT", "REVIEW", "ACCOUNT", "INPUT", "RESEARCH_INPUT"]
    code: str = Field(min_length=1, max_length=40)
    event_at: AwareDatetime
    recorded_at: AwareDatetime
    research_report_id: str | None = None
    shares: int | None = Field(default=None, ge=0)
    price_cny: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    thesis: str | None = Field(default=None, min_length=1)
    invalidation: str | None = Field(default=None, min_length=1)
    exit_conditions: str | None = Field(default=None, min_length=1)
    review_due: AwareDatetime | None = None
    risk_plan: str | None = Field(default=None, min_length=1)
    confirmed: bool = False
    notes: str = ""
    correction_of: str | None = None
    input_mode: Literal['USER_MANUAL', 'SIMULATED'] | None = None
    position_scope: PositionScope | None = None
    manual_input: ManualInput | None = None
    research_input: PlanRecord | None = None
    # User prose records a plan; no executable risk parameters, account or order fields.

    @model_validator(mode="after")
    def valid_time(self):
        require(self.recorded_at >= self.event_at, "JOURNAL_BACKDATED")
        require(self.kind != "POSITION" or self.shares is not None, "POSITION_SHARES_REQUIRED")
        if self.kind == 'ACCOUNT':
            require(self.position_scope is not None and self.code == '__ACCOUNT__', 'JOURNAL_ACCOUNT_REQUIRED')
            require(self.input_mode == self.position_scope.mode, 'JOURNAL_ACCOUNT_MODE')
        else:
            require(self.position_scope is None, 'JOURNAL_ACCOUNT_KIND')
        if self.kind == 'INPUT':
            require(self.manual_input is not None and self.manual_input.code == self.code, 'JOURNAL_INPUT_REQUIRED')
            require(self.input_mode == self.manual_input.mode and self.event_at == self.manual_input.event_at,
                    'JOURNAL_INPUT_BINDING')
        else:
            require(self.manual_input is None, 'JOURNAL_INPUT_KIND')
        if self.kind == 'RESEARCH_INPUT':
            require(self.research_input is not None and self.research_input.request.code == self.code,
                    'JOURNAL_RESEARCH_INPUT_REQUIRED')
            require(self.input_mode == self.research_input.request.mode and self.event_at == self.recorded_at,
                    'JOURNAL_RESEARCH_INPUT_BINDING')
            require(not self.research_input.plan or instant(self.research_input.plan.created_at) == self.recorded_at,
                    'JOURNAL_RESEARCH_CREATED_TIME')
            require(not self.research_input.review or instant(self.research_input.review.recorded_at) == self.recorded_at,
                    'JOURNAL_RESEARCH_REVIEW_TIME')
            require(self.correction_of is None, 'PLAN_RECORD_IMMUTABLE')
        else:
            require(self.research_input is None, 'JOURNAL_RESEARCH_INPUT_KIND')
        return self


def append_event(store: ResearchStore, path: Path) -> str:
    event = JournalEvent.model_validate(read_json(path))
    append_events(store, [event])
    return event.event_id


def append_events(store: ResearchStore, events: list[JournalEvent]) -> list[str]:
    store.initialize()
    with warehouse_connection(store.path) as db:
        store._check(db)
        db.execute('BEGIN')
        try:
            result = append_events_in_transaction(db, events)
            db.execute('COMMIT')
            return result
        except Exception:
            db.execute('ROLLBACK')
            raise


def append_events_in_transaction(db, events: list[JournalEvent]) -> list[str]:
    """Caller owns a managed write connection and transaction; all inserts roll back together."""
    require(len({e.event_id for e in events}) == len(events), 'JOURNAL_DUPLICATE_BATCH_ID')
    for event in events:
        _append_one(db, event)
    return [e.event_id for e in events]


def _append_one(db, event: JournalEvent) -> None:
    payload = event.model_dump(mode="json")
    key = event.event_id
    old = db.execute("SELECT payload FROM research_journal WHERE id=?", [key]).fetchone()
    if old:
        require(JournalEvent.model_validate(json.loads(old[0])).model_dump(mode="json") == payload, "JOURNAL_ID_CONFLICT")
        return
    if event.correction_of:
        target = db.execute('SELECT payload FROM research_journal WHERE id=?', [event.correction_of]).fetchone()
        require(event.correction_of != key and target is not None, 'CORRECTION_TARGET_REQUIRED')
        original = JournalEvent.model_validate_json(target[0])
        require(event.kind == original.kind and event.code == original.code, 'CORRECTION_KIND_CODE')
        require(event.input_mode == original.input_mode, 'CORRECTION_MODE')
        require(event.recorded_at >= original.recorded_at, 'CORRECTION_BEFORE_TARGET')
        bodies = db.execute('SELECT payload FROM research_journal').fetchall()
        require(not any(json.loads(body[0]).get('correction_of') == event.correction_of for body in bodies),
                'CORRECTION_ALREADY_REPLACED')
    if event.research_report_id:
        require(db.execute("SELECT 1 FROM research_report WHERE id=?", [event.research_report_id]).fetchone() is not None,
                "JOURNAL_REPORT_UNKNOWN")
    db.execute("INSERT INTO research_journal VALUES (?,?,?,?)",
               [key, event.event_at, event.recorded_at, encoded(payload).decode()])


def active_events(db, as_of: str) -> tuple[list[dict], list[dict]]:
    cutoff = instant(as_of)
    rows = db.execute('SELECT payload FROM research_journal WHERE event_at<=? AND available_at<=? ORDER BY event_at,available_at,id',
                      [cutoff, cutoff]).fetchall()
    events = [json.loads(row[0]) for row in rows]
    by_id = {e['event_id']: e for e in events}
    for event in events:
        if event.get('correction_of'):
            target = by_id.get(event['correction_of'])
            require(target is not None and (event['kind'], event['code']) == (target['kind'], target['code']),
                    'CORRECTION_KIND_CODE')
    corrected = {e['correction_of'] for e in events if e.get('correction_of')}
    return events, [e for e in events if e['event_id'] not in corrected]


def position_events(events: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    positions, original = {}, {}
    for event in events:
        if event['kind'] == 'POSITION':
            positions[event['code']] = event
            if event['shares'] == 0:
                original.pop(event['code'], None)
            else:
                original.setdefault(event['code'], event)
    return positions, original


def unreconciled_trades(events: list[dict]) -> list[str]:
    positions, _ = position_events(events)
    pending = set()
    for event in events:
        request = event.get('manual_input')
        if event['kind'] != 'INPUT' or not request or request['kind'] != 'EXECUTION' or request['remaining_shares'] is not None:
            continue
        position = positions.get(event['code'])
        if (position is None or instant(position['event_at']) < instant(event['event_at'])
                or instant(position['recorded_at']) < instant(event['recorded_at'])):
            pending.add(event['code'])
    return sorted(pending)


def journal_snapshot(store: ResearchStore, as_of: str, instruments: dict, max_stale_days: int = 7) -> dict:
    cutoff = instant(as_of)
    with warehouse_connection(store.path, read_only=True) as db:
        events, active = active_events(db, as_of)
    positions, original = position_events(active)
    pending = unreconciled_trades(active)
    reports = {}
    with warehouse_connection(store.path, read_only=True) as db:
        for event in active:
            ref = event.get("research_report_id")
            if ref and ref not in reports:
                row = db.execute("SELECT snapshot FROM research_report WHERE id=?", [ref]).fetchone()
                snapshot = json.loads(row[0]) if row else None
                require(snapshot is not None and digest(snapshot) == ref, "JOURNAL_REPORT_CHANGED")
                if instant(snapshot["as_of"]) <= cutoff:
                    reports[ref] = snapshot
    holdings = []
    for code, event in sorted(positions.items()):
        if event["shares"] == 0:
            continue
        stock = instruments.get(code)
        initial = original[code]
        ref = initial.get("research_report_id")
        research = reports.get(ref)
        gaps = ["人工快照非券商同步；未据成交日志自动推算持仓", "T+1可卖数量/现金/组合风险参数尚未设置"]
        for field, label in (("thesis", "原始投资逻辑"), ("invalidation", "逻辑失效条件"),
                             ("exit_conditions", "退出观察条件"), ("risk_plan", "用户风险计划")):
            if not event.get(field):
                gaps.append(f"缺少{label}，待补录")
        if not initial.get("thesis"):
            gaps.append("最初持仓缺少原始逻辑，后续文本不能冒充当时研究")
        if research is None:
            gaps.append("原始研究版本未关联或截至时不可核验")
        research_stale = None if research is None else (market_day(cutoff) - day(research["window_end"])).days > max_stale_days
        if research_stale:
            gaps.append("原始研究行情已陈旧，需要复盘；不代表应卖出")
        if event.get("exit_conditions"):
            gaps.append("用户退出观察条件待核实；未自动判定成立")
        if not event.get("confirmed", False):
            gaps.append("人工持仓事件待用户确认")
        if code in pending:
            gaps.append('有成交记录尚未补录成交后持仓；当前股数不能视为已对账')
        holdings.append(dict(code=code, shares=event["shares"], thesis=event["thesis"],
                             invalidation=event["invalidation"], exit_conditions=event["exit_conditions"],
                             original_thesis=initial.get("thesis"), original_research_report_id=ref,
                             current_research_report_id=event.get("research_report_id"), research_stale=research_stale,
                             risk_plan=event.get("risk_plan"), confirmed=event.get("confirmed", False),
                             exit_condition_state="PENDING_VERIFICATION", review_due=event["review_due"],
                             review_overdue=bool(event["review_due"] and instant(event["review_due"]) <= cutoff),
                             latest_price=stock.get("close") if stock else None,
                             price_date=stock.get("last_date") if stock else None,
                             gaps=gaps,
                             source_event=event["event_id"]))
    return dict(events=events, events_hash=digest(events), positions=holdings,
                unreconciled_trades=pending,
                pending_confirmation=[e["event_id"] for e in active if not e.get("confirmed", False)],
                limitation="未导入记录不等于没有持仓；EXECUTION/EXIT为日志，不擅自重算账户或生成订单")
