"""Plans, prioritized tasks and explicit recovery use private synthetic workspaces."""
from copy import deepcopy
from datetime import timedelta
import json

import pytest
from typer.testing import CliRunner

from astock.cli.main import app
from astock.decision import attempts, plans
from astock.decision.application import run_close
from astock.decision.daily import DailyObservation, load_daily_profile
from astock.decision.plan_models import PlanDraft, PlanInput
from astock.decision.report import markdown, public_projection
from astock.research.core import digest, encoded, read_json
from astock.portfolio import manual
from test_manual_workflow import workspace, close, request, rows
from test_daily_profile import daily_case


@pytest.fixture
def controls(workspace, monkeypatch):
    import astock.cli.workflow as cli
    import astock.decision.increment as increment
    root, path, profile, clock = workspace
    for name in ('previous', 'latest'):
        target = root / profile[name]
        value = read_json(target)
        source = deepcopy(value['sources'][0]); source.update(id='s2', code='600000.SH')
        company = deepcopy(value['companies'][0]); company['code'] = '600000.SH'
        for section in ('profile', 'events', 'support', 'counter', 'unknowns'):
            for statement in company[section]:
                for reference in statement.get('references', []):
                    reference['source_id'] = 's2'
        for figure in company['financials']:
            figure['reference']['source_id'] = 's2'
        value['sources'].append(source); value['companies'].append(company)
        target.write_bytes(encoded(value))
    (root / profile['documents'] / 's2.pdf').write_bytes(b'%PDF-mock')
    baseline = read_json(root / profile['baseline_market'])
    other = deepcopy(baseline['features'][0]); other.update(code='600000.SH', name='合成第二家公司')
    baseline['features'].append(other)
    (root / profile['baseline_market']).write_bytes(encoded(baseline))
    run = read_json(root / profile['run'])
    run['plans'][0].update(baseline_market_hash=digest(baseline),
                           baseline_catalog_hash=digest(read_json(root / profile['previous'])))
    (root / profile['run']).write_bytes(encoded(run))
    market = deepcopy(baseline); market['window_end'] = '2026-10-13'
    for feature in market['features']:
        feature['last_date'] = '2026-10-13'
    monkeypatch.setattr(increment, 'market_context', lambda *a, **k: (market, []))
    # This boundary is exercised without substitution by the native integration test.
    monkeypatch.setattr(plans, 'verify_retained_market_anchor', lambda *a, **k: None)
    monkeypatch.setattr(cli, 'get_project_root', lambda: root)
    return workspace


def plan_request(case, identifier, action='CREATE', code='600000.SH', **changes):
    root, path, _, clock = case
    draft = PlanDraft(thesis='SYNTHETIC PRIVATE research thesis', attention_reason='SYNTHETIC reason',
        no_trade_reasons=['未核实估值'], observable_checks=['核对下一份收入原表'],
        invalidation_conditions=['收入逻辑被推翻'],
        criteria=[dict(id='income', metric_id='revenue', expectation='NOT_LOWER', reason='合成收入检查')],
        review_due=clock[0] + timedelta(days=7)) if action == 'CREATE' else None
    return PlanInput(**{**dict(request_id=identifier, mode='SIMULATED', action=action, code=code,
        expected_plan_hash=plans.preview_plans(root, path)['plan_hash'], reason='SYNTHETIC PRIVATE operation', draft=draft), **changes})


def save(case, value):
    root, path, _, _ = case
    return plans.record_plan_input(root, path, value)


def test_create_plan_reaches_next_brief_without_editing_frozen_inputs(controls):
    root, path, profile, clock = controls
    before = {name: (root / profile[name]).read_bytes() for name in ('run', 'previous', 'latest', 'baseline_market')}
    value = plan_request(controls, 'new')
    receipt = save(controls, value)
    report = close(controls).report
    card = next(c for c in report['cards'] if c['code'] == '600000.SH')
    assert card['plan']['thesis'] == value.draft.thesis
    assert card['plan']['created_at'] == clock[0].isoformat()
    assert card['state'] == 'CONTINUE_WATCH' and not card['trade_eligible'] and card['order'] is None
    assert receipt['orders_created'] == 0 and report['research_inputs'][0]['request_id'] == 'new'
    assert '600000.SH' not in encoded(public_projection(report)).decode()
    assert 'SYNTHETIC PRIVATE' not in encoded(public_projection(report)).decode()
    assert before == {name: (root / profile[name]).read_bytes() for name in before}
    assert len(close(controls, at=clock[0] - timedelta(seconds=1)).report['cards']) == 1


