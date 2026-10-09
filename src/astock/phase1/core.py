"""Immutable encodings, exact paths, parameter identities and safe diagnostics."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from astock.data.raw_writer import atomic_new_file

ENDPOINT = "https://api.tushare.pro"
PRODUCTION = "data/private/phase1-integrated-v1"


class Phase1Error(ValueError):
    """Only fixed categories, never secret-bearing exception inputs, are exposed."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Phase1Error(reason)


def instant(value: str | datetime) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        require(isinstance(result, datetime) and result.utcoffset() is not None, "AWARE_TIME_REQUIRED")
        return result.astimezone(timezone.utc)
    except (TypeError, AttributeError, ValueError):
        raise Phase1Error("AWARE_TIME_REQUIRED") from None


def stamp(value: datetime | None = None) -> str:
    return instant(value or datetime.now(timezone.utc)).isoformat()


def day(value: str) -> date:
    try:
        require(isinstance(value, str) and bool(re.fullmatch(r"\d{8}|\d{4}-\d{2}-\d{2}", value)), "DATE_REQUIRED")
        return datetime.strptime(value, "%Y%m%d" if len(value) == 8 else "%Y-%m-%d").date()
    except ValueError:
        raise Phase1Error("DATE_REQUIRED") from None


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return stamp(value)
    if isinstance(value, date):
        return value.isoformat()
    raise Phase1Error("NON_JSON_VALUE")


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False, default=_json_default).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strict_json(body: bytes) -> Any:
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, "DUPLICATE_JSON_KEY")
            result[k] = v
        return result
    try:
        return json.loads(body, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Phase1Error("NONFINITE_JSON")))
    except (UnicodeError, json.JSONDecodeError):
        raise Phase1Error("INVALID_JSON") from None


def safe_path(root: Path, path: Path, *, exists: bool = False) -> Path:
    root = root.absolute()
    path = path.absolute()
    require(".." not in path.parts, "PATH_TRAVERSAL")
    require(path.is_relative_to(root), "OUTSIDE_STORE")
    for p in [*reversed(path.parents), path]:
        require(not p.is_symlink(), "SYMLINK_REJECTED")
        if p.is_file():
            require(p.stat().st_nlink == 1, "HARDLINK_REJECTED")
    if exists:
        require(path.is_file(), "MISSING_OBJECT")
    return path


def publish(path: Path, body: bytes) -> None:
    if path.exists():
        require(path.read_bytes() == body, "IMMUTABLE_OBJECT_CHANGED")
        return
    atomic_new_file(path, lambda p: p.write_bytes(body))


def logical_id(request: dict) -> str:
    # Same encoding as the old engine; fields/contracts/root/run never refund calls.
    params = {k: day(v).strftime('%Y%m%d') if isinstance(v, str) and
              (k.endswith('_date') or k == 'period') else v for k, v in request['params'].items()}
    return digest(dict(endpoint=ENDPOINT, dataset=request["dataset"], params=params))


def overlapping(left: dict, right: dict) -> bool:
    if left["dataset"] != right["dataset"]:
        return False
    a, b = left["params"], right["params"]
    axes = ("exchange", "ts_code", "list_status", "report_type", "comp_type", "period", "src", "level", "l3_code")
    if any(k in a and k in b and a[k] != b[k] for k in axes):
        return False
    if left['dataset'] == 'fina_indicator' and ('ann_date' in a) != ('ann_date' in b):
        return True  # Publication and report-period axes cannot prove disjointness.
    def interval(p):
        single = p.get("trade_date") or p.get("ann_date")
        start, end = single or p.get("start_date"), single or p.get("end_date")
        return (day(start), day(end)) if start and end else None
    ai, bi = interval(a), interval(b)
    return max(ai[0], bi[0]) <= min(ai[1], bi[1]) if ai and bi else True


def category(error: BaseException) -> str:
    if isinstance(error, Phase1Error) and re.fullmatch(r"[A-Z0-9_]+", str(error)):
        return str(error)
    return "UNEXPECTED_" + type(error).__name__.upper()


def scalar(value: Any, kind: str, nullable: bool) -> Any:
    if value is None:
        require(nullable, "NONNULL_FIELD_REQUIRED")
        return value
    if kind == "date":
        day(value)
    elif kind == "number":
        require(type(value) in (int, float) and math.isfinite(value), "NUMERIC_TYPE_REQUIRED")
    elif kind == "int":
        require(type(value) is int, "INTEGER_TYPE_REQUIRED")
    else:
        require(type(value) is str and bool(value.strip()), "STRING_TYPE_REQUIRED")
    return value


def append_log(path: Path, payload: dict) -> None:
    # No duplicate **kwargs; original stage/time remain intact.
    value = {"recorded_at": stamp(), **payload}
    with path.open("ab") as f:
        f.write(encoded(value) + b"\n")
        f.flush()
        os.fsync(f.fileno())
