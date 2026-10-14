"""Readable company cards and a short daily decision brief; full JSON retains evidence."""
from decimal import Decimal


def percent(value):
    return 'UNKNOWN' if value is None else f'{value * 100:.2f}%'


def statements(values, sources):
    lines = []
    for item in values:
        refs = [f"[{r['source_id']} · {r['locator']}]({sources[r['source_id']]['url']})" for r in item['references']]
        support = '；依据FACT：' + '、'.join(item['supports']) if item['supports'] else ''
        lines.append(f"- **{item['kind']}** {item['text']}{support} {' '.join(refs)}")
    return '\n'.join(lines) or '- UNKNOWN：没有取得足够证据。'


def card_markdown(card: dict, report: dict) -> str:
    research, allocation, f = card['research'], card['allocation'], card['price']['metrics']
    sources = {s['id']: s for s in report['sources']}
    lines = [f"# {card['name']}（{card['code']}）研究卡", '',
             f"研究截止：{report['as_of']}；价格截面：{report['market_date']}。状态：**{research['status']}**。",
             '用途为当前研究，非买入评级/历史PIT。未更新行情，不能按旧报价交易。', '',
             '## 公司与行业', '', statements(research['profile'], sources), '',
             f"申万一级：{allocation['industry_name']}；描述性强弱：{allocation['industry_strength']}；行业20日收益中位数{percent(allocation['industry_median_return20'])}。", '',
             '## 价格与市场环境', '',
             f"收盘{f['close']}元；20日价格收益{percent(f['return_20'])}；MA60 {f['ma60']}；最新成交额/前序均额 {f['activity_ratio']}。",
             f"程序资格：{allocation['eligible']}；分层：{'、'.join(allocation['tags'])}。{allocation['allocation_reason']}。", '',
             '市场环境见同次决策摘要及固定V2报告；涨价本身不能证明公司催化。', '',
             '## 财务原表核验', '',
             '|指标|本期|上期|单位|报告期间/余额日|原表定位|', '|---|---:|---:|---|---|---|']
    for figure in research['financials']:
        ref = figure['reference']
        source = sources[ref['source_id']] if ref else None
        link = f"[{ref['source_id']} · {ref['locator']}]({source['url']})" if ref else 'UNKNOWN'
        period = (figure['period_start'] or '余额日') + ' → ' + figure['period_end']
        lines.append(f"|{figure['name']}|{figure['value'] or ('0' if figure['value'] == '0' else 'UNKNOWN')}|{figure['comparison_value'] if figure['comparison_value'] is not None else '—'}|{figure['unit']}|{period}|{link}|")
    lines += ['', '口径：ASBE合并为主，母公司数字另标；不把半年EPS年化、不自动生成PE/目标价。百分比指标差额用百分点；负基数只算绝对变化。', '']
    for check in card['financial_checks']:
        if check['absolute_change'] is not None:
            change = f"变化{Decimal(check['change_percent']):.2f}%" if check['change_percent'] is not None else f"绝对变化{check['absolute_change']}（原单位）"
            lines.append(f"- {check['metric']}：{change}；{check['validation']}。")
    for title, key in [('公告/事件与催化', 'events'), ('支持继续研究的证据', 'support'), ('最重要的反面证据', 'counter'), ('尚未核实', 'unknowns')]:
        lines += ['', f'## {title}', '', statements(research[key], sources)]
    lines += ['', '## 研究优先级与下一次检查', '', research['priority_reason'], '',
              *[f'- {x}' for x in research['next_checks']], '', '## 条件化交易与退出草案', '',
              '所有条件均待人工审核，没有风险预算/仓位/止损百分比/目标收益/自动订单。']
    draft = card['decision_draft']
    for title, key in [('入场前', 'entry_conditions'), ('不能交易', 'no_trade_conditions'), ('观察退出', 'watch_exit'),
                       ('投资逻辑失效', 'thesis_exit'), ('风控退出', 'risk_exit'), ('趋势复核', 'trend_exit'), ('到期复盘', 'time_review')]:
        lines += ['', f'### {title}', '', *[f'- {s}' for s in draft[key]]]
    lines += ['', draft['actual_order_execution'], '', '## 来源与时点', '',
              '|来源|披露日期|实际取得|可用时间|审计情况|取得路径|Hash|', '|---|---|---|---|---|---|---|']
    for sid in card['source_ids']:
        s = sources[sid]
        lines.append(f"|[{sid}]({s['url']})|{s['published_on']}|{s['retrieved_at']}|{s['available_at']}|{s['audit']}|{s['hosting']}|{s['sha256']}|")
    lines += ['', '披露日期早于价格截面不等于本系统当时已取得；报告使用10月14日实际取得的信息。镜像只证明所保留文档内容，不冒充交易所直接取得。', '',
              *[f'- {x}' for x in report['limitations']], '']
    return '\n'.join(lines)


