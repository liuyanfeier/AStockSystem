"""Small shared primitives; sources, parameters and computations remain inspectable."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from astock.data.raw_validation import strict_json


class ResearchError(ValueError):
    """Stable safe diagnostic without private row contents."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ResearchError(code)


def encoded(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def digest(value: object) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def day(value: object) -> date:
    if isinstance(value, datetime):
        raise ResearchError("DATE_TYPE")
    if isinstance(value, date):
        return value
    text = str(value)
    return date.fromisoformat(text if "-" in text else f"{text[:4]}-{text[4:6]}-{text[6:]}")


def instant(value: str | datetime) -> datetime:
    result = datetime.fromisoformat(value) if isinstance(value, str) else value
    require(result.tzinfo is not None and result.utcoffset() is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(timezone.utc)


def market_day(value: datetime) -> date:
    return value.astimezone(ZoneInfo("Asia/Shanghai")).date()


def code_fingerprint() -> str:
    package = Path(__file__).resolve().parents[1]
    files = [*package.joinpath("research").glob("*.py"), package / "features/market.py",
             package / "regime/market.py", package / "screening/candidates.py",
             package / "reports/research.py", package / "features/lineage.py",
             package / "portfolio/models.py"]
    return digest({str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(files)})


def private_path(root: Path, path: Path, *, output: bool = False) -> Path:
    """CLI boundaries: no symlink escape, old store, public data or personal output."""
    absolute = path.absolute()
    current = absolute
    while current != current.parent:
        require(not current.is_symlink(), "SYMLINK_PATH")
        current = current.parent
    resolved = absolute.resolve()
    private = (root / "data/private/research-v1").resolve()
    reports = (root / "reports/private/research-v1").resolve()
    require(resolved.is_relative_to(private) or output and resolved.is_relative_to(reports),
            "RESEARCH_PRIVATE_PATH_REQUIRED")
    return resolved


def read_json(path: Path) -> object:
    return strict_json(path.read_bytes())
