"""Native market calculations never consume live private Journal or public output JSON."""
from copy import deepcopy

import pytest

from astock.company.workflow import verified_market_context
from astock.decision.increment import market_context
from astock.features.market import ObservationParameters
from astock.research.public_results import public_snapshot
from astock.research.service import analyze
from test_research_v1 import sample, run, ASOF, PARAMS


def test_market_only_native_contract_uses_same_numbers_without_journal_or_publisher(sample, tmp_path, monkeypatch):
    import astock.research.service as service
    import astock.research.public_results as publication
    store, bundle, old = run(sample, tmp_path)
    def denied(*a, **k):
        pytest.fail('native market computation must not query Journal or call a public renderer')
    monkeypatch.setattr(service, 'journal_snapshot', denied)
    monkeypatch.setattr(publication, 'public_snapshot', denied)
    direct = analyze(store, bundle, ASOF, ObservationParameters(**PARAMS), include_journal=False)
    assert direct['features'] == old['features'] and direct['market'] == old['market'] and 'journal' not in direct
    native, memberships = market_context(store, bundle, ASOF, ObservationParameters(**PARAMS))
    assert native['protocol'] == 'MARKET_SNAPSHOT_V1' and memberships == []
    assert 'journal' not in native and 'publication' not in native and 'manual_cards' not in native
    for feature in native['features']:
        original = next(f for f in old['features'] if f['code'] == feature['code'])
        assert feature['close'] == original['close']
        assert set(native['source_hash_sets'][feature['source_hash_set_id']]) == set(original['source_hashes'])


def test_old_baseline_requires_exact_anchor_then_full_business_reproduction(sample, tmp_path, monkeypatch):
    import astock.research.service as service
    store, bundle, _ = run(sample, tmp_path)
    parameters = ObservationParameters(**PARAMS)
    original = analyze(store, bundle, ASOF, parameters, radar=True)
    original['code_hash'] = '0' * 64  # Explicit synthetic earlier execution version.
    store.save_report(original)
    baseline = public_snapshot(original)
    frozen = deepcopy(baseline)
    def denied(*a, **k):
        pytest.fail('baseline recomputation must not read live private Journal')
    monkeypatch.setattr(service, 'journal_snapshot', denied)
    assert verified_market_context(baseline, store) == []
    assert baseline == frozen
    changed = deepcopy(baseline); changed['features'][0]['close'] += 1
    with pytest.raises(ValueError, match='ORIGINAL_ANCHOR_CHANGED'):
        verified_market_context(changed, store)
    missing = deepcopy(baseline); missing['publication']['private_snapshot_hash'] = 'f' * 64
    with pytest.raises(ValueError, match='ORIGINAL_ANCHOR_REQUIRED'):
        verified_market_context(missing, store)
    real_analyze = service.analyze
    def wrong_numbers(*a, **k):
        result = real_analyze(*a, **k)
        result['features'][0]['close'] += 1
        return result
    monkeypatch.setattr(service, 'analyze', wrong_numbers)
    with pytest.raises(ValueError, match='REPRODUCTION_MISMATCH'):
        verified_market_context(baseline, store)
