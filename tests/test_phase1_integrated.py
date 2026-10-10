"""Integrated public entry and adversarial regressions; transport is always closed."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from astock.phase1 import acquisition as a, contracts as c, domains as d, fixtures as f, pipeline as p
from astock.phase1.__main__ import main
from astock.phase1.core import Phase1Error, digest, encoded, file_hash, instant, logical_id, strict_json

ROOT = Path(__file__).resolve().parents[1]
EMPTY = dict(records=[], original_paths={}, original_hashes={})


def request(date='20250102', dataset='daily'):
    return c.request(ROOT, dataset, dict(trade_date=date))


def run(destination, members, *, payload=None, **kw):
    prior = kw.pop('prior', None)
    plan = a.make_plan(ROOT, destination, members, EMPTY, fixture=True,
                       prior_consumption=prior, resume_from=kw.pop('resume', None))
    clock = f.FixtureClock()
    if prior:
        clock.at = max(instant(r['claimed_at']) for r in prior) + timedelta(seconds=10)
    calls = []
    def handler(wire):
        calls.append(strict_json(wire.content))
        m = members[len(calls) - 1]
        r = f.row(ROOT, m['dataset'], ts_code='000001.SZ', trade_date=m['params']['trade_date'], open=10., high=11., low=9., close=10.)
        return httpx.Response(200, content=payload if payload is not None else encoded(f.response(m, [r])))
    result = a.run_batch(ROOT, destination, plan, EMPTY, token=SecretStr('closed-regression'),
                         transport=httpx.MockTransport(handler), clock=clock, **kw)
    return result, calls


@pytest.fixture(scope='module')
def demonstrated(tmp_path_factory):
    directory = tmp_path_factory.mktemp('integrated-demo')
    out = directory / 'result.json'
    assert main(['--root', str(ROOT), '--output', str(out), 'demo', '--destination', str(directory / 'store')]) == 0
    return directory / 'store', strict_json(out.read_bytes())


def test_public_nonempty_all_domains_and_legal_null(demonstrated):
    dest, result = demonstrated
    assert result['capture']['primary_error'] is None
    assert set(result['coverage']['domains']) == {'security', 'calendar', 'market', 'status', 'financial', 'industry', 'rule', 'index'}
    assert all(n > 0 for n in result['coverage']['datasets'].values())
    assert {'stock_basic', 'daily', 'daily_basic', 'adj_factor', 'stk_limit', 'stock_st', 'suspend_d', 'income', 'balancesheet', 'cashflow', 'fina_indicator'} <= set(result['coverage']['datasets'])
    with a.store(ROOT, dest, read_only=True) as db:
        rows = p.fact_rows(db)
    assert next(r for r in rows if r['dataset'] == 'suspend_d')['payload']['suspend_timing'] is None
    assert next(r for r in rows if r['dataset'] == 'stock_basic' and r['payload']['list_status'] == 'D')['payload']['ts_code'] == 'T00018.SH'
    assert len({r['payload']['ts_code'] for r in rows if r['dataset'] == 'stock_basic' and r['payload']['name'] == 'SAME_NAME'}) == 2
    assert result['real_market_API'] == result['original_SQL_writes'] == 0


def test_public_rebuild_two_stores_and_idempotent_increment(demonstrated, tmp_path):
    source, result = demonstrated
    hashes = []
    for i in range(2):
        out = tmp_path / f'rebuild-{i}.json'
        dest = tmp_path / f'rebuild-{i}'
        assert main(['--root', str(ROOT), '--output', str(out), 'rebuild', '--source', str(source), '--destination', str(dest)]) == 0
        rebuilt = strict_json(out.read_bytes())
        hashes.append(rebuilt['logical_content_hash'])
        before = file_hash(dest / 'catalog.duckdb')
        assert p.build(ROOT, dest, source_destination=source)['status'] == 'ALREADY_VALID'
        assert file_hash(dest / 'catalog.duckdb') == before
        assert p.query(ROOT, dest, 'S1', '2025-01-02', '2025-04-15T00:00:00Z')['domains']['financial']
    assert hashes == [result['build']['logical_content_hash']] * 2


def test_public_demo_reopen_does_not_replay(demonstrated, tmp_path):
    source, _ = demonstrated
    before = file_hash(source / 'catalog.duckdb')
    out = tmp_path / 'reopen.json'
    assert main(['--root', str(ROOT), '--output', str(out), 'demo', '--destination', str(source)]) == 0
    result = strict_json(out.read_bytes())
    assert result['capture']['new_mock_calls'] == 0 and result['build']['status'] == 'ALREADY_VALID'
    assert file_hash(source / 'catalog.duckdb') == before


def rows_from(demonstrated):
    with a.store(ROOT, demonstrated[0], read_only=True) as db:
        return p.fact_rows(db)


def test_financial_revision_publication_and_bank_fields(demonstrated):
    rows = rows_from(demonstrated)
    before = d.historical_snapshot(rows, 'S1', '2025-01-02', '2025-03-31T23:59:59Z')
    first = d.historical_snapshot(rows, 'S1', '2025-01-02', '2025-04-15T00:00:00Z')
    later = d.historical_snapshot(rows, 'S1', '2025-01-02', '2025-05-15T00:00:00Z')
    assert not before['domains']['financial']
    assert len(first['domains']['financial']) == len(later['domains']['financial']) == 4
    assert {r['payload']['ann_date'] for r in first['domains']['financial']} == {'20250401'}
    assert {r['payload']['ann_date'] for r in later['domains']['financial']} == {'20250501'}
    assert all(r['payload']['comp_type'] == '2' for r in first['domains']['financial'] if r['dataset'] != 'fina_indicator')
    assert all(r['payload']['report_type'] == '1' for r in first['domains']['financial'] if r['dataset'] != 'fina_indicator')


def test_observed_download_does_not_backdate_and_date_precision():
    source = dict(retrieved_at='2025-06-01T00:00:00Z', fixture_only=True, object_id='FIXTURE')
    k = d.knowledge(dict(ann_date='20250401'), source, {}, fixture=True)
    assert k['published_at'] is None and k['available_at'].startswith('2025-06-01')
    proof = f.proof('2025-04-01T00:00:00Z')
    proof.update(precision='DATE', calendar_rows=[dict(cal_date='20250402', is_open=1)])
    k = d.knowledge(dict(ann_date='20250401'), source, dict(knowledge=proof), fixture=True)
    assert k['published_at'] is None and k['available_at'].startswith('2025-04-02T01:30:00')
    with pytest.raises(Phase1Error):
        d.knowledge(dict(ann_date='20250401'), source, dict(knowledge=proof), fixture=False)


def test_industry_exit_bse_code_transition_and_rules(demonstrated):
    rows = rows_from(demonstrated)
    early = d.historical_snapshot(rows, 'S1', '2025-01-02', '2025-05-15T00:00:00Z', taxonomy='SW2021')
    later = d.historical_snapshot(rows, 'S1', '2025-01-06', '2025-05-15T00:00:00Z', taxonomy='SW2021')
    assert early['domains']['industry'][0]['payload']['industry_code'] == 'A'
    assert later['domains']['industry'][0]['payload']['industry_code'] == 'B'
    assert early['domains']['calendar'] and later['domains']['calendar']
    assert d.resolve(rows, '830001.BJ', '2025-01-05', '2025-05-15T00:00:00Z')['security_id'] == 'S3'
    assert d.resolve(rows, '830001.BJ', '2025-01-06', '2025-05-15T00:00:00Z')['status'] == 'EVIDENCE_REQUIRED'
    assert d.resolve(rows, '920001.BJ', '2025-01-06', '2025-05-15T00:00:00Z')['security_id'] == 'S3'
    assert d.rule_at(rows, 'SZSE', 'MAIN', 'ST', '2025-01-05', '2025-05-15T00:00:00Z')['rule']['price_limit_ratio'] == .1
    assert d.rule_at(rows, 'SZSE', 'MAIN', 'NORMAL', '2025-01-06', '2025-05-15T00:00:00Z')['rule']['price_limit_ratio'] == .2
    assert d.sellable_on('2025-01-03', 1, ['2025-01-03', '2025-01-06'])['date'] == '2025-01-06'
    assert not d.quantity_valid(dict(min_order_qty=100, order_qty_step=100), 150)['valid']


def test_causal_adjustment_anchor(demonstrated):
    rows = rows_from(demonstrated)
    assert d.adjusted_price(rows, '000001.SZ', '2025-01-02', '2025-01-06', '2025-05-15T00:00:00Z')['value'] == 5.25
    with pytest.raises(Phase1Error, match='FUTURE_ADJUSTMENT_ANCHOR'):
        d.adjusted_price(rows, '000001.SZ', '2025-01-02', '2025-01-06', '2025-01-03T00:00:00Z')
    assert d.adjusted_price(rows, '000001.SZ', '2025-01-02', '2025-01-02', '2025-01-02T00:00:00Z')['status'] == 'EVIDENCE_REQUIRED'


def test_no_overlapping_identity_or_same_time_revision_guess(demonstrated):
    rows = rows_from(demonstrated)
    mapping = next(r for r in rows if r['dataset'] == 'security_identifiers' and r['entity'] == 'S1')
    other = deepcopy(mapping)
    other['payload']['security_id'] = 'S4'
    other['series_key'] = 'INDEPENDENT_OVERLAP'
    other['fact_hash'] = digest(other)
    assert d.resolve(rows + [other], '000001.SZ', '2025-01-02', '2025-05-15T00:00:00Z')['status'] == 'CONFLICT'
    finance = next(r for r in rows if r['dataset'] == 'income')
    other = deepcopy(finance)
    other['payload']['total_revenue'] = 999.
    other['fact_hash'] = digest(other)
    assert d.known_versions([finance, other], '2025-06-01T00:00:00Z')[1]


def test_source_hash_readback_before_complete_and_reopen(tmp_path):
    dest = tmp_path / 'tampered'
    def fault(stage):
        if stage == 'before_readback':
            path = next((dest / 'objects').glob('*/response.body'))
            path.write_bytes(path.read_bytes() + b' ')
    result, calls = run(dest, [request(), request('20250103')], fault=fault)
    assert len(calls) == 1 and result['primary_error'] == 'SOURCE_BINDING_CHANGED'
    with a.store(ROOT, dest, read_only=True) as db:
        assert a.local_consumption(db)[0]['states'][-1] == 'FAILED'
        assert db.execute('SELECT count(*) FROM p1_receipt').fetchone()[0] == 0


@pytest.mark.parametrize('stage', ['after_claim', 'after_call_entered'])
def test_process_exit_consumes_never_resends(tmp_path, stage):
    dest = tmp_path / stage
    def fault(at):
        if at == stage: raise SystemExit(7)
    with pytest.raises(SystemExit): run(dest, [request()], fault=fault)
    with a.store(ROOT, dest, read_only=True) as db:
        current = a.local_consumption(db)
        assert len(current) == 1
        plan = a.make_plan(ROOT, dest, [request()], EMPTY, fixture=True, prior_consumption=current, resume_from=digest(current))
        with pytest.raises(Phase1Error, match='CONSUMED_NEW_REQUEST'):
            a.validate_plan(ROOT, dest, plan, EMPTY, db, fixture=True)


def test_generic_matched_recovery_and_multiple_plans(tmp_path):
    dest = tmp_path / 'recovery'
    result, calls = run(dest, [request(), request('20250103')], payload=b'{"bad":"body"}')
    assert len(calls) == 1 and result['primary_error'] == 'UNKNOWN_ENVELOPE_FIELD'
    with a.store(ROOT, dest, read_only=True) as db:
        current = a.local_consumption(db)
    result, calls = run(dest, [request('20250103')], prior=current, resume=digest(current))
    assert len(calls) == 1 and result['primary_error'] is None
    with a.store(ROOT, dest, read_only=True) as db:
        current = a.local_consumption(db)
    result, calls = run(dest, [request('20250106')], prior=current, resume=digest(current))
    assert len(calls) == 1 and result['final_audit']['checked'] == 2
    assert any(r['states'][-1] == 'FAILED' for r in result['consumption'])


def test_logging_failure_preserves_primary_and_stops(tmp_path):
    seen = []
    def logger(path, value):
        seen.append(value)
        if value['stage'] == 'STOP': raise OSError('unprintable-sensitive-exception')
    result, calls = run(tmp_path / 'logs', [request(), request('20250103')], payload=b'{"bad":1}', log=logger)
    assert len(calls) == 1
    assert result['primary_error'] == 'UNKNOWN_ENVELOPE_FIELD'
    assert result['secondary_errors'] == ['UNEXPECTED_OSERROR']
    assert 'unprintable-sensitive' not in encoded(result).decode()


def test_output_failure_reported_not_success(tmp_path):
    def output(path, body): raise OSError('private')
    result, calls = run(tmp_path / 'output', [request()], output=output)
    assert len(calls) == 1 and result['secondary_errors'] == ['UNEXPECTED_OSERROR']


def test_global_identity_fields_dates_and_directory_do_not_refund(tmp_path):
    original = request()
    altered = deepcopy(original)
    altered['fields'] = list(reversed(altered['fields']))
    altered['params']['trade_date'] = '2025-01-02'
    assert logical_id(original) == logical_id(altered)
    baseline = dict(records=[dict(consumed=True, logical_id=logical_id(original), state='FAILED', request=original)])
    with pytest.raises(Phase1Error, match='ALREADY_CONSUMED_GLOBAL_REQUEST'):
        a.make_plan(ROOT, tmp_path / 'different-root', [original], baseline, fixture=True)


@pytest.mark.parametrize('mutation,reason', [
    ('unknown', 'UNKNOWN_DATA_FIELD'), ('more', 'TRUNCATION_MORE_ROWS'), ('boolcount', 'COUNT_TYPE'),
    ('business', 'PROVIDER_BUSINESS_ERROR'), ('null_detail_dict', 'DETAIL_TYPE'), ('duplicate', 'DUPLICATE_NATURAL_KEY')])
def test_typed_profile_and_semantic_errors(mutation, reason):
    member = request()
    value = f.response(member, [f.row(ROOT, 'daily', ts_code='000001.SZ', trade_date='20250102')])
    if mutation == 'unknown': value['data']['next_page'] = 2
    if mutation == 'more': value['data']['has_more'] = True
    if mutation == 'boolcount': value['data']['count'] = False
    if mutation == 'business': value['code'] = -1
    if mutation == 'null_detail_dict': value['detail'] = {}
    if mutation == 'duplicate': value['data']['items'] *= 2
    with pytest.raises(Phase1Error, match=reason): c.decode(ROOT, member, encoded(value))


def test_empty_needs_exact_evidence_and_cap_is_not_completeness():
    member = request()
    with pytest.raises(Phase1Error, match='UNEXPLAINED_EMPTY'):
        c.decode(ROOT, member, encoded(f.response(member, [])))
    member['empty_evidence'] = dict(scope_hash=digest(member['params']), evidence_hash='a' * 64, basis='FIXTURE_NO_EVENTS')
    decoded = c.decode(ROOT, member, encoded(f.response(member, [])))
    assert decoded['completeness'] != 'CIVIL_WINDOW_VALID' and not decoded['research_admitted']
    data = c.request(ROOT, 'fina_indicator', dict(ts_code='000001.SZ', period='20241231'))
    rows = [f.row(ROOT, 'fina_indicator', ts_code='000001.SZ', ann_date='20250401', end_date='20241231') for _ in range(100)]
    with pytest.raises(Phase1Error, match='CAP_OR_TRUNCATION'):
        c.decode(ROOT, data, encoded(f.response(data, rows)))


def test_fina_window_report_period_other_finance_publication():
    indicator = c.request(ROOT, 'fina_indicator', dict(ts_code='000001.SZ', start_date='20240101', end_date='20241231'))
    r = f.row(ROOT, 'fina_indicator', ts_code='000001.SZ', end_date='20241231', ann_date='20250401')
    assert c.decode(ROOT, indicator, encoded(f.response(indicator, [r])))['rows']
    income = c.request(ROOT, 'income', indicator['params'])
    r = f.row(ROOT, 'income', ts_code='000001.SZ', end_date='20241231', ann_date='20250401')
    with pytest.raises(Phase1Error, match='ROW_OUTSIDE_WINDOW'):
        c.decode(ROOT, income, encoded(f.response(income, [r])))


def test_root_namespace_and_live_without_licenses_fail_before_socket(tmp_path):
    dest = tmp_path / 'owner'
    with a.store(ROOT, dest): pass
    with pytest.raises(Phase1Error, match='ROOT_STORE_NAMESPACE_CHANGED'):
        with a.store(tmp_path, dest): pass
    plan = a.make_plan(ROOT, ROOT / 'data/private/phase1-integrated-v1', [request()], EMPTY)
    with pytest.raises(Phase1Error, match='MATCHED_INDEPENDENT_HUMAN_REQUIRED'):
        a.authorize(ROOT, ROOT / 'data/private/phase1-integrated-v1', plan, EMPTY, None, None, live=True, transport=None)
    with pytest.raises(Phase1Error, match='ORIGINAL_STORE_IMMUTABLE'):
        a.owner(ROOT, ROOT / 'data/warehouse/new', True)


def test_build_transaction_failure_no_partial_facts(demonstrated, tmp_path):
    dest = tmp_path / 'rollback'
    def fault(stage): raise RuntimeError('synthetic-only')
    with pytest.raises(RuntimeError): p.build(ROOT, dest, source_destination=demonstrated[0], fault=fault)
    with a.store(ROOT, dest, read_only=True) as db:
        assert db.execute('SELECT count(*) FROM p1_fact').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM p1_generation').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM p1_lineage').fetchone()[0] == 0


def test_rebuild_source_tamper_rejected(demonstrated, tmp_path):
    dest = tmp_path / 'rebuilt'
    p.build(ROOT, dest, source_destination=demonstrated[0])
    with a.store(ROOT, dest) as db:
        db.execute("UPDATE p1_fact SET payload='{}' WHERE dataset='income'")
    with pytest.raises(Phase1Error, match='PERSISTED_FACT_CHANGED'):
        p.query(ROOT, dest, 'S1', '2025-01-02', '2025-05-15T00:00:00Z')


def test_append_revision_increment_keeps_old_fact_bytes(demonstrated, tmp_path):
    source, _ = demonstrated
    dest = tmp_path / 'increment'
    p.build(ROOT, dest, source_destination=source)
    with a.store(ROOT, dest, read_only=True) as db:
        old = p.fact_rows(db)
    member = c.request(ROOT, 'security_status', {}, metadata=dict(knowledge=f.proof('2025-06-02T00:00:00Z')))
    row = f.row(ROOT, 'security_status', security_id='S1', episode_id='E1', state_type='RISK_WARNING', state_value='ST',
                exchange='SZSE', valid_from='20250106', valid_to=None, evidence_source='FIXTURE_LATER_CORRECTION')
    package = dict(namespace='FIXTURE', request=member, response=f.response(member, [row]),
                   retrieved_at='2025-06-03T00:00:00Z', evidence='SYNTHETIC_NOT_LEGAL_EVIDENCE')
    p.import_evidence(ROOT, dest, [package])
    assert p.build(ROOT, dest)['facts'] == len(old) + 1
    with a.store(ROOT, dest, read_only=True) as db:
        newer = p.fact_rows(db)
    assert all(r in newer for r in old)
    before = d.historical_snapshot(newer, 'S1', '2025-01-06', '2025-06-01T00:00:00Z')
    after = d.historical_snapshot(newer, 'S1', '2025-01-06', '2025-06-03T00:00:00Z')
    assert next(r for r in before['domains']['status'] if r['dataset'] == 'security_status')['payload']['state_value'] == 'NORMAL'
    assert next(r for r in after['domains']['status'] if r['dataset'] == 'security_status')['payload']['state_value'] == 'ST'
    assert p.build(ROOT, dest)['status'] == 'ALREADY_VALID'


def test_source_changed_during_generation_rolls_back(demonstrated, tmp_path):
    source, _ = demonstrated
    import shutil
    clone = tmp_path / 'input-copy'
    # Inputs are fixed descriptors. Rebuild on a target then mutate the actual
    # source only in a separate owned fixture, leaving the shared sample intact.
    packages = f.sample_inputs(ROOT)[2]
    p.import_evidence(ROOT, clone, packages)
    body = next((clone / 'evidence').glob('*/response.body'))
    dest = tmp_path / 'target'
    def fault(stage): body.write_bytes(body.read_bytes() + b' ')
    with pytest.raises(Phase1Error, match='INPUT_CHANGED_DURING_BUILD'):
        p.build(ROOT, dest, source_destination=clone, fault=fault)
    with a.store(ROOT, dest, read_only=True) as db:
        assert db.execute('SELECT count(*) FROM p1_fact').fetchone()[0] == 0


def test_industry_version_explicit_and_exit_no_forward_fill(demonstrated):
    rows = rows_from(demonstrated)
    old = deepcopy(next(r for r in rows if r['dataset'] == 'industry_membership' and r['payload']['industry_code'] == 'A'))
    old['payload'].update(classification_version='SW2014', industry_code='C')
    old['series_key'], old['fact_hash'] = 'FIXTURE_OTHER_TAXONOMY', 'FIXTURE_HASH'
    result = d.historical_snapshot(rows + [old], 'S1', '2025-01-02', '2025-05-15T00:00:00Z')
    assert not result['domains']['industry']
    assert any(q['reason'] == 'TAXONOMY_VERSION_REQUIRED' for q in result['unknowns'])
    result = d.historical_snapshot(rows + [old], 'S1', '2025-01-06', '2025-05-15T00:00:00Z', taxonomy='SW2014')
    assert not result['domains']['industry']


def test_missing_bar_not_inferred_suspended(demonstrated):
    result = p.coverage(ROOT, demonstrated[0], expectations=[dict(dataset='daily', entity='000001.SZ', event_date='2025-01-03')])
    assert result['reasons']['EXPECTED_OBSERVATION_MISSING_NOT_INFERRED_SUSPENDED'] >= 1
    assert result['old_findings_preserved'] == 402060
    assert result['historical_coverage_certified'] is False
    assert all('exchange' in r and 'episode_id' in r for r in result['dimensions'])


def test_second_source_unit_conversion_and_disagreement(demonstrated, tmp_path):
    dest = tmp_path / 'second-source'
    p.build(ROOT, dest, source_destination=demonstrated[0])
    assert 'CROSS_SOURCE_VALUE_DISAGREEMENT' not in p.coverage(ROOT, dest)['reasons']
    member = c.request(ROOT, 'market_crosscheck', {}, metadata=dict(knowledge=f.proof('2025-01-02T08:05:00Z')))
    row = f.row(ROOT, 'market_crosscheck', ts_code='000001.SZ', exchange='SZSE', trade_date='20250102', close=99.,
                evidence_source='FIXTURE_DIFFERENT_SOURCE', volume_shares=100000., amount_cny=1050000.)
    p.import_evidence(ROOT, dest, [dict(namespace='FIXTURE', request=member, response=f.response(member, [row]), retrieved_at='2025-06-01T00:00:00Z', evidence='SYNTHETIC_NOT_LEGAL_EVIDENCE')])
    p.build(ROOT, dest)
    report = p.coverage(ROOT, dest)
    assert report['reasons']['CROSS_SOURCE_VALUE_DISAGREEMENT'] >= 1
    assert any(q.get('selection') == 'NEITHER_SOURCE_OVERWRITTEN' for q in report['findings'])


def test_rule_ipo_coverage_null_and_overlap(demonstrated):
    rows = rows_from(demonstrated)
    original = next(r for r in rows if r['dataset'] == 'rule_history' and r['valid_to'] is None)
    ipo = deepcopy(original)
    ipo['payload']['ipo_no_limit_sessions'] = 5
    assert d.rule_at([ipo], 'SZSE', 'MAIN', 'NORMAL', '2025-01-07', '2025-05-15T00:00:00Z')['status'] == 'EVIDENCE_REQUIRED'
    calendar = f.calendar_rows(dict(exchange='SZSE', start_date='20250106', end_date='20250110'))
    result = d.rule_at([ipo], 'SZSE', 'MAIN', 'NORMAL', '2025-01-10', '2025-05-15T00:00:00Z', listing_date='20250106', sessions=calendar)
    assert result['rule']['price_limit_basis'] == 'IPO_EXEMPTION'
    assert result['rule']['price_limit_ratio'] is None
    assert d.rule_at([ipo], 'SZSE', 'MAIN', 'NORMAL', '2025-01-10', '2025-05-15T00:00:00Z', listing_date='20250106', sessions=calendar[:-1])['status'] == 'EVIDENCE_REQUIRED'
    unknown = deepcopy(original)
    unknown['payload']['price_limit_ratio'] = None
    assert d.rule_at([unknown], 'SZSE', 'MAIN', 'NORMAL', '2025-01-07', '2025-05-15T00:00:00Z')['status'] == 'PARTIAL'
    other = deepcopy(original)
    other['series_key'] = 'OVERLAP'
    assert d.rule_at([original, other], 'SZSE', 'MAIN', 'NORMAL', '2025-01-07', '2025-05-15T00:00:00Z')['status'] == 'CONFLICT'


def test_new_scope_overlap_held_and_no_weak_pit_proof(tmp_path):
    from astock.phase1.core import overlapping
    left = c.request(ROOT, 'fina_indicator', dict(ts_code='000001.SZ', ann_date='20250401'))
    right = c.request(ROOT, 'fina_indicator', dict(ts_code='000001.SZ', start_date='20240101', end_date='20241231'))
    assert overlapping(left, right)
    with pytest.raises(Phase1Error, match='OVERLAPPING_NEW_BATCH_MEMBERS'):
        a.make_plan(ROOT, tmp_path / 'overlap', [left, right], EMPTY, fixture=True)
    proof = f.proof('2025-04-01T00:00:00Z')
    proof.update(namespace='APPROVED_POLICY', approval_ref='AUTHOR_CLAIM', policy_hash='a' * 64)
    with pytest.raises(Phase1Error, match='PIT_POLICY_NAMESPACE'):
        d.knowledge(dict(ann_date='20250401'), dict(retrieved_at='2025-06-01T00:00:00Z'), dict(knowledge=proof), fixture=False)


def test_fact_production_without_actual_approval_rejected(tmp_path):
    packages = f.sample_inputs(ROOT)[2]
    destination = ROOT / 'data/private/phase1-integrated-v1'
    existed = destination.exists()
    before = {str(path.relative_to(destination)): file_hash(path)
              for path in destination.rglob('*') if path.is_file()}
    with pytest.raises(Phase1Error, match='MATCHED_FACT_POLICY_LICENSE_REQUIRED'):
        p.import_evidence(ROOT, destination, packages, fixture=False)
    assert destination.exists() == existed
    assert {str(path.relative_to(destination)): file_hash(path)
            for path in destination.rglob('*') if path.is_file()} == before


def test_hard_process_death_preserves_durable_consumption(tmp_path):
    import subprocess, sys, os
    dest = tmp_path / 'process-death'
    script = '''
import os,sys,httpx
from pathlib import Path
from pydantic import SecretStr
from astock.phase1 import acquisition as a,contracts as c,fixtures as f
root,dest=Path(sys.argv[1]),Path(sys.argv[2])
m=c.request(root,'daily',{'trade_date':'20250102'})
b={'records':[],'original_paths':{},'original_hashes':{}}
plan=a.make_plan(root,dest,[m],b,fixture=True)
def fault(stage):
 if stage=='after_call_entered': os._exit(12)
def handler(request): raise AssertionError('TRANSPORT_MUST_NOT_ENTER')
a.run_batch(root,dest,plan,b,token=SecretStr('closed-death'),transport=httpx.MockTransport(handler),clock=f.FixtureClock(),fault=fault)
'''
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-c', script, str(ROOT), str(dest)], env=env, capture_output=True, timeout=30)
    assert result.returncode == 12
    with a.store(ROOT, dest, read_only=True) as db:
        assert a.local_consumption(db)[0]['states'] == ['CLAIMED', 'CALL_ENTERED']
        assert a.audit(ROOT, dest, db)['checked'] == 0


def test_cross_window_calendar_predecessor_checked(tmp_path):
    dest = tmp_path / 'calendar-windows'
    first = c.request(ROOT, 'trade_cal', dict(exchange='SZSE', start_date='20250101', end_date='20250103'))
    second = c.request(ROOT, 'trade_cal', dict(exchange='SZSE', start_date='20250104', end_date='20250106'))
    clock = f.FixtureClock()
    for index, member in enumerate([first, second]):
        prior = []
        if index:
            with a.store(ROOT, dest, read_only=True) as db: prior = a.local_consumption(db)
        plan = a.make_plan(ROOT, dest, [member], EMPTY, fixture=True, prior_consumption=prior)
        rows = f.calendar_rows(member['params'])
        if index:
            for row in rows: row['pretrade_date'] = '20250102'
        result = a.run_batch(ROOT, dest, plan, EMPTY, token=SecretStr('closed-calendar'), clock=clock,
                    transport=httpx.MockTransport(lambda request: httpx.Response(200, content=encoded(f.response(member, rows)))))
    assert result['primary_error'] == 'CROSS_WINDOW_PRETRADE_CONFLICT'
    assert result['final_audit']['checked'] == 1


def test_clock_rolls_back_after_claim_no_transport(tmp_path):
    class BadClock(f.FixtureClock):
        def utc(self):
            current = self.at
            self.at -= timedelta(seconds=1)
            return current
    dest = tmp_path / 'clock'
    member = request()
    plan = a.make_plan(ROOT, dest, [member], EMPTY, fixture=True)
    calls = []
    result = a.run_batch(ROOT, dest, plan, EMPTY, token=SecretStr('closed-clock'), clock=BadClock(),
              transport=httpx.MockTransport(lambda wire: calls.append(wire)))
    assert calls == [] and result['primary_error'] == 'CLOCK_ROLLBACK'
    assert result['consumption'][0]['states'] == ['CLAIMED']


def test_secret_encoded_echo_suppressed_and_redirect_not_followed(tmp_path):
    import base64
    result, calls = run(tmp_path / 'secret', [request(), request('20250103')], payload=encoded(dict(echo=base64.b64encode(b'closed-regression').decode())))
    assert len(calls) == 1 and result['primary_error'] == 'UNSAFE_BODY_SUPPRESSED'
    assert not list((tmp_path / 'secret').glob('objects/*/response.body'))
    member = request()
    dest = tmp_path / 'redirect'
    plan = a.make_plan(ROOT, dest, [member], EMPTY, fixture=True)
    called = []
    def handler(wire):
        called.append(str(wire.url))
        return httpx.Response(302, headers={'Location': 'https://example.invalid/forbidden'})
    result = a.run_batch(ROOT, dest, plan, EMPTY, token=SecretStr('closed-no-redirect'), clock=f.FixtureClock(), transport=httpx.MockTransport(handler))
    assert called == ['https://api.tushare.pro'] and result['primary_error'] == 'HTTP_OR_TRUNCATION'


@pytest.mark.parametrize('field', ['root', 'destination', 'pins', 'budget', 'plan_hash', 'namespace', 'legacy_hash'])
def test_approval_scope_mutations_stop_before_transport(tmp_path, field):
    dest = ROOT / 'data/private/phase1-integrated-v1'
    plan = a.make_plan(ROOT, dest, [request()], EMPTY)
    approval = dict(protocol=__import__('astock.phase1',fromlist=['PROTOCOL']).PROTOCOL, namespace='PRODUCTION', root=str(ROOT), destination=str(dest),
                    pins=a.pins(ROOT), budget=1, plan_hash=digest(plan), legacy_hash=digest(EMPTY))
    approval[field] = 'SYNTHETIC_MISMATCH_NO_LICENSE'
    with pytest.raises(Phase1Error, match='APPROVAL_SCOPE_CHANGED'):
        a.authorize(ROOT, dest, plan, EMPTY, approval, {}, live=True, transport=None)


def test_symlink_and_hardlink_objects_rejected(tmp_path):
    from astock.phase1.core import safe_path
    import os
    source = tmp_path / 'source'
    source.write_bytes(b'SYNTHETIC')
    link = tmp_path / 'symbolic'
    link.symlink_to(source)
    with pytest.raises(Phase1Error, match='SYMLINK_REJECTED'): safe_path(tmp_path, link)
    hard = tmp_path / 'hard'
    os.link(source, hard)
    with pytest.raises(Phase1Error, match='HARDLINK_REJECTED'): safe_path(tmp_path, hard)


def test_actual_application_shape_preserves_unconsumed_selection(tmp_path):
    from astock.phase1 import application
    selection, baseline = dict(execution_license=False, canonical_root=str(ROOT), original_capture_hash='FIXTURE_HASH', members=[]), dict(EMPTY, original_hashes={'capture':'FIXTURE_HASH'}, records=[])
    from uuid import uuid4
    for i in range(27):
        year, exchange = 2013 + i // 2, 'SSE' if i % 2 == 0 else 'SZSE'
        member = c.request(ROOT, 'trade_cal', dict(exchange=exchange, start_date=f'{year}0101', end_date=f'{year}1231'))
        mid, oid = logical_id(member), str(uuid4())
        selection['members'].append(dict(member_id=mid, object_id=oid, origin_plan='FIXTURE_ORIGIN', request=member))
        baseline['records'].append(dict(store='capture', origin_id=mid, object_id=oid, origin_plan='FIXTURE_ORIGIN', consumed=False, request=dict(dataset=member['dataset'], params=member['params'])))
    market = dict(requests=[dict(request=dict(request('20130109', dataset), member_id=logical_id(request('20130109', dataset)))) for dataset in sorted(c.MARKET)])
    selection_path, market_path = tmp_path / 'selection.json', tmp_path / 'market.json'
    selection_path.write_bytes(encoded(selection)); market_path.write_bytes(encoded(market))
    proposal = application.propose(ROOT, selection_path, market_path, baseline, dict(path='FIXTURE_NOT_A_REAL_PROTECTION_LICENSE', sha256='a'*64))
    assert proposal['execution_license'] is False and proposal['reviewer'] is proposal['approved_at'] is None
    assert proposal['exact_pilot_budget'] == 50 and proposal['full_target']['total_budget'] is None
    assert [m['origin_id'] for m in proposal['plan']['members'][:27]] == [m['member_id'] for m in selection['members']]
    assert proposal['plan_hash'] == digest(proposal['plan'])
    selection['members'][0]['object_id'] = str(uuid4())
    selection_path.write_bytes(encoded(selection))
    with pytest.raises(Phase1Error, match='EXACT27_ORIGIN_CHANGED'):
        application.propose(ROOT, selection_path, market_path, baseline, {})


def test_fact_batch_prevalidation_no_partial_publication(tmp_path):
    packages = f.sample_inputs(ROOT)[2]
    bad = deepcopy(packages[-1]); bad['response']['data']['fields'] = ['WRONG']
    dest = tmp_path / 'bad-packages'
    with pytest.raises(Phase1Error, match='PROVIDER_FIELDS_OR_ROWS'):
        p.import_evidence(ROOT, dest, [packages[0], bad])
    assert not list(dest.glob('evidence/*')) and not (dest / 'catalog.duckdb').exists()


def test_date_policy_cannot_skip_missing_civil_days():
    with pytest.raises(Phase1Error, match='PUBLICATION_CALENDAR_COVERAGE_UNKNOWN'):
        d.conservative_next_session('20250404', [dict(cal_date='20250407', is_open=1)])


def test_existing_raw_vintage_interpretation_no_resend_or_receipt_change(tmp_path):
    dest = tmp_path / 'raw-vintage'
    member = c.request(ROOT, 'income', dict(ts_code='000001.SZ', ann_date='20250401'))
    row = f.row(ROOT, 'income', ts_code='000001.SZ', ann_date='20250401', f_ann_date='20250401', end_date='20241231', report_type='1', comp_type='2', total_revenue=100.)
    value = f.response(member, [row])
    plan = a.make_plan(ROOT, dest, [member], EMPTY, fixture=True)
    result = a.run_batch(ROOT, dest, plan, EMPTY, token=SecretStr('closed-vintage'), clock=f.FixtureClock(),
                  transport=httpx.MockTransport(lambda wire: httpx.Response(200, content=encoded(value))))
    assert result['primary_error'] is None
    p.build(ROOT, dest)
    with a.store(ROOT, dest, read_only=True) as db:
        receipt = db.execute('SELECT * FROM p1_receipt').fetchall()
        old = p.fact_rows(db)
    assert old[0]['available_at'].startswith('2025-06-01')
    assert not d.known_versions(old, '2025-04-15T00:00:00Z')[0]
    original = next((dest / 'objects').iterdir())
    body, source = original / 'response.body', original / 'http-source.json'
    signed_request = deepcopy(member)
    signed_request['metadata']['knowledge'] = f.proof('2025-04-01T01:00:00Z')
    package = dict(namespace='FIXTURE', request=signed_request, response=value,
                   retrieved_at='2025-06-02T00:00:00Z', evidence='SYNTHETIC_NOT_LEGAL_EVIDENCE',
                   raw_reference=dict(kind='CAPTURE', body_path=str(body), body_hash=file_hash(body), source_path=str(source), source_hash=file_hash(source)))
    p.import_evidence(ROOT, dest, [package])
    p.build(ROOT, dest)
    with a.store(ROOT, dest, read_only=True) as db:
        newer = p.fact_rows(db)
        assert db.execute('SELECT * FROM p1_receipt').fetchall() == receipt
        assert db.execute('SELECT count(*) FROM p1_attempt').fetchone()[0] == 1
    known = d.known_versions(newer, '2025-04-15T00:00:00Z')[0]
    assert len(known) == 1 and known[0]['payload']['total_revenue'] == 100.
    assert all(r in newer for r in old)
    bad = deepcopy(package); bad['response']['data']['items'][0][member['fields'].index('total_revenue')] = 999.
    with pytest.raises(Phase1Error, match='INTERPRETATION_VALUE_CHANGED'):
        p.import_evidence(ROOT, dest, [bad])


def test_genuine_same_day_asof_all_domains_and_close_not_early(demonstrated):
    rows = rows_from(demonstrated)
    for result in demonstrated[1]['queries']:
        assert result['query_mode'] == 'HISTORICAL_KNOWLEDGE_CUTOFF'
        assert all(result['domains'][domain] for domain in ('security', 'calendar', 'market', 'status', 'financial', 'industry', 'rule'))
    early = d.historical_snapshot(rows, 'S1', '2025-04-15', '2025-04-15T01:15:00Z')
    assert not early['domains']['market']
    reconstructed = d.historical_snapshot(rows, 'S1', '2025-01-02', '2025-05-15T10:00:00Z')
    assert reconstructed['query_mode'] == 'CURRENT_RECONSTRUCTION' and not reconstructed['research_admitted']
