import yaml

from astock.paths import get_project_root


def test_placeholder_configs_are_disabled_and_unset():
    config = get_project_root() / "config"
    loaded = {path.stem: yaml.safe_load(path.read_text(encoding="utf-8")) for path in config.glob("*.yaml")}
    assert set(loaded) == {"data_sources", "regime", "risk", "universe"}
    assert all(item["enabled"] is False and item["schema_version"] == 1 for item in loaded.values())
    assert all(value is None for key, value in loaded["risk"].items() if key not in {"schema_version", "enabled"})
    assert loaded["regime"]["weights"] is None
    assert loaded["regime"]["thresholds"] is None
    assert all(value is None for value in loaded["regime"]["dimensions"].values())
    assert set(loaded["universe"]["categories"]) == {"core", "special_situations"}
    assert all(item["criteria"] is None for item in loaded["universe"]["categories"].values())
