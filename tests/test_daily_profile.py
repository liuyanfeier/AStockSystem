"""Daily entry regressions: configuration cannot widen authority or rewrite sources."""
from copy import deepcopy
from pathlib import Path

import pytest
from typer.testing import CliRunner

from astock.cli.main import app
from astock.decision.daily import load_daily_profile
from astock.research.core import encoded, read_json
from astock.research.store import ResearchStore
from test_decision_loop import inputs


@pytest.fixture
def daily_case(tmp_path, monkeypatch):
    import astock.cli.research as cli

    raw, old, latest, run, market = inputs()
    config = tmp_path / "config"
    config.mkdir()
    documents = tmp_path / "data/private/research-v3/test"
    documents.mkdir(parents=True)
    (documents / "s1.pdf").write_bytes(b"%PDF-mock")
    parameters = dict(version="SYNTHETIC", return_sessions=20, trend_sessions=60,
                      breakout_sessions=20, activity_sessions=20, top_n=10,
                      min_mean_amount_cny=100, max_stale_calendar_days=3)
    for name, value in (("run", run), ("old", old.model_dump(mode="json")),
                        ("latest", latest.model_dump(mode="json")), ("market", market),
                        ("parameters", parameters)):
        (config / f"{name}.json").write_bytes(encoded(value))
    source = tmp_path / "data/private/research-v1/source.duckdb"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"SYNTHETIC: preflight must not open this database")
    profile = dict(
        protocol="DAILY_PROFILE_V1", run="config/run.json", previous="config/old.json",
        latest="config/latest.json", documents="data/private/research-v3/test",
        baseline_market="config/market.json", bundle="b",
        store="data/private/research-v1/source.duckdb",
        journal_store="data/private/research-v1/decision-loop-v0/real/daily/journal.duckdb",
        output="reports/private/research-v1/daily", parameters="config/parameters.json",
    )
    path = config / "daily.json"
    path.write_bytes(encoded(profile))
    monkeypatch.setattr(cli, "get_project_root", lambda: tmp_path)
    return tmp_path, path, profile, market


def test_check_reads_only_configuration_not_credentials_or_databases(daily_case, monkeypatch):
    root, path, _, _ = daily_case
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    monkeypatch.setenv("TUSHARE_TOKEN", "synthetic-not-a-credential-do-not-display")

    def reject(*args, **kwargs):
        pytest.fail("configuration preflight must not open a database")

    monkeypatch.setattr(ResearchStore, "initialize", reject)
    monkeypatch.setattr(ResearchStore, "snapshot", reject)
    result = CliRunner().invoke(app, ["research", "daily", "--profile", str(path), "--check"])
    assert result.exit_code == 0, result.output
    assert "固定观察时间：2026-10-14" in result.output
    assert "尚未核验行情内容" in result.output
    assert "synthetic-not-a-credential" not in result.output
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_relative_paths_belong_to_project_not_current_directory(daily_case, monkeypatch):
    root, _, _, _ = daily_case
    monkeypatch.chdir(root / "data")
    profile, observation = load_daily_profile(root, Path("config/daily.json"))
    assert profile.store == root / "data/private/research-v1/source.duckdb"
    assert observation.required_market_date == "2026-10-13"
    assert profile.close_options()["public_output"] is None


@pytest.mark.parametrize("case", ["extra_permission", "parent", "outside", "public_output",
                                  "source_journal", "wrong_journal_mode", "missing_source",
                                  "duplicate_component", "future_observation", "wrong_account"])
def test_invalid_profile_fails_before_any_journal_or_report(daily_case, case):
    root, path, original, _ = daily_case
    value = deepcopy(original)
    if case == "extra_permission":
        value["live"] = "synthetic-private-text-never-print"
    elif case == "parent":
        value["store"] = "data/private/research-v1/../research-v1/source.duckdb"
    elif case == "outside":
        value["output"] = "/private/tmp/astock-outside-private-report"
    elif case == "public_output":
        value["output"] = "docs/research/results/new"
    elif case == "source_journal":
        value["journal_store"] = value["store"]
    elif case == "wrong_journal_mode":
        value["journal_store"] = "data/private/research-v1/decision-loop-v0/simulated/journal.duckdb"
    elif case == "missing_source":
        value["store"] = "data/private/research-v1/absent.duckdb"
    elif case == "duplicate_component":
        value["components"] = [dict(bundle=value["bundle"], store=value["store"])]
    elif case == "future_observation":
        run = read_json(root / value["run"])
        run["observed_at"] = "2999-10-14T03:00:00+00:00"
        (root / value["run"]).write_bytes(encoded(run))
    elif case == "wrong_account":
        account = root / "data/private/research-v1/account.json"
        account.write_bytes(encoded(dict(mode="SIMULATED", snapshot_at="2026-10-14T02:00:00+00:00",
                                         position_event_ids=[])))
        value["position_scope"] = str(account.relative_to(root))
    path.write_bytes(encoded(value))
    result = CliRunner().invoke(app, ["research", "daily", "--profile", str(path)])
    assert result.exit_code == 1 and "配置检查失败" in result.output
    assert "synthetic-private-text" not in result.output
    assert not (root / original["journal_store"]).exists()
    assert not (root / "reports").exists()


def test_symlinks_and_hardlinks_cannot_target_source_as_journal(daily_case):
    root, path, original, _ = daily_case
    value = deepcopy(original)
    link = root / "config/source-link.duckdb"
    link.symlink_to(root / original["store"])
    value["store"] = str(link.relative_to(root))
    path.write_bytes(encoded(value))
    with pytest.raises(ValueError, match="DAILY_SYMLINK"):
        load_daily_profile(root, path)
    journal = root / original["journal_store"]
    journal.parent.mkdir(parents=True)
    journal.hardlink_to(root / original["store"])
    path.write_bytes(encoded(original))
    with pytest.raises(ValueError, match="DAILY_SOURCE_JOURNAL_HARDLINK"):
        load_daily_profile(root, path)


def test_daily_uses_existing_close_and_is_repeatable(daily_case, monkeypatch):
    import astock.company.workflow as company
    import astock.decision.increment as increment

    root, path, profile, market = daily_case
    # Only the market boundary is stubbed; source-document validation, decision,
    # private journal and immutable report publication run through production code.
    monkeypatch.setattr(increment, "market_context", lambda *args, **kwargs: (market, []))
    monkeypatch.setattr(company, "verified_market_context", lambda *args, **kwargs: [])
    source_before = (root / profile["store"]).read_bytes()
    runner = CliRunner()
    args = ["research", "daily", "--profile", str(path)]
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    reports = sorted((root / profile["output"]).glob("*.json"))
    assert len(reports) == 1
    report_before = reports[0].read_bytes()
    second = runner.invoke(app, args)
    assert second.exit_code == 0, second.output
    assert reports[0].read_bytes() == report_before
    result = read_json(reports[0])
    assert result["portfolio"]["positions_state"] == "UNKNOWN_NOT_EMPTY"
    assert result["window_end"] == "2026-10-12" and not result["market_fresh"]
    assert not result["cards"][0]["trade_eligible"]
    assert result["cards"][0]["order"] is None
    assert (root / profile["store"]).read_bytes() == source_before
    assert "未获取新行情" in second.output
