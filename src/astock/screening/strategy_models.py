"""Versioned research rules and source-bound frames; no real order authority."""
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from astock.company.models import Strict
from astock.research.core import day, instant, market_day, require


class StrategyParameters(Strict):
    protocol: Literal['STRATEGY_RESEARCH_V1']
    version: str = Field(min_length=1)
    frozen_at: AwareDatetime
    variants: tuple[Literal['P0', 'B0', 'T0'], ...]
    fast_sessions: int = Field(ge=2, le=250)
    slow_sessions: int = Field(ge=3, le=250)
    return_sessions: int = Field(ge=1, le=250)
    trend_lag_sessions: int = Field(ge=1, le=20)
    pullback_sessions: int = Field(ge=1, le=20)
    touch_high_ratio: Decimal = Field(ge=1, allow_inf_nan=False)
    touch_close_floor_ratio: Decimal = Field(gt=0, le=1, allow_inf_nan=False)
    extension_cap_ratio: Decimal = Field(ge=1, allow_inf_nan=False)
    min_mean_amount_cny: Decimal = Field(ge=0, allow_inf_nan=False)
    top_n: int = Field(ge=1, le=100)
    research_only: Literal[True]
    strategy_validated: Literal[False]
    real_risk_budget: None = None

    @model_validator(mode='after')
    def fixed_comparison(self):
        require(self.variants == ('P0', 'B0', 'T0'), 'STRATEGY_ALL_VARIANTS_REQUIRED')
        require(self.fast_sessions < self.slow_sessions, 'STRATEGY_WINDOW_ORDER')
        require(self.touch_high_ratio <= self.extension_cap_ratio, 'STRATEGY_EXTENSION_ORDER')
        return self


class StrategyBar(Strict):
    date: str
    close: Decimal = Field(gt=0, allow_inf_nan=False)
    high: Decimal = Field(gt=0, allow_inf_nan=False)
    low: Decimal = Field(gt=0, allow_inf_nan=False)
    amount_cny: Decimal = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode='after')
    def price_order(self):
        day(self.date)
        require(self.low <= self.close <= self.high, 'STRATEGY_PRICE_ORDER')
        return self


class StrategyFrame(Strict):
    protocol: Literal['STRATEGY_FRAME_V1'] = 'STRATEGY_FRAME_V1'
    code: str
    name: str | None
    as_of: AwareDatetime
    market_date: str
    required_market_date: str
    board: Literal['SSE_MAIN', 'SZSE_MAIN', 'UNMODELED']
    price_basis: Literal['FACTOR_ADJUSTED_PRICE_NOT_TOTAL_RETURN', 'UNKNOWN']
    bars: list[StrategyBar]
    relative_return: Decimal | None = Field(default=None, allow_inf_nan=False)
    relative_dates: list[str] = Field(default_factory=list)
    previous_relative_return: Decimal | None = Field(default=None, allow_inf_nan=False)
    previous_relative_dates: list[str] = Field(default_factory=list)
    knowledge_basis: Literal['CURRENT_OBSERVATION', 'OFFLINE_SYNTHETIC'] = 'CURRENT_OBSERVATION'
    suspended: bool | None = None
    st: bool | None = None
    up_limit: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    down_limit: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    volume: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    source_hashes: list[str]
    gaps: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def frame_order(self):
        require([b.date for b in self.bars] == sorted({b.date for b in self.bars}), 'STRATEGY_BAR_ORDER')
        require(not self.bars or self.bars[-1].date == self.market_date, 'STRATEGY_LATEST_BAR_REQUIRED')
        require(day(self.market_date) <= market_day(instant(self.as_of)), 'STRATEGY_FUTURE_MARKET_DATE')
        require(day(self.required_market_date) <= market_day(instant(self.as_of)), 'STRATEGY_FUTURE_REQUIRED_DATE')
        require(all(len(h) == 64 and all(c in '0123456789abcdef' for c in h) for h in self.source_hashes),
                'STRATEGY_SOURCE_HASH')
        return self
