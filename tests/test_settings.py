from pathlib import Path

from astock.settings import Settings, load_settings


def test_settings_work_without_secrets(tmp_path):
    settings = load_settings(tmp_path)
    assert not settings.token_configured
    assert settings.data_dir == Path("data")
    assert settings.db_path is None


def test_secret_is_excluded_from_representations(monkeypatch):
    token = "synthetic-phase0-token-not-a-credential"
    monkeypatch.setenv("TUSHARE_TOKEN", token)
    settings = Settings()
    assert settings.token_configured
    assert token not in repr(settings)
    assert token not in str(settings)
    assert "tushare_token" not in settings.model_dump()
    assert token not in settings.model_dump_json()


def test_blank_environment_values_preserve_defaults(monkeypatch):
    for name in ("TUSHARE_TOKEN", "ASTOCK_DATA_DIR", "ASTOCK_DB_PATH"):
        monkeypatch.setenv(name, "")
    settings = Settings()
    assert not settings.token_configured
    assert settings.data_dir == Path("data")
    assert settings.db_path is None


def test_whitespace_token_is_unconfigured(monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", "  ")
    assert not Settings().token_configured


def test_root_dotenv_and_environment_precedence(tmp_path, monkeypatch):
    # Only a disposable synthetic fixture; never the repository's real .env.
    (tmp_path / ".env").write_text("ASTOCK_DATA_DIR=file_data\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / ".env").write_text("ASTOCK_DATA_DIR=wrong_data\n", encoding="utf-8")
    monkeypatch.chdir(elsewhere)
    assert load_settings(tmp_path).data_dir == Path("file_data")
    monkeypatch.setenv("ASTOCK_DATA_DIR", "environment_data")
    assert load_settings(tmp_path).data_dir == Path("environment_data")


def test_example_dotenv_does_not_require_secrets(tmp_path):
    (tmp_path / ".env").write_text(
        "TUSHARE_TOKEN=\nASTOCK_DATA_DIR=\nASTOCK_DB_PATH=\n", encoding="utf-8"
    )
    settings = load_settings(tmp_path)
    assert not settings.token_configured
    assert settings.data_dir == Path("data")
