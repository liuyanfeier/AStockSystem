from pathlib import Path

import pytest

from astock.paths import ProjectPaths, get_project_root, project_path


def test_root_is_independent_of_working_directory(tmp_path, monkeypatch):
    expected = get_project_root()
    monkeypatch.chdir(tmp_path)
    assert get_project_root() == expected
    assert (expected / "pyproject.toml").is_file()


def test_default_paths_do_not_create_files(tmp_path):
    before = set(tmp_path.rglob("*"))
    paths = ProjectPaths.from_config(tmp_path, Path("data"), None)
    assert paths.data_dir == tmp_path / "data"
    assert paths.db_path == tmp_path / "data/warehouse/astock.duckdb"
    assert paths.schema_file == tmp_path / "sql/001_foundation_schema.sql"
    assert set(tmp_path.rglob("*")) == before


def test_data_override_relocates_default_database(tmp_path):
    paths = ProjectPaths.from_config(tmp_path, Path("custom"), None)
    assert paths.db_path == tmp_path / "custom/warehouse/astock.duckdb"


def test_database_override_is_relative_to_project(tmp_path):
    paths = ProjectPaths.from_config(tmp_path, Path("custom"), Path("store/test.duckdb"))
    assert paths.db_path == tmp_path / "store/test.duckdb"


def test_explicit_external_storage_is_supported(tmp_path):
    external = tmp_path.parent / "external_synthetic_store"
    paths = ProjectPaths.from_config(tmp_path, external, None)
    assert paths.data_dir == external
    assert paths.db_path == external / "warehouse/astock.duckdb"


@pytest.mark.parametrize("relative", ["../outside", "/outside"])
def test_internal_resources_reject_traversal(tmp_path, relative):
    with pytest.raises(ValueError, match="escapes"):
        project_path(tmp_path, relative)


def test_internal_resources_reject_symlink_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "sql").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        project_path(root, "sql/001_foundation_schema.sql")
