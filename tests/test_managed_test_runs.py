"""A test-run receipt cannot adopt old data or turn a failure into cleanup permission."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

import astock.runtime.test_runs as runs


@pytest.fixture
def project(tmp_path, monkeypatch):
    for name in ("src", "tests", "sql", "config/storage", "compat", "scripts"):
        (tmp_path / name).mkdir(parents=True)
    for name in ("pyproject.toml", "uv.lock", "tests/conftest.py", "tests/test_example.py"):
        (tmp_path / name).write_text("# SYNTHETIC\n")
    policy = dict(version="SYNTHETIC_TEST_LIFECYCLE_V1", managed_budget_bytes=100_000,
                  default_expected_peak_bytes=1000, free_disk_reserve_bytes=0, passed_retention_days=7)
    (tmp_path / "config/storage/synthetic-tests-v1.json").write_text(json.dumps(policy))
    monkeypatch.setattr(runs.subprocess, "check_output", lambda *a, **k: "a" * 40)
    monkeypatch.setattr(runs.shutil, "disk_usage", lambda *a: type("Space", (), {"free": 10**9})())
    return tmp_path


def complete(run, code=0, *, when=None):
    (run.directory / "junit.xml").write_text(
        '<testsuites><testsuite><testcase name="synthetic">'
        + ('<failure message="synthetic failure"/>' if code else '')
        + '</testcase></testsuite></testsuites>')
    (run.directory / "pytest.log").write_text("SYNTHETIC result\n")
    return runs.finish_test_run(run, code, finished_at=when)


def test_recorded_run_is_fresh_bound_and_read_only_status_never_deletes(project):
    run = runs.prepare_test_run(project, ["tests/test_example.py"])
    other = runs.prepare_test_run(project, ["tests/test_example.py"])
    assert run.directory != other.directory
    assert "--basetemp" in run.command and str(run.directory / "work") in run.command
    assert "no:cacheprovider" in run.command
    work = run.directory / "work"
    work.mkdir()
    (work / "source.duckdb").write_bytes(b"SYNTHETIC DATABASE")
    at = datetime(2026, 10, 15, tzinfo=timezone.utc)
    result = complete(run, when=at)
    assert result["source_unchanged"] and result["state"] == "PASSED"
    assert result["counts"]["tests"] == 1
    assert set(result["evidence_sha256"]) == {"junit.xml", "pytest.log"}
    before = {p: p.read_bytes() for p in run.directory.rglob("*") if p.is_file()}
    status = runs.retention_status(project, now=at + timedelta(days=8))
    states = {item["run_id"]: item["state"] for item in status["items"]}
    assert states[run.directory.name] == "CANDIDATE_REQUIRES_CONFIRMATION"
    assert states[other.directory.name] == "RETAIN_UNKNOWN"
    assert not status["deletion_performed"]
    assert before == {p: p.read_bytes() for p in run.directory.rglob("*") if p.is_file()}
    assert runs.retention_status(project, now=at)["items"] != []
    with pytest.raises(FileExistsError):
        complete(run)


@pytest.mark.parametrize("failure", ["failed", "missing_result", "source_changed", "empty_junit", "bad_junit"])
def test_failed_incomplete_or_changed_runs_never_become_candidates(project, failure):
    run = runs.prepare_test_run(project, [])
    if failure == "failed":
        complete(run, 1)
    elif failure == "source_changed":
        (project / "tests/test_example.py").write_text("# CHANGED\n")
        assert complete(run)["state"] == "RETAIN_FAILED_OR_UNKNOWN"
    elif failure == "empty_junit":
        (run.directory / "junit.xml").write_text("<testsuites/>")
        assert runs.finish_test_run(run, 0)["state"] == "RETAIN_FAILED_OR_UNKNOWN"
    elif failure == "bad_junit":
        (run.directory / "junit.xml").write_text("not xml")
        with pytest.raises(Exception):
            runs.finish_test_run(run, 0)
    status = runs.retention_status(project, now=datetime(2099, 1, 1, tzinfo=timezone.utc))
    assert status["items"][0]["state"] == "RETAIN_UNKNOWN"


@pytest.mark.parametrize("selection", ["/private/tmp/real", "tests/../data", "--basetemp", "", "tests/absent.py"])
def test_selection_cannot_override_destination_or_adopt_old_data(project, selection):
    with pytest.raises(ValueError):
        runs.prepare_test_run(project, [selection])
    assert not (project / "data").exists()


def test_budget_counts_unknown_directories_and_rejects_before_creation(project, monkeypatch):
    base = project / "data/private/runtime/synthetic-tests"
    base.mkdir(parents=True)
    (base / "unknown").mkdir()
    (base / "unknown/retained-source").write_bytes(b"x" * 99_500)
    with pytest.raises(ValueError, match="MANAGED_BUDGET"):
        runs.prepare_test_run(project, [])
    assert sorted(p.name for p in base.iterdir()) == ["unknown"]
    with pytest.raises(ValueError, match="POSITIVE_BUDGET"):
        runs.prepare_test_run(project, [], 0)
    monkeypatch.setattr(runs.shutil, "disk_usage", lambda *a: type("Space", (), {"free": 0})())
    with pytest.raises(ValueError, match="INSUFFICIENT_FREE"):
        runs.prepare_test_run(project, [], 1)


def test_symlinked_managed_root_or_test_path_is_rejected(project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside-managed")
    (project / "tests/link.py").symlink_to(outside)
    with pytest.raises(ValueError, match="SYMLINK"):
        runs.prepare_test_run(project, ["tests/link.py"])
    (project / "data/private/runtime").mkdir(parents=True)
    (project / "data/private/runtime/synthetic-tests").symlink_to(outside)
    with pytest.raises(ValueError, match="SYMLINK"):
        runs.retention_status(project)
    assert not list(outside.iterdir())


def test_unregistered_and_symlinked_receipts_remain_unknown(project, tmp_path):
    run = runs.prepare_test_run(project, [])
    complete(run)
    other = run.directory.parent / "unregistered"
    other.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (other / "linked").symlink_to(outside, target_is_directory=True)
    run_result = run.directory / "result.json"
    copied = outside / "result.json"
    # A receipt replaced by a symlink is never accepted as managed evidence.
    run_result.rename(copied)
    run_result.symlink_to(copied)
    result = runs.retention_status(project, now=datetime(2099, 1, 1, tzinfo=timezone.utc))
    assert all(item["state"] == "RETAIN_UNKNOWN" for item in result["items"])
