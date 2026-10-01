"""Centralized paths for the editable repository checkout."""

from dataclasses import dataclass
from pathlib import Path


REQUIRED_DIRECTORIES = (
    "config", "docs", "sql", "src/astock/cli", "src/astock/data",
    "src/astock/features", "src/astock/regime", "src/astock/sectors",
    "src/astock/screening", "src/astock/catalysts", "src/astock/portfolio",
    "src/astock/backtest", "src/astock/reports", "tests", "data/raw",
    "data/curated", "data/warehouse", "research", "reports",
    "skills/a-share-research",
)


def get_project_root() -> Path:
    """Find the source checkout independently of the working directory."""
    source = Path(__file__).resolve()
    for candidate in source.parents:
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/astock/paths.py").resolve() == source
        ):
            return candidate
    raise RuntimeError("Use the editable source checkout installed with uv sync.")


def resolve_path(path: Path, root: Path) -> Path:
    """Resolve relative paths against root; allow explicit external storage."""
    expanded = path.expanduser()
    return (expanded if expanded.is_absolute() else root / expanded).resolve()


def project_path(root: Path, relative: str) -> Path:
    """Resolve an internal resource, rejecting traversal and escaping symlinks."""
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError("Internal project resource escapes the project root.")
    return resolved


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data_dir: Path
    db_path: Path

    @classmethod
    def from_config(
        cls, root: Path, data_dir: Path, db_path: Path | None
    ) -> "ProjectPaths":
        root = root.resolve()
        data = resolve_path(data_dir, root)
        database = (
            data / "warehouse/astock.duckdb"
            if db_path is None else resolve_path(db_path, root)
        )
        return cls(root, data, database.resolve())

    @property
    def schema_file(self) -> Path:
        return project_path(self.root, "sql/001_foundation_schema.sql")

    @property
    def required_directories(self) -> tuple[Path, ...]:
        return tuple(project_path(self.root, path) for path in REQUIRED_DIRECTORIES)
