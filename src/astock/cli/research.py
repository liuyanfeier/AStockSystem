"""Offline Research V1 commands. All mutable data/output stays in dedicated private roots."""
from pathlib import Path

import typer

from astock.paths import get_project_root
from astock.research.core import encoded, private_path, read_json
from astock.research.store import ResearchStore

app = typer.Typer(help="Source-traceable observation research; capture defaults to dry-run; no orders.",
                  add_completion=False, pretty_exceptions_enable=False)


def store_at(path: Path) -> ResearchStore:
    return ResearchStore(private_path(get_project_root(), path))


@app.command("import")
def import_command(bundle: Path = typer.Option(..., "--bundle"),
                   store: Path = typer.Option(Path("data/private/research-v1/research.duckdb"), "--store")) -> None:
    try:
        bundle_id = store_at(store).import_bundle(bundle)
        typer.echo(f"CURRENT_OBSERVATION bundle={bundle_id}; offline; source bytes retained")
    except Exception:
        typer.echo("Research import: FAIL (private details suppressed; no network)")
        raise typer.Exit(1) from None


def compute(bundle: str, as_of: str, parameters: Path, store: Path, watch: list[str]):
    from astock.features.market import ObservationParameters
    from astock.research.service import analyze
    research = store_at(store)
    params = ObservationParameters.model_validate(read_json(parameters))
    return research, analyze(research, bundle, as_of, params, watch)


@app.command("report")
def report_command(bundle: str = typer.Option(..., "--bundle"),
                   as_of: str = typer.Option(..., "--as-of"),
                   parameters: Path = typer.Option(Path("config/research/observation-v1.json"), "--parameters"),
                   store: Path = typer.Option(Path("data/private/research-v1/research.duckdb"), "--store"),
                   output: Path = typer.Option(Path("reports/private/research-v1"), "--output"),
                   watch: list[str] = typer.Option([], "--watch")) -> None:
    from astock.reports.research import publish
    try:
        destination = private_path(get_project_root(), output, output=True)
        research, snapshot = compute(bundle, as_of, parameters, store, watch)
        run_id = research.save_report(snapshot)
        publish(snapshot, destination)
        typer.echo(f"OBSERVATION_ONLY run={run_id}; screened={len(snapshot['candidates'])}; manual={len(snapshot['manual_cards'])}; private output saved")
    except Exception:
        typer.echo("Research report: FAIL (private details suppressed; no orders)")
        raise typer.Exit(1) from None


@app.command("market")
def market_command(bundle: str = typer.Option(..., "--bundle"),
                   as_of: str = typer.Option(..., "--as-of"),
                   parameters: Path = typer.Option(Path("config/research/observation-v1.json"), "--parameters"),
                   store: Path = typer.Option(Path("data/private/research-v1/research.duckdb"), "--store")) -> None:
    try:
        _, snapshot = compute(bundle, as_of, parameters, store, [])
        market = snapshot["market"]
        typer.echo(f"WATCHLIST_ONLY stocks={market['requested_stocks']}; breadth_n={market['breadth_denominator']}; ma_n={market['ma_denominator']}; UNCLASSIFIED")
        typer.echo("Full metrics belong to private report; no all-market inference.")
    except Exception:
        typer.echo("Research market: FAIL (safe details only)")
        raise typer.Exit(1) from None


@app.command("screen")
def screen_command(bundle: str = typer.Option(..., "--bundle"),
                   as_of: str = typer.Option(..., "--as-of"),
                   parameters: Path = typer.Option(Path("config/research/observation-v1.json"), "--parameters"),
                   store: Path = typer.Option(Path("data/private/research-v1/research.duckdb"), "--store")) -> None:
    try:
        _, snapshot = compute(bundle, as_of, parameters, store, [])
        typer.echo(f"OBSERVATION_ONLY screened={len(snapshot['candidates'])}; excluded={len(snapshot['excluded'])}; details in private report")
    except Exception:
        typer.echo("Research screen: FAIL (safe details only)")
        raise typer.Exit(1) from None


@app.command("journal-add")
def journal_add(event: Path = typer.Option(..., "--event"),
                store: Path = typer.Option(Path("data/private/research-v1/research.duckdb"), "--store")) -> None:
    from astock.research.journal import append_event
    try:
        append_event(store_at(store), event)
        typer.echo("Manual journal: appended/idempotent; private; no broker operation")
    except Exception:
        typer.echo("Manual journal: FAIL (private details suppressed)")
        raise typer.Exit(1) from None


@app.command("legacy-bundle")
def legacy_bundle(start: str = typer.Option(..., "--start"), end: str = typer.Option(..., "--end"),
                  code: list[str] = typer.Option(..., "--code"),
                  output: Path = typer.Option(..., "--output")) -> None:
    """Validate retained originals read-only and describe an explicit observation window."""
    from astock.research.core import day
    from astock.research.legacy import make_bundle
    try:
        root = get_project_root()
        result = make_bundle(root, private_path(root, output), day(start), day(end), code)
        typer.echo(f"Retained-source bundle: {len(result['files'])} files; CURRENT_OBSERVATION; zero HTTP")
    except Exception:
        typer.echo("Retained-source adapter: FAIL (private evidence details suppressed)")
        raise typer.Exit(1) from None


@app.command('capture')
def capture_command(plan: Path = typer.Option(Path('config/research/acquisition-proposal.json'), '--plan'),
                    live: bool = typer.Option(False, '--live'),
                    approval: Path | None = typer.Option(None, '--approval')) -> None:
    """Show the exact bounded plan; --live additionally requires a matched human approval."""
    from astock.research.acquisition import capture
    try:
        result = capture(get_project_root(), plan, live=live, approval_file=approval)
        typer.echo(encoded(result).decode())
        if result.get('stopped'):
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        typer.echo('Research capture: FAIL (safe summary; no implicit retries)')
        raise typer.Exit(1) from None


@app.command('capture-import')
def capture_import(capture_dir: Path = typer.Option(..., '--capture-dir')) -> None:
    """Validate retained complete responses and import directly into a private store."""
    from astock.research.acquisition import disk_bytes, read_capture
    from astock.research.core import digest, require
    from astock.research.tushare import make_capture_bundle
    try:
        destination = private_path(get_project_root(), capture_dir)
        plan, _ = read_capture(destination)
        # Conservative peak allowance for pilot DB/retained bytes and metadata.
        require(disk_bytes(destination) + plan.max_total_body_bytes + 32 * 1024**2 <= plan.max_added_disk_bytes,
                'CAPTURE_IMPORT_PEAK_BUDGET')
        manifest = make_capture_bundle(destination)
        bundle = destination / f'{digest(manifest)}.bundle.json'
        bid = ResearchStore(destination / 'research.duckdb').import_bundle(bundle)
        require(disk_bytes(destination) <= plan.max_added_disk_bytes, 'CAPTURE_IMPORT_DISK_BUDGET')
        typer.echo(f'CURRENT_OBSERVATION bundle={bid}; retained response adapter; no network')
    except Exception:
        typer.echo('Research capture import: FAIL (private details suppressed)')
        raise typer.Exit(1) from None


@app.command('capture-status')
def capture_status_command(capture_dir: Path = typer.Option(..., '--capture-dir')) -> None:
    """Read terminal states and never-issued member IDs without fetching or resetting."""
    from astock.research.acquisition import capture_status
    try:
        typer.echo(encoded(capture_status(private_path(get_project_root(), capture_dir))).decode())
    except Exception:
        typer.echo('Research capture status: FAIL (safe summary only)')
        raise typer.Exit(1) from None
