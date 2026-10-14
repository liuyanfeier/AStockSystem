"""Deterministic research allocation, sourced cards and conditional decision drafts."""
from collections import Counter
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from astock.company.models import ResearchCatalog
from astock.features.market import ObservationParameters
from astock.research.core import digest, encoded, instant, market_day, read_json, require
from astock.research.publication import publish_bytes
from astock.screening.candidates import observation_card, screen


def verified_market_context(snapshot: dict, store) -> list[dict]:
    """Reuse the established Raw→Store→report path, not self-declared member hashes."""
    from astock.research.service import analyze
    from astock.research.public_results import public_snapshot
    parameters = ObservationParameters.model_validate(snapshot['parameters'])
    regenerated = public_snapshot(analyze(store, snapshot['bundle_id'], snapshot['as_of'], parameters, radar=True))
    require(digest(regenerated) == digest(snapshot), 'COMPANY_MARKET_REPRODUCTION_MISMATCH')
    _, rows = store.snapshot(snapshot['bundle_id'], snapshot['as_of'])
    return [{k: r[k] for k in ('code', 'industry_code', 'source_hash')} for r in rows['industry_membership']]


def shortlist(snapshot: dict, memberships: list[dict], policy: dict) -> dict:
    require(snapshot['purpose'] == 'CURRENT_OBSERVATION', 'COMPANY_MARKET_PURPOSE')
    require(10 <= policy['size'] <= 20 and 1 <= policy['maximum_per_industry'] <= 3, 'COMPANY_SHORTLIST_BOUND')
    require(0 <= policy['not_extended_return20'] < policy['extreme_return20'], 'COMPANY_PRIORITY_THRESHOLDS')
    parameters = ObservationParameters.model_validate(snapshot['parameters'])
    eligible, excluded = screen(snapshot['features'], parameters, market_day(instant(snapshot['as_of'])), limit=False)
    eligible_codes = {s['code'] for s in eligible}
    exclusions = {s['code']: s['reasons'] for s in excluded}
    sectors = {s['code']: s for s in snapshot['radar']['industries']}
    pool = {s['code'] for s in snapshot['features']}
    members = {s['code']: s for s in memberships if s['code'] in pool}
    require(len(members) == len([s for s in memberships if s['code'] in pool]), 'COMPANY_INDUSTRY_OVERLAP')
    allowed_hashes = set(snapshot['radar']['industry_coverage']['source_hashes'])
    require(all(m['source_hash'] in allowed_hashes and m['industry_code'] in sectors for m in members.values()),
            'COMPANY_MEMBERSHIP_LINEAGE')
    nominations = policy['representative_codes']
    require(len(set(nominations)) == len(nominations) and set(nominations) <= pool, 'COMPANY_REPRESENTATIVE_SCOPE')
    audit = []
    for f in sorted(snapshot['features'], key=lambda s: s['code']):
        member = members.get(f['code'])
        sector = sectors.get(member['industry_code']) if member else None
        strong = sector and sector['strength'] == 'STRONG'
        r = f['return_20']
        tags = []
        if r is not None and r >= policy['extreme_return20']:
            tags.append('EXTREME_RISE_RISK')
        if sector and r is not None:
            if strong and r > 0:
                tags.append('STRONG_SECTOR_STRONG_STOCK')
            if strong and 0 < r <= policy['not_extended_return20']:
                tags.append('STRONG_SECTOR_NOT_EXTENDED')
            if sector['strength'] != 'STRONG' and r > 0:
                tags.append('WEAK_OR_MIXED_SECTOR_OUTLIER')
        quality = bool(f['gaps']) or member is None or f['mean_amount_cny'] is None
        liquidity = f['mean_amount_cny'] is not None and f['mean_amount_cny'] < parameters.min_mean_amount_cny
        if quality or liquidity or 'ST' in (f['name'] or ''):
            tags.append('QUALITY_LIQUIDITY_OR_ST_REVIEW')
        if f['code'] in nominations:
            tags.append('REPRESENTATIVE_RESEARCH_SAMPLE')
        if not tags:
            tags.append('ORDINARY_OR_INELIGIBLE')
        audit.append(dict(code=f['code'], name=f['name'], exchange=f['exchange'], board=f['provider_market'],
                          eligible=f['code'] in eligible_codes, exclusions=exclusions.get(f['code'], []),
                          industry_code=member['industry_code'] if member else None,
                          industry_name=sector['name'] if sector else 'UNKNOWN',
                          industry_strength=sector['strength'] if sector else 'UNKNOWN',
                          industry_median_return20=sector['breadth']['metrics']['return_20_distribution']['median'] if sector else None,
                          membership_source_hash=member['source_hash'] if member else None,
                          return20=r, mean_amount_cny=f['mean_amount_cny'], tags=tags,
                          selected=False, allocation_reason='未进入有限深度研究容量；不等于公司质量差'))
    by_code = {r['code']: r for r in audit}
    selected, counts = [], Counter()

    def add(row, reason):
        industry = row['industry_code'] or 'UNKNOWN'
        if row['selected'] or len(selected) >= policy['size']:
            return
        if counts[industry] >= policy['maximum_per_industry']:
            row['allocation_reason'] = '行业集中度上限；保留筛选资格，研究优先级降级'
            return
        row.update(selected=True, allocation_reason=reason)
        selected.append(row)
        counts[industry] += 1

    for code in nominations:
        add(by_code[code], '公开研究任务提名的代表样本；同时保留程序资格、风险与争议')
    # Round-robin gives every stratum a research slot rather than maximizing return.
    tiers = ['STRONG_SECTOR_NOT_EXTENDED', 'STRONG_SECTOR_STRONG_STOCK',
             'WEAK_OR_MIXED_SECTOR_OUTLIER', 'EXTREME_RISE_RISK', 'QUALITY_LIQUIDITY_OR_ST_REVIEW']
    ranked = sorted(audit, key=lambda r: (-(r['return20'] if r['return20'] is not None else -999), r['code']))
    queues = {t: [r for r in ranked if t in r['tags'] and (r['eligible'] or t == tiers[-1])
                  and (t != tiers[-1] or (r['return20'] or 0) > 0)] for t in tiers}
    while len(selected) < policy['size']:
        before = len(selected)
        for tier in tiers:
            while queues[tier]:
                row = queues[tier].pop(0)
                previous = len(selected)
                add(row, f'分层代表：{tier}；层内按20日收益/代码，行业上限约束')
                if len(selected) > previous:
                    break
        if len(selected) == before:
            break
    return dict(protocol='COMPANY_SHORTLIST_V1', market_snapshot_hash=digest(snapshot),
                bundle_id=snapshot['bundle_id'], market_as_of=snapshot['as_of'], market_date=snapshot['window_end'],
                parameters_hash=snapshot['parameters_hash'], policy=policy, policy_hash=digest(policy),
                pool=len(audit), eligible_total=len(eligible), selected=selected, audit=audit,
                limitations=['研究优先级不是买入评级；启发式未经收益验证',
                             '行业为当前SW2021成员；固定价格截面不含10月12日之后的行情',
                             '技术资格不包含完整财务、公告、ST与可成交性检查'])


