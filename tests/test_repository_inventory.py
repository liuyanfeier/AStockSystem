"""Capacity governance must not count aliases twice or follow external data."""

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from astock.paths import get_project_root


SCRIPT = get_project_root() / "scripts/repository_inventory.py"


@pytest.fixture
def inventory_module():
    spec = importlib.util.spec_from_file_location("repository_inventory", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capacity_distinguishes_hardlinks_from_logical_copies(tmp_path, inventory_module):
    raw = tmp_path / "data/raw"
    raw.mkdir(parents=True)
    source = raw / "a.duckdb"
    source.write_bytes(b"SYNTHETIC_NOT_A_DATABASE")
    os.link(source, raw / "b.duckdb")
    result = inventory_module.inventory(tmp_path, hash_data=True)
    assert result["groups"]["data"]["files"] == 2
    assert result["groups"]["data"]["logical_bytes"] == 2 * source.stat().st_size
    assert result["unique_file_allocated_bytes"] == source.stat().st_blocks * 512
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    assert set(result["duplicate_database_hashes"][checksum]) == {
        "data/raw/a.duckdb", "data/raw/b.duckdb"}


def test_inventory_excludes_private_snapshots_and_external_symlinks(tmp_path, inventory_module):
    root = tmp_path / "root"
    (root / "data/raw").mkdir(parents=True)
    (root / "data/raw/source").write_bytes(b"REAL_SHAPED_FIXTURE")
    private = root / "data/private/repository-governance"
    private.mkdir(parents=True)
    (private / "old-inventory").write_bytes(b"DO_NOT_COUNT")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private-file").write_bytes(b"DO_NOT_FOLLOW")
    (root / "external-dir").symlink_to(outside, target_is_directory=True)
    (root / "data/raw/external-file").symlink_to(outside / "private-file")
    result = inventory_module.inventory(root, hash_data=True, excluded=private)
    assert set(result["data_files"]) == {"data/raw/source"}
    assert result["symlink_paths"] == ["data/raw/external-file", "external-dir"]


def test_cli_refuses_public_output_and_snapshot_overwrite(tmp_path):
    root = tmp_path / "root"
    (root / "data/raw").mkdir(parents=True)
    (root / "data/raw/source").write_bytes(b"FIXTURE")
    command = [sys.executable, str(SCRIPT), "--root", str(root), "--output"]
    public = root / "docs/capacity.json"
    rejected = subprocess.run(command + [str(public)], capture_output=True, text=True)
    assert rejected.returncode == 2 and "inside data/private" in rejected.stderr
    assert not public.exists()
    output = root / "data/private/repository-governance/snapshot.json"
    assert subprocess.run(command + [str(output)], capture_output=True).returncode == 0
    before = output.read_bytes()
    rejected = subprocess.run(command + [str(output)], capture_output=True, text=True)
    assert rejected.returncode == 2 and "already exists" in rejected.stderr
    assert output.read_bytes() == before
