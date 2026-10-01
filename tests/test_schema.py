import duckdb
import pytest

from astock.paths import get_project_root


@pytest.fixture
def schema_sql():
    return (get_project_root() / "sql/001_foundation_schema.sql").read_text(encoding="utf-8")


@pytest.fixture
def database(schema_sql):
    with duckdb.connect(":memory:") as connection:
        connection.execute("SET TimeZone = 'UTC'")
        connection.execute(schema_sql)
        yield connection


def insert_security(database, **overrides):
    values = {
        "security_id": "synthetic-security", "symbol": "TEST", "name": "Synthetic",
        "exchange": "TEST_EXCHANGE", "board": "TEST_BOARD",
        "list_date": "2020-01-01", "delist_date": None,
        "security_type": "synthetic", "source": "synthetic-fixture",
        "valid_from": "2020-01-01", "valid_to": None,
        "published_at": "2020-01-01 08:00:00+00",
        "available_at": "2020-01-01 09:00:00+00",
    }
    values.update(overrides)
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    database.execute(f"INSERT INTO security_master ({columns}) VALUES ({placeholders})", list(values.values()))


def insert_rule(database, **overrides):
    values = {
        "rule_id": "synthetic-rule", "exchange": "TEST_EXCHANGE", "board": "TEST_BOARD",
        "security_status": "TEST_STATUS", "effective_from": "2020-01-01",
        "effective_to": None, "price_limit_rule": "synthetic, not an actual trading rule",
        "price_limit_fraction": None, "settlement_t_plus_n": None, "lot_size": None,
        "source": "synthetic-fixture", "published_at": "2019-12-01 08:00:00+00",
        "available_at": "2019-12-01 09:00:00+00",
    }
    values.update(overrides)
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    database.execute(f"INSERT INTO market_rule_history ({columns}) VALUES ({placeholders})", list(values.values()))


def insert_hypothesis(database, **overrides):
    values = {
        "hypothesis_id": "synthetic-contract-check", "created_at": "2020-01-01 00:00:00+00",
        "question": "Synthetic storage fixture", "economic_rationale": "No investment claim",
        "data_required": "Synthetic data only",
    }
    values.update(overrides)
    columns = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    database.execute(f"INSERT INTO research_hypothesis ({columns}) VALUES ({placeholders})", list(values.values()))


def test_only_foundation_tables_exist_and_are_unseeded(database):
    tables = {row[0] for row in database.execute("SHOW TABLES").fetchall()}
    expected = {
        "security_master", "trade_calendar", "market_rule_history",
        "data_quality_log", "research_hypothesis", "schema_version",
    }
    assert tables == expected
    for table in expected - {"schema_version"}:
        assert database.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)


def test_schema_rerun_preserves_rows_and_version_time(database, schema_sql):
    insert_security(database)
    before = database.execute("SELECT * FROM schema_version").fetchall()
    database.execute(schema_sql)
    assert database.execute("SELECT * FROM schema_version").fetchall() == before
    assert database.execute("SELECT count(*) FROM security_master").fetchone() == (1,)


@pytest.mark.parametrize("overrides", [
    {"available_at": "2020-01-01 07:59:59+00"},
    {"available_at": None},
    {"valid_to": "2020-01-01"},
    {"valid_to": "2019-12-31"},
    {"delist_date": "2019-12-31"},
    {"source": " "},
])
def test_security_rejects_invalid_contract_values(database, overrides):
    with pytest.raises(duckdb.ConstraintException):
        insert_security(database, **overrides)


def test_security_duplicate_key_is_rejected(database):
    insert_security(database)
    with pytest.raises(duckdb.ConstraintException):
        insert_security(database, name="conflicting-content")


def test_security_revisions_and_delisted_records_are_retained(database):
    insert_security(database)
    insert_security(
        database, name="Revised synthetic name", delist_date="2021-01-01",
        published_at="2021-01-01 08:00:00+00", available_at="2021-01-01 09:00:00+00",
    )
    rows = database.execute("SELECT name, delist_date FROM security_master ORDER BY available_at").fetchall()
    assert len(rows) == 2
    assert rows[0] == ("Synthetic", None)
    assert str(rows[1][1]) == "2021-01-01"


