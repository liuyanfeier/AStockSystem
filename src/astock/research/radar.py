"""Descriptive breadth and current SW2021 industry cohorts, with every denominator."""
from collections import Counter, defaultdict
from statistics import median, mean, pstdev
from astock.research.core import day, require
from astock.screening.candidates import screen


def distribution(stocks: list[dict], field: str) -> dict:
    values = sorted(s[field] for s in stocks if s.get(field) is not None)
    n = len(values)
    return dict(denominator=n, excluded=len(stocks)-n, median=median(values) if n else None,
                equal_weight_mean=mean(values) if n else None, minimum=values[0] if n else None,
                maximum=values[-1] if n else None, dispersion=pstdev(values) if n else None)


def breadth(stocks: list[dict]) -> dict:
    metrics = {}
    for field in ('return_1', 'return_5', 'return_20'):
        values = [s[field] for s in stocks if s.get(field) is not None]
        n = len(values)
        metrics[field] = dict(denominator=n, excluded=len(stocks)-n,
                             up=sum(v > 0 for v in values), down=sum(v < 0 for v in values), flat=sum(v == 0 for v in values),
                             up_ratio=sum(v > 0 for v in values)/n if n else None,
                             down_ratio=sum(v < 0 for v in values)/n if n else None,
                             flat_ratio=sum(v == 0 for v in values)/n if n else None)
    for field in ('above_ma20', 'above_ma60', 'new_high20', 'new_low20'):
        values = [s[field] for s in stocks if s.get(field) is not None]
        metrics[field] = dict(denominator=len(values), excluded=len(stocks)-len(values),
                             count=sum(values), ratio=sum(values)/len(values) if values else None)
    for field in ('return_5', 'return_20', 'activity_ratio', 'volatility_daily'):
        metrics[field + '_distribution'] = distribution(stocks, field)
    amount = [s['amount_today_cny'] for s in stocks if s.get('amount_today_cny') is not None]
    metrics['amount_cny'] = dict(total=sum(amount) if amount else None, denominator=len(amount), excluded=len(stocks)-len(amount))
    metrics['amount_change_1'] = distribution(stocks, 'amount_change_1')
    # Reasons overlap, while each metric's excluded count is exact and disjoint from its denominator.
    reasons = Counter()
    for s in stocks:
        if not s['expected_sessions']: reasons['CALENDAR_UNKNOWN'] += 1
        elif s['last_date'] is None: reasons['LATEST_PRICE_MISSING'] += 1
        if s['expected_sessions'] < 60: reasons['SHORT_LISTING_OR_WINDOW'] += 1
        if s.get('missing_sessions'): reasons['HISTORY_GAP_SUSPENSION_NOT_ASSUMED'] += 1
        if s['price_basis'] == 'UNKNOWN' and s['last_date']: reasons['FACTOR_GAP'] += 1
    return dict(pool_count=len(stocks), metrics=metrics, exclusion_reasons=dict(reasons),
                exclusion_note='原因可重叠；每个指标分母+excluded等于池数量。缺行情不自动认定停牌。')


def changes(current: dict, previous: dict) -> dict:
    result = {}
    for name in ('above_ma20', 'above_ma60', 'new_high20', 'new_low20'):
        now, old = current['metrics'][name], previous['metrics'][name]
        result[name] = dict(count_change=now['count']-old['count'], denominator_now=now['denominator'],
                            denominator_previous=old['denominator'], ratio_change=now['ratio']-old['ratio'] if now['ratio'] is not None and old['ratio'] is not None else None)
    return result


def industry_cohorts(rows: dict, codes: set[str]) -> tuple[dict, dict, dict]:
    classes = {r['industry_code']: r for r in rows.get('industry_classification', [])}
    members, outside, unknown_dates = {}, [], []
    for row in rows.get('industry_membership', []):
        require(row['industry_code'] in classes, 'INDUSTRY_CLASSIFICATION_MISSING')
        code = row['code']
        require(code not in members, 'INDUSTRY_OVERLAP')
        members[code] = row['industry_code']
        if code not in codes: outside.append(code)
        if row['in_date'] is None: unknown_dates.append(code)
    audit = dict(version='SW2021_L1', basis='当前捕获的is_new=Y成员；前日比较使用同一当前成员队列，不是历史PIT行业',
                 classified_current_pool=len(codes & set(members)), missing_current_pool=sorted(codes - set(members)),
                 members_outside_current_pool=sorted(outside), unknown_effective_dates=sorted(unknown_dates),
                 source_hashes=sorted({r['source_hash'] for name in ('industry_classification', 'industry_membership') for r in rows.get(name, [])}))
    return classes, members, audit


