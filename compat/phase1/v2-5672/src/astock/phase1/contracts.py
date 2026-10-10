"""Complete source-preserving provider profiles and dataset-specific validation."""
from __future__ import annotations

import io
from functools import lru_cache
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from astock.phase1.core import day, digest, encoded, require, scalar, strict_json

CATALOG = "config/phase1/contracts-v1.yaml"
FINANCIAL = {"income", "balancesheet", "cashflow", "fina_indicator"}
MARKET = {"daily", "daily_basic", "adj_factor", "stk_limit", "suspend_d", "stock_st"}


@lru_cache(maxsize=8)
def _catalog_bytes(body):
    return yaml.safe_load(body)


def catalog(root: Path) -> dict:
    result = deepcopy(_catalog_bytes((root / CATALOG).read_bytes()))
    require(result["protocol"] == "PHASE1_INTEGRATED_V1", "CATALOG_PROTOCOL")
    for name, c in result["datasets"].items():
        require(c["key"] and set(c["key"]) <= set(c["fields"]), "CATALOG_KEY")
        require(c["cap"] is None or type(c["cap"]) is int and c["cap"] > 0, "CATALOG_CAP")
    return result["datasets"]


def request(root: Path, dataset: str, params: dict, *, fields: list | None = None,
            empty_evidence: dict | None = None, metadata: dict | None = None) -> dict:
    c = catalog(root).get(dataset)
    require(c is not None and isinstance(params, dict) and set(params) <= set(c["params"]), "REQUEST_SCOPE")
    require(all(isinstance(v, str) and v for v in params.values()), "PARAMETER_TYPE")
    for k, v in params.items():
        if k.endswith("_date") or k == "period":
            day(v)
    if "start_date" in params and "end_date" in params:
        require(day(params["start_date"]) <= day(params["end_date"]), "REQUEST_WINDOW")
    if dataset == "trade_cal":
        require(set(params) == {"exchange", "start_date", "end_date"} and params["exchange"] in ("SSE", "SZSE", "BSE"), "CALENDAR_REQUEST")
    if dataset in FINANCIAL:
        require("ts_code" in params, "NON_VIP_SECURITY_REQUIRED")
    selected = fields or list(c["fields"])
    require(len(set(selected)) == len(selected) and set(selected) == set(c["fields"]), "REQUEST_FIELDS")
    return dict(dataset=dataset, params=params, fields=selected, contract_hash=digest(c),
                empty_evidence=empty_evidence, metadata=metadata or {})


def envelope(body: bytes) -> tuple[dict, str]:
    value = strict_json(body)
    require(isinstance(value, dict), "PROVIDER_ENVELOPE")
    legacy = {"request_id", "code", "msg", "data"}
    require(set(value) in (legacy, legacy | {"detail"}), "UNKNOWN_ENVELOPE_FIELD")
    require(type(value["code"]) is int and value["code"] == 0, "PROVIDER_BUSINESS_ERROR")
    require(isinstance(value["request_id"], str) and bool(value["request_id"]), "REQUEST_ID_REQUIRED")
    require(value["msg"] is None or isinstance(value["msg"], str), "PROVIDER_MESSAGE_TYPE")
    require("detail" not in value or value["detail"] is None or isinstance(value["detail"], str), "DETAIL_TYPE")
    data = value["data"]
    require(isinstance(data, dict), "PROVIDER_DATA_TYPE")
    base = {"fields", "items"}
    require(set(data) in (base, base | {"count", "has_more"}), "UNKNOWN_DATA_FIELD")
    if "count" in data:
        require(type(data["count"]) is int and data["count"] >= 0, "COUNT_TYPE")
        require(type(data["has_more"]) is bool, "HAS_MORE_TYPE")
        require(not data["has_more"], "TRUNCATION_MORE_ROWS")
    profile = "DIAGNOSTIC_V1" if set(value) != legacy or set(data) != base else "LEGACY"
    return value, profile


