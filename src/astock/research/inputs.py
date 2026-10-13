"""Explicit file manifests; preserve actual native identities, units and capture times."""
from __future__ import annotations

import hashlib
import io
import math
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd
import pyarrow.parquet as pq
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from astock.data.availability import AvailabilityBasis, RecordTimes, TimePrecision
from astock.research.core import day, digest, instant, market_day, read_json, require


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class EvidenceFile(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class SourceFile(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset: Literal["instruments", "calendar", "daily", "index_daily", "adj_factor", "status"]
    format: Literal["parquet", "csv", "json"]
    source: str = Field(min_length=1)
    retrieved_at: AwareDatetime
    available_at: AwareDatetime
    adapter: Literal["native-v1", "tushare-v1", "tushare-response-v1"] = "native-v1"
    request: dict | None = None
    calendar_exchange: Literal["SSE", "SZSE"] | None = None
    evidence_grade: Literal["USER_DECLARED", "LOCAL_CAPTURE_BOUND", "SYNTHETIC"] = "USER_DECLARED"
    evidence: list[EvidenceFile] = Field(default_factory=list)
    # Units are explicit even for Tushare: native volume shares/amount CNY;
    # Tushare daily/index_daily volume lots of 100 shares, amount thousand CNY.
    volume_unit: Literal["shares", "lots100"] | None = None
    amount_unit: Literal["CNY", "thousand_CNY"] | None = None

    @model_validator(mode="after")
    def source_time(self):
        require(self.available_at >= self.retrieved_at, "CAPTURE_TIME_BACKDATED")
        if self.dataset in {"daily", "index_daily"}:
            require(self.volume_unit is not None and self.amount_unit is not None, "UNITS_REQUIRED")
            if self.adapter in {"tushare-v1", "tushare-response-v1"}:
                require((self.volume_unit, self.amount_unit) == ("lots100", "thousand_CNY"), "TUSHARE_UNITS")
        require((self.format == "json") == (self.adapter == "tushare-response-v1"), "RESPONSE_FORMAT_ADAPTER")
        if self.evidence_grade == "LOCAL_CAPTURE_BOUND":
            require(self.adapter == "tushare-response-v1" and len(self.evidence) == 4,
                    "CAPTURE_EVIDENCE_REQUIRED")
        if self.adapter == "tushare-response-v1":
            from astock.research.tushare import DATASETS, validate_member
            require(self.request is not None, "RESPONSE_REQUEST_REQUIRED")
            validate_member(self.request)
            require(DATASETS[self.request["api"]] == self.dataset, "RESPONSE_DATASET")
        require(not any(s in self.source.lower() for s in ("token=", "password=", "api_key=")), "SECRET_SOURCE_URI")
        return self


class Bundle(StrictModel):
    protocol: Literal["RESEARCH_INPUT_V1"]
    purpose: Literal["CURRENT_OBSERVATION"]
    window_start: date
    window_end: date
    universe: list[str] = Field(min_length=1)
    benchmarks: list[str] = Field(default_factory=list)
    universe_scope: Literal["WATCHLIST", "PROVIDER_SAMPLE"]
    files: list[SourceFile] = Field(min_length=1)

    @model_validator(mode="after")
    def window(self):
        require(self.window_start <= self.window_end, "WINDOW_ORDER")
        codes = self.universe + self.benchmarks
        require(len(codes) == len(set(codes)) and all(c.strip() == c and c for c in codes), "IDENTITY_DUPLICATE")
        require(len({(f.path, f.dataset) for f in self.files}) == len(self.files), "FILE_DUPLICATE")
        return self


def number(value: object, *, nullable: bool = False) -> float | None:
    if value is None or isinstance(value, str) and not value:
        require(nullable, "NUMBER_REQUIRED")
        return None
    require(not isinstance(value, bool), "NUMBER_TYPE")
    value = float(value)
    require(math.isfinite(value), "NONFINITE_VALUE")
    return value


def records(spec: SourceFile, body: bytes, bundle: Bundle, *, evidence_bodies: dict[str, bytes] | None = None) -> list[dict]:
    from astock.research.evidence import capture_grade
    grade = capture_grade(spec, body, bundle, evidence_bodies)
    if spec.format == "json":
        from astock.research.tushare import response_rows
        rows = response_rows(spec, body)
    elif spec.format == "parquet":
        rows = pq.read_table(io.BytesIO(body)).to_pylist()
    else:
        rows = pd.read_csv(io.BytesIO(body), dtype=str, keep_default_na=False).to_dict("records")
    result = []
    allowed_codes = set(bundle.universe + bundle.benchmarks)
    for raw in rows:
        # No suffix-based exchange/company inference. Tushare native identifier
        # is preserved exactly; identities must be declared by instruments input.
        code = raw.get("ts_code") if spec.adapter in {"tushare-v1", "tushare-response-v1"} else raw.get("code")
        if spec.dataset in {'industry_classification', 'industry_membership'}:
            from astock.research.market_inputs import MarketBundle
            require(isinstance(bundle, MarketBundle), 'INDUSTRY_V2_REQUIRED')
            if spec.dataset == 'industry_classification':
                row = dict(industry_code=raw.get('index_code', raw.get('industry_code')),
                           name=raw.get('industry_name', raw.get('name')), version=raw.get('src', raw.get('version')),
                           level=raw.get('level'))
                require(row['version'] == 'SW2021' and row['level'] == 'L1' and row['industry_code'] and row['name'], 'INDUSTRY_VERSION')
            else:
                row = dict(code=code, industry_code=raw.get('l1_code', raw.get('industry_code')),
                           in_date=raw.get('in_date') or None, out_date=raw.get('out_date') or None,
                           is_new=raw.get('is_new'), version='SW2021')
                require(row['is_new'] == 'Y' and row['out_date'] is None and row['industry_code'] and code, 'INDUSTRY_MEMBERSHIP_SCOPE')
                if row['in_date']:
                    require(day(row['in_date']) <= market_day(instant(spec.retrieved_at)), 'FUTURE_MEMBERSHIP_DATE')
                    row['in_date'] = day(row['in_date']).isoformat()
            result.append(row)
            continue
        if spec.dataset == "instruments":
            if code not in allowed_codes:
                continue
            kind = raw.get("kind", "STOCK")
            require(kind in {"STOCK", "INDEX"}, "INSTRUMENT_KIND")
            exchange = raw.get("exchange") or "UNKNOWN"
            require(exchange in {"SSE", "SZSE", "BSE", "UNKNOWN"}, "EXCHANGE_UNKNOWN")
            identity = dict(code=code, name=raw.get("name") or None, exchange=exchange, kind=kind)
            if spec.adapter == "tushare-response-v1":
                identity.update(calendar_exchange=raw.get("calendar_exchange") or exchange,
                                identity_basis=raw["identity_basis"], provider_market=raw.get("market"),
                                publisher=raw.get("publisher"), list_date=raw.get("list_date"),
                                evidence_grade=grade)
            if bundle.protocol == 'RESEARCH_INPUT_V2':
                identity.update(provider_market=raw.get('market', raw.get('provider_market')),
                                list_status=raw.get('list_status'), list_date=raw.get('list_date'),
                                currency=raw.get('curr_type', raw.get('currency')))
                if exchange == 'BSE' and bundle.bse_calendar_reference == 'SSE_AGREES_SZSE_DOCUMENTED':
                    identity.update(calendar_exchange='SSE', calendar_basis='Tushare doc26: BSE references agreed SSE/SZSE')
                if kind == 'STOCK':
                    require(identity['list_status'] == 'L' and identity['list_date'] and identity['currency'] == 'CNY', 'CURRENT_POOL_IDENTITY')
            result.append(identity)
            continue
        if spec.dataset == "calendar":
            d = day(raw.get("cal_date") if spec.adapter in {"tushare-v1", "tushare-response-v1"} else raw.get("date"))
            exchange = raw.get("exchange")
            require(exchange in {"SSE", "SZSE", "BSE"}, "CALENDAR_EXCHANGE")
            opened = raw.get("is_open")
            require(type(opened) is int and opened in {0, 1} or type(opened) is str and opened in {"0", "1"}, "IS_OPEN_TYPE")
            row = dict(date=d.isoformat(), exchange=exchange, is_open=int(opened))
        else:
            if code not in allowed_codes:
                continue
            d = day(raw.get("trade_date") if spec.adapter in {"tushare-v1", "tushare-response-v1"} else raw.get("date"))
            row = dict(code=code, date=d.isoformat())
            if spec.dataset in {"daily", "index_daily"}:
                for f in ("open", "high", "low", "close"):
                    row[f] = number(raw.get(f))
                require(0 < row["low"] <= min(row["open"], row["close"]) <=
                        max(row["open"], row["close"]) <= row["high"], "OHLC_RELATION")
                row["pre_close"] = number(raw.get("pre_close"), nullable=True)
                volume = number(raw.get("vol") if spec.adapter in {"tushare-v1", "tushare-response-v1"} else raw.get("volume"))
                amount = number(raw.get("amount"))
                require(volume >= 0 and amount >= 0, "NEGATIVE_ACTIVITY")
                row.update(volume=volume * (100 if spec.volume_unit == "lots100" else 1),
                           amount=amount * (1000 if spec.amount_unit == "thousand_CNY" else 1))
            elif spec.dataset == "adj_factor":
                factor = number(raw.get("adj_factor"))
                require(factor > 0, "ADJUSTMENT_FACTOR")
                row["adj_factor"] = factor
            else:
                # Status adapter never interprets absence from an ST/suspension
                # response as evidence of normal trading.
                for f in ("st", "suspended"):
                    v = raw.get(f)
                    require(v in {"UNKNOWN", "YES", "NO"}, "STATUS_ENUM")
                    row[f] = v
                if spec.adapter == "tushare-response-v1":
                    if raw.get("event_key"):
                        row["event_key"] = raw["event_key"]
                    row["status_event"] = dict(api=spec.request["api"], suspend_type=raw.get("suspend_type"),
                                               suspend_timing=raw.get("suspend_timing"), warning_type=raw.get("type"))
                row["up_limit"] = number(raw.get("up_limit"), nullable=True)
                row["down_limit"] = number(raw.get("down_limit"), nullable=True)
                if row["up_limit"] is not None and row["down_limit"] is not None:
                    require(0 < row["down_limit"] <= row["up_limit"], "LIMIT_ORDER")
        if not bundle.window_start <= d <= bundle.window_end:
            continue
        require(d <= market_day(instant(spec.retrieved_at)), "FUTURE_EVENT_DATE")
        RecordTimes(event_date=d, retrieved_at=spec.retrieved_at, available_at=spec.available_at,
                    availability_basis=AvailabilityBasis.OBSERVED_CAPTURE, time_precision=TimePrecision.SECOND)
        result.append(row)
    if spec.adapter == "tushare-response-v1":
        for row in result:
            row.update(retrieved_at=spec.retrieved_at.isoformat(), available_at=spec.available_at.isoformat(),
                       evidence_grade=grade)
    return result


def load_bundle(path: Path, manifest: dict | None = None) -> tuple[Bundle, list[tuple[SourceFile, bytes, list[dict]]]]:
    from astock.research.market_inputs import parse_bundle
    bundle = parse_bundle(read_json(path) if manifest is None else manifest)
    inputs = []
    seen: dict[tuple, dict] = {}
    identities = {}
    calendars = set()
    open_sessions = set()
    for spec in bundle.files:
        source = Path(spec.path)
        source = source if source.is_absolute() else path.parent / source
        require(source.is_file() and not source.is_symlink(), "SOURCE_MISSING_OR_SYMLINK")
        proofs = {}
        for evidence in spec.evidence:
            proof = Path(evidence.path)
            proof = proof if proof.is_absolute() else path.parent / proof
            require(proof.is_file() and not proof.is_symlink(), "SOURCE_EVIDENCE_CHANGED")
            value = proof.read_bytes()
            require(hashlib.sha256(value).hexdigest() == evidence.sha256, "SOURCE_EVIDENCE_CHANGED")
            proofs[evidence.sha256] = value
        body = source.read_bytes()
        require(hashlib.sha256(body).hexdigest() == spec.sha256, "SOURCE_HASH_MISMATCH")
        parsed = records(spec, body, bundle, evidence_bodies=proofs)
        for row in parsed:
            key = (spec.dataset, row.get("code"), row.get("exchange") if spec.dataset == "calendar" else None, row.get("date"))
            if spec.dataset in {'industry_classification', 'industry_membership'}:
                key = (spec.dataset, row.get('code'), row['industry_code'], None)
            if spec.dataset == "status" and spec.adapter == "tushare-response-v1":
                key = (*key[:3], (key[3], spec.sha256, row.get("event_key")))
            require(key not in seen, "DUPLICATE_OR_CONFLICT")
            seen[key] = row
            if spec.dataset == "instruments":
                identities[row["code"]] = row
            if spec.dataset == "calendar":
                calendars.add((row["exchange"], row["date"]))
                if row["is_open"] == 1:
                    open_sessions.add((row["exchange"], row["date"]))
        inputs.append((spec, body, parsed))
    if bundle.protocol == 'RESEARCH_INPUT_V2':
        validate_market_inputs(bundle, inputs)
    require(set(identities) == set(bundle.universe + bundle.benchmarks), "IDENTITY_EVIDENCE_REQUIRED")
    for code in bundle.universe:
        require(identities[code]["kind"] == "STOCK", "UNIVERSE_KIND")
    for code in bundle.benchmarks:
        require(identities[code]["kind"] == "INDEX", "BENCHMARK_KIND")
    # Civil-day coverage proves holidays/weekends explicitly; weekdays are not
    # a trading calendar. Unknown exchange remains non-computable, not guessed.
    from datetime import timedelta
    for exchange in {i.get("calendar_exchange", i["exchange"]) for i in identities.values()} - {"UNKNOWN"}:
        for offset in range((bundle.window_end - bundle.window_start).days + 1):
            require((exchange, (bundle.window_start + timedelta(days=offset)).isoformat()) in calendars,
                    "INCOMPLETE_CALENDAR")
    for (dataset, code, _, _), row in seen.items():
        if dataset in {"daily", "index_daily", "adj_factor", "status"}:
            require(code in identities, "UNDECLARED_IDENTITY")
            if identities[code].get("list_date"):
                require(day(row["date"]) >= day(identities[code]["list_date"]), "OBSERVATION_BEFORE_LISTING")
            expected_kind = "INDEX" if dataset == "index_daily" else "STOCK"
            require(identities[code]["kind"] == expected_kind, "PRICE_KIND")
            exchange = identities[code].get("calendar_exchange", identities[code]["exchange"])
            if exchange != "UNKNOWN":
                require((exchange, row["date"]) in open_sessions, "NON_SESSION_OBSERVATION")
    from astock.research.tushare import merge_status
    merge_status([r for spec, _, rows in inputs if spec.dataset == "status" for r in rows])
    # Cross-market benchmarks use an explicitly declared research calendar ONLY
    # when retained SSE and SZSE calendars agree throughout the requested window.
    if any(i["kind"] == "INDEX" and i.get("calendar_exchange") for i in identities.values()):
        by_exchange = {e: {r["date"]: r["is_open"] for spec, _, rows in inputs
                          if spec.dataset == "calendar" for r in rows if r["exchange"] == e} for e in ("SSE", "SZSE")}
        require(by_exchange["SSE"] and by_exchange["SSE"] == by_exchange["SZSE"], "BENCHMARK_CALENDAR_DISAGREEMENT")
    return bundle, inputs


def validate_market_inputs(bundle, inputs) -> None:
    """Pool closure comes from three retained partition responses, not a manifest label."""
    # Industry overlap/unsupported class is invalid input, not an optional ranking gap.
    classes = {r['industry_code'] for s,_,rows in inputs if s.dataset=='industry_classification' for r in rows}
    membership = [r for s,_,rows in inputs if s.dataset=='industry_membership' for r in rows]
    require(all(r['industry_code'] in classes for r in membership), 'INDUSTRY_CLASSIFICATION_MISSING')
    require(len({r['code'] for r in membership}) == len(membership), 'INDUSTRY_OVERLAP')
    if bundle.universe_scope != 'CURRENT_A_SHARE_L':
        return
    identity_sources = [(s, rows) for s, _, rows in inputs if s.dataset == 'instruments' and s.request and s.request['api'] == 'stock_basic']
    require(len(identity_sources) == 3 and {s.request['params']['exchange'] for s, _ in identity_sources} == {'SSE', 'SZSE', 'BSE'}, 'CURRENT_POOL_PARTITIONS')
    require(all(s.evidence_grade in {'LOCAL_CAPTURE_BOUND', 'SYNTHETIC'} and s.request.get('contract_version') == 'RESEARCH_PROVIDER_V2' for s, _ in identity_sources), 'CURRENT_POOL_CAPTURE_REQUIRED')
    from astock.research.tushare import decode_response
    original_codes = {r['ts_code'] for s, body, _ in inputs if s in [t[0] for t in identity_sources] for r in decode_response(body, s.request)}
    require(set(bundle.universe) == original_codes, 'CURRENT_POOL_UNIVERSE_CHANGED')
    if bundle.bse_calendar_reference == 'SSE_AGREES_SZSE_DOCUMENTED':
        calendars = {e: {r['date']: r['is_open'] for s, _, rows in inputs if s.dataset == 'calendar' for r in rows if r['exchange'] == e} for e in ('SSE', 'SZSE')}
        require(calendars['SSE'] and calendars['SSE'] == calendars['SZSE'], 'BSE_CALENDAR_REFERENCE_DISAGREEMENT')
