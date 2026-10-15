"""Manual account facts, without risk thresholds or broker instructions."""
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from astock.company.models import Strict
from astock.research.core import instant, require


class PositionScope(Strict):
    mode: Literal['USER_MANUAL', 'SIMULATED']
    snapshot_at: str
    position_event_ids: list[str]
    complete_positions_confirmed: bool = False
    cash_cny: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    cash_confirmed: bool = False
    # PositionScope contains only scope/cash; research prose belongs to the input below.

    @model_validator(mode='after')
    def valid_scope(self):
        instant(self.snapshot_at)
        require(len(set(self.position_event_ids)) == len(self.position_event_ids), 'PORTFOLIO_DUPLICATE_EVENT')
        require(not self.cash_confirmed or self.cash_cny is not None, 'PORTFOLIO_CASH_UNKNOWN')
        return self


class ManualInput(Strict):
    protocol: Literal['MANUAL_INPUT_V1'] = 'MANUAL_INPUT_V1'
    request_id: str = Field(min_length=1, max_length=100)
    mode: Literal['USER_MANUAL', 'SIMULATED']
    kind: Literal['NOTE', 'POSITION', 'EXECUTION']
    code: str = Field(pattern=r'^\d{6}\.(SH|SZ|BJ)$')
    event_at: AwareDatetime
    note: str = Field(default='', max_length=4000)
    shares: int | None = Field(default=None, ge=0, strict=True)
    price_cny: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    side: Literal['BUY', 'SELL'] | None = None
    remaining_shares: int | None = Field(default=None, ge=0, strict=True)
    expected_position_hash: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    complete_positions_confirmed: bool = False
    cash_cny: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    cash_confirmed: bool = False
    thesis: str | None = Field(default=None, min_length=1, max_length=4000)
    invalidation: str | None = Field(default=None, min_length=1, max_length=4000)
    exit_conditions: str | None = Field(default=None, min_length=1, max_length=4000)

    @model_validator(mode='after')
    def valid_input(self):
        if self.kind == 'NOTE':
            require(bool(self.note.strip()) and all(value is None for value in (
                self.shares, self.price_cny, self.side, self.remaining_shares,
                self.expected_position_hash, self.cash_cny, self.thesis,
                self.invalidation, self.exit_conditions)), 'MANUAL_NOTE_FIELDS')
            require(not self.complete_positions_confirmed and not self.cash_confirmed, 'MANUAL_NOTE_ACCOUNT')
        else:
            require(self.expected_position_hash is not None, 'MANUAL_POSITION_PREVIEW_REQUIRED')
            require(self.shares is not None, 'MANUAL_SHARES_REQUIRED')
            if self.kind == 'POSITION':
                require(self.side is None and self.price_cny is None and self.remaining_shares is None,
                        'MANUAL_POSITION_FIELDS')
            else:
                require(self.shares > 0 and self.side is not None and self.price_cny is not None,
                        'MANUAL_EXECUTION_FIELDS')
                require(self.remaining_shares is not None or not self.complete_positions_confirmed,
                        'MANUAL_UNRECONCILED_ACCOUNT')
                require(self.remaining_shares is not None or all(value is None for value in (
                    self.thesis, self.invalidation, self.exit_conditions)), 'MANUAL_EXECUTION_POSITION_FIELDS')
        require(not self.cash_confirmed or self.cash_cny is not None, 'MANUAL_CASH_UNKNOWN')
        require(self.cash_cny is None or self.cash_confirmed, 'MANUAL_CASH_CONFIRMATION_REQUIRED')
        return self
