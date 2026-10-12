"""One computation path for market, screen and report; no parallel business implementations."""
from __future__ import annotations

from astock.features.market import ObservationParameters, features
from astock.regime.market import market_regime
from astock.research.core import code_fingerprint, day, digest, instant, market_day, require
from astock.research.journal import journal_snapshot
from astock.research.store import ResearchStore
from astock.screening.candidates import observation_card, screen


def analyze(store: ResearchStore, bundle_id: str, as_of: str, parameters: ObservationParameters,
            watch: list[str] | None = None) -> dict:
    cutoff = instant(as_of)
    manifest, rows = store.snapshot(bundle_id, as_of)
    end = day(manifest["window_end"])
    require(end <= market_day(cutoff), "REPORT_BEFORE_WINDOW_END")
    identities = {r["code"]: r for r in rows.get("instruments", [])}
    codes = manifest["universe"] + manifest["benchmarks"]
    calculated = {}
    for code in codes:
        kind = "STOCK" if code in manifest["universe"] else "INDEX"
        identity = identities.get(code, dict(code=code, name=None, kind=kind, exchange="UNKNOWN"))
        calculated[code] = features(code, identity, rows.get("daily" if kind == "STOCK" else "index_daily", []),
                                    rows.get("adj_factor", []), rows.get("calendar", []), end, parameters)
    benchmarks = [calculated[c] for c in manifest["benchmarks"]]
    stocks = [calculated[c] for c in manifest["universe"]]
    # The first explicitly declared benchmark is the reference; require equal
    # final dates and configured return window before comparing returns.
    benchmark = benchmarks[0] if benchmarks else None
    for stock in stocks:
        if benchmark and stock["window_return"] is not None and benchmark["window_return"] is not None and stock["return_window_dates"] == benchmark["return_window_dates"]:
            stock["relative_return"] = stock["window_return"] - benchmark["window_return"]
    candidates, excluded = screen(stocks, parameters, market_day(cutoff))
    watch = sorted(set(watch or []))
    require(set(watch) <= set(manifest["universe"]), "WATCH_OUTSIDE_UNIVERSE")
    status = {(r["code"], r["date"]): r for r in rows.get("status", [])}
    cards = [observation_card(s, status.get((s["code"], s["last_date"])), selection="程序筛选：" + "；".join(s["inclusion_reasons"])) for s in candidates]
    selected = {s["code"] for s in candidates}
    manual = [observation_card(calculated[c], status.get((c, calculated[c]["last_date"])), selection="人工指定的有限观察，未必通过程序筛选") for c in watch if c not in selected]
    limitations = ["用途CURRENT_OBSERVATION；当前采集历史值不可用作当时已知的回测输入", "没有经验证/用户批准的入场退出风险参数"]
    stale = (market_day(cutoff) - end).days
    limitations.append(f"行情窗口截止距研究截止{stale}个自然日；报价日期不等于研究可知日期")
    if parameters.return_sessions < 20 or parameters.trend_sessions < 60:
        limitations.append("当前参数为短窗口探索，不能代替20/60日趋势研究或宣称策略有效")
    if stale > parameters.max_stale_calendar_days:
        limitations.append(f"行情截止距研究截止{stale}个自然日，超时效配置；不得冒充最新市场")
    unavailable = [f["sha256"] for f in manifest["files"] if instant(f["available_at"]) > cutoff]
    if unavailable:
        limitations.append(f"{len(unavailable)}份来源在截止时不可知，被as-of过滤")
    if not benchmarks:
        limitations.append("缺基准指数：不计算相对强弱、不能判断市场整体趋势")
    result = dict(protocol="RESEARCH_REPORT_V1", purpose=manifest["purpose"], bundle_id=bundle_id,
                  as_of=cutoff.isoformat(), window_start=manifest["window_start"], window_end=manifest["window_end"],
                  code_hash=code_fingerprint(), parameters=parameters.model_dump(mode="json"),
                  parameters_hash=digest(parameters.model_dump(mode="json")),
                  sources=manifest["files"], market=market_regime(stocks, benchmarks, manifest["universe_scope"]),
                  features=stocks, candidates=cards, manual_cards=manual, excluded=excluded,
                  limitations=limitations, journal=journal_snapshot(store, as_of, calculated))
    return result
