"""Small pinned HTTPS REST client. No persistence, SDK or response-body logging."""

import math
import ssl
import time
import threading
from datetime import datetime, timezone
from typing import Any, Callable

import httpx
from pydantic import SecretStr, StrictStr, field_validator, model_validator

from astock.data.audit import ErrorCategory, RequestParams, SafeError, SafeModel
from astock.data.contracts import DatasetContract, TUSHARE_HTTPS_ENDPOINT, require_https


PROBE_DATASETS = ('trade_cal', 'stock_basic', 'daily', 'daily_basic', 'adj_factor',
                  'stk_limit', 'stock_st', 'suspend_d')
CLIENT_VERSION = '0.1.0'


class ProviderFailure(Exception):
    def __init__(self, error: SafeError):
        self.error = error
        super().__init__(error.category.value)


class ProviderTable(SafeModel):
    fields: list[StrictStr]
    items: list[list[Any]]
    retrieved_at: datetime

    @field_validator('fields')
    @classmethod
    def valid_fields(cls, fields):
        if not fields or len(set(fields)) != len(fields) or any(not f.isidentifier() for f in fields):
            raise ValueError('Invalid field structure')
        return fields

    @model_validator(mode='after')
    def valid_rows(self):
        for row in self.items:
            if len(row) != len(self.fields):
                raise ValueError('Row width differs from fields')
            if any(type(v) not in (str, int, float, bool, type(None)) or
                   (type(v) is float and not math.isfinite(v)) for v in row):
                raise ValueError('Expected finite JSON scalar values')
        if self.retrieved_at.tzinfo is None:
            raise ValueError('Retrieval timestamp requires a timezone')
        return self


def _tls_failure(exc: Exception) -> bool:
    # Inspect causes without ever serializing exception text or request bodies.
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if isinstance(exc, ssl.SSLError):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


class TushareClient:
    def __init__(self, token: SecretStr, *, endpoint: str = TUSHARE_HTTPS_ENDPOINT,
                 transport: httpx.MockTransport | None = None,
                 clock: Callable = time.monotonic, sleep: Callable = time.sleep):
        self._endpoint = require_https(endpoint)
        if not isinstance(token, SecretStr) or not token.get_secret_value().strip():
            raise ValueError('TUSHARE_TOKEN is not configured')
        if transport is not None and not isinstance(transport, httpx.MockTransport):
            raise ValueError('Only mock test transport injection is allowed')
        self._token = token
        self._transport = transport
        self._clock, self._sleep = clock, sleep
        self._last_start = None
        self.request_count = 0
        self._owner_thread = threading.get_ident()

    def _pace(self):
        if self._last_start is not None:
            remaining = 1.25 - (self._clock() - self._last_start)
            if remaining > 0:
                self._sleep(remaining)
        self._last_start = self._clock()

    def fetch(self, contract: DatasetContract, params: RequestParams) -> ProviderTable:
        if contract.dataset not in PROBE_DATASETS or contract.contract_version != '1.0':
            raise ValueError('Endpoint outside pinned Phase 1B catalog')
        return self._fetch(contract, params, attempts=2)

    def fetch_bse_mapping(self, contract: DatasetContract) -> ProviderTable:
        if contract.dataset != 'bse_mapping' or contract.contract_version != '2.0' or self.request_count:
            raise ValueError('Only one Phase 1C.0 mapping attempt is permitted')
        return self._fetch(contract, RequestParams(), attempts=1)

    def fetch_slice(self, contract: DatasetContract, params: RequestParams) -> ProviderTable:
        from astock.data.slice_plan import APPROVED, DATASETS
        allowed_dates = {date for dates in APPROVED.values() for date in dates}
        calendars = {(min(dates), max(dates)) for dates in APPROVED.values()}
        scope = params.public_dict()
        market = (contract.dataset in DATASETS and set(scope) == {'trade_date'}
                  and scope['trade_date'] in allowed_dates)
        calendar = (contract.dataset == 'trade_cal' and set(scope) == {'exchange','start_date','end_date'}
                    and scope['exchange'] == 'SSE' and (scope['start_date'],scope['end_date']) in calendars)
        if contract.contract_version != '2.0' or not (market or calendar):
            raise ValueError('Request outside approved Phase 1C.1 slices')
        return self._fetch(contract, params, attempts=1)

    def _fetch(self, contract: DatasetContract, params: RequestParams, *, attempts: int) -> ProviderTable:
        if threading.get_ident() != self._owner_thread:
            raise ValueError('Phase 1B client is single-threaded')
        require_https(self._endpoint)
        require_https(contract.endpoint)
        wire_params = params.public_dict()
        for key in ('trade_date', 'start_date', 'end_date'):
            if key in wire_params:
                wire_params[key] = wire_params[key].replace('-', '')
        for attempt in range(attempts):
            self._pace()
            self.request_count += 1
            retry = False
            try:
                with httpx.Client(transport=self._transport, verify=True, follow_redirects=False,
                                  trust_env=False, timeout=20) as client:
                    response = client.post(self._endpoint, json={
                        'api_name': contract.dataset, 'token': self._token.get_secret_value(),
                        'params': wire_params, 'fields': ','.join(contract.required_fields),
                    })
                retrieved_at = datetime.now(timezone.utc)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                retry = not _tls_failure(exc)
                error = SafeError(category=ErrorCategory.TRANSPORT)
            except httpx.HTTPError:
                error = SafeError(category=ErrorCategory.TRANSPORT)
            else:
                if 300 <= response.status_code < 400:
                    error = SafeError(category=ErrorCategory.REDIRECT, http_status=response.status_code)
                elif response.status_code != 200:
                    retry = 500 <= response.status_code < 600
                    error = SafeError(category=ErrorCategory.PROVIDER, http_status=response.status_code)
                else:
                    try:
                        payload = response.json()
                        code = payload['code']
                        if type(code) is not int:
                            raise ValueError('Invalid code')
                        if code != 0:
                            category = (ErrorCategory.PERMISSION if code == 2002 else
                                        ErrorCategory.AUTH if code == 40101 else ErrorCategory.PROVIDER)
                            error = SafeError(category=category, http_status=200, provider_code=code)
                        else:
                            data = payload['data']
                            if not isinstance(data, dict):
                                raise ValueError('Invalid data')
                            table = ProviderTable(fields=data['fields'], items=data['items'],
                                                  retrieved_at=retrieved_at)
                            if set(table.fields) != set(contract.required_fields):
                                raise ValueError('Contract fields differ')
                            # Detect an echoed credential before any table can reach a writer/review.
                            if any(self._token.get_secret_value() in value for value in
                                   [*table.fields, *(v for row in table.items for v in row if isinstance(v, str))]):
                                raise ValueError('Sensitive response rejected')
                            return table
                    except (ValueError, KeyError, TypeError):
                        error = SafeError(category=ErrorCategory.INVALID_RESPONSE, http_status=200)
            if not retry or attempt == attempts - 1:
                raise ProviderFailure(error) from None
        raise AssertionError('Unreachable')
