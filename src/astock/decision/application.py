"""One offline close application service for CLI, reports and future interfaces."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from astock.company import workflow as company_workflow
from astock.decision.daily import DailyObservation, DailyProfile, resolve_daily_profile
from astock.decision import increment as market_increment
from astock.decision.portfolio import portfolio_report
from astock.decision.report import publish_private
from astock.decision.workflow import attach_prior_observations, compare, persist, verified_catalog
from astock.decision.attempts import DailyRunFailure, Stage, finish_attempt, start_attempt
from astock.decision.models import RunInput
from astock.decision.plans import resolve_plan_run, retained_catalog
from astock.decision.todos import decision_items
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
    attempt_id: str


def run_close(root: Path, request: DailyProfile,
              observation: DailyObservation | None = None,
              resumes_attempt_id: str | None = None) -> DailyResult:
    profile, instruction = resolve_daily_profile(root, request, observation)
    try:
        attempt = start_attempt(profile, instruction, resumes_attempt_id)
    except Exception:
        raise DailyRunFailure(None, 'START', False) from None
    stage: Stage = 'MARKET'
    try:
        def progress(value: Stage) -> None:
            nonlocal stage
            stage = value
        result = _execute_close(profile, instruction, progress, attempt.attempt_id)
        stage = 'RECEIPT'
        finish_attempt(profile, attempt, 'DONE', report_id=result.report_id)
        return result
    except Exception as error:
        saved = False
        try:
            finish_attempt(profile, attempt, stage, error=error)
            saved = True
        except Exception:
            pass
        raise DailyRunFailure(attempt.attempt_id, stage, saved) from None


def _execute_close(profile: DailyProfile, instruction: RunInput, progress: Callable[[Stage], None],
                   attempt_id: str) -> DailyResult:
    primary = ResearchStore(profile.store)
    owners = {item.bundle: ResearchStore(item.store) for item in profile.components}
    parameters = ObservationParameters.model_validate(read_json(profile.parameters))
    market, members = market_increment.market_context(primary, profile.bundle, instruction.observed_at, parameters,
                                     [item.bundle for item in profile.components], owners,
                                     read_json(profile.revisions) if profile.revisions else None)
    progress('EVIDENCE')
    old = verified_catalog(read_json(profile.previous), profile.documents)
    new = verified_catalog(read_json(profile.latest), profile.documents)
    progress('BASELINE')
    baseline = read_json(profile.baseline_market)
    company_workflow.verified_market_context(baseline, owners.get(baseline['bundle_id'], primary))
    journal = ResearchStore(profile.journal_store)
    progress('PLANS')
    instruction, plan_records = resolve_plan_run(journal, instruction, old, new, baseline)
    effective_catalog, retained = retained_catalog(old, new, {p.code for p in instruction.plans})
    progress('DECISIONS')
    report = compare(instruction, old, effective_catalog, market, members, baseline)
    report['latest_reviewed_catalog_hash'] = digest(new.model_dump(mode='json'))
    report['retained_only_codes'] = sorted(retained)
    for card in report['cards']:
        if card['code'] in retained:
            card['retained_baseline_only'] = True
            for check in card['checks']:
                check.update(state='UNKNOWN', explanation='仅有基线保留材料；该对象尚无本轮复核目录',
                             evidence_class='RETAINED_BASELINE_ONLY')
            card['hypothesis_state'] = 'UNKNOWN'
            if card['state'] != 'END_WATCH':
                card.update(state='WAIT_EVIDENCE', state_text='暂停新交易，等待证据')
            card['no_trade_reasons'].append('仅有基线材料，未完成本轮研究复核')
    progress('PORTFOLIO')
    fallback = PositionScope.model_validate(read_json(profile.position_scope)) if profile.position_scope else None
    journal.initialize()
    attach_prior_observations(report, journal)
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
    progress('PERSIST')
    persist(report, journal, profile.output / 'events', attach_prior=False)
    report['portfolio'] = portfolio
    report['research_inputs'] = [dict(receipt_id=e['event_id'], recorded_at=e['recorded_at'],
                                     **e['research_input']['request']) for e in plan_records]
    report['decision_items'] = decision_items(report)
    progress('PUBLISH')
    key = publish_private(report, profile.output)
    return DailyResult(key, report, profile.output / f'{key}.json', profile.output / f'{key}.md', attempt_id)
