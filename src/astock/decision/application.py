"""One offline close application service for CLI, reports and future interfaces."""
from dataclasses import dataclass
from pathlib import Path

from astock.company import workflow as company_workflow
from astock.decision.daily import DailyObservation, DailyProfile, resolve_daily_profile
from astock.decision import increment as market_increment
from astock.decision.portfolio import portfolio_report
from astock.decision.report import publish_private
from astock.decision.workflow import compare, persist, verified_catalog
from astock.features.market import ObservationParameters
from astock.portfolio.manual import resolve_position_scope
from astock.portfolio.models import PositionScope
from astock.research.core import digest, read_json
from astock.research.journal import journal_snapshot
from astock.research.store import ResearchStore


@dataclass(frozen=True)
class DailyResult:
    report_id: str
    report: dict
    json_path: Path
    markdown_path: Path


def run_close(root: Path, request: DailyProfile,
              observation: DailyObservation | None = None) -> DailyResult:
    profile, instruction = resolve_daily_profile(root, request, observation)
    primary = ResearchStore(profile.store)
    owners = {item.bundle: ResearchStore(item.store) for item in profile.components}
    parameters = ObservationParameters.model_validate(read_json(profile.parameters))
    market, members = market_increment.market_context(primary, profile.bundle, instruction.observed_at, parameters,
                                     [item.bundle for item in profile.components], owners,
                                     read_json(profile.revisions) if profile.revisions else None)
    old = verified_catalog(read_json(profile.previous), profile.documents)
    new = verified_catalog(read_json(profile.latest), profile.documents)
    baseline = read_json(profile.baseline_market)
    company_workflow.verified_market_context(baseline, owners.get(baseline['bundle_id'], primary))
    report = compare(instruction, old, new, market, members, baseline)
    journal = ResearchStore(profile.journal_store)
    fallback = PositionScope.model_validate(read_json(profile.position_scope)) if profile.position_scope else None
    journal.initialize()
    scope = resolve_position_scope(journal, instruction.observed_at, instruction.mode, fallback)
    portfolio = portfolio_report(journal, market, report, scope)
    manual = journal_snapshot(journal, instruction.observed_at, {})
    report['manual_records'] = [dict(receipt_id=e['event_id'], recorded_at=e['recorded_at'],
                                    **e['manual_input']) for e in manual['events'] if e.get('manual_input')]
    report['pending_position_reconciliation'] = manual['unreconciled_trades']
    report['baseline_verification'] = dict(
        baseline_hash=digest(baseline), original_code_hash=baseline.get('code_hash'),
        current_code_hash=market.get('code_hash'),
        method='Recompute all public business fields; require exact retained original anchor when execution metadata differs')
    persist(report, journal, profile.output / 'events')
    report['portfolio'] = portfolio
    key = publish_private(report, profile.output)
    return DailyResult(key, report, profile.output / f'{key}.json', profile.output / f'{key}.md')
