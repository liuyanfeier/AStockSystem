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
    format: Literal["parquet", "csv"]
    source: str = Field(min_length=1)
    retrieved_at: AwareDatetime
    available_at: AwareDatetime
    adapter: Literal["native-v1", "tushare-v1"] = "native-v1"
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
            if self.adapter == "tushare-v1":
                require((self.volume_unit, self.amount_unit) == ("lots100", "thousand_CNY"), "TUSHARE_UNITS")
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


def records(spec: SourceFile, body: bytes, bundle: Bundle) -> list[dict]:
    if spec.format == "parquet":
        rows = pq.read_table(io.BytesIO(body)).to_pylist()
    else:
        rows = pd.read_csv(io.BytesIO(body), dtype=str, keep_default_na=False).to_dict("records")
    result = []
    for raw in rows:
        # No suffix-based exchange/company inference. Tushare native identifier
        # is preserved exactly; identities must be declared by instruments input.
        code = raw.get("ts_code") if spec.adapter == "tushare-v1" else raw.get("code")
        if spec.dataset == "instruments":
            if code not in bundle.universe + bundle.benchmarks:
                continue
            kind = raw.get("kind", "STOCK")
            require(kind in {"STOCK", "INDEX"}, "INSTRUMENT_KIND")
            exchange = raw.get("exchange") or "UNKNOWN"
            require(exchange in {"SSE", "SZSE", "BSE", "UNKNOWN"}, "EXCHANGE_UNKNOWN")
            result.append(dict(code=code, name=raw.get("name") or None, exchange=exchange, kind=kind))
            continue
        if spec.dataset == "calendar":
            d = day(raw.get("cal_date") if spec.adapter == "tushare-v1" else raw.get("date"))
            exchange = raw.get("exchange")
            require(exchange in {"SSE", "SZSE", "BSE"}, "CALENDAR_EXCHANGE")
            opened = raw.get("is_open")
            require(type(opened) is int and opened in {0, 1} or type(opened) is str and opened in {"0", "1"}, "IS_OPEN_TYPE")
            row = dict(date=d.isoformat(), exchange=exchange, is_open=int(opened))
        else:
            if code not in bundle.universe + bundle.benchmarks:
                continue
            d = day(raw.get("trade_date") if spec.adapter == "tushare-v1" else raw.get("date"))
            row = dict(code=code, date=d.isoformat())
            if spec.dataset in {"daily", "index_daily"}:
                for f in ("open", "high", "low", "close"):
                    row[f] = number(raw.get(f))
                require(0 < row["low"] <= min(row["open"], row["close"]) <=
                        max(row["open"], row["close"]) <= row["high"], "OHLC_RELATION")
                row["pre_close"] = number(raw.get("pre_close"), nullable=True)
                volume = number(raw.get("vol") if spec.adapter == "tushare-v1" else raw.get("volume"))
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
    return result


def load_bundle(path: Path) -> tuple[Bundle, list[tuple[SourceFile, bytes, list[dict]]]]:
    bundle = Bundle.model_validate(read_json(path))
    inputs = []
    seen: dict[tuple, dict] = {}
    identities = {}
    calendars = set()
    open_sessions = set()
    for spec in bundle.files:
        source = Path(spec.path)
        source = source if source.is_absolute() else path.parent / source
        require(source.is_file() and not source.is_symlink(), "SOURCE_MISSING_OR_SYMLINK")
        for evidence in spec.evidence:
            proof = Path(evidence.path)
            proof = proof if proof.is_absolute() else path.parent / proof
            require(proof.is_file() and not proof.is_symlink() and
                    hashlib.sha256(proof.read_bytes()).hexdigest() == evidence.sha256, "SOURCE_EVIDENCE_CHANGED")
        body = source.read_bytes()
        require(hashlib.sha256(body).hexdigest() == spec.sha256, "SOURCE_HASH_MISMATCH")
        parsed = records(spec, body, bundle)
        for row in parsed:
            key = (spec.dataset, row.get("code"), row.get("exchange") if spec.dataset == "calendar" else None, row.get("date"))
            require(key not in seen, "DUPLICATE_OR_CONFLICT")
            seen[key] = row
            if spec.dataset == "instruments":
                identities[row["code"]] = row
            if spec.dataset == "calendar":
                calendars.add((row["exchange"], row["date"]))
                if row["is_open"] == 1:
                    open_sessions.add((row["exchange"], row["date"]))
        inputs.append((spec, body, parsed))
    require(set(identities) == set(bundle.universe + bundle.benchmarks), "IDENTITY_EVIDENCE_REQUIRED")
    for code in bundle.universe:
        require(identities[code]["kind"] == "STOCK", "UNIVERSE_KIND")
    for code in bundle.benchmarks:
        require(identities[code]["kind"] == "INDEX", "BENCHMARK_KIND")
    # Civil-day coverage proves holidays/weekends explicitly; weekdays are not
    # a trading calendar. Unknown exchange remains non-computable, not guessed.
    from datetime import timedelta
    for exchange in {i["exchange"] for i in identities.values()} - {"UNKNOWN"}:
        for offset in range((bundle.window_end - bundle.window_start).days + 1):
            require((exchange, (bundle.window_start + timedelta(days=offset)).isoformat()) in calendars,
                    "INCOMPLETE_CALENDAR")
    for (dataset, code, _, _), row in seen.items():
        if dataset in {"daily", "index_daily", "adj_factor", "status"}:
            require(code in identities, "UNDECLARED_IDENTITY")
            expected_kind = "INDEX" if dataset == "index_daily" else "STOCK"
            require(identities[code]["kind"] == expected_kind, "PRICE_KIND")
            exchange = identities[code]["exchange"]
            if exchange != "UNKNOWN":
                require((exchange, row["date"]) in open_sessions, "NON_SESSION_OBSERVATION")
    return bundle, inputs
