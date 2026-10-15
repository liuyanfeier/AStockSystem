"""Record newly created synthetic test runs and propose retention, without deleting."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import uuid
import xml.etree.ElementTree as ET

from pydantic import BaseModel, ConfigDict, Field


class TestPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(pattern="^SYNTHETIC_TEST_LIFECYCLE_V1$")
    managed_budget_bytes: int = Field(gt=0)
    default_expected_peak_bytes: int = Field(gt=0)
    free_disk_reserve_bytes: int = Field(ge=0)
    passed_retention_days: int = Field(ge=0)


@dataclass(frozen=True)
class TestRun:
    root: Path
    directory: Path
    command: list[str]


def checked_path(path: Path) -> Path:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("TEST_RUN_SYMLINK")
    return path


def load_policy(root: Path) -> TestPolicy:
    path = checked_path(root / "config/storage/synthetic-tests-v1.json")
    return TestPolicy.model_validate_json(path.read_bytes())


def tree_size(path: Path) -> dict:
    """Metadata only; no symlink traversal or database opens; errors propagate."""
    result = dict(files=0, logical_bytes=0, symlinks=0, special_files=0)
    if not path.exists():
        return result
    def failure(error: OSError) -> None:
        raise error
    for directory, dirs, files in os.walk(path, followlinks=False, onerror=failure):
        base = Path(directory)
        for name in [*dirs, *files]:
            entry = base / name
            info = entry.lstat()
            if stat.S_ISLNK(info.st_mode):
                result["symlinks"] += 1
            elif stat.S_ISREG(info.st_mode):
                result["files"] += 1
                result["logical_bytes"] += info.st_size
            elif not stat.S_ISDIR(info.st_mode):
                result["special_files"] += 1
        dirs[:] = [name for name in dirs if not (base / name).is_symlink()]
    return result


def source_fingerprint(root: Path) -> str:
    """Hash runnable code, fixtures, schema/config and lock; never .env or data."""
    paths = [root / name for name in ("pyproject.toml", "uv.lock")]
    def failure(error: OSError) -> None:
        raise error
    for name in ("src", "tests", "sql", "config", "compat", "scripts"):
        base = checked_path(root / name)
        for directory, dirs, files in os.walk(base, followlinks=False, onerror=failure):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for child in dirs:
                checked_path(Path(directory) / child)
            paths.extend(Path(directory) / f for f in files
                         if Path(f).suffix in {".py", ".sql", ".json", ".toml", ".yaml", ".yml"})
    digest = hashlib.sha256()
    for path in sorted(paths):
        checked_path(path)
        digest.update(str(path.relative_to(root)).encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def publish_record(path: Path, value: dict) -> None:
    checked_path(path)
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def prepare_test_run(root: Path, selections: list[str], expected_peak_bytes: int | None = None) -> TestRun:
    root = root.resolve()
    policy = load_policy(root)
    peak = policy.default_expected_peak_bytes if expected_peak_bytes is None else expected_peak_bytes
    if peak <= 0:
        raise ValueError("TEST_RUN_POSITIVE_BUDGET_REQUIRED")
    selected = selections or ["tests"]
    for selection in selected:
        path = Path(selection.split("::", 1)[0])
        if not path.parts or path.is_absolute() or ".." in path.parts or path.parts[0] != "tests":
            raise ValueError("TEST_RUN_SELECTION_OUTSIDE_TESTS")
        target = checked_path(root / path)
        if not target.exists():
            raise ValueError("TEST_RUN_SELECTION_MISSING")
    base = checked_path(root / "data/private/runtime/synthetic-tests")
    usage = tree_size(base)
    if usage["logical_bytes"] + peak > policy.managed_budget_bytes:
        raise ValueError("TEST_RUN_MANAGED_BUDGET_EXCEEDED")
    if shutil.disk_usage(root).free < peak + policy.free_disk_reserve_bytes:
        raise ValueError("TEST_RUN_INSUFFICIENT_FREE_SPACE")
    fingerprint = source_fingerprint(root)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    identifier = uuid.uuid4().hex
    directory = base / identifier
    directory.mkdir(parents=True, exist_ok=False)
    command = ["-m", "pytest", *selected, "-q", "-p", "no:cacheprovider",
               "--basetemp", str(directory / "work"), "--junitxml", str(directory / "junit.xml")]
    publish_record(directory / "manifest.json", dict(
        protocol="SYNTHETIC_TEST_RUN_V1", category="synthetic_test", owner="pytest",
        run_id=identifier, created_at=datetime.now(timezone.utc).isoformat(),
        implementation_sha=revision, source_tree_sha256=fingerprint,
        pytest_arguments=command,
        selections=selected, expected_peak_bytes=peak, policy=policy.model_dump(),
        reproduction="Use this source fingerprint and lock, then rerun the recorded selections in a new workspace",
        protected_reason="Running/failed/unknown retained; passing workspace only a cleanup candidate",
        network="Repository socket guard; common credential environment variables removed by runner",
    ))
    return TestRun(root, directory, command)


def finish_test_run(run: TestRun, returncode: int, *, finished_at: datetime | None = None) -> dict:
    counts = dict(tests=0, failures=0, errors=0, skipped=0)
    junit = run.directory / "junit.xml"
    if junit.exists():
        suites = ET.parse(junit).getroot()
        cases = suites.findall(".//testcase")
        counts = dict(tests=len(cases), failures=sum(c.find("failure") is not None for c in cases),
                      errors=sum(c.find("error") is not None for c in cases),
                      skipped=sum(c.find("skipped") is not None for c in cases))
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    passed = returncode == 0 and counts["passed"] > 0 and not counts["failures"] and not counts["errors"]
    result = dict(protocol="SYNTHETIC_TEST_RESULT_V1", returncode=returncode,
                  state="PASSED" if passed else "RETAIN_FAILED_OR_UNKNOWN",
                  finished_at=(finished_at or datetime.now(timezone.utc)).isoformat(),
                  counts=counts, workspace=tree_size(run.directory / "work"),
                  source_tree_sha256_after=source_fingerprint(run.root),
                  deletion_performed=False)
    result["evidence_sha256"] = {name: hashlib.sha256((run.directory / name).read_bytes()).hexdigest()
                                 for name in ("junit.xml", "pytest.log") if (run.directory / name).exists()}
    manifest = json.loads((run.directory / "manifest.json").read_text())
    result["source_unchanged"] = result["source_tree_sha256_after"] == manifest["source_tree_sha256"]
    if not result["source_unchanged"]:
        result["state"] = "RETAIN_FAILED_OR_UNKNOWN"
    publish_record(run.directory / "result.json", result)
    return result


def retention_status(root: Path, *, now: datetime | None = None) -> dict:
    root = root.resolve()
    policy = load_policy(root)
    base = checked_path(root / "data/private/runtime/synthetic-tests")
    at = now or datetime.now(timezone.utc)
    items = []
    for path in sorted(base.iterdir()) if base.exists() else []:
        item = dict(run_id=path.name, state="RETAIN_UNKNOWN", logical_bytes=0)
        if path.is_dir() and not path.is_symlink():
            item.update(tree_size(path))
            try:
                manifest_path = checked_path(path / "manifest.json")
                result_path = checked_path(path / "result.json")
                manifest, result = json.loads(manifest_path.read_text()), json.loads(result_path.read_text())
                if (manifest["protocol"] == "SYNTHETIC_TEST_RUN_V1" and manifest["run_id"] == path.name
                        and result["protocol"] == "SYNTHETIC_TEST_RESULT_V1" and result["state"] == "PASSED"
                        and result["returncode"] == 0 and result["source_unchanged"]
                        and result["counts"]["passed"] > 0 and not result["counts"]["failures"]
                        and not result["counts"]["errors"] and not item["special_files"]):
                    due = datetime.fromisoformat(result["finished_at"]) + timedelta(days=policy.passed_retention_days)
                    item["state"] = "CANDIDATE_REQUIRES_CONFIRMATION" if at >= due else "RETAIN_WITHIN_WINDOW"
                    item["eligible_after"] = due.isoformat()
            except (OSError, ValueError, KeyError, TypeError):
                pass
        items.append(item)
    usage = tree_size(base)
    return dict(protocol="SYNTHETIC_TEST_RETENTION_V1", observed_at=at.isoformat(),
                **usage, managed_budget_bytes=policy.managed_budget_bytes, items=items,
                deletion_performed=False, scope="New managed test runs only; not project-wide capacity or deletion permission")
