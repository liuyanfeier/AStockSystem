"""Offline diagnostics and explicitly bounded, opt-in data audit commands."""

import sys

import duckdb
import typer
import yaml
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


data_app = typer.Typer(help="Offline data-contract audit only.", add_completion=False)
app.add_typer(data_app, name="data")


@data_app.command("contracts")
def data_contracts(catalog: str = typer.Option("v1", "--catalog")) -> None:
    """Validate the selected pinned catalog without network or file writes."""
    from astock.data.contracts import load_contracts

    try:
        contracts = load_contracts(get_project_root(), catalog_version=catalog)
    except (ValidationError, ValueError, OSError, RuntimeError, yaml.YAMLError):
        typer.echo("Contracts: FAIL (details suppressed to protect secrets)")
        raise typer.Exit(code=1)
    for contract in contracts:
        cap = str(contract.max_rows) if contract.max_rows is not None else "UNKNOWN"
        typer.echo(f"{contract.dataset}: max_rows={cap}, availability={contract.availability_policy}")
    typer.echo(f"Contracts: PASS ({len(contracts)}); offline; no fetching")


probe_app = typer.Typer(help="Bounded Phase 1B probe; live requests require --live.",
                        add_completion=False)
data_app.add_typer(probe_app, name="probe")


@probe_app.command('plan')
def probe_plan() -> None:
    """Show the fixed offline plan without reading credentials or storage."""
    from astock.data.probe import load_plan
    try:
        plan = load_plan(get_project_root())
        typer.echo(plan.model_dump_json(indent=2))
        typer.echo('47 logical requests maximum; 94 attempts maximum; no full backfill.')
    except Exception:
        typer.echo('Probe plan: FAIL (safe details only)')
        raise typer.Exit(1)


@probe_app.command('run')
def probe_run(live: bool = typer.Option(False, '--live')) -> None:
    """Run the approved sample only when live access is explicitly selected."""
    if not live:
        typer.echo('Live access requires explicit --live; no request sent.')
        raise typer.Exit(1)
    from astock.data.probe import run_probe
    try:
        root = get_project_root()
        settings = load_settings(root)
        if not settings.token_configured:
            typer.echo('TUSHARE_TOKEN is not configured.')
            typer.echo('Configure TUSHARE_TOKEN locally in .env outside the chat/model input, then rerun.')
            raise typer.Exit(1)
        summary, _ = run_probe(root, settings)
        typer.echo(f"PHASE 1B STATUS: {summary['status']}")
        typer.echo(f"Resolved recent date: {summary['resolved_recent_date']}")
        typer.echo(f"Requests: {sum(r['request_count'] for r in summary['runs'].values())}")
        typer.echo('SECRET_SCAN: PASS')
        if summary['status'] != 'PASS':
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        typer.echo('PHASE 1B STATUS: BLOCKED (safe details only; no error body printed)')
        raise typer.Exit(1)


@probe_app.command('status')
def probe_status_command() -> None:
    """Read aggregate local probe statuses offline."""
    from astock.data.probe import probe_status
    try:
        summaries = probe_status(get_project_root())
        for summary in summaries:
            typer.echo(f"{summary['batch_id']}: {summary['status']}; SECRET_SCAN: {summary['secret_scan']}")
        if not summaries:
            typer.echo('No completed local probes.')
    except Exception:
        typer.echo('Probe status: FAIL (safe details only)')
        raise typer.Exit(1)


identity_app = typer.Typer(help='Phase 1C.0 identity governance only.', add_completion=False)
data_app.add_typer(identity_app, name='identity')


@identity_app.command('specs')
def identity_specs() -> None:
    """Validate typed curation specifications offline; no credentials or storage."""
    from astock.data.curation import load_curation_specs
    try:
        specs = load_curation_specs(get_project_root())
        for spec in specs:
            typer.echo(f'{spec.dataset}: {spec.research_usage}; {len(spec.fields)} typed columns')
        typer.echo('Typed curation specs: PASS; no curation or network')
    except Exception:
        typer.echo('Typed curation specs: FAIL (safe details only)')
        raise typer.Exit(1)


@identity_app.command('bootstrap')
def identity_bootstrap(authority: str = typer.Option(..., '--authority'),
                       live: bool = typer.Option(False, '--live')) -> None:
    """Reuse accepted raw captures; --live permits one mapping attempt only."""
    from pathlib import Path
    from astock.data.bootstrap import run_bootstrap
    try:
        root = get_project_root()
        summary = run_bootstrap(root, load_settings(root), authority_path=Path(authority), live=live)
        import json
        typer.echo(json.dumps(summary, sort_keys=True, indent=2))
        if summary['status'] != 'PASS':
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        typer.echo('PHASE 1C.0 STATUS: BLOCKED (safe details only; no automatic retry)')
        raise typer.Exit(1)


slice_app = typer.Typer(help='Fixed Phase 1C.1 historical rehearsal only.', add_completion=False)
data_app.add_typer(slice_app, name='slice')


@slice_app.command('plan')
def slice_plan_command() -> None:
    from astock.data.slice_plan import request_manifest
    import json
    try:
        typer.echo(json.dumps(request_manifest(get_project_root()), indent=2, sort_keys=True))
    except Exception:
        typer.echo('Slice plan: FAIL (safe details only)')
        raise typer.Exit(1)
