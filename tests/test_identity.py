"""Synthetic identity histories only; never consume local/provider stock lists."""

from datetime import date, datetime, timezone

import duckdb
import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.identity import IdentifierHistory, IdentityHistory, is_native_identifier, is_normalized_ashare_identifier
from astock.data.probe_audit import table_audit
from astock.data.raw_writer import RawWriter, migrate
from astock.data.tushare_client import ProviderTable
from astock.paths import get_project_root


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
LATER = datetime(2026, 2, 1, tzinfo=timezone.utc)


def entry(**overrides):
    values = dict(security_id="synthetic-security", source="synthetic-provider",
                  identifier_type="provider_code", identifier="831305.BJ", exchange="BSE",
                  valid_from=date(2021, 11, 15), valid_to=None, published_at=None,
                  available_at=NOW, retrieved_at=NOW, evidence_source="synthetic://verified-document")
    return IdentifierHistory(**(values | overrides))


def resolve(history, identifier="831305.BJ", event=date(2025, 8, 13), as_of=NOW, **scope):
    return history.resolve(source=scope.get("source", "synthetic-provider"),
                           identifier_type=scope.get("identifier_type", "provider_code"),
                           identifier=identifier, exchange=scope.get("exchange", "BSE"),
                           event_date=event, as_of=as_of)


@pytest.mark.parametrize("switch", [date(2025, 5, 6), date(2025, 10, 9)])
def test_bse_transition_uses_explicit_pair_and_exact_effective_boundary(switch):
    # Deliberately different last digits: no suffix-derived mapping is possible.
    history = IdentityHistory([entry(valid_to=switch),
                               entry(identifier="920405.BJ", valid_from=switch)])
    from datetime import timedelta
    before = switch - timedelta(days=1)
    assert resolve(history, event=before) == "synthetic-security"
    assert resolve(history, event=switch) is None
    assert resolve(history, "920405.BJ", before) is None
    assert resolve(history, "920405.BJ", switch) == "synthetic-security"
    assert resolve(history, "920305.BJ", switch) is None


def test_intervals_code_reuse_and_source_scopes_do_not_merge_securities():
    history = IdentityHistory([
        entry(security_id="synthetic-predecessor", valid_to=date(2006, 10, 20), valid_from=date(2000, 7, 19)),
        entry(security_id="synthetic-successor", valid_from=date(2006, 10, 26)),
        entry(source="another-provider", security_id="synthetic-other")])
    assert resolve(history, event=date(2000, 7, 18)) is None
    assert resolve(history, event=date(2000, 7, 19)) == "synthetic-predecessor"
    assert resolve(history, event=date(2006, 10, 20)) is None
    assert resolve(history, event=date(2006, 10, 26)) == "synthetic-successor"
    assert resolve(history, exchange="SSE") is None
    assert resolve(history, identifier_type="exchange_symbol") is None
    assert resolve(history, source="another-provider") == "synthetic-other"


def test_as_of_selects_knowledge_version_before_effective_filter():
    history = IdentityHistory([entry(), entry(valid_to=date(2025, 10, 9),
                                              available_at=LATER, retrieved_at=LATER)])
    assert resolve(history, event=date(2025, 10, 9), as_of=NOW) == "synthetic-security"
    assert resolve(history, event=date(2025, 10, 9), as_of=LATER) is None
    assert resolve(history, as_of=datetime(2025, 12, 31, tzinfo=timezone.utc)) is None
    assert resolve(history, as_of=LATER) == "synthetic-security"
    with pytest.raises(ValueError, match="timezone-aware"):
        resolve(history, as_of=NOW.replace(tzinfo=None))


def test_conflicting_overlaps_and_same_time_versions_are_rejected():
    with pytest.raises(ValueError, match="Overlapping"):
        IdentityHistory([entry(), entry(security_id="other", valid_from=date(2025, 1, 1))])
    with pytest.raises(ValueError, match="Duplicate"):
        IdentityHistory([entry(), entry(security_id="other")])
    # A later correction cannot erase the ambiguity that existed at an earlier as-of.
    with pytest.raises(ValueError, match="Overlapping"):
        IdentityHistory([entry(), entry(security_id="other", valid_from=date(2025, 1, 1)),
                         entry(valid_to=date(2025, 1, 1), available_at=LATER, retrieved_at=LATER)])