def arithmetic(figure: dict) -> dict:
    value = Decimal(figure['value']) if figure['value'] is not None else None
    prior = Decimal(figure['comparison_value']) if figure['comparison_value'] is not None else None
    result = dict(metric=figure['id'], value=figure['value'], comparison_value=figure['comparison_value'],
                  change_percent=None, absolute_change=None, validation='NO_COMPARISON')
    if value is None or prior is None:
        return result
    # Flow comparisons must have matching fiscal intervals, not H1 versus Q1/FY.
    start, old_start = figure['period_start'], figure['comparison_period_start']
    if (start is None) != (old_start is None):
        result['validation'] = 'INCOMPARABLE_PERIODS'
        return result
    if start:
        from astock.research.core import day
        now_length = (day(figure['period_end']) - day(start)).days
        old_length = (day(figure['comparison_period_end']) - day(old_start)).days
        if abs(now_length - old_length) > 2:
            result['validation'] = 'INCOMPARABLE_PERIODS'
            return result
    result['absolute_change'] = str(value - prior)
    if prior <= 0 or figure['unit'] == 'PERCENT':
        # Negative base: report loss change in original units, no misleading profit growth.
        result['validation'] = 'ABSOLUTE_CHANGE_ONLY'
        return result
    computed = (value / prior - 1) * 100
    result['change_percent'] = str(computed)
    reported = figure.get('reported_change_percent')
    result['validation'] = 'RECOMPUTED'
    if reported is not None:
        require(abs(computed - Decimal(reported)) <= Decimal('0.02'), 'COMPANY_REPORTED_ARITHMETIC_MISMATCH')
        result['validation'] = 'MATCHES_REPORTED_ROUNDING'
    return result


