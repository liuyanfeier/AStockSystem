"""One verified source read per calculation, no cross-task cache or admission shortcut."""
from copy import deepcopy
from pathlib import Path

import pytest

from astock.decision.increment import market_context
from astock.features.market import ObservationParameters
from astock.research.core import ResearchError, encoded, read_json
from astock.research.service import analyze
from astock.research.strategies import observations_from_snapshot, observe_setups
from astock.screening.strategy_models import StrategyParameters
from test_strategy_rules import source_rows
from test_research_v1 import PARAMS

AS_OF = '2026-12-31T16:00:00+08:00'


class SourceFixture:
    """Pure unit fixture; native integration separately exercises ResearchStore validation."""
    def __init__(self, path: Path):
        self.path = path
        self.calls = []
        manifest, rows = source_rows()
        manifest.update(protocol='RESEARCH_INPUT_V1', universe_scope='WATCHLIST',
            files=[dict(sha256='a'*64, available_at='2026-10-15T00:00:00Z', evidence_grade='SYNTHETIC')])
        self.value = manifest, rows
        self.failure = None

    def snapshot(self, bundle: str, as_of: str) -> tuple[dict, dict]:
        self.calls.append((bundle, as_of))
        if self.failure:
            raise ResearchError(self.failure)
        return deepcopy(self.value)


@pytest.fixture
def source(tmp_path):
    return SourceFixture(tmp_path/'synthetic-source.duckdb')


@pytest.fixture
def policy():
    return StrategyParameters.model_validate(read_json(Path(__file__).parents[1]/'config/research/strategy-research-v1.json'))


def test_market_and_strategy_share_one_verified_read_and_preserve_inputs(source, policy):
    before = encoded(source.value)
    results = []
    def observe(manifest: dict, rows: dict) -> None:
        results.append(observations_from_snapshot(manifest, rows, ['fixture'], AS_OF,
                       manifest['window_end'], policy))
    native, memberships = market_context(source, 'fixture', AS_OF, ObservationParameters(**PARAMS),
                                         snapshot_consumer=observe)
    assert source.calls == [('fixture', AS_OF)] and not memberships
    assert native['features'][0]['close'] == 11.3
    assert results[0]['summary']['P0']['first_matches'] == 1
    assert results[0]['summary']['B0']['first_matches'] == 1
    assert results[0]['mode'] == 'OFFLINE_SYNTHETIC'
    assert encoded(source.value) == before and not source.path.exists()
    standalone = observe_setups(source, 'fixture', AS_OF, source.value[0]['window_end'], policy)
    assert encoded(results[0]) == encoded(standalone)
    assert len(source.calls) == 2  # A new request re-enters the source adapter.


def test_changed_or_failed_source_is_not_hidden_by_previous_success(source):
    consumed = []
    parameters = ObservationParameters(**PARAMS)
    market_context(source, 'fixture', AS_OF, parameters,
                   snapshot_consumer=lambda *args: consumed.append(True))
    source.failure = 'RETAINED_SOURCE_CHANGED'
    with pytest.raises(ResearchError, match='RETAINED_SOURCE_CHANGED'):
        market_context(source, 'fixture', AS_OF, parameters,
                       snapshot_consumer=lambda *args: consumed.append(True))
    assert len(source.calls) == 2 and consumed == [True]


def test_composition_conflict_stops_consumers_and_each_component_is_checked(source,tmp_path):
    other = SourceFixture(tmp_path/'other.duckdb')
    other.value[1]['daily'][-1]['close'] = 20
    other.value[1]['daily'][-1]['source_hash'] = 'b'*64
    called = []
    with pytest.raises(ResearchError, match='INCREMENT_REVISION_SELECTION_REQUIRED'):
        market_context(source, 'new', AS_OF, ObservationParameters(**PARAMS), ['old'], {'old': other},
                       snapshot_consumer=lambda *args: called.append(True))
    assert source.calls == [('new',AS_OF)] and other.calls == [('old',AS_OF)] and not called


def test_failed_consumer_propagates_and_does_not_publish_partial_success(source):
    def failed(*args) -> None:
        raise ResearchError('SYNTHETIC_CONSUMER_FAILURE')
    with pytest.raises(ResearchError, match='SYNTHETIC_CONSUMER_FAILURE'):
        analyze(source, 'fixture', AS_OF, ObservationParameters(**PARAMS),
                include_journal=False, snapshot_consumer=failed)
    assert source.calls == [('fixture',AS_OF)] and not source.path.exists()
