"""Append-only manual plans/positions/executions/exits/reviews, never broker integration."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from astock.data.warehouse_lock import warehouse_connection
from astock.research.core import digest, encoded, instant, read_json, require
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
    thesis: str = Field(min_length=1)
    invalidation: str = Field(min_length=1)
    exit_conditions: str = Field(min_length=1)
    review_due: AwareDatetime | None = None
    notes: str = ""
    correction_of: str | None = None
    # Deliberately no account/password/risk/order fields; this records supplied facts.

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


def journal_snapshot(store: ResearchStore, as_of: str, instruments: dict) -> dict:
    cutoff = instant(as_of)
    with warehouse_connection(store.path, read_only=True) as db:
        rows = db.execute("SELECT payload FROM research_journal WHERE event_at<=? AND available_at<=? ORDER BY event_at,available_at,id",
                          [cutoff, cutoff]).fetchall()
    events = [json.loads(r[0]) for r in rows]
    corrected = {e["correction_of"] for e in events if e["correction_of"]}
    active = [e for e in events if e["event_id"] not in corrected]
    positions = {}
    for e in active:
        if e["kind"] == "POSITION":
            positions[e["code"]] = e
    holdings = []
    for code, event in sorted(positions.items()):
        if event["shares"] == 0:
            continue
        stock = instruments.get(code)
        holdings.append(dict(code=code, shares=event["shares"], thesis=event["thesis"],
                             invalidation=event["invalidation"], exit_conditions=event["exit_conditions"],
                             review_due=event["review_due"],
                             review_overdue=bool(event["review_due"] and instant(event["review_due"]) <= cutoff),
                             latest_price=stock.get("close") if stock else None,
                             price_date=stock.get("last_date") if stock else None,
                             gaps=["人工快照非券商同步；未据成交日志自动推算持仓", "T+1可卖数量/现金/组合风险参数尚未设置"],
                             source_event=event["event_id"]))
    return dict(events=events, events_hash=digest(events), positions=holdings,
                limitation="未导入记录不等于没有持仓；EXECUTION/EXIT为日志，不擅自重算账户或生成订单")