def test_request_id_conflict_preview_and_atomic_failure_preserve_records(controls, monkeypatch):
    root, path, _, clock = controls
    value = plan_request(controls, 'create')
    stale = plan_request(controls, 'end', 'END_WATCH', '600036.SH')
    receipt = save(controls, value)
    before = rows(controls)
    assert save(controls, value) == receipt
    with pytest.raises(ValueError, match='REQUEST_ID_CONFLICT'):
        save(controls, value.model_copy(update={'reason': 'different'}))
    clock[0] += timedelta(minutes=1)
    with pytest.raises(ValueError, match='PREVIEW_CHANGED'):
        save(controls, stale)
    assert rows(controls) == before
    append = plans.append_events_in_transaction
    def broken(db, events):
        append(db, events)
        raise OSError('SYNTHETIC PRIVATE fault')
    monkeypatch.setattr(plans, 'append_events_in_transaction', broken)
    end = plan_request(controls, 'retry', 'END_WATCH', '600000.SH')
    with pytest.raises(OSError):
        save(controls, end)
    assert rows(controls) == before and plans.existing_plan_input(root, path, 'retry') is None
    monkeypatch.setattr(plans, 'append_events_in_transaction', append)
    assert save(controls, end)['action'] == 'END_WATCH'


def test_end_watch_keeps_holding_risk_and_restart_creates_new_plan(controls):
    root, path, _, clock = controls
    original = plans.preview_plans(root, path)['plans'][0]['plan']
    manual.record_manual_input(root, path, request(controls, 'holding', shares=200))
    save(controls, plan_request(controls, 'end', 'END_WATCH', '600036.SH'))
    ended = close(controls).report
    assert ended['cards'][0]['state'] == 'END_WATCH'
    assert ended['portfolio']['positions'][0]['shares'] == 200
    todo = next(t for t in ended['decision_items']['items'] if t['code'] == '600036.SH')
    assert todo['priority'] == 0 and any('已结束' in reason for reason in todo['reasons'])
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, request(controls, 'note', 'NOTE', note='已阅'))
    assert close(controls).report['cards'][0]['state'] == 'END_WATCH'
    clock[0] += timedelta(minutes=1)
    save(controls, plan_request(controls, 'restart', code='600036.SH'))
    restarted = close(controls).report
    assert restarted['cards'][0]['plan']['created_at'] != original['created_at']
    assert restarted['cards'][0]['state'] == 'CONTINUE_WATCH'
    assert restarted['portfolio']['positions'][0]['shares'] == 200
    assert len(plans.preview_plans(root, path)['plans']) == 1


def test_missing_current_review_uses_old_times_and_remains_unknown(controls):
    root, _, profile, clock = controls
    save(controls, plan_request(controls, 'new'))
    target = root / profile['latest']; catalog = read_json(target)
    catalog['companies'] = [c for c in catalog['companies'] if c['code'] != '600000.SH']
    catalog['sources'] = [s for s in catalog['sources'] if s['code'] != '600000.SH']
    target.write_bytes(encoded(catalog))
    report = close(controls).report
    card = next(c for c in report['cards'] if c['code'] == '600000.SH')
    assert card['retained_baseline_only'] and card['state'] == 'WAIT_EVIDENCE'
    assert card['hypothesis_state'] == 'UNKNOWN' and card['checks'][0]['state'] == 'UNKNOWN'
    assert card['sources'][0]['available_at'] == read_json(root / profile['previous'])['sources'][1]['available_at']
    clock[0] += timedelta(minutes=1)
    with pytest.raises(ValueError, match='LATEST_REVIEW_REQUIRED'):
        save(controls, plan_request(controls, 'review', 'REVIEW_EVIDENCE'))


def test_review_acknowledgement_is_bound_to_exact_catalog_version(controls):
    root, _, profile, clock = controls
    first_run = read_json(root / profile['run'])
    first_run['simulation_events'] = [dict(code='600036.SH', criterion_id='growth',
        state='INVALIDATION_REVIEW', explanation='合成反证', available_at=clock[0].isoformat(),
        provenance='OFFLINE_SIMULATION_NOT_DISCLOSURE')]
    (root / profile['run']).write_bytes(encoded(first_run))
    assert close(controls).report['cards'][0]['state'] == 'INVALIDATION_REVIEW'
    clock[0] += timedelta(minutes=1)
    first_run['simulation_events'] = []
    (root / profile['run']).write_bytes(encoded(first_run))
    save(controls, plan_request(controls, 'review', 'REVIEW_EVIDENCE', '600036.SH'))
    assert close(controls).report['cards'][0]['state'] == 'CONTINUE_WATCH'
    clock[0] += timedelta(minutes=1)
    target = root / profile['latest']; catalog = read_json(target)
    catalog['companies'][0]['counter'][0]['text'] = '新的合成未决风险'
    target.write_bytes(encoded(catalog))
    report = close(controls).report
    assert report['cards'][0]['state'] == 'WAIT_EVIDENCE'
    assert report['cards'][0]['manual_action'] is None


