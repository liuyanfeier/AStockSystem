"""Descriptive daily features on an evidenced consecutive session tail only."""
from __future__ import annotations

import math
from datetime import date

import numpy as np
from pydantic import Field, model_validator

from astock.research.core import day, require
from astock.research.inputs import StrictModel


class ObservationParameters(StrictModel):
    version: str = Field(min_length=1)
    return_sessions: int = Field(ge=1, le=250)
    trend_sessions: int = Field(ge=2, le=250)
    breakout_sessions: int = Field(ge=2, le=250)
    activity_sessions: int = Field(ge=2, le=250)
    top_n: int = Field(ge=1, le=100)
    min_mean_amount_cny: float = Field(ge=0, allow_inf_nan=False)
    max_stale_calendar_days: int = Field(ge=0, le=365)
    strategy_validated: bool = False
    risk_budget: None = None

    @model_validator(mode="after")
    def observation_only(self):
        require(self.strategy_validated is False, "NO_VALIDATED_STRATEGY")
        return self


def features(code: str, identity: dict, prices: list[dict], factors: list[dict],
             calendar: list[dict], end: date, p: ObservationParameters) -> dict:
    sessions = sorted(day(r["date"]) for r in calendar
                      if r["exchange"] == identity.get("calendar_exchange", identity["exchange"]) and r["is_open"] == 1 and day(r["date"]) <= end)
    data = {day(r["date"]): r for r in prices if r["code"] == code and day(r["date"]) <= end}
    factor = {day(r["date"]): r["adj_factor"] for r in factors if r["code"] == code}
    f = dict(code=code, name=identity.get("name"), exchange=identity["exchange"],
             kind=identity["kind"], expected_sessions=len(sessions), observed_sessions=len(data),
             consecutive_sessions=0, last_date=None, close=None, return_1=None,
             window_return=None, ma=None, above_ma=None, mean_amount_cny=None,
             activity_ratio=None, volatility_daily=None, prior_high=None,
             breakout=None, relative_return=None, return_window_dates=None, price_basis="UNKNOWN", gaps=[], source_hashes=[])
    if not sessions:
        f["gaps"].append("交易日历/交易所身份不可用，不能认定连续窗口")
        return f
    f["missing_sessions"] = [d.isoformat() for d in sessions if d not in data]
    # NEVER skip over missing/suspended sessions to build an apparently continuous return.
    tail = []
    for d in reversed(sessions):
        if d not in data:
            break
        tail.append(data[d])
    tail.reverse()
    f["consecutive_sessions"] = len(tail)
    if not tail:
        f["gaps"].append("最后交易日行情缺失；不以前一日冒充当日")
        return f
    f.update(last_date=tail[-1]["date"], close=tail[-1]["close"],
             source_hashes=sorted({r["source_hash"] for r in tail} |
                                  {r["source_hash"] for r in factors if r["code"] == code and r["date"] in {t["date"] for t in tail}} |
                                  {r["source_hash"] for r in calendar if r["exchange"] == identity.get("calendar_exchange", identity["exchange"])} |
                                  ({identity["source_hash"]} if identity.get("source_hash") else set())))
    needed = max(p.return_sessions + 1, p.trend_sessions, p.breakout_sessions + 1, p.activity_sessions)
    if len(tail) < needed:
        f["gaps"].append(f"连续{len(tail)}日，不足配置所需{needed}日；长窗口指标保持缺失")
    # Index price is a price index. Stocks require factors for every observation
    # involved; never mislabel raw-price changes as investment total return.
    if identity["kind"] == "INDEX":
        adjusted = [r["close"] for r in tail]
        f["price_basis"] = "INDEX_PRICE"
    elif all(day(r["date"]) in factor for r in tail):
        anchor = factor[day(tail[-1]["date"])]
        adjusted = [r["close"] * factor[day(r["date"])] / anchor for r in tail]
        f["price_basis"] = "FACTOR_ADJUSTED_PRICE_NOT_TOTAL_RETURN"
    else:
        adjusted = None
        f["gaps"].append("复权因子缺失；不计算可能跨公司行为的价格收益/趋势")
    if adjusted is not None:
        if len(adjusted) >= 2:
            f["return_1"] = adjusted[-1] / adjusted[-2] - 1
        if len(adjusted) >= p.return_sessions + 1:
            f["window_return"] = adjusted[-1] / adjusted[-p.return_sessions - 1] - 1
            f["return_window_dates"] = [r["date"] for r in tail[-p.return_sessions - 1:]]
        if len(adjusted) >= p.trend_sessions:
            f["ma"] = float(np.mean(adjusted[-p.trend_sessions:]))
            f["above_ma"] = adjusted[-1] > f["ma"]
        if len(adjusted) >= p.breakout_sessions + 1:
            # Use highs preceding today; exclude today's high to avoid self-reference.
            previous = tail[-p.breakout_sessions - 1:-1]
            values = [r["high"] if identity["kind"] == "INDEX" else
                      r["high"] * factor[day(r["date"])] / factor[day(tail[-1]["date"])] for r in previous]
            f["prior_high"] = max(values)
            f["breakout"] = adjusted[-1] > f["prior_high"]
        if len(adjusted) >= p.return_sessions + 1:
            returns = np.diff(np.log(adjusted[-p.return_sessions - 1:]))
            f["volatility_daily"] = float(np.std(returns, ddof=1)) if len(returns) > 1 else None
    if len(tail) >= p.activity_sessions:
        amounts = [r["amount"] for r in tail[-p.activity_sessions:]]
        f["mean_amount_cny"] = float(np.mean(amounts))
        prior_mean = float(np.mean(amounts[:-1]))
        f["activity_ratio"] = amounts[-1] / prior_mean if prior_mean > 0 else None
        if prior_mean == 0:
            f["gaps"].append("前序成交额为零；活跃度比值未知")
    require(all(not isinstance(v, float) or math.isfinite(v) for v in f.values()), "NONFINITE_FEATURE")
    return f
