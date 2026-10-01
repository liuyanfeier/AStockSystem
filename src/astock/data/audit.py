"""Fail-closed MOCK transport and deliberately narrow public audit metadata."""

import re
from datetime import date
from enum import StrEnum
from typing import Literal
from uuid import UUID

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_serializer, model_validator

from astock.data.contracts import ALL_DATASETS, DATASETS, require_https


class SafeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class ErrorCategory(StrEnum):
    TRANSPORT = "TRANSPORT"
    REDIRECT = "REDIRECT"
    AUTH = "AUTH"
    PERMISSION = "PERMISSION"
    PROVIDER = "PROVIDER"
    INVALID_RESPONSE = "INVALID_RESPONSE"


class SafeError(SafeModel):
    # Never copy response messages, bodies, URLs, headers or exception text.
    category: ErrorCategory
    http_status: int | None = Field(default=None, ge=100, le=599)
    provider_code: int | None = None


class RequestParams(SafeModel):
    ts_code: str | None = Field(default=None, pattern=r"^[0-9]{6}\.(SH|SZ|BJ|SI|CSI|WI)$")
    trade_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    exchange: Literal["SSE", "SZSE", "BSE"] | None = None
    market: Literal["MSCI", "CSI", "SSE", "SZSE", "CICC", "SW", "OTH"] | None = None
    list_status: Literal["L", "D", "P", "G", "UN"] | None = None
    src: Literal["SW2014", "SW2021"] | None = None
    level: Literal["L1", "L2", "L3"] | None = None
    is_new: Literal["Y", "N"] | None = None
    l1_code: str | None = Field(default=None, pattern=r"^[0-9]{6}\.SI$")
    l2_code: str | None = Field(default=None, pattern=r"^[0-9]{6}\.SI$")
    l3_code: str | None = Field(default=None, pattern=r"^[0-9]{6}\.SI$")

    @model_validator(mode="after")
    def check_window(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Request window is reversed")
        return self

    @model_serializer
    def serialize_public(self) -> dict:
        return {key: value.isoformat() if isinstance(value, date) else value
                for key, value in self.__dict__.items() if value is not None}

    def public_dict(self) -> dict:
        return self.model_dump(mode="json")


def redact_request_params(untrusted: dict) -> dict:
    """Drop unknown/nested/invalid values; retain only typed allowlisted parameters.

    Do not serialize untrusted input or ValidationError.errors() for review/logging.
    """
    clean = {}
    for key, value in untrusted.items():
        if key not in RequestParams.model_fields or value is None:
            continue
        try:
            item = RequestParams.model_validate({key: value})
            clean.update(item.public_dict())
        except ValueError:
            continue
    try:
        return RequestParams.model_validate(clean).public_dict()
    except ValueError:
        return {}


class TransportConfig(SafeModel):
    endpoint: str = "https://api.tushare.pro"

    @model_validator(mode="after")
    def check_endpoint(self):
        object.__setattr__(self, "endpoint", require_https(self.endpoint))
        return self


class MockProviderTransport:
    """There is intentionally no real-network transport constructor."""

    def __init__(self, config: TransportConfig, transport: httpx.MockTransport):
        if not isinstance(transport, httpx.MockTransport):
            raise TypeError("Only httpx.MockTransport is allowed in Phase 1A")
        self.config = config
        self.transport = transport

    def probe(self, dataset: str, params: RequestParams) -> SafeError | None:
        if dataset not in DATASETS:
            raise ValueError("Unknown dataset")
        try:
            with httpx.Client(transport=self.transport, verify=True, follow_redirects=False,
                              trust_env=False) as client:
                response = client.post(self.config.endpoint, json={
                    "api_name": dataset, "token": "", "params": params.public_dict(), "fields": "",
                })
        except httpx.HTTPError:
            return SafeError(category=ErrorCategory.TRANSPORT)
        if 300 <= response.status_code < 400:
            return SafeError(category=ErrorCategory.REDIRECT, http_status=response.status_code)
        if response.status_code != 200:
            return SafeError(category=ErrorCategory.PROVIDER, http_status=response.status_code)
        try:
            payload = response.json()
            code = payload["code"]
            if type(code) is not int:
                raise ValueError("Invalid provider code")
        except (ValueError, KeyError, TypeError):
            return SafeError(category=ErrorCategory.INVALID_RESPONSE, http_status=200)
        if code != 0:
            return SafeError(category=ErrorCategory.AUTH if code == 40101 else
                             ErrorCategory.PERMISSION if code == 2002 else ErrorCategory.PROVIDER,
                             http_status=200, provider_code=code)
        return None


class RawObjectManifest(SafeModel):
    object_id: UUID
    run_id: UUID
    dataset: Literal[*ALL_DATASETS]
    relative_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieved_at: AwareDatetime
    row_count: int = Field(ge=0)
    schema_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    min_event_date: date | None = None
    max_event_date: date | None = None
    request_params: RequestParams

    @model_validator(mode="after")
    def check_metadata(self):
        expected = rf"data/raw/tushare/{self.dataset}/run_id={self.run_id}/part-[0-9]{{3}}\.parquet"
        if not re.fullmatch(expected, self.relative_path):
            raise ValueError("Raw path must match the provider/dataset/run layout")
        if (self.min_event_date is None) != (self.max_event_date is None):
            raise ValueError("Event date bounds must be paired")
        if self.min_event_date and self.min_event_date > self.max_event_date:
            raise ValueError("Event date bounds are reversed")
        return self