@pytest.mark.parametrize("overrides", [
    {"effective_to": "2019-12-31"}, {"effective_to": "2020-01-01"},
    {"price_limit_fraction": -0.1}, {"price_limit_fraction": 1.1},
    {"settlement_t_plus_n": -1}, {"lot_size": 0},
    {"available_at": "2019-12-01 07:59:59+00"}, {"source": ""},
])
def test_rules_reject_invalid_contract_values(database, overrides):
    with pytest.raises(duckdb.ConstraintException):
        insert_rule(database, **overrides)


def test_future_effective_rule_can_be_known_earlier(database):
    insert_rule(database)
    assert database.execute(
        "SELECT available_at < effective_from::TIMESTAMPTZ FROM market_rule_history"
    ).fetchone() == (True,)


def test_rule_correction_does_not_rewrite_original(database):
    insert_rule(database)
    insert_rule(
        database, effective_to="2021-01-01", published_at="2021-01-01 08:00:00+00",
        available_at="2021-01-01 09:00:00+00",
    )
    assert database.execute(
        "SELECT effective_to FROM market_rule_history ORDER BY available_at"
    ).fetchall()[0] == (None,)
    assert database.execute("SELECT count(*) FROM market_rule_history").fetchone() == (2,)


def test_calendar_rejects_non_previous_open_date(database):
    with pytest.raises(duckdb.ConstraintException):
        database.execute("""
            INSERT INTO trade_calendar
            VALUES ('TEST', '2020-01-01', true, '2020-01-01', 'synthetic', NULL,
                    '2019-12-01 00:00:00+00')
        """)


@pytest.mark.parametrize("overrides", [
    {"research_start": "2020-01-01"},
    {"research_start": "2020-02-01", "research_end": "2020-01-01"},
    {"validation_start": "2020-01-01"},
    {"oos_start": "2020-01-01"},
    {"research_start": "2020-01-01", "research_end": "2020-02-01",
     "validation_start": "2020-02-01", "validation_end": "2020-03-01"},
    {"validation_start": "2020-01-01", "validation_end": "2020-02-01",
     "oos_start": "2020-02-01", "oos_end": "2020-03-01"},
    {"research_start": "2020-01-01", "research_end": "2020-02-01",
     "oos_start": "2020-01-15", "oos_end": "2020-03-01"},
    {"revision": 0},
    {"recorded_at": "2019-01-01 00:00:00+00"},
])
def test_hypothesis_rejects_invalid_periods_and_revision(database, overrides):
    with pytest.raises(duckdb.ConstraintException):
        insert_hypothesis(database, **overrides)


def test_hypothesis_retains_registration_when_results_are_appended(database):
    insert_hypothesis(database)
    insert_hypothesis(database, revision=2, result="synthetic contract check only")
    rows = database.execute(
        "SELECT revision, result FROM research_hypothesis ORDER BY revision"
    ).fetchall()
    assert rows == [(1, None), (2, "synthetic contract check only")]


def test_hypothesis_accepts_chronological_periods(database):
    insert_hypothesis(
        database, research_start="2020-01-01", research_end="2020-01-31",
        validation_start="2020-02-01", validation_end="2020-02-29",
        oos_start="2020-03-01", oos_end="2020-03-31",
    )
    assert database.execute("SELECT count(*) FROM research_hypothesis").fetchone() == (1,)


def test_quality_log_rejects_unknown_severity(database):
    with pytest.raises(duckdb.ConstraintException):
        database.execute("""
            INSERT INTO data_quality_log
            VALUES ('synthetic', 'synthetic', CURRENT_TIMESTAMP, 'contract',
                    'UNKNOWN', false, NULL, NULL, NULL)
        """)
