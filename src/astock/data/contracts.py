"""Versioned, offline dataset descriptions; no fetching or plugin registry."""

from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


DATASETS = (
    "stock_basic", "trade_cal", "daily", "daily_basic", "adj_factor", "stk_limit",
    "suspend_d", "stock_st", "index_basic", "index_daily", "index_classify", "index_member_all",
)


TUSHARE_HTTPS_ENDPOINT = "https://api.tushare.pro"


def require_https(url: str) -> str:
    parts = urlsplit(url)
    try:
        port = parts.port
    except ValueError:
        raise ValueError("Invalid provider endpoint") from None
    if (parts.scheme != "https" or parts.hostname != "api.tushare.pro" or port not in (None, 443)
            or parts.path not in ("", "/") or parts.username is not None or parts.password is not None
            or "?" in url or "#" in url):
        raise ValueError("Provider endpoint must be the exact pinned Tushare HTTPS origin")
    return TUSHARE_HTTPS_ENDPOINT


class DatasetContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    contract_version: Literal["1.0"]
    dataset: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    provider: Literal["tushare"]
    endpoint: str
    required_fields: list[str] = Field(min_length=1)
    natural_key: list[str] = Field(min_length=1)
    max_rows: int | None = Field(default=None, gt=0)
    timezone: Literal["Asia/Shanghai"]
    units: dict[str, str]
    availability_policy: Literal["UNKNOWN_UNTIL_EVIDENCE"]
    revision_policy: Literal["APPEND_CAPTURE_NEVER_OVERWRITE"]
    fetch_partition: list[str] = Field(min_length=1)
    quality_checks: list[str] = Field(min_length=1)
    source_url: str
    documentation_checked_on: date
    update_schedule: str | None
    notes: list[str]

    @model_validator(mode="after")
    def check_contract(self):
        require_https(self.endpoint)
        source = urlsplit(self.source_url)
        if source.scheme != "https" or not source.hostname or source.username or source.password:
            raise ValueError("Documentation URL must be public HTTPS")
        ZoneInfo(self.timezone)
        for fields in (self.required_fields, self.natural_key, self.fetch_partition, self.quality_checks):
            if any(not field.strip() for field in fields) or len(fields) != len(set(fields)):
                raise ValueError("Contract lists must contain unique nonempty values")
        if not set(self.natural_key) <= set(self.required_fields):
            raise ValueError("Natural key columns must be requested")
        if not set(self.units) <= set(self.required_fields):
            raise ValueError("Unit columns must be requested")
        return self


def load_contracts(root: Path) -> tuple[DatasetContract, ...]:
    contracts = []
    for path in sorted((root / "config/contracts/v1").glob("*.yaml")):
        contract = DatasetContract.model_validate(yaml.safe_load(path.read_text()))
        if path.stem != contract.dataset:
            raise ValueError("Contract filename must match dataset")
        contracts.append(contract)
    if {c.dataset for c in contracts} != set(DATASETS) or len(contracts) != len(DATASETS):
        raise ValueError("Exactly the twelve Tier-A contracts are required")
    return tuple(contracts)
