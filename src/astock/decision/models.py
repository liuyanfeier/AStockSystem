"""Small explicit contracts; research criteria never authorize trading parameters."""
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from astock.company.models import Strict
from astock.research.core import instant, require


class Criterion(Strict):
    id: str
    metric_id: str
    expectation: Literal['NOT_LOWER', 'NOT_HIGHER', 'POSITIVE']
    reason: str = Field(min_length=1)
    failure: Literal['CHALLENGED', 'INVALIDATION_REVIEW'] = 'CHALLENGED'


class ResearchPlan(Strict):
    code: str = Field(pattern=r'^\d{6}\.(SH|SZ|BJ)$')
    baseline_catalog_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    baseline_market_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    baseline_market_date: str
    baseline_market_bundle_id: str
    thesis: str = Field(min_length=1)
    attention_reason: str
    no_trade_reasons: list[str] = Field(min_length=1)
    observable_checks: list[str] = Field(min_length=1)
    invalidation_conditions: list[str] = Field(min_length=1)
    unresolved_material_risk: str | None = None
    criteria: list[Criterion] = Field(min_length=1)
    created_at: str
    review_due: str
    review_date_basis: Literal['PROGRAM_PROPOSED_RESEARCH_DATE'] = 'PROGRAM_PROPOSED_RESEARCH_DATE'

    @model_validator(mode='after')
    def validate_plan(self):
        require(instant(self.review_due) > instant(self.created_at), 'DECISION_REVIEW_DATE')
        require(len({c.id for c in self.criteria}) == len(self.criteria), 'DECISION_DUPLICATE_CRITERION')
        return self


class SimulationEvent(Strict):
    """Lab input has no fabricated provider URL, disclosure date or real FACT grade."""
    code: str
    criterion_id: str
    state: Literal['SUPPORTED', 'UNKNOWN', 'CHALLENGED', 'INVALIDATION_REVIEW']
    explanation: str = Field(min_length=1)
    available_at: str
    provenance: Literal['OFFLINE_SIMULATION_NOT_DISCLOSURE']


class ReviewAction(Strict):
    code: str
    action: Literal['END_WATCH', 'ACKNOWLEDGE_CHANGED_EVIDENCE']
    reason: str = Field(min_length=1)
    recorded_at: str
    confirmed: Literal[True]
    provenance: Literal['USER_MANUAL', 'OFFLINE_SIMULATION_NOT_USER_ACTION']
    evidence_hashes: list[str] = Field(default_factory=list)


class RunInput(Strict):
    protocol: Literal['DECISION_LOOP_V0']
    mode: Literal['REAL_EVIDENCE', 'OFFLINE_SIMULATION']
    observed_at: str
    required_market_date: str
    plans: list[ResearchPlan] = Field(min_length=1, max_length=20)
    simulation_events: list[SimulationEvent] = Field(default_factory=list)
    review_actions: list[ReviewAction] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_run(self):
        from astock.research.core import day, market_day
        cutoff = instant(self.observed_at)
        require(day(self.required_market_date) <= market_day(cutoff), 'DECISION_FUTURE_EXPECTED_DATE')
        require(len({p.code for p in self.plans}) == len(self.plans), 'DECISION_DUPLICATE_COMPANY')
        require(all(instant(p.created_at) <= cutoff for p in self.plans), 'DECISION_FUTURE_PLAN')
        require(self.mode == 'OFFLINE_SIMULATION' or not self.simulation_events, 'DECISION_SIMULATION_IN_REAL')
        codes = {p.code: p for p in self.plans}
        keys = [(e.code, e.criterion_id) for e in self.simulation_events]
        require(len(set(keys)) == len(keys), 'DECISION_DUPLICATE_SIMULATION')
        for e in self.simulation_events:
            require(e.code in codes and e.criterion_id in {c.id for c in codes[e.code].criteria}, 'DECISION_SIMULATION_SCOPE')
            require(instant(e.available_at) <= cutoff, 'DECISION_FUTURE_EVENT')
        require(len({a.code for a in self.review_actions}) == len(self.review_actions), 'DECISION_DUPLICATE_ACTION')
        for a in self.review_actions:
            require(a.code in codes and instant(a.recorded_at) <= cutoff, 'DECISION_ACTION_SCOPE_TIME')
            require((self.mode == 'OFFLINE_SIMULATION') == (a.provenance == 'OFFLINE_SIMULATION_NOT_USER_ACTION'), 'DECISION_ACTION_MODE')
        return self


class PositionScope(Strict):
    mode: Literal['USER_MANUAL', 'SIMULATED']
    snapshot_at: str
    position_event_ids: list[str]
    complete_positions_confirmed: bool = False
    cash_cny: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    cash_confirmed: bool = False

    @model_validator(mode='after')
    def valid_scope(self):
        instant(self.snapshot_at)
        require(len(set(self.position_event_ids)) == len(self.position_event_ids), 'PORTFOLIO_DUPLICATE_EVENT')
        require(not self.cash_confirmed or self.cash_cny is not None, 'PORTFOLIO_CASH_UNKNOWN')
        return self