def test_unknown_company_metric_and_wrong_mode_are_rejected(controls):
    root, _, profile, _ = controls
    with pytest.raises(ValueError, match='PROFILE_MODE'):
        save(controls, plan_request(controls, 'mode', mode='USER_MANUAL'))
    assert not (root / profile['journal_store']).exists()
    with pytest.raises(ValueError, match='COMPANY_EVIDENCE_REQUIRED'):
        save(controls, plan_request(controls, 'unknown', code='999999.SH'))
    value = plan_request(controls, 'metric')
    value.draft.criteria[0].metric_id = 'not_in_source'
    with pytest.raises(ValueError, match='METRIC_REQUIRED'):
        save(controls, value)
    assert rows(controls) == []


def test_plan_wizard_cancel_save_and_duplicate(controls):
    _, path, profile, clock = controls
    runner = CliRunner()
    args = ['research', 'plan', '--profile', str(path), '--request-id', 'wizard-plan']
    result = runner.invoke(app, args, input='2\n600036.SH\n合成结束理由\nn\n')
    assert result.exit_code == 0 and '已取消' in result.output
    result = runner.invoke(app, args, input='2\n600036.SH\n合成结束理由\ny\n')
    assert result.exit_code == 0, result.output
    before = rows(controls)
    result = runner.invoke(app, args, input='')
    assert result.exit_code == 0 and '重复调用没有新增' in result.output
    assert rows(controls) == before


def test_todos_consolidate_risk_and_notes_do_not_close_them(controls, monkeypatch):
    import astock.decision.todos as todos
    root, path, profile, clock = controls
    manual.record_manual_input(root, path, request(controls, 'position', shares=200))
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, request(controls, 'trade', 'EXECUTION',
        shares=100, side='SELL', price_cny='11'))
    report = close(controls).report
    own = [i for i in report['decision_items']['items'] if i['code'] == '600036.SH']
    assert len(own) == 1 and own[0]['priority'] == 0
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, request(controls, 'read', 'NOTE', note='已阅'))
    assert next(i for i in close(controls).report['decision_items']['items'] if i['code'] == '600036.SH')['id'] == own[0]['id']
    policy = todos.workflow_policy().model_copy(update={'visible_todo_limit': 1})
    monkeypatch.setattr(todos, 'workflow_policy', lambda: policy)
    result = close(controls).report
    assert result['decision_items']['total'] > 1 and len(result['decision_items']['items']) > 1
    assert '项保存在同名私有JSON' in markdown(result)
    assert 'decision_items' not in public_projection(result)


def test_partial_markdown_failure_resumes_exact_observation_without_rewriting_json(controls, monkeypatch):
    import astock.decision.report as publication
    root, path, profile, clock = controls
    render = publication.markdown
    monkeypatch.setattr(publication, 'markdown', lambda *a, **k: (_ for _ in ()).throw(OSError('SYNTHETIC PRIVATE secret')))
    with pytest.raises(attempts.DailyRunFailure) as failure:
        close(controls)
    identifier = failure.value.attempt_id
    assert failure.value.stage == 'PUBLISH' and failure.value.receipt_saved
    failed = attempts.attempt_status(root, path, identifier)[0]
    assert failed['state'] == 'FAILED' and failed['stage'] == 'PUBLISH'
    before = {p.name: p.read_bytes() for p in (root / profile['output']).glob('*.json')}
    assert len(before) == 1
    assert not list((root / profile['output']).glob('*.md'))
    receipts = b''.join(p.read_bytes() for p in (root / profile['output'] / 'attempts' / identifier).glob('*.json'))
    assert b'SYNTHETIC PRIVATE' not in receipts
    monkeypatch.setattr(publication, 'markdown', render)
    observation = attempts.resume_observation(root, path, identifier)
    resolved, _ = load_daily_profile(root, path)
    recovered = run_close(root, resolved, observation, resumes_attempt_id=identifier)
    assert recovered.report_id + '.json' in before
    assert recovered.json_path.read_bytes() == before[recovered.json_path.name]
    assert recovered.markdown_path.exists()
    assert attempts.attempt_status(root, path, recovered.attempt_id)[0]['resumes_attempt_id'] == identifier
    assert recovered.report['as_of'] == observation.observed_at.isoformat()