def verify_documents(catalog: ResearchCatalog, documents: Path) -> list[dict]:
    """Verify retained bytes; a hash proves binding, not provider authenticity or truth."""
    root = documents.resolve()
    require(not any(p.is_symlink() for p in (documents, *documents.parents)), 'COMPANY_DOCUMENT_SYMLINK')
    checks = []
    for source in catalog.sources:
        if source.state != 'RETRIEVED':
            continue
        path = root / f'{source.id}.pdf'
        require(not path.is_symlink() and path.is_file(), 'COMPANY_DOCUMENT_MISSING')
        body = path.read_bytes()
        require(body.startswith(b'%PDF-') and sha256(body).hexdigest() == source.sha256, 'COMPANY_DOCUMENT_CHANGED')
        checks.append(dict(id=source.id, sha256=source.sha256, bytes=len(body),
                           binding='LOCAL_DOCUMENT_BYTES', hosting=source.hosting,
                           limitation='未验证提供方签名；镜像不等同于交易所直接下载'))
    return checks


def build(snapshot: dict, selection: dict, catalog: ResearchCatalog, documents: Path) -> dict:
    document_checks = verify_documents(catalog, documents)
    require(digest(snapshot) == selection['market_snapshot_hash'], 'COMPANY_MARKET_CHANGED')
    require(instant(snapshot['as_of']) <= instant(catalog.as_of), 'COMPANY_MARKET_AFTER_RESEARCH')
    chosen = {r['code']: r for r in selection['selected']}
    require({c.code for c in catalog.companies} <= set(chosen), 'COMPANY_OUTSIDE_SHORTLIST')
    require({s.id for s in catalog.sources if s.state == 'RETRIEVED'} == {c['id'] for c in document_checks},
            'COMPANY_DOCUMENT_BINDING_REQUIRED')
    # Check records themselves, not only IDs: user-supplied validation cannot grant trust.
    for check in document_checks:
        source = next(s for s in catalog.sources if s.id == check['id'])
        require(check['sha256'] == source.sha256, 'COMPANY_DOCUMENT_BINDING_CHANGED')
    prices = {s['code']: s for s in snapshot['features']}
    sources = {s.id: s for s in catalog.sources}
    cards = []
    for company in catalog.companies:
        f = prices[company.code]
        card = observation_card(f, None, selection=chosen[company.code]['allocation_reason'])
        card['no_trade_conditions'] = [s.replace('公告、基本面、行业/主题及竞争预期未核实', '有限财务/公告已核查；竞争预期、产业证据与最新风险尚未完整核实') for s in card['no_trade_conditions']]
        figures = [v.model_dump(mode='json') for v in company.financials]
        statements = [*company.profile, *company.events, *company.support, *company.counter, *company.unknowns]
        refs = {r.source_id for s in statements for r in s.references}
        refs |= {v.reference.source_id for v in company.financials if v.reference}
        invalidations = company.thesis_invalidations
        draft = dict(state='CONDITIONAL_DRAFT_REQUIRES_HUMAN_REVIEW', trade_eligible=False,
                     entry_conditions=[
                         '更新收盘行情并核查市场宽度/指数趋势是否允许承担风险；允许继续空仓',
                         '重新计算行业扩散和个股相对表现；背离需原始事实解释',
                         '复核下一次财报/公告是否支持公司研究逻辑，未决风险解决',
                         'Breakout/Pullback只为待验证假设：观察价格行为和成交，重新计算参考值',
                         '交易当日核实ST、停复牌、涨跌停、流动性、T+1和隔夜跳空可成交约束',
                         '用户批准风险预算、仓位、集中度、初始退出与复盘日期后才能人工决策'],
                     no_trade_conditions=[*card['no_trade_conditions'], '旧价格截面不能作为当前报价',
                                          '存在重大未决财务/公告风险、无可核验催化或逻辑失效条件不清晰时不交易',
                                          '用户风险预算/交易参数未设定；不得由研究优先级代替'],
                     watch_exit=['不再符合研究筛选或证据陈旧：退出观察队列，不产生订单'],
                     thesis_exit=invalidations,
                     risk_exit=['重大风险公告、市场环境变化、集中度超经批准预算：人工复核；阈值尚未批准'],
                     trend_exit=['持续趋势/相对强弱反转时复核；具体阈值待验证及用户批准'],
                     time_review=company.next_checks,
                     actual_order_execution='独立记录实际成交、原因与执行偏差；本工作流不产生订单',
                     risk_budget=None, position=None, stop_loss_percent=None, target_return=None,
                     review_deadline=None)
        if 'EXTREME_RISE_RISK' in chosen[company.code]['tags']:
            draft['no_trade_conditions'].append('短期涨幅过大：没有可验证业务增量、估值依据和回撤后成交验证时，不追高')
        cards.append(dict(code=company.code, name=f['name'], research=company.model_dump(mode='json'),
                          allocation=chosen[company.code], price=card, financial_checks=[arithmetic(v) for v in figures],
                          source_ids=sorted(refs), published_before_price_date=[s for s in sorted(refs) if sources[s].published_on.isoformat() <= snapshot['window_end']],
                          decision_draft=draft))
    return dict(protocol='COMPANY_RESEARCH_REPORT_V1', purpose='CURRENT_RESEARCH_NOT_HISTORICAL_BACKTEST',
                as_of=catalog.as_of, market_date=snapshot['window_end'], market_snapshot_hash=digest(snapshot),
                market_bundle_id=snapshot['bundle_id'], market_parameters_hash=snapshot['parameters_hash'],
                catalog_hash=digest(catalog.model_dump(mode='json')), shortlist=selection,
                market_context=dict(metrics=snapshot['radar']['market']['metrics'], benchmarks=[
                    {k:b.get(k) for k in ('code','name','above_ma60','return_20')} for b in snapshot['market']['benchmarks']],
                    industries=[{k:i.get(k) for k in ('code','name','strength','diffusion')} for i in snapshot['radar']['industries']]),
                sources=[s.model_dump(mode='json') for s in catalog.sources], document_checks=document_checks,
                cards=cards, personal_records_included=False, raw_included=False,
                limitations=['披露事实为公司声明；本地Hash仅证明保留字节一致，并非独立审计结论',
                             '研究可知时间以实际取得/保守披露日边界为准，不能回填成10月12日已知的完整研究',
                             '来源核查是有限原始文件样本，未穷尽全部公告、年度/季度及负面事件',
                             '财务质量、估值和策略盈利能力均需后续验证；风险参数空置，无订单'])


