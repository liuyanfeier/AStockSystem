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
        if result.get('stopped') or result.get('failed_this_run', 0) or result.get('unknown_this_run', 0):
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        typer.echo('Research capture: FAIL (safe summary; no implicit retries)')
        raise typer.Exit(1) from None


@app.command('capture-import')
def capture_import(capture_dir: Path = typer.Option(..., '--capture-dir'),
                   include_capture: list[Path] = typer.Option([], '--include-capture'),
                   benchmark_bundle: Path | None = typer.Option(None, '--benchmark-bundle')) -> None:
    """Validate retained complete responses and import directly into a private store."""
    from astock.research.acquisition import disk_bytes, read_capture
    from astock.research.core import digest, require
    from astock.research.tushare import make_capture_bundle
    try:
        destination = private_path(get_project_root(), capture_dir)
        supplemental = [private_path(get_project_root(), p) for p in include_capture]
        plan, _ = read_capture(destination)
        # Conservative peak allowance for pilot DB/retained bytes and metadata.
        require(disk_bytes(destination) + plan.max_total_body_bytes + 32 * 1024**2 <= plan.max_added_disk_bytes,
                'CAPTURE_IMPORT_PEAK_BUDGET')
        require(sum(disk_bytes(p) for p in supplemental) + disk_bytes(destination) +
                plan.max_total_body_bytes + 32 * 1024**2 <= plan.max_added_disk_bytes,
                'CAPTURE_MERGED_IMPORT_PEAK_BUDGET')
        manifest = make_capture_bundle(destination, supplemental_captures=supplemental,
                                       benchmark_bundle=private_path(get_project_root(), benchmark_bundle) if benchmark_bundle else None)
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


@app.command('radar')
def radar_command(bundle: str = typer.Option(..., '--bundle'), as_of: str = typer.Option(..., '--as-of'),
                  store: Path = typer.Option(Path('data/private/research-v1/research.duckdb'), '--store'),
                  parameters: Path = typer.Option(Path('config/research/observation-v1.json'), '--parameters'),
                  output: Path = typer.Option(Path('reports/private/research-v1/radar'), '--output'),
                  component: list[str] = typer.Option([], '--component'),
                  revisions: Path | None = typer.Option(None, '--revisions'),
                  public_output: Path | None = typer.Option(None, '--public-output')) -> None:
    """Shared Store/features/screening, with market and current-industry breadth."""
    from astock.features.market import ObservationParameters
    from astock.research.service import analyze
    from astock.reports.research import publish
    try:
        root = get_project_root()
        research = store_at(store)
        params = ObservationParameters.model_validate(read_json(parameters))
        snapshot = analyze(research, bundle, as_of, params, radar=True, components=component,
                           revisions=read_json(revisions) if revisions else None)
        run = research.save_report(snapshot)
        publish(snapshot, private_path(root, output, output=True))
        if public_output:
            from astock.research.public_results import publish_public
            public_run = publish_public(snapshot, root, public_output)
            typer.echo(f'Public business projection={public_run}; personal records excluded')
        typer.echo(f'OBSERVATION_ONLY radar={run}; scope={snapshot["radar"]["scope"]}; zero market calls')
    except Exception:
        typer.echo('Research radar: FAIL (private details suppressed; no orders)')
        raise typer.Exit(1) from None


@app.command('company')
def company_command(market: Path = typer.Option(..., '--market'),
                    store: Path = typer.Option(..., '--store'),
                    catalog: Path = typer.Option(..., '--catalog'),
                    documents: Path = typer.Option(..., '--documents'),
                    policy: Path = typer.Option(Path('config/research/company-priority-v1.json'), '--policy'),
                    output: Path = typer.Option(..., '--output')) -> None:
    """Build sourced company cards from an existing fixed market snapshot; zero HTTP/orders."""
    from astock.company.models import ResearchCatalog
    from astock.company.workflow import build, publish, shortlist, verified_market_context
    from astock.research.core import require
    try:
        root = get_project_root().resolve()
        target = output.absolute()
        require(not any(p.is_symlink() for p in (target, *target.parents)), 'COMPANY_OUTPUT_SYMLINK')
        require(target.resolve().is_relative_to(root / 'docs/research/results'), 'COMPANY_PUBLIC_OUTPUT_PATH')
        require(documents.resolve().is_relative_to(root / 'data/private/research-v3'), 'COMPANY_PRIVATE_DOCUMENT_PATH')
        snapshot = read_json(market)
        evidence = ResearchCatalog.model_validate(read_json(catalog))
        members = verified_market_context(snapshot, store_at(store))
        selection = shortlist(snapshot, members, read_json(policy))
        report = build(snapshot, selection, evidence, documents)
        run = publish(report, target)
        typer.echo(f'COMPANY_OBSERVATION_ONLY run={run}; cards={len(report["cards"])}; no HTTP/orders')
    except Exception:
        typer.echo('Company research: FAIL (safe details only; no HTTP/orders)')
        raise typer.Exit(1) from None