def brief_markdown(report: dict) -> str:
    m = report['market_context']['metrics']
    index_state = '、'.join(b['name'] + ('低于MA60' if b['above_ma60'] is False else '高于MA60' if b['above_ma60'] is True else '趋势UNKNOWN') for b in report['market_context']['benchmarks'])
    strong = [i['name'] for i in report['market_context']['industries'] if i['strength'] == 'STRONG']
    lines = ['# 每日研究决策摘要 · Research V3', '',
             f"研究截止 {report['as_of']}；行情固定于{report['market_date']}，不是实时市场。", '',
             f"**市场一句话：** 20日上涨{m['return_20']['up']}/{m['return_20']['denominator']}，MA60上方{m['above_ma60']['count']}/{m['above_ma60']['denominator']}；{index_state}。优先核查机会与反面风险，未形成交易许可。", '',
             f"**行业：** 当前描述性STRONG：{'、'.join(strong) or '无'}。行业强势不保证公司经营改善；弱行业中的强股需解释背离。统计为当前成员等权，并非行业指数收益。", '',
             f"从{report['shortlist']['eligible_total']}只技术候选分配{len(report['shortlist']['selected'])}只研究样本，本次完成{len(report['cards'])}份公司卡。研究优先级不是买入评级。", '',
             '|公司/研究状态|最重要的支持|最重要的反面证据|下一步|', '|---|---|---|---|']
    for card in report['cards']:
        c = card['research']
        text = lambda x: x[0]['text'].replace('|', '／') if x else 'UNKNOWN'
        lines.append(f"|[{card['name']}]({card['code']}.md) · {c['status']}|{text(c['support'])}|{text(c['counter'])}|{c['next_checks'][0]}|")
    extreme = [c['name'] for c in report['cards'] if 'EXTREME_RISE_RISK' in c['allocation']['tags']]
    lines += ['', f"**暂不追高：** {'、'.join(extreme)}。大幅上涨需业务增量、估值和成交证据；当前不具备经审核的追高计划。", '',
              '**近期关注：** 下一份实际披露的三季报、盈利/现金流背离、资产减值及偿债、异常波动公告和已宣布项目的兑现情况。计划事件不等于已发生催化。', '',
              '**本周工作：** 优先复核招行资产质量和航运盈利驱动；检查文轩/澳弘经营与价格背离；对善水、近岸及万科解决现金回款、亏损和偿债风险。补齐年度/季度原表与独立行业证据，再讨论交易草案。', '',
              '**不交易条件：** 未取得新行情与ST/停复牌/限价证据，重大风险未决，无法清楚写出逻辑失效条件，或用户风险预算/集中度/退出参数未批准。当前全部公司只产生观察与人工审核草案。', '',
              '**时点与缺口：** 财报期间、披露日、取得时间分别保存；10月14日的研究不能冒充10月12日历史已知结论。有限来源未穷尽全部公告；未经核实的主题叙事、最新财报及估值保持UNKNOWN。', '',
              '完整事实/推断/假设/未知、原表定位、Hash、筛出与降级理由、条件化入场/退出见各公司卡、[research.json](research.json)及[SHORTLIST.json](SHORTLIST.json)。', '']
    return '\n'.join(lines)
