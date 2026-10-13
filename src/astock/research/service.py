"""One computation path for market, screen and report; no parallel business implementations."""
from __future__ import annotations

from astock.features.market import ObservationParameters, features
from astock.regime.market import market_regime
from astock.research.core import code_fingerprint, day, digest, instant, market_day, require
from astock.research.journal import journal_snapshot
from astock.research.store import ResearchStore
from astock.screening.candidates import observation_card, screen


def analyze(store: ResearchStore, bundle_id: str, as_of: str, parameters: ObservationParameters,
            watch: list[str] | None = None, *, radar: bool = False,
            components: list[str] | None = None, revisions: dict | None = None) -> dict:
    cutoff = instant(as_of)
    if components:
        from astock.research.increment import compose
        manifest, rows = compose(store, [bundle_id, *components], as_of, revisions or {})
        bundle_id = digest(dict(components=[bundle_id, *components], revisions=revisions or {}))
    else:
        manifest, rows = store.snapshot(bundle_id, as_of)
    end = day(manifest["window_end"])
    require(end <= market_day(cutoff), "REPORT_BEFORE_WINDOW_END")
    identities = {r["code"]: r for r in rows.get("instruments", [])}
    codes = manifest["universe"] + manifest["benchmarks"]
    from collections import defaultdict
    grouped = {dataset: defaultdict(list) for dataset in ('daily', 'index_daily', 'adj_factor', 'calendar')}
    for dataset, groups in grouped.items():
        for row in rows.get(dataset, []):
            groups[row['exchange'] if dataset == 'calendar' else row['code']].append(row)
    stock_codes = set(manifest["universe"])
    calculated = {}
    previous_calculated = {}
    for code in codes:
        kind = "STOCK" if code in stock_codes else "INDEX"
        identity = identities.get(code, dict(code=code, name=None, kind=kind, exchange="UNKNOWN"))
        prices = grouped['daily' if kind == 'STOCK' else 'index_daily'][code]
        factors = grouped['adj_factor'][code]
        calendar = grouped['calendar'][identity.get('calendar_exchange', identity['exchange'])]
        calculated[code] = features(code, identity, prices, factors, calendar, end, parameters, radar=radar)
        if radar:
            days = sorted(day(r['date']) for r in calendar if r['is_open'] == 1 and day(r['date']) < end)
            previous_calculated[code] = features(code, identity, prices, factors, calendar, days[-1] if days else end,
                                               parameters, radar=True)
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
    from astock.research.tushare import merge_status
    status = merge_status(rows.get("status", []))
    cards = [observation_card(s, status.get((s["code"], s["last_date"])), selection="程序筛选：" + "；".join(s["inclusion_reasons"])) for s in candidates]
    selected = {s["code"] for s in candidates}
    manual = [observation_card(calculated[c], status.get((c, calculated[c]["last_date"])), selection="人工指定的有限观察，未必通过程序筛选") for c in watch if c not in selected]
    limitations = ["用途CURRENT_OBSERVATION；当前采集历史值不可用作当时已知的回测输入", "没有经验证/用户批准的入场退出风险参数"]
    limitations.extend(["来源等级USER_DECLARED仅文件声明；LOCAL_CAPTURE_BOUND为本地TLS采集/消费链绑定，非独立提供者签名；SYNTHETIC不是行情事实",
                        "指数点位是价格指数；成交为该指数覆盖证券口径，不代表全市场资金流或指数本身可交易股数",
                        "稀疏ST/停复牌缺席不证明正常；限价证据不保证成交"])
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
                  limitations=limitations, journal=journal_snapshot(store, as_of, calculated, parameters.max_stale_calendar_days))
    if radar:
        from astock.research.radar import attach_radar
        attach_radar(result, manifest, rows, stocks, benchmarks, previous_calculated, parameters)
        if components:
            result['composition'] = manifest['composition']
            result['limitations'].append('增量复权因子来自多个采集版本；回溯修订需另作来源版本检查，不能宣称所有历史因子同一vintage。冲突需明确来源选择。')
    return result