def publish(report: dict, output: Path) -> str:
    from astock.company.render import card_markdown, brief_markdown
    # Only this constructed projection crosses into Git. No private report or Journal input.
    allowed = {'protocol', 'purpose', 'as_of', 'market_date', 'market_snapshot_hash', 'market_bundle_id',
               'market_parameters_hash', 'catalog_hash', 'shortlist', 'market_context', 'sources', 'document_checks', 'cards',
               'personal_records_included', 'raw_included', 'limitations'}
    from astock.company.models import Company, Source
    public = {k: report[k] for k in allowed}
    public['sources'] = [Source.model_validate(s).model_dump(mode='json') for s in report['sources']]
    for card in public['cards']:
        Company.model_validate(card['research'])
        require(set(card) <= {'code','name','research','allocation','price','financial_checks','source_ids','published_before_price_date','decision_draft'}, 'COMPANY_PUBLIC_CARD_FIELDS')
    body = encoded(public)
    for forbidden in (b'/Users/', b'/home/', b'journal', b'personal_note', b'account_id'):
        require(forbidden not in body, 'COMPANY_PUBLIC_PRIVATE_TEXT')
    run = digest(public)
    output.mkdir(parents=True, exist_ok=True)
    publish_bytes(output / 'research.json', body + b'\n')
    publish_bytes(output / 'DECISION_BRIEF.md', brief_markdown(public).encode())
    for card in report['cards']:
        publish_bytes(output / f"{card['code']}.md", card_markdown(card, public).encode())
    publish_bytes(output / 'SHORTLIST.json', encoded(report['shortlist']) + b'\n')
    return run