@pytest.mark.parametrize("overrides", [
    {"identifier": " "}, {"evidence_source": ""}, {"security_id": ""},
    {"valid_to": date(2021, 11, 15)}, {"valid_to": date(2021, 11, 14)},
    {"available_at": datetime(2025, 1, 1, tzinfo=timezone.utc)},
    {"published_at": LATER}, {"retrieved_at": NOW.replace(tzinfo=None)},
])
def test_unknown_evidence_and_invalid_times_do_not_create_eligible_mappings(overrides):
    with pytest.raises(ValidationError):
        entry(**overrides)


def test_native_identifier_retention_and_separate_normalization(tmp_path):
    native = "T123456.SH"  # Synthetic non-normalized provider identifier.
    assert is_native_identifier(native) and not is_normalized_ashare_identifier(native)
    assert is_normalized_ashare_identifier("123456.SH")
    assert not is_native_identifier(None) and not is_native_identifier(123456)
    history = IdentityHistory([entry(identifier=native, exchange="SSE")])
    assert resolve(history, native, exchange="SSE") == "synthetic-security"
    assert resolve(history, "123456.SH", exchange="SSE") is None
    contract = next(c for c in load_contracts(get_project_root(), catalog_version="v1") if c.dataset == "adj_factor")
    table = ProviderTable(fields=["ts_code", "trade_date", "adj_factor"],
                          items=[[native, "20250102", 1.0]], retrieved_at=NOW)
    audit = table_audit(table, contract)
    assert audit["invalid_source_identifier_count"] == 0
    assert audit["non_normalized_identifier_count"] == 1
    assert audit["dq_status"] == "PASS" and audit["identity_status"] == "REVIEW_REQUIRED"
    # Storage keeps exact native identifier while the normalized identity gate stays open.
    from uuid import uuid4
    with duckdb.connect(":memory:") as db:
        migrate(db, get_project_root())
        run = uuid4()
        db.execute('''INSERT INTO ingestion_run (run_id,source,dataset,mode,started_at,status,
            code_commit,config_hash,provider_client_version) VALUES (?,'tushare','adj_factor',
            'PROBE',?,'RUNNING',?,?,'0.1.0')''', [str(run), NOW, "a" * 40, "b" * 64])
        manifest = RawWriter(tmp_path, db).write(run, "adj_factor", 0, table, RequestParams())
        assert pq.ParquetFile(tmp_path / manifest.relative_path).read()["ts_code"].to_pylist() == [native]
    table.items[0][0] = ""
    assert table_audit(table, contract)["invalid_source_identifier_count"] == 1
    assert table_audit(table, contract)["dq_status"] == "ERROR"


def test_migration_and_transactional_append_reject_ambiguity_and_preserve_history():
    with duckdb.connect(":memory:") as db:
        migrate(db, get_project_root())
        assert db.execute("SELECT count(*) FROM security_identifier_history").fetchone() == (0,)
        history = IdentityHistory([])
        history.append(db, entry())
        with pytest.raises(ValueError, match="Overlapping"):
            history.append(db, entry(security_id="other", valid_from=date(2025, 1, 1)))
        assert db.execute("SELECT count(*) FROM security_identifier_history").fetchone() == (1,)
        history.append(db, entry(valid_to=date(2025, 10, 9), available_at=LATER, retrieved_at=LATER))
        migrate(db, get_project_root())
        assert db.execute("SELECT count(*) FROM security_identifier_history").fetchone() == (2,)
        assert db.execute("SELECT version FROM schema_version ORDER BY version").fetchall() == [(1,), (2,), (3,), (4,), (5,)]
        assert db.execute("SELECT valid_to FROM security_identifier_history ORDER BY available_at").fetchall() == [(None,), (date(2025, 10, 9),)]
        for clause in ["identifier=''", "valid_to=valid_from", "available_at=retrieved_at-INTERVAL '1 second'", "published_at=available_at+INTERVAL '1 second'"]:
            # Direct SQL enforces local constraints; temporal overlaps need the append boundary.
            with pytest.raises(duckdb.ConstraintException):
                db.execute(f"UPDATE security_identifier_history SET {clause}")
