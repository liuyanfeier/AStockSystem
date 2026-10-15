"""One P0/B0/T0 rule evaluator, shared by observations and the synthetic lab."""
from decimal import Decimal, localcontext
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Literal

from astock.research.core import digest, require
from astock.screening.strategy_models import StrategyFrame, StrategyParameters


Variant = Literal['P0', 'B0', 'T0']


@lru_cache(maxsize=1)
def strategy_code_hash() -> str:
    package = Path(__file__).resolve().parents[1]
    files = ('screening/strategies.py','screening/strategy_models.py','features/strategy.py',
             'features/market.py','research/core.py')
    return digest({name:sha256((package/name).read_bytes()).hexdigest() for name in files})


def _mean(bars, end: int, period: int, field: str = 'close') -> Decimal | None:
    return sum((getattr(b,field) for b in bars[end-period+1:end+1]),Decimal(0)) / period if end + 1 >= period else None


def _conditions(frame: StrategyFrame, p: StrategyParameters, variant: Variant, *, previous: bool = False) -> tuple[dict, dict]:
    bars = frame.bars[:-1] if previous else frame.bars
    relative = frame.previous_relative_return if previous else frame.relative_return
    dates = frame.previous_relative_dates if previous else frame.relative_dates
    n = len(bars); i = n-1
    closes = [b.close for b in bars]
    fast = _mean(bars, i, p.fast_sessions)
    slow = _mean(bars, i, p.slow_sessions)
    reference = [b.date for b in bars[-p.return_sessions-1:]] if n >= p.return_sessions+1 else []
    relative_known = relative is not None and bool(reference) and dates == reference
    checks = dict(factor_basis_known=True if frame.price_basis != 'UNKNOWN' else None,
                  source_known=True if frame.source_hashes else None,
                  relative_not_negative=relative >= 0 if relative_known else None)
    details = dict(close=str(closes[-1]) if closes else None, ma_fast=str(fast) if fast is not None else None,
                   ma_slow=str(slow) if slow is not None else None, relative_return=str(relative) if relative_known else None,
                   touch_date=None)
    if variant == 'B0':
        high = max(b.high for b in bars[-p.return_sessions-1:-1]) if n >= p.return_sessions+1 else None
        checks.update(close_breaks_prior_high=closes[-1] > high if high is not None else None,
                      above_slow=closes[-1] > slow if slow is not None else None)
        details['prior_high'] = str(high) if high is not None else None
    elif variant == 'T0':
        old_slow = _mean(bars, i-1, p.slow_sessions)
        checks.update(above_slow=closes[-1] > slow if slow is not None else None,
                      prior_not_above_slow=closes[-2] <= old_slow if old_slow is not None else None)
    else:
        lagged = _mean(bars, i-p.trend_lag_sessions, p.fast_sessions)
        checks.update(fast_above_slow=fast > slow if fast is not None and slow is not None else None,
                      fast_not_falling=fast >= lagged if fast is not None and lagged is not None else None,
                      rebound_over_prior_high=closes[-1] > bars[-2].high if n >= 2 else None,
                      above_fast=closes[-1] > fast if fast is not None else None,
                      not_extended=closes[-1] <= fast*p.extension_cap_ratio if fast is not None else None)
        touch = None
        known = n >= max(p.fast_sessions,p.slow_sessions) + p.pullback_sessions - 1
        if known:
            for j in range(i, i-p.pullback_sessions, -1):
                mean = _mean(bars, j, p.fast_sessions)
                if bars[j].low <= mean*p.touch_high_ratio and bars[j].close >= mean*p.touch_close_floor_ratio:
                    touch = j
                    break
        checks['recent_pullback'] = touch is not None if known else None
        checks['since_touch_above_slow'] = all(bars[j].close > _mean(bars,j,p.slow_sessions)
            for j in range(touch,n)) if touch is not None else False if known else None
        details['touch_date'] = bars[touch].date if touch is not None else None
    return checks, details


def _match(checks: dict) -> bool | None:
    # Unknown input stays unknown even when another condition happens to be false.
    return None if any(v is None for v in checks.values()) else all(checks.values())


def evaluate_strategy(frame: StrategyFrame, p: StrategyParameters, variant: Variant,
                       *, already_active: bool = False) -> dict:
    require(variant in p.variants, 'STRATEGY_VARIANT')
    require(frame.as_of >= p.frozen_at, 'STRATEGY_PARAMETERS_AFTER_ASOF')
    with localcontext() as context:
        context.prec = 40
        checks, metrics = _conditions(frame,p,variant)
        previous, _ = _conditions(frame,p,variant,previous=True)
        matched, prior = _match(checks), _match(previous)
        first = matched is True and prior is False
        signal = None if matched is None or matched is True and prior is None else first
        reasons = [name for name,value in checks.items() if value is None or value is False]
        if matched is True and prior is True:
            reasons.append('CONDITION_ALREADY_PRESENT')
        if matched is True and prior is None:
            reasons.append('PREVIOUS_CONDITION_UNKNOWN')
        if already_active:
            signal = False
            reasons.append('EXISTING_PLAN_OR_PAPER_POSITION')
        mean_amount = _mean(frame.bars,len(frame.bars)-1,p.fast_sessions,'amount_cny')
        eligibility = []
        if frame.board == 'UNMODELED':eligibility.append('BOARD_NOT_MODELED')
        if frame.st is not False:eligibility.append('ST_OR_UNKNOWN')
        if frame.suspended is not False:eligibility.append('SUSPENDED_OR_UNKNOWN')
        if frame.up_limit is None or frame.down_limit is None:eligibility.append('LIMIT_RULE_UNKNOWN')
        elif frame.down_limit >= frame.up_limit:eligibility.append('LIMIT_RULE_UNUSABLE')
        elif frame.bars and not frame.down_limit <= frame.bars[-1].close <= frame.up_limit:
            eligibility.append('CLOSE_OUTSIDE_KNOWN_LIMITS')
        if frame.volume is None or frame.volume <= 0:eligibility.append('NO_CONFIRMED_ACTIVITY')
        if mean_amount is None or mean_amount < p.min_mean_amount_cny:eligibility.append('LIQUIDITY_NOT_CONFIRMED')
        if frame.market_date != frame.required_market_date:eligibility.append('MARKET_DATE_STALE')
        if frame.knowledge_basis != 'OFFLINE_SYNTHETIC':eligibility.append('REAL_PROSPECTIVE_EXECUTION_NOT_ADMITTED')
        parameters_hash = digest(p.model_dump(mode='json'))
        source_hash = digest(sorted(set(frame.source_hashes)))
        identifier = digest([strategy_code_hash(),parameters_hash,frame.code,variant,frame.market_date,source_hash,metrics,checks])
        return dict(protocol='SETUP_OBSERVATION_V1', id=identifier, code=frame.code, name=frame.name, variant=variant,
            as_of=frame.as_of.isoformat(), market_date=frame.market_date, required_market_date=frame.required_market_date,
            code_hash=strategy_code_hash(), parameters_hash=parameters_hash, source_hash_set_id=source_hash, metrics=metrics, checks=checks,
            condition_match=matched, previous_condition_match=prior, first_match=signal,
            active_plan_or_position=already_active, rejection_reasons=reasons,
            paper_ready=signal is True and not eligibility, paper_blockers=eligibility,
            real_trade_eligible=False, risk_budget=None, order=None, effectiveness='NOT_VALIDATED')
