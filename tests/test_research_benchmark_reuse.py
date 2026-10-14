"""Reusing retained benchmark identity must not broaden stock-source authority."""
from copy import deepcopy
import hashlib
from pathlib import Path
import httpx
import pytest
from astock.research.core import ResearchError, digest, encoded
from astock.research.inputs import load_bundle
from astock.research.tushare import make_capture_bundle
from market_fixture import plan as market_plan, response as market_response
from research_fixture import approved_mock, fixture_plan, response, BytesStream


@pytest.fixture(scope='module')
def retained(tmp_path_factory):
    root = tmp_path_factory.mktemp('benchmark-reuse')
    (root/'legacy').mkdir()
    (root/'market').mkdir()
    legacy_plan = fixture_plan()
    _, _, old = approved_mock(root/'legacy', legacy_plan,
                              lambda m, n: httpx.Response(200, stream=BytesStream(encoded(response(legacy_plan, m)))))
    original = make_capture_bundle(old)
    original_path = old/f'{digest(original)}.bundle.json'
    frozen = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in old.rglob('*') if p.is_file()}
    p = market_plan()
    def missing_identity(member, count):
        value = market_response(p, member)
        if member['api'] == 'index_basic':
            value['data']['items'] = []
        return httpx.Response(200, stream=BytesStream(encoded(value)))
    result, calls, current = approved_mock(root/'market', p, missing_identity, continue_on_error=True)
    assert len(calls) == 299 and result['complete_this_run'] == 297 and result['failed_this_run'] == 2
    return current, original_path, original, frozen


def test_retained_index_identity_closes_missing_benchmarks_without_rewriting_history(retained):
    current, old_path, old, frozen = retained
    with pytest.raises(ResearchError, match='IDENTITY_EVIDENCE_REQUIRED'):
        make_capture_bundle(current)
    manifest = make_capture_bundle(current, benchmark_bundle=old_path)
    bundle, inputs = load_bundle(current/f'{digest(manifest)}.bundle.json')
    assert bundle.universe_scope == 'CURRENT_A_SHARE_L' and len(bundle.universe) == 10
    old_indices = {s['sha256'] for s in old['files'] if s['request']['api'] == 'index_basic'}
    reused = [s for s in manifest['files'] if s['request']['api'] == 'index_basic']
    assert len(reused) == 2 and {s['sha256'] for s in reused} == old_indices
    assert all(s['evidence_grade'] == 'SYNTHETIC' and len(s['evidence']) == 4 for s in reused)
    assert frozen == {n: hashlib.sha256(Path(n).read_bytes()).hexdigest() for n in frozen}
    assert all(row['kind'] == 'INDEX' for spec, _, rows in inputs
               if spec.request['api'] == 'index_basic' for row in rows)


@pytest.mark.parametrize('mutation', ['window', 'benchmarks', 'calendar', 'stock_source', 'missing_proof'])
def test_reuse_preserves_window_benchmark_calendar_and_authority_boundaries(retained, tmp_path, mutation):
    current, old_path, original, _ = retained
    manifest = deepcopy(make_capture_bundle(current, benchmark_bundle=old_path))
    spec = next(s for s in manifest['files'] if s['request']['api'] == 'index_basic')
    if mutation == 'window':
        manifest['window_start'] = '2026-04-02'
    elif mutation == 'benchmarks':
        manifest['benchmarks'] = manifest['benchmarks'][:1]
    elif mutation == 'calendar':
        spec['calendar_exchange'] = 'SZSE'
    elif mutation == 'stock_source':
        manifest['files'].append(deepcopy(next(s for s in original['files'] if s['request']['api'] == 'stock_basic')))
    else:
        spec['evidence'] = spec['evidence'][:-1]
    with pytest.raises(ResearchError, match='CAPTURE_SCOPE_BINDING|CAPTURE_CALENDAR_BINDING|CAPTURE_EVIDENCE_REQUIRED'):
        load_bundle(tmp_path/'changed.bundle.json', manifest)


def test_unbound_declared_index_identity_is_not_a_reuse_source(retained, tmp_path):
    current, _, original, _ = retained
    unbound = deepcopy(original)
    for source in unbound['files']:
        if source['request']['api'] == 'index_basic':
            source['evidence_grade'] = 'USER_DECLARED'
            source['evidence'] = []
    path = tmp_path/'unbound.bundle.json'
    path.write_bytes(encoded(unbound))
    with pytest.raises(ResearchError, match='BENCHMARK_REUSE_EVIDENCE'):
        make_capture_bundle(current, benchmark_bundle=path)


def test_benchmark_reuse_does_not_change_legacy_bundle_behavior(retained):
    _, path, original, _ = retained
    assert make_capture_bundle(path.parent) == original
    with pytest.raises(ResearchError, match='BENCHMARK_REUSE_V2_ONLY'):
        make_capture_bundle(path.parent, benchmark_bundle=path)
