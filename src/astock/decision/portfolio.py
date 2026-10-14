"""Reported-holdings exposure; incomplete accounts never receive invented weights."""
from decimal import Decimal

from astock.decision.models import PositionScope
from astock.research.core import day, instant, require
from astock.research.journal import journal_snapshot


def portfolio_report(store, market: dict, decisions: dict, scope: PositionScope | None) -> dict:
    prices = {f['code']: f for f in market['features']}
    journal = journal_snapshot(store, decisions['as_of'], prices)
    positions = journal['positions']
    if scope:
        require(instant(scope.snapshot_at) <= instant(decisions['as_of']), 'PORTFOLIO_FUTURE_SNAPSHOT')
        require(set(scope.position_event_ids) == {p['source_event'] for p in positions}, 'PORTFOLIO_SCOPE_EVENTS')
        events = {e['event_id']: e for e in journal['events']}
        require(all(instant(events[k]['event_at']) <= instant(scope.snapshot_at) for k in scope.position_event_ids), 'PORTFOLIO_SNAPSHOT_TIME')
    else:
        return dict(mode='UNKNOWN', positions_state='UNKNOWN_NOT_EMPTY', positions=[],
                    account_assets_cny=None, account_weights=None, industry_exposure=None,
                    cash_cny=None, risk_parameters=None,
                    gaps=['未提供完整持仓范围声明；没有记录不等于空仓，有记录也不证明当前完整持仓'])
    cards = {c['code']: c for c in decisions['cards']}
    # Sector association comes from the verified radar membership, not free-form holdings notes.
    sector_by_code = {s['code']: s.get('industry_code') for s in market['features']}
    sector_by_code.update({r['code']:r['industry_code'] for r in decisions['cards'] if r.get('industry_code')})
    for industry in market.get('radar', {}).get('industries', []):
        for code in industry.get('member_codes', []):
            sector_by_code[code] = industry['code']
    rows = []
    for p in positions:
        code = p['code']; f = prices.get(code); card = cards.get(code)
        fresh = bool(f and f.get('last_date') == decisions['required_market_date'] and f.get('close') is not None)
        value = Decimal(str(f['close'])) * p['shares'] if f and f.get('close') is not None else None
        state = card['state'] if card else 'UNKNOWN'
        rows.append(dict(code=code, shares=p['shares'], confirmed=p['confirmed'], mode=scope.mode,
                         indicative_value_cny=str(value) if value is not None else None,
                         price_date=f.get('last_date') if f else None, price_fresh=fresh,
                         industry_code=sector_by_code.get(code), hypothesis_state=card['hypothesis_state'] if card else 'UNKNOWN',
                         research_refresh_due=card['evidence_refresh_due'] if card else None,
                         major_risk_check='CHANGED_EVIDENCE_REVIEW' if card and any(c['type']=='EVENTS' for c in card['evidence_changes']) else 'NOT_EXHAUSTIVELY_CHECKED',
                         review_overdue=p['review_overdue'] or bool(card and card['review_overdue']),
                         priority='优先复核' if state == 'INVALIDATION_REVIEW' or p['review_overdue'] or not fresh else '待确认' if not p['confirmed'] else '按计划跟踪',
                         thesis=p['original_thesis'], source_event=p['source_event'], gaps=p['gaps']))
    all_valued = all(r['indicative_value_cny'] is not None for r in rows)
    total = sum((Decimal(r['indicative_value_cny']) for r in rows), Decimal(0)) if all_valued else None
    complete = scope.complete_positions_confirmed and all(r['confirmed'] for r in rows)
    current = all(r['price_fresh'] for r in rows)
    # Empty declared snapshots only prove flat when the user explicitly confirms completeness.
    account_known = complete and current and total is not None and scope.cash_confirmed
    assets = total + scope.cash_cny if account_known else None
    sector_values = {}
    for r in rows:
        key = r['industry_code'] or 'UNKNOWN'
        if r['indicative_value_cny'] is not None:
            sector_values[key] = sector_values.get(key, Decimal(0)) + Decimal(r['indicative_value_cny'])
        r['reported_stock_value_share'] = str(Decimal(r['indicative_value_cny'])/total) if total and r['indicative_value_cny'] is not None else None
        r['account_weight'] = str(Decimal(r['indicative_value_cny'])/assets) if assets and r['indicative_value_cny'] is not None else None
    gaps = ['风险阈值/单笔风险/最大仓位未授权；不判定超限，不产生订单', '交易状态、公告风险和T+1可卖数量未完成完整核实']
    if not complete:gaps.append('持仓范围或条目未确认，无法证明完整账户')
    if not scope.cash_confirmed:gaps.append('现金未知或未确认，账户总资产及账户权重UNKNOWN')
    if not all_valued:gaps.append('部分价格缺失，不对已知持仓重新归一化为完整组合')
    if not current:gaps.append('报价陈旧；已报持仓占比仅为该价格日的描述性估值')
    return dict(mode=scope.mode, positions_state='DECLARED_COMPLETE' if complete else 'PARTIAL_OR_UNCONFIRMED',
                snapshot_at=scope.snapshot_at, positions=rows, account_assets_cny=str(assets) if assets is not None else None,
                account_weights={r['code']:r['account_weight'] for r in rows} if account_known else None,
                cash_cny=str(scope.cash_cny) if scope.cash_confirmed else None,
                reported_stock_value_cny=str(total) if total is not None else None,
                industry_exposure={k:dict(reported_value_cny=str(v), reported_stock_value_share=str(v/total) if total else None)
                                   for k,v in sector_values.items()},
                exposure_basis='仅声明的已报持仓和对应报价日；不是完整账户权重，不是风险阈值',
                risk_parameters=None, order=None, gaps=gaps)
