"""Deterministic private snapshot + Chinese candidate cards, with evidence and no-trade conditions."""
from __future__ import annotations

from pathlib import Path

from astock.research.core import digest, encoded, require
from astock.research.publication import publish_bytes


def display(value: object, *, percent: bool = False) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, float):
        return f"{value:.2%}" if percent else f"{value:,.4f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown(snapshot: dict) -> str:
    params, market = snapshot["parameters"], snapshot["market"]
    lines = ["# AStockSystem 候选观察报告", "", "OBSERVATION_ONLY · 不生成订单 · 不代表已验证策略", "",
             f"研究可知截止：{snapshot['as_of']}；行情窗口：{snapshot['window_start']} → {snapshot['window_end']}",
             f"输入bundle：{snapshot['bundle_id']}；计算代码hash：{snapshot['code_hash']}",
             f"参数：{params['version']}（收益{params['return_sessions']}日 / 均线{params['trend_sessions']}日 / 前高{params['breakout_sessions']}日）",
             "", "## 市场观察", "", f"范围：{market['scope']}；请求股票{market['requested_stocks']}只。",
             f"涨/跌/平：{market['advancing']}/{market['declining']}/{market['unchanged']}，有效分母{market['breadth_denominator']}。",
             f"高于均线：{market['above_ma']}/{market['ma_denominator']}；标签：{market['regime_label']}",
             f"成交活跃比：{display(market['mean_activity_ratio']['value'])}（分母{market['mean_activity_ratio']['denominator']}）",
             f"日波动均值：{display(market['mean_daily_volatility']['value'],percent=True)}（分母{market['mean_daily_volatility']['denominator']}）",
             f"风格：{market['style_proxy']}"]
    for benchmark in market["benchmarks"]:
        lines.append(f"基准{benchmark['code']}：窗口收益{display(benchmark['window_return'],percent=True)}；连续{benchmark['consecutive_sessions']}日。")
    if not market["benchmarks"]:
        lines.append("基准指数：UNKNOWN；相对强弱保持缺失。")
    lines.extend(["", "## 质量与缺口", ""] + [f"- {x}" for x in snapshot["limitations"] + market["limitations"]])
    lines.extend(["", "## 候选与人工观察", "", f"程序筛选{len(snapshot['candidates'])}只，人工观察{len(snapshot['manual_cards'])}只；可为空。"])
    for card in snapshot["candidates"] + snapshot["manual_cards"]:
        f = card["metrics"]
        lines.extend(["", f"### {display(card['code'])} {display(card['name'])}", "", f"选择依据：{card['selection']}",
                      f"末日{display(f['last_date'])} 收盘{display(f['close'])}；连续{f['consecutive_sessions']}日；价格口径{f['price_basis']}",
                      f"1日收益{display(f['return_1'],percent=True)} / 窗口收益{display(f['window_return'],percent=True)} / 相对基准{display(f['relative_return'],percent=True)}",
                      f"均线{display(f['ma'])} / 前高{display(f['prior_high'])} / 平均成交额CNY{display(f['mean_amount_cny'])}",
                      f"成交活跃比{display(f['activity_ratio'])}；日波动{display(f['volatility_daily'],percent=True)}；排序：{card.get('ranking_basis','窗口收益')}",
                      f"状态：ST={card['status']['st']}，停牌观察={card['status']['suspended']}（含日内事件，非全天/收盘后可交易判定）；风险预算未设定；交易资格false。"])
        for setup in card.get("setups", []):
            lines.append(f"待研究Setup {setup['kind']}：{setup['state']}，参考{display(setup['reference'])}；{setup['condition']}")
        for title, key in (("入场观察条件", "entry_observation"), ("反面证据与风险", "counter_evidence"),
                           ("逻辑失效条件", "invalidation_conditions"), ("不交易条件", "no_trade_conditions")):
            lines.extend(["", f"**{title}**", ""] + [f"- {display(x)}" for x in card[key]])
        lines.extend(["", card["exit_followup"], "", "价格证据hash：" + ", ".join(f["source_hashes"])])
    lines.extend(["", "## 筛选排除记录", ""])
    for item in snapshot["excluded"]:
        lines.append(f"- {display(item['code'])}：{'；'.join(item['reasons'])}")
    lines.extend(["", "## 私有持仓与退出跟踪", "", snapshot["journal"]["limitation"]])
    for h in snapshot["journal"]["positions"]:
        lines.extend(["", f"- {display(h['code'])}：人工持仓{h['shares']}股；来源事件{display(h['source_event'])}；复盘到期={h['review_overdue']}",
                      f"  原始逻辑：{display(h.get('original_thesis',h['thesis']))}；失效：{display(h['invalidation'])}；退出观察：{display(h['exit_conditions'])}",
                      f"  原始研究{display(h.get('original_research_report_id'))}；陈旧={display(h.get('research_stale'))}；退出条件={h.get('exit_condition_state','PENDING_VERIFICATION')}；人工确认={h.get('confirmed',False)}",
                      f"  行情日{display(h['price_date'])}；{'；'.join(h['gaps'])}"])
    lines.extend(["", "待确认人工事件：" + display(", ".join(snapshot["journal"].get("pending_confirmation", [])) or "未导入/无待确认事件"),
                  "", "## 下一研究日跟踪", "",
                  "- 更新连续行情与来源时间；以新数据复算前高/均线、同日期基准及活跃度。",
                  "- 核实候选ST/停复牌/限价与公告、基本面反面证据；当前缺口不构成交易许可。",
                  "- 逐项复核持仓原始逻辑、用户退出观察条件、到期复盘和未确认事件。"])
    lines.extend(["", "## 来源与复现", "", f"参数hash：{snapshot['parameters_hash']}；日志hash：{snapshot['journal']['events_hash']}"])
    for f in snapshot["sources"]:
        lines.append(f"- {display(f['dataset'])}：{display(f['source'])}；sha256={f['sha256']}；retrieved={f['retrieved_at']}；available={f['available_at']}；单位={f['volume_unit']}/{f['amount_unit']}；来源等级={f.get('evidence_grade','USER_DECLARED')}")
    lines.extend(["", "基本面/行业主题/公告催化：UNKNOWN。真实来源与人工记录保存在私有目录；本报告不宣称历史PIT可回测。", ""])
    return "\n".join(lines)


def publish(snapshot: dict, directory: Path) -> str:
    run_id = digest(snapshot)
    directory.mkdir(parents=True, exist_ok=True)
    # Each member becomes visible only after closed-byte validation and fsync.
    # A crash between members is recovered by the same immutable publication.
    for name, body in (("snapshot.json", encoded(snapshot) + b"\n"), ("report.md", markdown(snapshot).encode())):
        path = directory / f"{run_id}.{name}"
        require(not path.is_symlink(), "REPORT_SYMLINK")
        if path.exists():
            require(path.read_bytes() == body, "REPORT_OUTPUT_CHANGED")
        else:
            publish_bytes(path, body)
    return run_id