@app.command('daily')
def daily_command(profile: Path = typer.Option(..., '--profile'),
                  check: bool = typer.Option(False, '--check')) -> None:
    """Run the existing offline close from one profile; no implicit dates or HTTP."""
    from astock.decision.daily import load_daily_profile
    try:
        resolved, instruction = load_daily_profile(get_project_root(), profile)
    except Exception:
        typer.echo('日常配置检查失败：请检查配置版本、路径、文件和真实/模拟模式；未运行收盘流程。')
        raise typer.Exit(1) from None
    typer.echo(f'固定观察时间：{instruction.observed_at}；要求行情日：{instruction.required_market_date}；模式：{instruction.mode}')
    if check:
        typer.echo('配置检查通过；仅读取配置和路径，尚未核验行情内容；未创建Journal或报告。')
        return
    decision_close(**resolved.close_options())
    typer.echo('离线研究摘要已生成；未获取新行情，固定旧输入不代表当日更新。')


@app.command('decision-close')
def decision_close(run: Path = typer.Option(..., '--run'),
                   previous: Path = typer.Option(..., '--previous'),
                   latest: Path = typer.Option(..., '--latest'),
                   documents: Path = typer.Option(..., '--documents'),
                   baseline_market: Path = typer.Option(..., '--baseline-market'),
                   bundle: str = typer.Option(..., '--bundle'),
                   store: Path = typer.Option(..., '--store'),
                   journal_store: Path = typer.Option(..., '--journal-store'),
                   output: Path = typer.Option(..., '--output'),
                   parameters: Path = typer.Option(Path('config/research/observation-v1.json'), '--parameters'),
                   component: list[str] = typer.Option([], '--component'),
                   component_store: list[Path] = typer.Option([], '--component-store'),
                   revisions: Path | None = typer.Option(None, '--revisions'),
                   position_scope: Path | None = typer.Option(None, '--position-scope'),
                   public_output: Path | None = typer.Option(None, '--public-output')) -> None:
    """Repeatable offline close: verified market + research changes + private manual journal."""
    from astock.features.market import ObservationParameters
    from astock.decision.models import RunInput, PositionScope
    from astock.decision.increment import market_context
    from astock.decision.workflow import compare, persist, verified_catalog
    from astock.decision.portfolio import portfolio_report
    from astock.decision.report import publish_private, publish_public
    from astock.research.core import require
    try:
        root = get_project_root().resolve()
        instruction = RunInput.model_validate(read_json(run))
        from datetime import datetime, timezone
        from astock.research.core import instant
        require(instruction.mode=='OFFLINE_SIMULATION' or instant(instruction.observed_at)<=datetime.now(timezone.utc), 'DECISION_REAL_OBSERVATION_IN_FUTURE')
        mode_dir = 'real' if instruction.mode == 'REAL_EVIDENCE' else 'simulated'
        allowed_journal = root/'data/private/research-v1/decision-loop-v0'/mode_dir
        require(private_path(root,journal_store).is_relative_to(allowed_journal), 'DECISION_JOURNAL_MODE_PATH')
        require(documents.resolve().is_relative_to(root/'data/private/research-v3'), 'DECISION_DOCUMENT_PATH')
        require(not any(p.is_symlink() for p in (documents.absolute(),*documents.absolute().parents)), 'DECISION_DOCUMENT_SYMLINK')
        require(len(component)==len(component_store), 'DECISION_COMPONENT_STORE_COUNT')
        require(len(set(component))==len(component), 'DECISION_DUPLICATE_COMPONENT')
        owners = {b:store_at(p) for b,p in zip(component,component_store)}
        market,members = market_context(store_at(store),bundle,instruction.observed_at,
                                       ObservationParameters.model_validate(read_json(parameters)),component,owners,
                                       read_json(revisions) if revisions else None)
        old = verified_catalog(read_json(previous),documents)
        new = verified_catalog(read_json(latest),documents)
        from astock.company.workflow import verified_market_context
        baseline=read_json(baseline_market)
        baseline_owner=owners.get(baseline['bundle_id'],store_at(store))
        verified_market_context(baseline,baseline_owner)
        report = compare(instruction,old,new,market,members,baseline)
        journal = store_at(journal_store)
        destination = private_path(root,output,output=True)
        scope = PositionScope.model_validate(read_json(private_path(root,position_scope))) if position_scope else None
        require(scope is None or scope.mode == ('USER_MANUAL' if instruction.mode=='REAL_EVIDENCE' else 'SIMULATED'), 'DECISION_SIMULATED_ACCOUNT_BOUNDARY')
        journal.initialize()
        portfolio=portfolio_report(journal,market,report,scope)
        persist(report,journal,destination/'events')
        report['portfolio']=portfolio
        key=publish_private(report,destination)
        if public_output:publish_public(report,root,public_output)
        typer.echo(f'DECISION_LOOP_V0 mode={instruction.mode}; run={key}; no HTTP/orders; private portfolio separated')
    except Exception:
        typer.echo('Decision close: FAIL (private details suppressed; no HTTP/orders)')
        raise typer.Exit(1) from None
