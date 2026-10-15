"""Short action-oriented private report and an explicit corporate-only public projection."""
from pathlib import Path

from astock.research.core import digest, encoded, require
from astock.research.publication import publish_bytes


def markdown(report: dict, *, public: bool = False) -> str:
    lines = ['# 每日决策报告 · Decision Loop V0', '',
             f"研究截止：{report['as_of']}；行情截至：{report['window_end']}；要求完整交易日：{report['required_market_date']}。",
             f"证据模式：{report['mode']}。模拟事件不是实际披露，研究提醒不产生订单。", '',
             'A. 今日市场风险状态', '']
    metrics = report['market']['metrics']
    breadth = metrics.get('return_20', {}); trend = metrics.get('above_ma60', {})
    lines += [f"20日上涨 {breadth.get('up','UNKNOWN')}/{breadth.get('denominator','UNKNOWN')}；MA60上方 {trend.get('count','UNKNOWN')}/{trend.get('denominator','UNKNOWN')}。",
              '行情完整日未刷新，不能宣称今天市场状态已验证。' if not report['market_fresh'] else '已覆盖要求日期；描述性指标不代替风险预算。', '',
              'B. 持仓与组合风险', '']
    if public:
        lines += ['公开结果不包含个人持仓、现金、Journal或人工备注。真实账户状态无法从本报告推断。']
    else:
        p = report['portfolio']
        lines += [f"模式：{p['mode']}；持仓范围：{p['positions_state']}；账户总资产：{p.get('account_assets_cny') or 'UNKNOWN'}。"]
        for row in p['positions']:
            lines += [f"- {row['code']}：{row['priority']}；用户确认={row['confirmed']}；价格新鲜={row['price_fresh']}；逻辑={row['hypothesis_state']}。"]
        lines += [*p['gaps']]
    lines += ['', 'C. 重点公司新事实与假设变化', '']
    for card in report['cards']:
        lines += [f"**{card['name']} {card['code']}：{card['state_text']}**",
                  f"研究检查：{card['hypothesis_state']}；真实证据变化 {len(card['evidence_changes'])} 项。"]
        if card.get('price'):
            price=card['price']
            lines += [f"报价日 {price.get('last_date')}；收盘 {price.get('close')}；MA60上方={price.get('above_ma60')}；该行情截面筛选资格={card.get('technical_eligible','UNKNOWN')}。"]
        if card['no_new_disclosures']:
            lines += ['原披露事实未变化；本次没有新的真实公告证据，不能推断没有新公告。']
        if card.get('previous_observation'):
            p=card['previous_observation']
            lines += [f"上次观察 {p['as_of']}：{p['state']} → {card['state']}；两次观察变化 {len(card.get('changes_since_prior',[]))} 项。"]
        for check in card['checks']:
            lines += [f"- {check['reason']}：{check['state']}；{check['explanation']}（{check['evidence_class']}）。"]
            before,after=check.get('previous'),check.get('latest')
            if before and after:
                lines += [f"  原披露 {before['value']} → 最新保留披露 {after['value']} {after['unit']}，期间 {after['period_end']}；模拟事件不改写这些真实数字。"]
        lines += [f"下一步：{'；'.join(card['next_actions'])}", '']
    lines += ['D. 今日不应交易的对象与理由', '']
    for card in report['cards']:
        lines += [f"- {card['name']}：{'；'.join(card['no_trade_reasons'])}。"]
    lines += ['', 'E. 到期复盘或退出检查', '']
    for card in report['cards']:
        lines += [f"- {card['name']}：{'已到期，需人工复核' if card['review_overdue'] else '未到期'}；{card['plan']['review_due']}（程序提出的研究复核日期）。"]
    lines += ['', 'F. 今日人工动作', '']
    if not public:
        records = sorted(report.get('manual_records', []), key=lambda r: (r['recorded_at'], r['receipt_id']))
        for item in records[-10:]:
            detail = item['note'] if item['kind'] == 'NOTE' else (
                f"持仓快照 {item['shares']}股" if item['kind'] == 'POSITION' else
                f"{item['side']} 已成交 {item['shares']}股，成交价 {item['price_cny']}元；" +
                (f"明确补录成交后 {item['remaining_shares']}股" if item['remaining_shares'] is not None else '成交后持仓未核对'))
            lines.append(f"- {item['code']}：{detail}；事实时间 {item['event_at']}；录入 {item['recorded_at']}（{item['mode']}）。")
        if report.get('pending_position_reconciliation'):
            lines.append('待核对成交后持仓：' + '、'.join(report['pending_position_reconciliation']) + '；已阅不解除此待办。')
    lines += ['', '先补新行情与交易状态；核对重大公告。逻辑失效只触发人工检查，真实卖出另记实际成交。',
              '有真实持仓时请在私有Journal确认快照、原逻辑与复盘；没有提供持仓时保持未知。', '',
              'G. 数据截止与未覆盖事项', '', report['limitation'],
              '估值、竞争、现金/完整持仓、风险参数、最新公告完整性及策略收益仍未验证。', '']
    return '\n'.join(lines)


