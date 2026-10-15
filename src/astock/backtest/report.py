"""Chinese synthetic mechanics report, published as one immutable result pair."""
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from astock.research.core import digest, encoded, require
from astock.research.publication import publish_bytes


def _percent(value: str | None) -> str:
    return '未知/无样本' if value is None else f'{Decimal(value)*100:.3f}%'


def lab_markdown(report: dict) -> str:
    lines = ['# 三组策略的全合成演示', '',
        '所有公司、价格、交易日历和成交均为虚构。此报告检验程序机制，不能用于判断哪组策略更赚钱。', '',
        f"实验名义现金：每组 {report['experiment']['nominal_lab_cash']} 元；每笔 {report['experiment']['shares']} 股。",
        '费用和滑点采用统一假设，同时保留两倍费用/滑点的结果；没有用户账户、真实持仓或真实订单。', '',
        '|组别|观察记录|输入未知|形态满足|首次信号|取消|买入|已平仓|未平仓|平均净收益|收盘估值最大回撤|双倍成本平均净收益|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for variant, value in report['results'].items():
        counts = value['opportunity_counts']
        cells = [variant, *[str(counts[key]) for key in
            ('total', 'unknown', 'matching', 'first', 'canceled', 'entry_fills', 'closed_trades')],
            str(len(value['open_positions'])), _percent(value['average_net_return']),
            _percent(value['lab_mark_to_market_max_drawdown']),
            _percent(report['higher_cost_results'][variant]['average_net_return'])]
        lines.append('|'+'|'.join(cells)+'|')
    lines += ['', '观察记录包含预热期，形态满足不等于新信号，新信号不等于已成交；三组账户相互独立。']
    for variant, value in report['results'].items():
        lines += ['', f'## {variant} 成交与阻断', '']
        for trade in value['trades']:
            lines += [f"- {trade['code']}：{trade['entry_date']} 下一开盘买入，{trade['exit_date']} 可执行开盘卖出；"
                f"净盈亏 {Decimal(trade['pnl_cny']):.3f} 元，净收益 {_percent(trade['return_net'])}。",
                f"  退出原因：{'、'.join(trade['all_exit_triggers'])}；买入/卖出费用 "
                f"{Decimal(trade['entry_fee_cny']):.3f}/{Decimal(trade['exit_fee_cny']):.3f} 元；"
                f"入场/退出相对信号收盘偏差 {_percent(trade['entry_deviation_from_signal'])}/{_percent(trade['exit_deviation_from_signal'])}。",
                f"  持仓价格最大有利/不利变化 {_percent(trade['maximum_favorable_price_return'])}/"
                f"{_percent(trade['maximum_adverse_price_return'])}；持有间隔 {trade['holding_sessions']} 个合成交易日。"]
        if not value['trades']:
            lines.append('- 没有已平仓样本，收益统计保持未知。')
        for record in value['sessions']:
            actions = [action for action in record['actions'] if action.startswith(('CANCEL_', 'EXIT_PENDING_',
                'CORPORATE_', 'HOLDING_PRICE_', 'RESEARCH_REVIEW_'))]
            if actions:
                lines.append(f"- {record['date']} {record['code']}：{'、'.join(actions)}。")
        lines.append(f"- 期末实验现金 {value['cash_ledger_cny']} 元；未平仓 {len(value['open_positions'])}；待成交 {len(value['pending'])}。")
    lines += ['', '## 复盘边界', '', *['- '+item for item in report['limitations']], '',
        f"判定：{report['strategy_effectiveness']}。参数Hash：{report['parameters_hash']}；实验Hash：{report['experiment_hash']}。",
        f"规则代码Hash：{report['code_hash']}；执行代码Hash：{report['execution_code_hash']}；输入Hash：{report['input_hash']}。",
        '完整逐日信号、取消、成交、待成交、费用敏感性和估值记录保留在同名JSON。']
    return '\n'.join(lines)+'\n'


def publish_lab(report: dict, output: Path) -> tuple[str, Path, Path]:
    require(not any(path.is_symlink() for path in (output, *output.parents)), 'STRATEGY_LAB_OUTPUT_SYMLINK')
    output.mkdir(parents=True, exist_ok=True)
    value = {**report, 'renderer_hash': sha256(Path(__file__).read_bytes()).hexdigest()}
    key = digest(value)
    json_path, markdown_path = output/f'{key}.json', output/f'{key}.md'
    publish_bytes(json_path, encoded(value)+b'\n')
    publish_bytes(markdown_path, lab_markdown(value).encode())
    return key, json_path, markdown_path
