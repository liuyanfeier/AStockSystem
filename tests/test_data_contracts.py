from copy import deepcopy

import pytest
from pydantic import ValidationError
from typer.main import get_command
from typer.testing import CliRunner

from astock.cli.main import app
from astock.data.contracts import DATASETS, DatasetContract, load_contracts
from astock.paths import get_project_root


def test_all_versioned_contracts_validate_and_unknown_caps_stay_unknown():
    contracts = load_contracts(get_project_root())
    assert {c.dataset for c in contracts} == set(DATASETS)
    assert {c.dataset for c in contracts if c.max_rows is None} == {
        'trade_cal', 'adj_factor', 'index_daily', 'index_classify',
    }
    assert all(c.availability_policy == 'UNKNOWN_UNTIL_EVIDENCE' for c in contracts)
    assert all(c.documentation_checked_on.isoformat() == '2026-10-01' for c in contracts)


@pytest.mark.parametrize('change', [
    {'endpoint': 'http://api.tushare.pro'}, {'max_rows': 0}, {'max_rows': -1},
    {'natural_key': ['missing_column']}, {'required_fields': []},
    {'required_fields': ['ts_code', 'ts_code']}, {'timezone': 'UTC'},
    {'availability_policy': 'ASSUME_CLOSE'}, {'contract_version': '2.0'},
    {'units': {'nonexistent_column': 'yuan'}}, {'fetch_partition': ['']},
])
def test_contract_rejects_unsafe_or_ambiguous_configuration(change):
    payload = deepcopy(load_contracts(get_project_root())[0].model_dump())
    payload.update(change)
    with pytest.raises(ValidationError):
        DatasetContract.model_validate(payload)


def test_contract_catalog_requires_all_tier_a_files(tmp_path):
    with pytest.raises(ValueError, match='twelve'):
        load_contracts(tmp_path)


def test_contract_diagnostic_is_offline_read_only_and_has_no_ingestion_commands():
    root = get_project_root()
    before = set(root.glob('data/**/*'))
    result = CliRunner().invoke(app, ['data', 'contracts'])
    assert result.exit_code == 0, result.output
    assert 'Contracts: PASS (12)' in result.output
    assert 'UNKNOWN' in result.output
    assert set(get_command(app).commands['data'].commands) == {'contracts'}
    assert set(root.glob('data/**/*')) == before


def test_contract_diagnostic_suppresses_invalid_yaml(tmp_path, monkeypatch):
    from astock.cli import main

    directory = tmp_path / 'config/contracts/v1'
    directory.mkdir(parents=True)
    (directory / 'daily.yaml').write_text('synthetic-secret: [')
    monkeypatch.setattr(main, 'get_project_root', lambda: tmp_path)
    result = CliRunner().invoke(app, ['data', 'contracts'])
    assert result.exit_code == 1
    assert 'Contracts: FAIL' in result.output
    assert 'synthetic-secret' not in result.output