def publish_private(report: dict, output: Path) -> str:
    output.mkdir(parents=True, exist_ok=True)
    key = digest(report)
    publish_bytes(output/f'{key}.json', encoded(report)+b'\n')
    publish_bytes(output/f'{key}.md', markdown(report).encode())
    return key


def public_projection(report: dict) -> dict:
    # Explicitly authorized three public corporate cases. Neither the Journal nor portfolio crosses this boundary.
    allowed_codes = {'600036.SH', '000002.SZ', '601872.SH'}
    allowed = {'protocol','mode','as_of','window_end','required_market_date','market_snapshot_hash',
               'previous_catalog_hash','latest_catalog_hash','run_input_hash','market','market_fresh','limitation'}
    result = {k:report[k] for k in allowed}
    fields = {'code','name','industry_code','state','state_text','hypothesis_state','checks','evidence_changes','sources','previous_sources','price','technical_eligible',
              'previous_catalog_hash','latest_catalog_hash','no_new_disclosures','review_overdue',
              'evidence_refresh_due','next_actions','no_trade_reasons','trade_eligible','risk_budget','position_limit','order'}
    result['cards'] = []
    for card in report['cards']:
        if card['code'] not in allowed_codes:continue
        c = {k:card[k] for k in fields}
        c['plan'] = {'review_due':card['plan']['review_due']}
        source_fields={'id','code','url','sha256','published_on','retrieved_at','available_at','hosting','state','publication_basis','audit'}
        c['sources']=[{k:v for k,v in s.items() if k in source_fields} for s in c['sources']]
        c['previous_sources']=[{k:v for k,v in s.items() if k in source_fields} for s in c['previous_sources']]
        c['evidence_changes']=[{**change,'previous':{k:v for k,v in (change['previous'] or {}).items() if k in source_fields},
                               'latest':{k:v for k,v in (change['latest'] or {}).items() if k in source_fields}}
                              if change['type']=='SOURCE_VERSION' else change for change in c['evidence_changes']]
        if card.get('previous_observation') and not card['previous_observation']['personal_action_included']:
            c['previous_observation']=card['previous_observation']
            c['changes_since_prior']=[{k:v for k,v in change.items() if k in ('type','previous','latest')}
                                       for change in card['changes_since_prior'] if change['type']!='CRITERION']
        # User plan prose and user review actions stay private, even for public company tickers.
        c['next_actions']=[{'600036.SH':'核对净息差、不良生成、关注贷款、拨备与资本',
                           '000002.SZ':'核对展期履约、受限现金、到期债务与亏损减值',
                           '601872.SH':'核对分业务运价、盈利现金回款与船队资本开支'}[card['code']]]
        c['no_trade_reasons']=[{'600036.SH':'信用质量与估值仍需补证据',
                               '000002.SZ':'亏损、偿债及持续经营重大不确定性未解决',
                               '601872.SH':'周期盈利持续性仍待核实'}[card['code']],
                              '风险参数未授权；最新行情、交易状态和公告覆盖需复核']
        c['checks']=[{**check,'reason':(check.get('latest') or check.get('previous') or {}).get('name',check['metric_id'])+'检查',
                      'explanation':'模拟条件事件；不是真实新披露' if 'simulation_event' in check else '基于已披露指标的有限检查',
                      'simulation_event':{k:check['simulation_event'][k] for k in ('code','criterion_id','state','available_at','provenance')}}
                     if 'simulation_event' in check else {**check,'reason':(check.get('latest') or check.get('previous') or {}).get('name',check['metric_id'])+'检查','explanation':'基于已披露指标的有限检查'}
                     for check in card['checks']]
        if card.get('queue_end_from_personal_action') or card.get('manual_action') and card['manual_action'].get('provenance')!='OFFLINE_SIMULATION_NOT_USER_ACTION':
            c.update(state='PRIVATE_ACTION_WITHHELD',state_text='人工观察队列操作不公开')
        result['cards'].append(c)
    result['publication'] = dict(personal_records_included=False, raw_included=False,
                               scope='用户任务明确选定的三个公开公司案例；不公开私人观察池/持仓/现金/Journal')
    body = encoded(result)
    for forbidden in (b'/Users/', b'/home/', b'account_id', b'personal_note'):
        require(forbidden not in body, 'DECISION_PUBLIC_PRIVATE_TEXT')
    return result


def publish_public(report: dict, root: Path, output: Path) -> str:
    target = output.absolute()
    require(not any(p.is_symlink() for p in (target,*target.parents)) and target.resolve().is_relative_to(root.resolve()/'docs/research/results'), 'DECISION_PUBLIC_OUTPUT')
    public = public_projection(report)
    target.mkdir(parents=True, exist_ok=True)
    key = digest(public)
    publish_bytes(target/'decision.json', encoded(public)+b'\n')
    publish_bytes(target/'DECISION.md', markdown(public, public=True).encode())
    return key
