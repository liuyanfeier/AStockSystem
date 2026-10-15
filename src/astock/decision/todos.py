"""One open task per object; risk, reconciliation and research remain explicit."""
from astock.decision.settings import workflow_policy
from astock.research.core import digest


def decision_items(report: dict) -> dict:
    items = {}

    def add(key: str, code: str | None, priority: int, reason: str, action: str):
        item = items.setdefault(key, dict(id=digest(['DECISION_ITEM_V1', key]), code=code,
                                          priority=priority, reasons=[], next_actions=[], state='OPEN'))
        item['priority'] = min(item['priority'], priority)
        for name, value in (('reasons', reason), ('next_actions', action)):
            if value not in item[name]:
                item[name].append(value)

    portfolio = report['portfolio']
    holdings = {p['code']: p for p in portfolio['positions']}
    for code in report.get('pending_position_reconciliation', []):
        add(code, code, 0, '成交后持仓尚未核对；已阅不能解除', '补录该时点的实际持仓快照')
    for code, position in holdings.items():
        if not position['price_fresh']:
            add(code, code, 0, '持仓报价未覆盖要求日期', '先核对当前价格和交易状态，再复核退出计划')
        if not position['confirmed']:
            add(code, code, 1, '已报持仓尚未确认', '核对实际持股数并明确确认')
        if position['review_overdue']:
            add(code, code, 1, '持仓研究复核已到期', '核对原持仓逻辑、反证和退出观察条件')
        if position['hypothesis_state'] == 'INVALIDATION_REVIEW':
            add(code, code, 0, '持仓逻辑触发失效复核', '先核对原始事实及实际持仓；不自动卖出')
    for card in report['cards']:
        code = card['code']
        if card['state'] == 'END_WATCH':
            if code in holdings:
                add(code, code, 0, '已结束研究观察但仍有已报持仓', '继续核对持仓风险和退出；结束观察不等于已卖出')
            continue
        if card['state'] == 'INVALIDATION_REVIEW':
            add(code, code, 0, '研究逻辑触发失效复核', '核对反面证据及原始文档；实际成交另记')
        if card.get('retained_baseline_only'):
            add(code, code, 1, '仅有保留基线材料，未进入本轮复核目录', '取得并核验新的研究复核材料')
        elif card['state'] == 'WAIT_EVIDENCE':
            add(code, code, 1, '研究条件或证据仍未解决', '补齐证据后明确复核；普通已阅不解除')
        if card['review_overdue']:
            add(code, code, 1, '研究复核已到期', '刷新研究检查；到期不代表财报事实作废')
        if card['evidence_changes']:
            add(code, code, 1, '保留证据发生变化', '逐项核对变化及反证后再作明确研究复核')
    if not report['market_fresh']:
        add('__MARKET__', None, 1,
            f"行情截至{report['window_end']}，尚未覆盖要求的{report['required_market_date']}",
            '核对已授权来源更新范围；本次离线运行不重新采集')
    if portfolio['positions_state'] == 'UNKNOWN_NOT_EMPTY' or portfolio.get('account_assets_cny') is None:
        add('__ACCOUNT__', None, 2, '完整持仓、现金或估值条件不足，账户总资产未知',
            '需要组合检查时补录明确持仓范围和现金；未提供不推断空仓')
    values = sorted(items.values(), key=lambda item: (item['priority'], item['code'] or '', item['id']))
    for item in values:
        item['priority_text'] = ('优先核对持仓/风险', '本轮研究待办', '信息待补')[item['priority']]
    return dict(protocol='DECISION_ITEMS_V1', total=len(values),
                visible_limit=workflow_policy().visible_todo_limit, items=values,
                rule='同一对象合并原因；已阅不关闭；事实修复或明确研究操作后重新计算')
