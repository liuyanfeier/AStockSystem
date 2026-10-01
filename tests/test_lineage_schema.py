import json
from datetime import datetime, timezone

import duckdb
import pytest

from astock.paths import get_project_root


RUN = '00000000-0000-0000-0000-000000000001'
OBJECT = '00000000-0000-0000-0000-000000000002'
NOW = datetime(2024, 1, 3, tzinfo=timezone.utc)


@pytest.fixture
def db():
    with duckdb.connect(':memory:') as connection:
        for name in ('001_foundation_schema.sql', '002_provider_lineage.sql'):
            connection.execute((get_project_root() / 'sql' / name).read_text())
        yield connection


def insert(db, table, values):
    columns = ', '.join(values)
    marks = ', '.join('?' for _ in values)
    db.execute(f'INSERT INTO {table} ({columns}) VALUES ({marks})', list(values.values()))


def run_values():
    return dict(run_id=RUN, source='tushare', dataset='daily', mode='AUDIT',
                started_at=NOW, status='RUNNING', code_commit='a' * 40,
                config_hash='b' * 64, provider_client_version='0.0.1')


def raw_values():
    return dict(object_id=OBJECT, run_id=RUN, dataset='daily',
                relative_path=f'data/raw/tushare/daily/run_id={RUN}/part-000.parquet',
                sha256='c' * 64, retrieved_at=NOW, row_count=0, schema_hash='d' * 64,
                request_params=json.dumps({'trade_date': '2024-01-03'}))


def test_migration_is_repeatable_and_does_not_seed_market_or_run_data(db):
    db.execute((get_project_root() / 'sql/002_provider_lineage.sql').read_text())
    assert db.execute('SELECT version FROM schema_version ORDER BY version').fetchall() == [(1,), (2,)]
    tables = {row[0] for row in db.execute('SHOW TABLES').fetchall()}
    assert tables == {'security_master', 'trade_calendar', 'market_rule_history', 'data_quality_log',
                      'research_hypothesis', 'schema_version', 'ingestion_run', 'raw_object_manifest'}
    for table in tables - {'schema_version'}:
        assert db.execute(f'SELECT count(*) FROM {table}').fetchone() == (0,)


@pytest.mark.parametrize('change', [
    {'request_count': -1}, {'row_count': -1}, {'raw_object_count': -1},
    {'status': 'DONE'}, {'mode': 'TRADING'}, {'source': 'token-secret'},
    {'code_commit': 'invalid'}, {'config_hash': 'invalid'}, {'provider_client_version': 'token-secret'},
    {'requested_start': '2024-01-04', 'requested_end': '2024-01-03'},
    {'finished_at': '2024-01-02T00:00:00Z', 'status': 'FAILED'},
    {'status': 'SUCCEEDED'}, {'finished_at': NOW},
    {'error_category': 'raw-provider-message'}, {'error_http_status': 401},
])
def test_run_constraints(db, change):
    with pytest.raises(duckdb.Error):
        insert(db, 'ingestion_run', run_values() | change)


def test_valid_completed_run_and_manifest(db):
    insert(db, 'ingestion_run', run_values() | {'status': 'FAILED', 'finished_at': NOW,
                                               'error_category': 'AUTH', 'error_provider_code': 40101})
    insert(db, 'raw_object_manifest', raw_values())
    assert db.execute('SELECT row_count FROM raw_object_manifest').fetchone() == (0,)


@pytest.mark.parametrize('change', [
    {'run_id': OBJECT}, {'dataset': 'daily_basic'}, {'sha256': 'invalid'},
    {'schema_hash': 'f' * 63}, {'row_count': -1}, {'relative_path': '../private/file'},
    {'min_event_date': '2024-01-03'},
    {'min_event_date': '2024-01-04', 'max_event_date': '2024-01-03'},
    {'request_params': '{"token":"synthetic-not-a-real-credential"}'},
    {'request_params': '{"ts_code":"synthetic-not-a-real-credential"}'},
    {'request_params': '{"ts_code":{"token":"synthetic"}}'},
    {'request_params': '{"exchange":null}'}, {'request_params': '[]'},
    {'request_params': '{"trade_date":"2024-99-99"}'},
    {'request_params': '{"start_date":"2024-01-04","end_date":"2024-01-03"}'},
    {'request_params': '{"ts_code":"000001.SZ","ts_code":"synthetic-secret"}'},
])
def test_raw_constraints_and_secret_boundary(db, change):
    insert(db, 'ingestion_run', run_values())
    with pytest.raises(duckdb.Error):
        insert(db, 'raw_object_manifest', raw_values() | change)
