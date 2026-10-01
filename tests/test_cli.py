import duckdb
import pytest
from typer.main import get_command
from typer.testing import CliRunner

from astock.cli import main
from astock.paths import REQUIRED_DIRECTORIES, get_project_root


runner = CliRunner()


@pytest.fixture
def doctor_root(tmp_path, monkeypatch):
    for relative in REQUIRED_DIRECTORIES:
        (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    schema = get_project_root() / "sql/001_foundation_schema.sql"
    (tmp_path / "sql/001_foundation_schema.sql").write_bytes(schema.read_bytes())
    monkeypatch.setattr(main, "get_project_root", lambda: tmp_path)
    return tmp_path


def test_doctor_is_offline_read_only_and_secret_free(doctor_root):
    before = {path.relative_to(doctor_root) for path in doctor_root.rglob("*")}
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "Tushare token configured: NO" in result.output
    assert "Overall: PASS" in result.output
    assert {path.relative_to(doctor_root) for path in doctor_root.rglob("*")} == before
    assert not list(doctor_root.rglob("*.duckdb"))


def test_doctor_reports_only_token_presence(doctor_root, monkeypatch):
    token = "synthetic-doctor-token-not-a-credential"
    monkeypatch.setenv("TUSHARE_TOKEN", token)
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 0
    assert "Tushare token configured: YES" in result.output
    assert token not in result.output


def test_doctor_fails_for_missing_directory(doctor_root):
    # Delete only an empty disposable test directory to simulate failure.
    (doctor_root / "reports").rmdir()
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 1
    assert "Directory reports: FAIL" in result.output
    assert "Overall: FAIL" in result.output


def test_doctor_fails_for_missing_schema(doctor_root):
    (doctor_root / "sql/001_foundation_schema.sql").rename(doctor_root / "sql/missing.sql")
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 1
    assert "Foundation schema file: FAIL" in result.output


def test_doctor_does_not_create_missing_custom_storage(doctor_root, monkeypatch):
    monkeypatch.setenv("ASTOCK_DATA_DIR", "not_created")
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 1
    assert not (doctor_root / "not_created").exists()


def test_doctor_fails_for_database_path_that_is_directory(doctor_root, monkeypatch):
    monkeypatch.setenv("ASTOCK_DB_PATH", "data/warehouse")
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 1
    assert "Configured DuckDB path is not a directory: FAIL" in result.output


def test_doctor_suppresses_exception_text(doctor_root, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("synthetic-sensitive-error-do-not-print")

    monkeypatch.setattr(main, "load_settings", fail)
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 1
    assert "synthetic-sensitive-error-do-not-print" not in result.output
    assert "Overall: FAIL" in result.output


def test_doctor_fails_if_duckdb_unavailable(doctor_root, monkeypatch):
    def fail(*args, **kwargs):
        raise duckdb.Error("synthetic-sensitive-error-do-not-print")

    monkeypatch.setattr(main.duckdb, "connect", fail)
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 1
    assert "DuckDB in-memory database: FAIL" in result.output
    assert "synthetic-sensitive-error-do-not-print" not in result.output


def test_doctor_checks_python_baseline(doctor_root, monkeypatch):
    monkeypatch.setattr(main.sys, "version_info", (3, 11, 0))
    result = runner.invoke(main.app, ["doctor"])
    assert result.exit_code == 1
    assert "Python 3.12: FAIL" in result.output


def test_help_has_only_diagnostic_command():
    result = runner.invoke(main.app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.output
    assert set(get_command(main.app).commands) == {"doctor", "data"}