def attach_radar(report, manifest, rows, stocks, benchmarks, previous, parameters) -> None:
    report['protocol'] = 'RESEARCH_RADAR_V2'
    codes = {s['code'] for s in stocks}
    classes, members, industry_audit = industry_cohorts(rows, codes)
    current = breadth(stocks)
    prior_stocks = [previous[s['code']] for s in stocks]
    prior = breadth(prior_stocks)
    from astock.research.core import instant, market_day
    now_candidates, _ = screen(stocks, parameters, market_day(instant(report['as_of'])), limit=False)
    # Prior screening uses the same actual research as-of, so stale evidence is not revived.
    from astock.research.core import instant, market_day
    prior_candidates, _ = screen(prior_stocks, parameters, market_day(instant(report['as_of'])), limit=False)
    current_codes, old_codes = {s['code'] for s in now_candidates}, {s['code'] for s in prior_candidates}
    by_board = defaultdict(list)
    for stock in stocks:
        by_board[(stock['exchange'], stock.get('provider_market') or 'UNKNOWN')].append(stock)
    boards = [dict(exchange=e, board=b, breadth=breadth(group), candidate_count=sum(s['code'] in current_codes for s in group))
              for (e,b),group in sorted(by_board.items())]
    by_industry = defaultdict(list)
    for stock in stocks:
        if stock['code'] in members: by_industry[members[stock['code']]].append(stock)
    industries = []
    benchmark = benchmarks[0] if benchmarks else None
    for code, classification in sorted(classes.items()):
        group = by_industry[code]
        b, pb = breadth(group), breadth([previous[s['code']] for s in group])
        returns = b['metrics']['return_20_distribution']
        common = [s for s in group if s.get('return_20') is not None and previous[s['code']].get('return_20') is not None]
        delta = median([s['return_20'] for s in common])-median([previous[s['code']]['return_20'] for s in common]) if common else None
        valid = [s for s in group if s.get('return_20') is not None]
        relative = [s['return_20']-benchmark['return_20'] for s in valid if benchmark and benchmark.get('return_20') is not None and s['return20_dates'] == benchmark['return20_dates']]
        strong = [s for s in valid if s['return_20'] > 0]
        trend = b['metrics']['above_ma60']['ratio']
        direction = ('STRONG' if returns['median'] > 0 and trend is not None and trend > .5 else
                     'WEAK' if returns['median'] < 0 and trend is not None and trend < .5 else 'MIXED') if returns['median'] is not None else 'UNKNOWN'
        diffusion = ('INSUFFICIENT_COVERAGE' if len(valid)<len(group) else 'BROAD' if len(strong) > len(valid)/2 else 'NARROW_LEADERS' if strong else 'NO_POSITIVE_MEMBERS') if valid else 'UNKNOWN'
        industries.append(dict(code=code, name=classification['name'], breadth=b, change=changes(b,pb),
                               median_return20_change=delta, change_denominator=len(common),
                               return20_window_dates=valid[0]['return20_dates'] if valid and len({tuple(s['return20_dates']) for s in valid})==1 else None, strength=direction, change_label='RISING' if delta is not None and delta>0 else 'FALLING' if delta is not None and delta<0 else 'UNCHANGED' if delta==0 else 'UNKNOWN',
                               diffusion=diffusion, candidate_count=sum(s['code'] in current_codes for s in group),
                               candidate_pool_share=sum(s['code'] in current_codes for s in group)/len(current_codes) if current_codes else None,
                               relative_benchmark_median=median(relative) if relative else None, relative_denominator=len(relative),
                               leaders=[dict(code=s['code'], return20=s['return_20']) for s in sorted(valid,key=lambda s:(-s['return_20'],s['code']))[:3]],
                               statistic_basis='个股等权均值/中位数，非市值加权行业指数收益'))
    industry_by_code = {i['code']:i for i in industries}
    for card in report['candidates'] + report['manual_cards']:
        industry = industry_by_code.get(members.get(card['code']))
        stock = card['metrics']
        card['industry'] = dict(code=industry['code'],name=industry['name'],basis=industry_audit['basis']) if industry else None
        card['relative_industry_return20'] = stock.get('return_20')-industry['breadth']['metrics']['return_20_distribution']['median'] if industry and stock.get('return_20') is not None and stock.get('return20_dates') == industry['return20_window_dates'] and industry['return20_window_dates'] is not None and industry['breadth']['metrics']['return_20_distribution']['median'] is not None else None
        if industry and industry['candidate_pool_share'] is not None and industry['candidate_pool_share'] > .5:
            card['counter_evidence'].append('候选多数集中同一行业，属于共同风险敞口，不能当作多个独立机会')
    advancing = current['metrics']['return_20']['up_ratio']
    index_directions = [b['above_ma60'] for b in benchmarks if b.get('above_ma60') is not None]
    breadth_direction = current['metrics']['above_ma60']['ratio']
    alignment = ('ALIGNED' if all(x == (breadth_direction > .5) for x in index_directions) else 'DIVERGENT') if index_directions and breadth_direction is not None and breadth_direction != .5 else 'UNKNOWN'
    full = manifest['universe_scope'] == 'CURRENT_A_SHARE_L' and len(stocks)==len(manifest['universe']) and all(s['last_date'] == manifest['window_end'] for s in stocks)
    # Absence remains visible even when all three identity partitions succeeded.
    report['radar'] = dict(scope='CURRENT_POOL_WITH_GAPS' if manifest['universe_scope']=='CURRENT_A_SHARE_L' and not full else 'CURRENT_POOL_PRICE_COVERED' if full else 'LIMITED_SAMPLE',
                           actual_source_grades=sorted({f.get('evidence_grade','USER_DECLARED') for f in manifest['files']}),
                           market=current, source_coverage=source_coverage(manifest, rows), previous_market=prior, daily_change=changes(current,prior), boards=boards,
                           index_breadth_alignment=alignment, trend='EXPANDING' if advancing is not None and advancing>.5 else 'CONTRACTING' if current['metrics']['return_20']['down_ratio'] is not None and current['metrics']['return_20']['down_ratio']>.5 else 'MIXED_OR_UNKNOWN',
                           industries=industries, industry_coverage=industry_audit,
                           candidate_tracking=dict(eligible_total=len(current_codes), displayed=len(report['candidates']), omitted=len(current_codes)-len(report['candidates']),
                                                   new=sorted(current_codes-old_codes), continued=sorted(current_codes&old_codes), left=sorted(old_codes-current_codes),
                                                   comparison_basis='同一as-of来源复算前一交易日、同一当前证券/行业队列；非当时已知的历史报告'),
                           regime_basis='描述性20日宽度、60日趋势和指数一致性；50%仅是多数定义，未经策略验证，不绑定仓位',
                           style_basis='按供应商交易所/market板块比较；缺市值/估值风格因子',
                           position_weight=None)
    report['limitations'].extend(['当前上市池含幸存者偏差，只用于当前观察', '行业强弱按当前成员等权统计；不是历史PIT、动态主题或资金流向',
                                  '新增上市保留在分母，60日不足保持UNKNOWN；停牌/缺行情不跨越补窗',
                                  '北交所参考日历只在显式声明且沪深一致时使用，价格/因子覆盖另查；不据代码后缀推断身份'])



