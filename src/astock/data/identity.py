"""Offline, source-scoped identity history; no code conversion or seeded mappings."""

import re
from collections import defaultdict
from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator, model_validator
from astock.data.warehouse_lock import require_writer


def is_native_identifier(value: object) -> bool:
    """Source identifiers need nonblank text, not a normalized A-share pattern."""
    return isinstance(value, str) and bool(value.strip())


def is_normalized_ashare_identifier(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9]{6}\.(SH|SZ|BJ)", value) is not None


class IdentifierHistory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    security_id: str
    source: str
    identifier_type: str
    identifier: str
    exchange: str
    valid_from: date
    valid_to: date | None = None
    published_at: AwareDatetime | None = None
    available_at: AwareDatetime
    retrieved_at: AwareDatetime
    evidence_source: str

    @field_validator("security_id", "source", "identifier_type", "identifier", "exchange", "evidence_source")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not is_native_identifier(value):
            raise ValueError("Identity fields require nonblank text")
        return value

    @model_validator(mode="after")
    def check_times(self):
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("Effective intervals must be nonempty [from, to)")
        if self.published_at is not None and self.available_at < self.published_at:
            raise ValueError("Availability cannot precede publication")
        # This minimum model supports observed knowledge only, not reconstructed PIT.
        if self.available_at < self.retrieved_at:
            raise ValueError("Observed availability cannot precede retrieval")
        return self

    @property
    def scope(self) -> tuple[str, str, str, str]:
        return self.source, self.identifier_type, self.identifier, self.exchange

    @property
    def lineage(self) -> tuple[str, str, str, str, date]:
        return (*self.scope, self.valid_from)


def _aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Knowledge time must be timezone-aware")


def _known_versions(rows: tuple[IdentifierHistory, ...], as_of: datetime) -> list[IdentifierHistory]:
    latest = {}
    for row in rows:
        if row.available_at <= as_of:
            previous = latest.get(row.lineage)
            if previous is None or row.available_at > previous.available_at:
                latest[row.lineage] = row
    return list(latest.values())


class IdentityHistory:
    """Reject conflicts at every knowledge boundary, then resolve exact identifiers.

    Corrections append versions at the same effective-start lineage. Select knowledge
    versions BEFORE filtering effective dates; otherwise stale open intervals leak.
    """

    def __init__(self, rows: list[IdentifierHistory]):
        self.rows = tuple(rows)
        seen = set()
        for row in self.rows:
            key = (*row.lineage, row.available_at)
            if key in seen:
                raise ValueError("Duplicate identity knowledge version")
            seen.add(key)
        for boundary in sorted({row.available_at for row in self.rows}):
            scopes = defaultdict(list)
            for row in _known_versions(self.rows, boundary):
                scopes[row.scope].append(row)
            for versions in scopes.values():
                versions.sort(key=lambda row: row.valid_from)
                for left, right in zip(versions, versions[1:]):
                    if left.valid_to is None or left.valid_to > right.valid_from:
                        raise ValueError("Overlapping identity mapping; quarantine rather than choose")

    def resolve(self, *, source: str, identifier_type: str, identifier: str,
                exchange: str, event_date: date, as_of: datetime) -> str | None:
        _aware(as_of)
        scope = source, identifier_type, identifier, exchange
        matches = [row.security_id for row in _known_versions(self.rows, as_of)
                   if row.scope == scope and row.valid_from <= event_date
                   and (row.valid_to is None or event_date < row.valid_to)]
        if len(matches) > 1:
            raise ValueError("Ambiguous identity mapping")
        return matches[0] if matches else None

    @staticmethod
    def append(db, row: IdentifierHistory) -> None:
        """Transactionally validate stored knowledge and insert without rewriting.

        DuckDB CHECKs cannot enforce cross-row temporal overlap. Use this boundary
        for writes; direct SQL is only a schema constraint, not an identity audit.
        """
        require_writer(db)
        db.execute("BEGIN TRANSACTION")
        try:
            result = db.execute("SELECT * FROM security_identifier_history")
            names = [column[0] for column in result.description]
            stored = [IdentifierHistory(**dict(zip(names, values, strict=True)))
                      for values in result.fetchall()]
            IdentityHistory([*stored, row])
            names = list(IdentifierHistory.model_fields)
            db.execute(f"INSERT INTO security_identifier_history ({','.join(names)}) "
                       f"VALUES ({','.join('?' for _ in names)})", [getattr(row, name) for name in names])
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
