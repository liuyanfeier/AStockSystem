"""Manual facts reach the next private brief without inventing account state or orders."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest
from typer.testing import CliRunner

from astock.cli.main import app
from astock.data.warehouse_lock import warehouse_connection
from astock.decision.application import run_close
from astock.decision.daily import DailyObservation, load_daily_profile
from astock.decision.report import markdown, public_projection
from astock.portfolio import manual
from astock.portfolio.models import ManualInput
from astock.research.core import encoded, read_json
from astock.research.journal import JournalEvent, append_events, journal_snapshot
from astock.research.store import ResearchStore
from test_daily_profile import daily_case
from test_research_v1 import sample, PARAMS


@pytest.fixture
def workspace(daily_case, monkeypatch):
    import astock.decision.increment as increment
    import astock.company.workflow as company
    import astock.cli.manual as cli
    root, path, profile, market = daily_case
    run = read_json(root / profile['run'])
    run['mode'] = 'OFFLINE_SIMULATION'
    (root / profile['run']).write_bytes(encoded(run))
    profile['journal_store'] = 'data/private/research-v1/decision-loop-v0/simulated/manual/journal.duckdb'
    path.write_bytes(encoded(profile))
    current_market = deepcopy(market)
    current_market['window_end'] = '2026-10-13'
    current_market['features'][0]['last_date'] = '2026-10-13'
    monkeypatch.setattr(increment, 'market_context', lambda *a, **k: (current_market, []))
    monkeypatch.setattr(company, 'verified_market_context', lambda *a, **k: [])
    monkeypatch.setattr(cli, 'get_project_root', lambda: root)
    clock = [datetime(2026, 10, 14, 4, tzinfo=timezone.utc)]
    monkeypatch.setattr(manual, 'now_utc', lambda: clock[0])
    return root, path, profile, clock


def request(workspace, identifier, kind='POSITION', **values):
    root, path, _, clock = workspace
    state = manual.preview_positions(root, path)
    data = dict(request_id=identifier, mode='SIMULATED', kind=kind, code='600036.SH', event_at=clock[0])
    if kind != 'NOTE':
        data['expected_position_hash'] = state['position_hash']
    return ManualInput.model_validate({**data, **values})


def close(workspace, at=None):
    root, path, _, clock = workspace
    observation = DailyObservation(observed_at=at or clock[0] + timedelta(seconds=1),
                                   required_market_date='2026-10-13')
    profile, _ = load_daily_profile(root, path, observation)
    return run_close(root, profile, observation)


def rows(workspace):
    root, _, profile, _ = workspace
    with warehouse_connection(root / profile['journal_store'], read_only=True) as db:
        return db.execute('SELECT id,payload FROM research_journal ORDER BY id').fetchall()


def test_partial_sale_and_read_acknowledgement_reach_next_brief(workspace):
    root, path, _, clock = workspace
    before = request(workspace, 'initial', shares=200, complete_positions_confirmed=True,
                     cash_cny='1000', cash_confirmed=True, thesis='SYNTHETIC original thesis')
    manual.record_manual_input(root, path, before)
    initial = close(workspace).report
    assert initial['portfolio']['account_assets_cny'] == '3000'
    clock[0] += timedelta(minutes=1)
    sell = request(workspace, 'sell', 'EXECUTION', shares=100, side='SELL', price_cny='11.25',
                   remaining_shares=100, note='SYNTHETIC PRIVATE sale note')
    receipt = manual.record_manual_input(root, path, sell)
    assert receipt['shares_after'] == 100 and receipt['orders_created'] == 0
    after = close(workspace).report
    assert after['portfolio']['positions'][0]['shares'] == 100
    assert after['portfolio']['positions'][0]['thesis'] == 'SYNTHETIC original thesis'
    assert after['portfolio']['account_assets_cny'] is None and after['portfolio']['cash_cny'] is None
    assert '明确补录成交后 100股' in markdown(after)
    source_event = after['portfolio']['positions'][0]['source_event']
    clock[0] += timedelta(minutes=1)
    note = request(workspace, 'read', 'NOTE', note='SYNTHETIC PRIVATE 已阅，风险未解除')
    manual.record_manual_input(root, path, note)
    final = close(workspace).report
    assert final['portfolio']['positions'][0]['source_event'] == source_event
    assert final['portfolio']['account_assets_cny'] is None
    assert '已阅，风险未解除' in markdown(final)
    published = encoded(public_projection(final))
    assert b'SYNTHETIC PRIVATE' not in published and b'manual_records' not in published and b'"shares"' not in published
    assert final['cards'][0]['order'] is None and not final['cards'][0]['trade_eligible']


def test_execution_without_post_trade_snapshot_stays_pending_after_ack(workspace):
    root, path, _, clock = workspace
    manual.record_manual_input(root, path, request(workspace, 'p', shares=200))
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, request(workspace, 'e', 'EXECUTION', shares=100, side='SELL', price_cny='11'))
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, request(workspace, 'n', 'NOTE', note='已阅'))
    pending = close(workspace).report
    assert pending['portfolio']['positions'][0]['shares'] == 200
    assert pending['pending_position_reconciliation'] == ['600036.SH']
    assert '已阅不解除此待办' in markdown(pending)
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, request(workspace, 'reconcile', shares=100))
    assert close(workspace).report['pending_position_reconciliation'] == []


def test_idempotent_request_conflict_and_stale_preview_are_atomic(workspace):
    root, path, _, clock = workspace
    first = request(workspace, 'one', shares=100)
    stale = request(workspace, 'two', shares=200)
    receipt = manual.record_manual_input(root, path, first)
    saved = rows(workspace)
    clock[0] += timedelta(minutes=1)
    assert manual.record_manual_input(root, path, first) == receipt
    assert rows(workspace) == saved
    with pytest.raises(ValueError, match='REQUEST_ID_CONFLICT'):
        manual.record_manual_input(root, path, first.model_copy(update={'shares': 101}))
    with pytest.raises(ValueError, match='PREVIEW_CHANGED'):
        manual.record_manual_input(root, path, stale)
    assert rows(workspace) == saved and manual.existing_input(root, path, 'two') is None


def test_batch_failure_rolls_back_receipt_position_and_scope(workspace, monkeypatch):
    root, path, _, clock = workspace
    value = request(workspace, 'retry', shares=100)
    append = manual.append_events_in_transaction
    def fail_after_first(db, events):
        append(db, events[:1])
        raise ValueError('SYNTHETIC_FAULT')
    monkeypatch.setattr(manual, 'append_events_in_transaction', fail_after_first)
    with pytest.raises(ValueError, match='SYNTHETIC_FAULT'):
        manual.record_manual_input(root, path, value)
    assert rows(workspace) == []
    monkeypatch.setattr(manual, 'append_events_in_transaction', append)
    assert manual.record_manual_input(root, path, value)['shares_after'] == 100


def test_late_record_does_not_backfill_a_past_report(workspace):
    root, path, _, clock = workspace
    value = request(workspace, 'late', shares=100, event_at=clock[0] - timedelta(hours=2))
    manual.record_manual_input(root, path, value)
    before = close(workspace, at=clock[0] - timedelta(minutes=1)).report
    assert before['portfolio']['positions_state'] == 'UNKNOWN_NOT_EMPTY' and before['manual_records'] == []
    assert close(workspace).report['portfolio']['positions'][0]['shares'] == 100


@pytest.mark.parametrize('complete,cash,expected', [(False, None, None), (True, '0', '0')])
def test_zero_shares_only_prove_flat_with_explicit_completeness_and_cash(workspace, complete, cash, expected):
    root, path, _, _ = workspace
    value = request(workspace, 'zero', shares=0, complete_positions_confirmed=complete,
                    cash_cny=cash, cash_confirmed=cash is not None)
    manual.record_manual_input(root, path, value)
    assert close(workspace).report['portfolio']['account_assets_cny'] == expected


@pytest.mark.parametrize('case', ['mode', 'future'])
def test_wrong_mode_or_future_fact_does_not_create_journal(workspace, case):
    root, path, profile, clock = workspace
    value = request(workspace, 'invalid', shares=100,
                    **({'mode': 'USER_MANUAL'} if case == 'mode' else {'event_at': clock[0] + timedelta(days=1)}))
    with pytest.raises(ValueError):
        manual.record_manual_input(root, path, value)
    assert not (root / profile['journal_store']).exists()


def test_correction_cannot_hide_a_position_or_branch_the_correction_chain(tmp_path):
    store = ResearchStore(tmp_path / 'synthetic.duckdb')
    event = JournalEvent(event_id='p', kind='POSITION', code='600036.SH', shares=200,
                         event_at='2026-10-14T00:00:00Z', recorded_at='2026-10-14T00:00:00Z')
    append_events(store, [event])
    for kind, code in [('REVIEW', event.code), ('POSITION', '000001.SZ')]:
        changed = JournalEvent(**{**event.model_dump(), 'event_id': 'bad', 'kind': kind, 'code': code, 'correction_of': 'p'})
        with pytest.raises(ValueError, match='CORRECTION_KIND_CODE'):
            append_events(store, [changed])
    corrected = JournalEvent(**{**event.model_dump(), 'event_id': 'fix', 'shares': 150, 'correction_of': 'p'})
    append_events(store, [corrected])
    with pytest.raises(ValueError, match='ALREADY_REPLACED'):
        append_events(store, [corrected.model_copy(update={'event_id': 'branch'})])
    assert journal_snapshot(store, '2026-10-15T00:00:00Z', {})['positions'][0]['shares'] == 150


def test_chinese_wizard_cancel_save_and_duplicate_request(workspace):
    root, path, profile, clock = workspace
    runner = CliRunner()
    args = ['research', 'record', '--profile', str(path), '--request-id', 'wizard']
    cancelled = runner.invoke(app, args, input=f'1\n600036.SH\n{clock[0].isoformat()}\n合成已阅\nn\n')
    assert cancelled.exit_code == 0 and '已取消' in cancelled.output
    assert not (root / profile['journal_store']).exists()
    saved = runner.invoke(app, args, input=f'2\n600036.SH\n{clock[0].isoformat()}\n200\n合成逻辑\n合成反证\nn\n\n合成备注\ny\n')
    assert saved.exit_code == 0, saved.output
    assert '600036.SH 200股' in saved.output and '未产生订单' in saved.output
    before = rows(workspace)
    repeated = runner.invoke(app, args, input='')
    assert repeated.exit_code == 0 and '重复调用没有新增' in repeated.output
    assert rows(workspace) == before


def test_note_does_not_invalidate_a_position_preview_but_pending_trade_blocks_completeness(workspace):
    root, path, _, clock = workspace
    previewed = request(workspace, 'p', shares=200)
    manual.record_manual_input(root, path, request(workspace, 'note', 'NOTE', note='仅已阅'))
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, previewed)
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, request(workspace, 'sell', 'EXECUTION', side='SELL', shares=100, price_cny='11'))
    before = rows(workspace)
    clock[0] += timedelta(minutes=1)
    unrelated = request(workspace, 'other', shares=50, code='000001.SZ', complete_positions_confirmed=True)
    with pytest.raises(ValueError, match='UNRECONCILED_ACCOUNT'):
        manual.record_manual_input(root, path, unrelated)
    assert rows(workspace) == before


def test_explicit_observation_reuses_profile_without_overwriting_inputs(workspace):
    root, path, profile, clock = workspace
    manual.record_manual_input(root, path, request(workspace, 'position', shares=100))
    before = path.read_bytes(), (root / profile['run']).read_bytes()
    args = ['research', 'daily', '--profile', str(path), '--observed-at',
            (clock[0] + timedelta(seconds=1)).isoformat(), '--market-date', '2026-10-13']
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    assert '中文简报' in result.output and '未获取新行情' in result.output
    assert close(workspace).report['portfolio']['positions'][0]['shares'] == 100
    assert before == (path.read_bytes(), (root / profile['run']).read_bytes())


@pytest.mark.parametrize('options', [ ['--observe-now'], ['--market-date','2026-10-13'],
    ['--observe-now','--observed-at','2026-10-14T04:00:00Z','--market-date','2026-10-13'] ])
def test_ambiguous_observation_options_fail_before_outputs(workspace, options):
    root, path, profile, _ = workspace
    result = CliRunner().invoke(app, ['research','daily','--profile',str(path),*options])
    assert result.exit_code == 1 and '配置检查失败' in result.output
    assert not (root / profile['journal_store']).exists()


def test_native_source_to_manual_input_to_next_brief(daily_case, sample, monkeypatch):
    """Full synthetic pipeline: no market/company service substitution or real account."""
    from hashlib import sha256
    from pathlib import Path
    import pyarrow as pa
    import pyarrow.parquet as pq
    from astock.features.market import ObservationParameters
    from astock.research.core import digest
    from astock.research.public_results import public_snapshot
    from astock.research.service import analyze

    root, path, profile, _ = daily_case
    manifest_path, bundle, _ = sample
    codes = {'STOCK-A': '600036.SH', 'STOCK-B': '600000.SH', 'BENCH-A': '000001.SH'}
    dates = {f'2026-09-{day:02}': date for day, date in zip(range(7, 12),
             ['2026-10-06', '2026-10-07', '2026-10-08', '2026-10-09', '2026-10-12'])}
    for spec in bundle['files']:
        source_path = Path(spec['path'])
        data = pq.read_table(source_path).to_pylist()
        for row in data:
            if 'code' in row:
                row['code'] = codes[row['code']]
            if 'name' in row:
                row['name'] = '合成公司/指数（非真实行情）'
            if 'date' in row:
                row['date'] = dates[row['date']]
        if spec['dataset'] == 'calendar':
            data.extend(dict(exchange='SSE', date=date, is_open=0)
                        for date in ('2026-10-10', '2026-10-11'))
        pq.write_table(pa.Table.from_pylist(data), source_path)
        spec.update(sha256=sha256(source_path.read_bytes()).hexdigest(),
                    retrieved_at='2026-10-14T00:00:00Z', available_at='2026-10-14T00:00:00Z',
                    evidence_grade='SYNTHETIC')
    bundle.update(universe=[codes[c] for c in bundle['universe']],
                  benchmarks=[codes[c] for c in bundle['benchmarks']],
                  window_start='2026-10-06', window_end='2026-10-12')
    manifest_path.write_bytes(encoded(bundle))
    source_path = root / profile['store']
    source_path.unlink()  # The fixture's explicit synthetic non-DB placeholder only.
    source = ResearchStore(source_path)
    bundle_id = source.import_bundle(manifest_path)
    params = ObservationParameters(**PARAMS)
    (root / profile['parameters']).write_bytes(encoded(params.model_dump(mode='json')))
    original = analyze(source, bundle_id, '2026-10-14T01:00:00Z', params, radar=True)
    source.save_report(original)
    baseline = public_snapshot(original)
    (root / profile['baseline_market']).write_bytes(encoded(baseline))
    run = read_json(root / profile['run'])
    run.update(mode='OFFLINE_SIMULATION', required_market_date='2026-10-12')
    run['plans'][0].update(baseline_market_hash=digest(baseline), baseline_market_bundle_id=bundle_id)
    (root / profile['run']).write_bytes(encoded(run))
    profile.update(bundle=bundle_id,
                   journal_store='data/private/research-v1/decision-loop-v0/simulated/native/journal.duckdb')
    strategy_path = root/'config/strategy.json'
    strategy_path.write_bytes((Path(__file__).parents[1]/'config/research/strategy-research-v1.json').read_bytes())
    profile['strategy_parameters'] = 'config/strategy.json'
    path.write_bytes(encoded(profile))
    before = sha256(source_path.read_bytes()).hexdigest()
    clock = [datetime(2026, 10, 14, 4, tzinfo=timezone.utc)]
    monkeypatch.setattr(manual, 'now_utc', lambda: clock[0])
    case = root, path, profile, clock
    manual.record_manual_input(root, path, request(case, 'native-initial', shares=200,
                               complete_positions_confirmed=True, cash_cny='1000', cash_confirmed=True,
                               thesis='合成持仓逻辑：仅用于闭环演示'))
    resolved, _ = load_daily_profile(root, path)
    def observe():
        return run_close(root, resolved, DailyObservation(observed_at=clock[0] + timedelta(seconds=1),
                                                         required_market_date='2026-10-12'))
    first = observe()
    assert first.report['strategy_observations']['status'] == 'NOT_AVAILABLE_AT_OBSERVATION'
    assert '不把新规则回填' in first.markdown_path.read_text()
    assert first.report['portfolio']['account_assets_cny'] == '3800.0'
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, request(case, 'native-sell', 'EXECUTION', shares=100,
                               side='SELL', price_cny='14', remaining_shares=100, note='合成部分卖出'))
    second = observe()
    assert second.report['portfolio']['positions'][0]['shares'] == 100
    assert second.report['portfolio']['account_assets_cny'] is None
    clock[0] += timedelta(minutes=1)
    manual.record_manual_input(root, path, request(case, 'native-note', 'NOTE', note='合成已阅；未知现金和风险仍需核实'))
    final = observe()
    assert final.report['portfolio']['positions'][0]['shares'] == 100
    assert '600036.SH：已报 100股' in final.markdown_path.read_text()
    assert '合成夹具数字，不是实际披露' in final.markdown_path.read_text()
    assert final.report['portfolio']['cash_cny'] is None
    assert len(final.report['manual_records']) == 3
    assert sha256(source_path.read_bytes()).hexdigest() == before
    assert all(not c['trade_eligible'] and c['order'] is None for c in final.report['cards'])
    from astock.decision.plan_models import PlanDraft, PlanInput
    from astock.decision import plans
    clock[0] += timedelta(minutes=1)
    end = PlanInput(request_id='native-end', mode='SIMULATED', action='END_WATCH', code='600036.SH',
                    expected_plan_hash=plans.preview_plans(root, path)['plan_hash'], reason='合成结束观察，持仓仍在')
    plans.record_plan_input(root, path, end)
    ended = observe()
    assert ended.report['cards'][0]['state'] == 'END_WATCH'
    assert ended.report['portfolio']['positions'][0]['shares'] == 100
    assert any('仍有已报持仓' in reason for item in ended.report['decision_items']['items'] for reason in item['reasons'])
    clock[0] += timedelta(minutes=1)
    draft = PlanDraft(thesis='合成新版本研究逻辑', attention_reason='合成重新观察',
        no_trade_reasons=['未核实估值'], observable_checks=['核对原始收入表'], invalidation_conditions=['原始收入逻辑失效'],
        criteria=[dict(id='new-income', metric_id='revenue', expectation='NOT_LOWER', reason='合成收入检查')],
        review_due=clock[0] + timedelta(days=7))
    restart = PlanInput(request_id='native-restart', mode='SIMULATED', action='CREATE', code='600036.SH',
        expected_plan_hash=plans.preview_plans(root, path)['plan_hash'], reason='合成重开新计划', draft=draft)
    plans.record_plan_input(root, path, restart)
    restarted = observe()
    assert restarted.report['cards'][0]['state'] == 'CONTINUE_WATCH'
    assert restarted.report['cards'][0]['plan']['thesis'] == draft.thesis
    clock[0] = datetime(2026,10,15,9,tzinfo=timezone.utc)
    new_version = observe()
    strategies = new_version.report['strategy_observations']
    assert strategies['status'] == 'OBSERVED' and strategies['mode'] == 'OFFLINE_SYNTHETIC'
    assert all(c['pool']==2 and c['unknown']==2 and c['paper_ready']==0 for c in strategies['summary'].values())
    assert '三组规则观察' in new_version.markdown_path.read_text()
    from astock.decision.report import public_projection
    assert 'strategy_observations' not in public_projection(new_version.report)
    assert sha256(source_path.read_bytes()).hexdigest() == before
    assert sha256(source_path.read_bytes()).hexdigest() == before


def test_renderer_change_publishes_a_new_pair_and_preserves_old_bytes(workspace, monkeypatch):
    from astock.decision import report as publication
    root, _, profile, _ = workspace
    first = close(workspace)
    original = first.json_path.read_bytes(), first.markdown_path.read_bytes()
    output = root / profile['output']
    render = publication.markdown
    monkeypatch.setattr(publication, 'renderer_fingerprint', lambda: 'f' * 64)
    monkeypatch.setattr(publication, 'markdown', lambda r: render(r) + '\n合成渲染升级')
    changed = deepcopy(first.report)
    key = publication.publish_private(changed, output)
    assert key != first.report_id
    assert (first.json_path.read_bytes(), first.markdown_path.read_bytes()) == original
    assert (output / f'{key}.md').read_text().endswith('合成渲染升级')
    assert publication.publish_private(changed, output) == key