def test_persist_partial_failure_is_idempotent_on_resume(controls, monkeypatch):
    import astock.decision.workflow as workflow
    root, path, _, _ = controls
    append = workflow.append_event
    def one_then_fail(*args):
        append(*args)
        raise OSError('SYNTHETIC persist failure')
    monkeypatch.setattr(workflow, 'append_event', one_then_fail)
    with pytest.raises(attempts.DailyRunFailure) as failure:
        close(controls)
    assert failure.value.stage == 'PERSIST'
    before = rows(controls)
    monkeypatch.setattr(workflow, 'append_event', append)
    observation = attempts.resume_observation(root, path, failure.value.attempt_id)
    resolved, _ = load_daily_profile(root, path)
    result = run_close(root, resolved, observation, resumes_attempt_id=failure.value.attempt_id)
    assert all(row in rows(controls) for row in before)
    count = len(rows(controls))
    assert run_close(root, resolved, observation).report_id == result.report_id
    assert len(rows(controls)) == count


def test_resume_rejects_changed_input_or_engine_and_status_needs_no_source(controls, monkeypatch):
    root, path, profile, _ = controls
    result = close(controls)
    monkeypatch.setattr(attempts, 'engine_fingerprint', lambda: '0' * 64)
    with pytest.raises(ValueError, match='ENGINE_CHANGED'):
        attempts.resume_observation(root, path, result.attempt_id)
    params = root / profile['parameters']; value = read_json(params); value['version'] = 'changed'
    params.write_bytes(encoded(value))
    with pytest.raises(ValueError, match='INPUT_CHANGED'):
        attempts.resume_observation(root, path, result.attempt_id)
    (root / profile['store']).unlink()  # This fixture's explicit synthetic placeholder.
    status = CliRunner().invoke(app, ['research', 'daily-status', '--profile', str(path)])
    assert status.exit_code == 0 and 'SUCCEEDED' in status.output


def test_interrupted_receipt_is_unknown_and_status_is_read_only(controls):
    root, path, profile, _ = controls
    resolved, instruction = load_daily_profile(root, path)
    start = attempts.start_attempt(resolved, instruction)
    before = {p: p.read_bytes() for p in resolved.output.rglob('*') if p.is_file()}
    status = attempts.attempt_status(root, path, start.attempt_id)[0]
    assert status['state'] == 'RUNNING_OR_INTERRUPTED'
    assert before == {p: p.read_bytes() for p in resolved.output.rglob('*') if p.is_file()}
    assert not (root / profile['journal_store']).exists()
    with pytest.raises(ValueError, match='ATTEMPT_ID'):
        attempts.attempt_status(root, path, '../elsewhere')


def test_attempt_symlink_and_tampered_binding_fail_closed(controls, tmp_path):
    root, path, profile, _ = controls
    result = close(controls)
    output = root / profile['output']
    terminal = output / 'attempts' / result.attempt_id / 'result.json'
    value = read_json(terminal); value['start_hash'] = '0' * 64; terminal.write_bytes(encoded(value))
    with pytest.raises(ValueError, match='BINDING'):
        attempts.attempt_status(root, path, result.attempt_id)
    missing_id = 'a' * 32
    (output / 'attempts' / missing_id).symlink_to(tmp_path)
    with pytest.raises(ValueError, match='SYMLINK'):
        attempts.attempt_status(root, path, missing_id)


def test_resume_detects_a_legacy_backdated_fact_without_resetting_it(controls):
    from astock.research.journal import JournalEvent, append_events
    from astock.research.store import ResearchStore
    root, path, profile, clock = controls
    report = close(controls)
    value = JournalEvent(event_id='legacy-late-fact', kind='POSITION', code='600036.SH', shares=100,
                         event_at=clock[0] - timedelta(minutes=1), recorded_at=clock[0])
    append_events(ResearchStore(root / profile['journal_store']), [value])
    before = rows(controls)
    with pytest.raises(ValueError, match='JOURNAL_CHANGED'):
        attempts.resume_observation(root, path, report.attempt_id)
    assert rows(controls) == before
