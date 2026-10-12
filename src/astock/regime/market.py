"""Local-pool regime vector with denominators and unavailable market/style evidence."""
from __future__ import annotations


def market_regime(stocks: list[dict], benchmarks: list[dict], scope: str) -> dict:
    def mean(field: str):
        values = [s[field] for s in stocks if s.get(field) is not None]
        return dict(value=sum(values) / len(values) if values else None, denominator=len(values))
    changed = [s for s in stocks if s["return_1"] is not None]
    trending = [s for s in stocks if s["above_ma"] is not None]
    return dict(scope="观察池内，非全市场", declared_scope=scope, requested_stocks=len(stocks),
                advancing=sum(s["return_1"] > 0 for s in changed),
                declining=sum(s["return_1"] < 0 for s in changed), unchanged=sum(s["return_1"] == 0 for s in changed),
                breadth_denominator=len(changed),
                above_ma=sum(s["above_ma"] for s in trending), ma_denominator=len(trending),
                mean_activity_ratio=mean("activity_ratio"), mean_daily_volatility=mean("volatility_daily"),
                benchmarks=benchmarks, style_proxy="UNKNOWN：缺市值/风格组合与对应历史证据",
                regime_label="UNCLASSIFIED：描述性向量，不绑定仓位或交易规则",
                limitations=["观察池含选择偏差，宽度不能代表全A股", "成交不等于资金流向，价格不证明催化或行业归因",
                             "当前下载的历史序列仅供当前观察，不构成历史PIT回测数据"])
