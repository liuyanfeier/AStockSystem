"""Explainable research filters; status uncertainty remains a mandatory no-trade reason."""
from __future__ import annotations

from datetime import date

from astock.features.market import ObservationParameters
from astock.research.core import day


def screen(stocks: list[dict], p: ObservationParameters, as_of: date) -> tuple[list[dict], list[dict]]:
    included, excluded = [], []
    for stock in stocks:
        reasons = []
        if stock["last_date"] is None:
            reasons.append("最终交易日价格或身份/日历不可用")
        elif (as_of - day(stock["last_date"])).days > p.max_stale_calendar_days:
            reasons.append("行情陈旧，超过观察时效配置")
        if stock["window_return"] is None or stock["above_ma"] is None or stock["mean_amount_cny"] is None:
            reasons.append("连续窗口/因子不满足筛选指标")
        else:
            if stock["window_return"] <= 0:
                reasons.append("观察窗口价格收益非正")
            if stock["above_ma"] is not True:
                reasons.append("价格未高于配置均线")
            if stock["mean_amount_cny"] < p.min_mean_amount_cny:
                reasons.append("平均成交额低于观察筛选门槛")
        if reasons:
            excluded.append(dict(code=stock["code"], reasons=reasons))
        else:
            included.append({**stock, "inclusion_reasons": ["窗口价格收益为正", "价格高于配置均线", "平均成交额满足观察筛选门槛"]})
    # No opaque composite score. Deterministic ranking by comparable return;
    # relative strength is only provided when SAME dates/basis benchmark exists.
    included.sort(key=lambda s: (-s["window_return"], s["code"]))
    for stock in included[p.top_n:]:
        excluded.append(dict(code=stock["code"], reasons=["符合筛选但超出报告数量上限"]))
    return included[:p.top_n], excluded


def observation_card(stock: dict, status: dict | None, *, selection: str) -> dict:
    status = status or dict(st="UNKNOWN", suspended="UNKNOWN", up_limit=None, down_limit=None)
    no_trade = ["本卡仅供研究观察，尚无经用户批准的交易计划与风险预算",
                "公告、基本面、行业/主题及竞争预期未核实", "T+1、涨跌停、隔夜跳空与实际可成交性未完整验证"]
    if status["st"] != "NO":
        no_trade.append("ST/风险警示状态未知或存在")
    if status["suspended"] != "NO":
        no_trade.append("停牌状态未知或存在")
    if status["up_limit"] is None or status["down_limit"] is None:
        no_trade.append("涨跌停价格证据缺失")
    elif stock["close"] is not None and (stock["close"] >= status["up_limit"] or stock["close"] <= status["down_limit"]):
        no_trade.append("收盘触及价格限制，不能假设下一交易日可成交")
    no_trade.extend(stock["gaps"])
    return dict(code=stock["code"], name=stock["name"], selection=selection,
                metrics=stock, status=status, trade_eligible=False, risk_budget=None,
                entry_observation=["待验证Breakout/Pullback假设：连续窗口证据充分后观察趋势、前高与成交变化",
                                   "触发仅产生研究提醒；入场价格、仓位及初始退出须另建计划并批准"],
                counter_evidence=["正价格趋势不能证明公司价值、催化持续或未来收益", "样本池选择偏差、短窗口噪声与行情陈旧风险", *stock["gaps"]],
                invalidation_conditions=["发现原始数据、证券身份或公司行为处理错误", "补充公告/财务证据推翻原投资假设",
                                         "持续跟踪时趋势/相对强弱反转；具体退出阈值尚未验证批准"],
                no_trade_conditions=no_trade,
                exit_followup="持仓需记录原始逻辑、失效/时间退出条件与实际执行；本卡没有自动卖出指令")
