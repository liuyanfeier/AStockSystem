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


class JournalEvent(StrictModel):
    event_id: str = Field(min_length=1, max_length=100)
    kind: Literal["PLAN", "POSITION", "EXECUTION", "EXIT", "REVIEW"]
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
    # User prose records a plan; no executable risk parameters, account or order fields.

    @model_validator(mode="after")
    def valid_time(self):
        require(self.recorded_at >= self.event_at, "JOURNAL_BACKDATED")
        require(self.kind != "POSITION" or self.shares is not None, "POSITION_SHARES_REQUIRED")
        return self


def append_event(store: ResearchStore, path: Path) -> str:
    event = JournalEvent.model_validate(read_json(path))
    payload = event.model_dump(mode="json")
    key = event.event_id
    store.initialize()
    with warehouse_connection(store.path) as db:
        store._check(db)
        old = db.execute("SELECT payload FROM research_journal WHERE id=?", [key]).fetchone()
        if old:
            require(old[0] == encoded(payload).decode(), "JOURNAL_ID_CONFLICT")
            return key
        if event.correction_of:
            require(event.correction_of != key and db.execute("SELECT 1 FROM research_journal WHERE id=?", [event.correction_of]).fetchone() is not None,
                    "CORRECTION_TARGET_REQUIRED")
        if event.research_report_id:
            require(db.execute("SELECT 1 FROM research_report WHERE id=?", [event.research_report_id]).fetchone() is not None,
                    "JOURNAL_REPORT_UNKNOWN")
        db.execute("INSERT INTO research_journal VALUES (?,?,?,?)",
                   [key, event.event_at, event.recorded_at, encoded(payload).decode()])
    return key


def journal_snapshot(store: ResearchStore, as_of: str, instruments: dict, max_stale_days: int = 7) -> dict:
    cutoff = instant(as_of)
    with warehouse_connection(store.path, read_only=True) as db:
        rows = db.execute("SELECT payload FROM research_journal WHERE event_at<=? AND available_at<=? ORDER BY event_at,available_at,id",
                          [cutoff, cutoff]).fetchall()
    events = [json.loads(r[0]) for r in rows]
    corrected = {e["correction_of"] for e in events if e["correction_of"]}
    active = [e for e in events if e["event_id"] not in corrected]
    positions, original = {}, {}
    for e in active:
        if e["kind"] == "POSITION":
            positions[e["code"]] = e
            original.setdefault(e["code"], e)
    reports = {}
    with warehouse_connection(store.path, read_only=True) as db:
        for event in active:
            ref = event.get("research_report_id")
            if ref and ref not in reports:
                row = db.execute("SELECT snapshot FROM research_report WHERE id=?", [ref]).fetchone()
                snapshot = json.loads(row[0]) if row else None
                if snapshot and instant(snapshot["as_of"]) <= cutoff:
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
                pending_confirmation=[e["event_id"] for e in active if not e.get("confirmed", False)],
                limitation="未导入记录不等于没有持仓；EXECUTION/EXIT为日志，不擅自重算账户或生成订单")