def source_coverage(manifest: dict, rows: dict) -> dict:
    """Expected denominator is current listed cohort at each source date, not returned count."""
    allowed = set(manifest['universe'])
    pool = [r for r in rows.get('instruments',[]) if r['code'] in allowed]
    prices = defaultdict(set); factors = defaultdict(set)
    for r in rows.get('daily',[]):prices[r['date']].add(r['code'])
    for r in rows.get('adj_factor',[]):factors[r['date']].add(r['code'])
    dates = sorted({r['date'] for r in rows.get('calendar',[]) if r['is_open']==1})
    results=[]
    for d in dates:
        expected = {r['code'] for r in pool if not r.get('list_date') or day(r['list_date'])<=day(d)}
        results.append(dict(date=d, expected_current_cohort=len(expected), prices=len(expected & prices[d]),
                            factors=len(expected & factors[d]), missing_prices=sorted(expected-prices[d]),
                            missing_factors_for_prices=sorted(expected & prices[d]-factors[d]),
                            pre_listing_excluded=len(pool)-len(expected)))
    return dict(basis='当前上市池在各日期已上市成员；不是历史完整证券全集。缺价格可为停牌/供应商遗漏，原因未核实时UNKNOWN。',
                identity_count=len(pool), declared_count=len(manifest['universe']), by_session=results)
