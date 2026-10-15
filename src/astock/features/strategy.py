"""Small versioned strategy windows from the same verified rows and price transform."""
from collections import defaultdict
from decimal import Decimal, localcontext

from astock.features.market import adjusted_ohlc, consecutive_tail
from astock.research.core import day, instant, market_day, require
from astock.research.tushare import merge_status
from astock.screening.strategy_models import StrategyBar, StrategyFrame, StrategyParameters


def decimal_value(value) -> Decimal:
    return Decimal(str(value))


def _return(prices: list[dict] | None, tail: list[dict], period: int, offset: int = 0):
    stop = len(tail) - offset
    if prices is None or stop < period + 1:
        return None, []
    return prices[stop-1]['close'] / prices[stop-period-1]['close'] - 1, [r['date'] for r in tail[stop-period-1:stop]]


def strategy_frames(manifest: dict, rows: dict, as_of: str, required_market_date: str,
                     parameters: StrategyParameters) -> list[StrategyFrame]:
    """No copied Store or publication JSON; source adapter supplies verified as-of rows."""
    require(manifest['purpose'] == 'CURRENT_OBSERVATION', 'STRATEGY_PURPOSE')
    require(day(manifest['window_end']) <= day(required_market_date) <= market_day(instant(as_of)), 'STRATEGY_DATE_SCOPE')
    identities = {r['code']: r for r in rows.get('instruments', [])}
    grouped = {name: defaultdict(list) for name in ('daily','index_daily','adj_factor','calendar')}
    for name, values in grouped.items():
        for row in rows.get(name, []):
            values[row['exchange'] if name == 'calendar' else row['code']].append(row)
    end = day(manifest['window_end'])
    needed = max(parameters.slow_sessions + parameters.pullback_sessions,
                 parameters.fast_sessions + parameters.trend_lag_sessions + 1,
                 parameters.return_sessions + 2, parameters.slow_sessions + 2)
    benchmark = None
    benchmark_sources = set()
    if manifest['benchmarks']:
        code = manifest['benchmarks'][0]
        identity = identities.get(code)
        if identity:
            benchmark_calendar = grouped['calendar'][identity.get('calendar_exchange', identity['exchange'])]
            _, _, tail = consecutive_tail(code, identity, grouped['index_daily'][code],
                benchmark_calendar, end, listing=True)
            tail = tail[-needed:]
            _, values = adjusted_ohlc(code, identity, tail, [], decimal_value)
            benchmark = values, tail
            benchmark_sources = {r['source_hash'] for r in benchmark_calendar}
            benchmark_sources |= {h for row in tail for h in row.get('component_sources', [row['source_hash']])}
            if identity.get('source_hash'):
                benchmark_sources.add(identity['source_hash'])
    status = merge_status(rows.get('status', []))
    result = []
    with localcontext() as context:
        context.prec = 40
        for code in manifest['universe']:
            identity = identities.get(code, dict(code=code, name=None, exchange='UNKNOWN', kind='STOCK'))
            calendar = grouped['calendar'][identity.get('calendar_exchange', identity['exchange'])]
            sessions, _, tail = consecutive_tail(code, identity, grouped['daily'][code], calendar, end, listing=True)
            tail = tail[-needed:]
            basis, values = adjusted_ohlc(code, identity, tail, grouped['adj_factor'][code], decimal_value)
            gaps = []
            if not sessions:
                gaps.append('CALENDAR_OR_IDENTITY_UNKNOWN')
            if not tail:
                gaps.append('LATEST_PRICE_MISSING')
            if values is None:
                gaps.append('REQUIRED_WINDOW_FACTOR_UNKNOWN')
            relative, relative_dates, prior_relative, prior_dates = None, [], None, []
            if benchmark:
                current, dates = _return(values, tail, parameters.return_sessions)
                bench, bench_dates = _return(*benchmark, parameters.return_sessions)
                previous, previous_dates = _return(values, tail, parameters.return_sessions, 1)
                bench_previous, bench_previous_dates = _return(*benchmark, parameters.return_sessions, 1)
                if current is not None and bench is not None and dates == bench_dates:
                    relative, relative_dates = current - bench, dates
                if previous is not None and bench_previous is not None and previous_dates == bench_previous_dates:
                    prior_relative, prior_dates = previous - bench_previous, previous_dates
            if relative is None:
                gaps.append('RELATIVE_WINDOW_UNKNOWN_OR_MISMATCH')
            observed = status.get((code, end.isoformat()), {})
            board = {'SSE':'SSE_MAIN','SZSE':'SZSE_MAIN'}.get(identity['exchange'], 'UNMODELED') if identity.get('provider_market') == '主板' else 'UNMODELED'
            hashes = {h for row in tail for h in row.get('component_sources', [row['source_hash']])}
            hashes |= {r['source_hash'] for r in grouped['adj_factor'][code] if r['date'] in {p['date'] for p in tail}}
            hashes |= {r['source_hash'] for r in calendar}
            if identity.get('source_hash'):
                hashes.add(identity['source_hash'])
            if benchmark:
                hashes.update(benchmark_sources)
            if observed.get('source_hashes'):
                hashes.update(observed['source_hashes'])
            bars = [StrategyBar(date=r['date'], amount_cny=decimal_value(r['amount']), **v)
                    for r,v in zip(tail, values or [])]
            result.append(StrategyFrame(code=code, name=identity.get('name'), as_of=as_of,
                market_date=end.isoformat(), required_market_date=required_market_date, board=board,
                price_basis=basis, bars=bars, relative_return=relative, relative_dates=relative_dates,
                previous_relative_return=prior_relative, previous_relative_dates=prior_dates,
                st={'YES':True,'NO':False}.get(observed.get('st')),
                suspended={'YES':True,'NO':False}.get(observed.get('suspended')),
                up_limit=observed.get('up_limit'), down_limit=observed.get('down_limit'),
                volume=tail[-1]['volume'] if tail else None, source_hashes=sorted(hashes), gaps=gaps))
    return result
