"""Versioned product defaults; these are not trading risk parameters."""
from pathlib import Path
from typing import Literal

from pydantic import Field

from astock.company.models import Strict
from astock.research.core import read_json


class WorkflowPolicy(Strict):
    version: Literal['DAILY_WORKFLOW_POLICY_V1']
    default_research_review_days: int = Field(gt=0, le=90)
    visible_todo_limit: int = Field(gt=0, le=50)


def workflow_policy() -> WorkflowPolicy:
    path = Path(__file__).resolve().parents[3] / 'config/daily/workflow-v1.json'
    return WorkflowPolicy.model_validate(read_json(path))
