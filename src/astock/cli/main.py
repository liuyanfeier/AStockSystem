"""Read-only Phase 0 diagnostics. No market-data or network operations."""

import sys

import duckdb
import typer
from pydantic import ValidationError

from astock.paths import get_project_root
from astock.settings import load_settings


app = typer.Typer(
    help="AStockSystem offline diagnostics.",
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.callback()
def main() -> None:
    """Research foundation; no ingestion or trading commands."""


@app.command()
def doctor() -> None:
    """Check configuration and local capabilities without creating files."""
    passed = True

    def check(label: str, ok: bool) -> None:
        nonlocal passed
        passed = passed and ok
        typer.echo(f"{label}: {'PASS' if ok else 'FAIL'}")

    typer.echo(f"Python version: {sys.version.split()[0]}")
    check("Python 3.12", sys.version_info[:2] == (3, 12))
    try:
        root = get_project_root()
        settings = load_settings(root)
        paths = settings.paths(root)
        typer.echo(f"Project root: {paths.root}")
        typer.echo(f"Configured data directory: {paths.data_dir}")
        typer.echo(f"Configured DuckDB path: {paths.db_path}")
        typer.echo(f"Tushare token configured: {'YES' if settings.token_configured else 'NO'}")
        for directory in paths.required_directories:
            check(f"Directory {directory.relative_to(paths.root)}", directory.is_dir())
        check("Configured data directory", paths.data_dir.is_dir())
        check("Configured DuckDB parent directory", paths.db_path.parent.is_dir())
        check("Configured DuckDB path is not a directory", not paths.db_path.is_dir())
        check("Foundation schema file", paths.schema_file.is_file())
    except (ValidationError, ValueError, OSError, RuntimeError):
        check("Project configuration (details suppressed to protect secrets)", False)

    try:
        with duckdb.connect(":memory:") as connection:
            check("DuckDB in-memory database", connection.execute("SELECT 1").fetchone() == (1,))
    except duckdb.Error:
        check("DuckDB in-memory database", False)

    typer.echo(f"Overall: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise typer.Exit(code=1)
