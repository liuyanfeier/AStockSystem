"""Typed research instructions, separate from positions, fills and orders."""
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from astock.company.models import Strict
from astock.decision.models import Criterion, ResearchPlan, ReviewAction
from astock.research.core import require


class PlanDraft(Strict):
    thesis: str = Field(min_length=1, max_length=4000)
    attention_reason: str = Field(min_length=1, max_length=4000)
    no_trade_reasons: list[str] = Field(min_length=1, max_length=20)
    observable_checks: list[str] = Field(min_length=1, max_length=20)
    invalidation_conditions: list[str] = Field(min_length=1, max_length=20)
    criteria: list[Criterion] = Field(min_length=1, max_length=20)
    review_due: AwareDatetime
    unresolved_material_risk: str | None = Field(default=None, min_length=1, max_length=4000)

    @model_validator(mode='after')
    def valid_text(self):
        require(bool(self.thesis.strip()) and bool(self.attention_reason.strip()), 'PLAN_EMPTY_TEXT')
        require(all(text.strip() for values in (self.no_trade_reasons, self.observable_checks,
                                                self.invalidation_conditions) for text in values), 'PLAN_EMPTY_TEXT')
        return self


class PlanInput(Strict):
    protocol: Literal['RESEARCH_PLAN_INPUT_V1'] = 'RESEARCH_PLAN_INPUT_V1'
    request_id: str = Field(min_length=1, max_length=100)
    mode: Literal['USER_MANUAL', 'SIMULATED']
    action: Literal['CREATE', 'END_WATCH', 'REVIEW_EVIDENCE']
    code: str = Field(pattern=r'^\d{6}\.(SH|SZ|BJ)$')
    expected_plan_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    reason: str = Field(min_length=1, max_length=4000)
    draft: PlanDraft | None = None

    @model_validator(mode='after')
    def valid_action(self):
        require(bool(self.reason.strip()), 'PLAN_EMPTY_REASON')
        require((self.action == 'CREATE') == (self.draft is not None), 'PLAN_DRAFT_ACTION')
        return self


class PlanRecord(Strict):
    request: PlanInput
    plan: ResearchPlan | None = None
    review: ReviewAction | None = None
    target_plan_hash: str | None = None
    bootstrap_hash: str
    baseline_hash: str
    previous_catalog_hash: str
    reviewed_catalog_hash: str

    @model_validator(mode='after')
    def valid_record(self):
        create = self.request.action == 'CREATE'
        require(create == (self.plan is not None) and create == (self.review is None), 'PLAN_RECORD_ACTION')
        require(not self.plan or self.plan.code == self.request.code, 'PLAN_RECORD_CODE')
        require(not self.review or self.review.code == self.request.code, 'PLAN_RECORD_CODE')
        require(create or self.target_plan_hash is not None, 'PLAN_RECORD_TARGET')
        return self