def decode(root: Path, member: dict, body: bytes) -> dict:
    c = catalog(root)[member["dataset"]]
    require(member["contract_hash"] == digest(c), "CONTRACT_PIN_CHANGED")
    value, profile = envelope(body)
    data, selected = value["data"], member["fields"]
    require(data["fields"] == selected and isinstance(data["items"], list), "PROVIDER_FIELDS_OR_ROWS")
    require(c["cap"] is None or len(data["items"]) < c["cap"], "CAP_OR_TRUNCATION")
    if not data["items"]:
        evidence = member["empty_evidence"]
        require(isinstance(evidence, dict) and set(evidence) == {"scope_hash", "evidence_hash", "basis"}
                and evidence["scope_hash"] == digest(member["params"])
                and len(evidence["evidence_hash"]) == 64 and bool(evidence["basis"]), "UNEXPLAINED_EMPTY")
    rows, seen = [], set()
    for items in data["items"]:
        require(isinstance(items, list) and len(items) == len(selected), "ROW_WIDTH")
        row = dict(zip(selected, items, strict=True))
        for f, v in row.items():
            scalar(v, c["fields"][f]["type"], c["fields"][f]["nullable"])
        key = tuple(row[f] for f in c["key"])
        require(not any(row[f] is None and f not in c["nullable_key"] for f in c["key"]), "NULL_NATURAL_KEY")
        require(key not in seen, "DUPLICATE_NATURAL_KEY")
        seen.add(key)
        scope(root, member, row, c)
        rows.append(row)
    if member["dataset"] == "trade_cal":
        calendar(member, rows)
    if member["dataset"] in ("daily", "index_daily"):
        for r in rows:
            if all(r.get(f) is not None for f in ("open", "high", "low", "close")):
                require(0 <= r["low"] <= min(r["open"], r["close"]) <= max(r["open"], r["close"]) <= r["high"], "OHLC_RELATION")
    if member["dataset"] == "adj_factor":
        require(all(r["adj_factor"] is None or r["adj_factor"] > 0 for r in rows), "ADJUSTMENT_FACTOR")
    if member["dataset"] == "stk_limit":
        require(all(r["down_limit"] is None or r["up_limit"] is None or 0 <= r["down_limit"] <= r["up_limit"] for r in rows), "PRICE_LIMIT_ORDER")
    arrays = {f: [day(r[f]) if r[f] is not None and c["fields"][f]["type"] == "date" else r[f] for r in rows] for f in selected}
    types = {"str": pa.string(), "date": pa.date32(), "number": pa.float64(), "int": pa.int64()}
    table = pa.table(arrays, schema=pa.schema([(f, types[c["fields"][f]["type"]]) for f in selected]))
    buf = io.BytesIO()
    pq.write_table(table, buf)
    completeness = "CIVIL_WINDOW_VALID" if member["dataset"] == "trade_cal" else "CAP_BELOW_LIMIT_NOT_UNIVERSE_PROOF" if c["cap"] else "RAW_UNCERTIFIED_UNKNOWN_CAP"
    return dict(rows=rows, typed=buf.getvalue(), schema_hash=digest([(f, str(table.schema.field(f).type)) for f in selected]),
                envelope_profile=profile, diagnostics={k: data[k] for k in ("count", "has_more") if k in data},
                diagnostic_semantics="UNVERIFIED_NOT_COMPLETENESS_EVIDENCE", completeness=completeness,
                leading_previous_certified=False, research_admitted=False)


def scope(root: Path, member: dict, row: dict, c: dict) -> None:
    p = member["params"]
    for k in ("ts_code", "exchange", "list_status", "report_type", "comp_type", "src", "level", "l1_code", "l2_code", "l3_code"):
        if k in p and k in row:
            require(row[k] == p[k], "ROW_OUTSIDE_SCOPE")
    for param, column in (("trade_date", "trade_date"), ("ann_date", "ann_date"), ("f_ann_date", "f_ann_date"), ("period", "end_date")):
        if param in p:
            require(row.get(column) is not None and day(row[column]) == day(p[param]), "ROW_OUTSIDE_DATE")
    axis = c["date_axis"]
    if axis and ("start_date" in p or "end_date" in p):
        require(row.get(axis) is not None, "WINDOW_DATE_UNKNOWN")
        require(("start_date" not in p or day(p["start_date"]) <= day(row[axis])) and
                ("end_date" not in p or day(row[axis]) <= day(p["end_date"])), "ROW_OUTSIDE_WINDOW")


def calendar(member: dict, rows: list[dict]) -> None:
    p = member["params"]
    first, last = day(p["start_date"]), day(p["end_date"])
    expected = {first + timedelta(days=i) for i in range((last - first).days + 1)}
    require({day(r["cal_date"]) for r in rows} == expected, "INCOMPLETE_CIVIL_CALENDAR")
    previous = None
    for r in sorted(rows, key=lambda r: r["cal_date"]):
        require(type(r["is_open"]) is int and r["is_open"] in (0, 1), "IS_OPEN_TYPE")
        require(r["pretrade_date"] is not None and day(r["pretrade_date"]) < day(r["cal_date"]), "PRETRADE_REQUIRED")
        require(previous is None or r["pretrade_date"] == previous, "PRETRADE_RELATION")
        previous = r["cal_date"] if r["is_open"] else r["pretrade_date"]
