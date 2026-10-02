"""Explicit007 fresh/upgrade/repeat/fault rollback and practical FK guarantees."""

import hashlib
from uuid import uuid4
from datetime import datetime, timezone

import duckdb
import pytest

from astock.data.raw_writer import migrate
from astock.data.receipt_integrity import batch_requests, validate_slice_receipt
from astock.data.receipt_migration import apply_receipt_integrity_upgrade
from astock.data.slice_capture import finalize_receipt
from astock.data.slice_errors import ReceiptIntegrityError
from astock.data.warehouse_lock import WarehouseConnectionProxy
from test_receipt_integrity import legacy, SHA


OLD_TABLES = ('schema_version', 'ingestion_run', 'raw_object_manifest', 'slice_batch',
              'slice_request', 'slice_curated_binding', 'security_identifier_history',
              'security_venue_history', 'identity_quarantine', 'curation_run',
              'curated_object_manifest', 'dataset_date_audit')


def old_rows(db):
    return {table: db.execute(f'SELECT * FROM {table} ORDER BY ALL').fetchall() for table in OLD_TABLES}


def files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / 'data').rglob('*') if p.is_file()}


class FaultDB(WarehouseConnectionProxy):
    def __init__(self, db, pattern):
        super().__init__(db)
        self.db = db
        self.pattern = pattern

    def execute(self, sql, *args):
        if self.pattern in sql:
            if self.pattern == 'CREATE TABLE slice_receipt_validation_audit':
                # First table really exists inside the transaction before this fault.
                self.db.execute(sql.split(self.pattern)[0])
            raise RuntimeError('synthetic injected fault')
        return self.db.execute(sql, *args)


def test_generic_migration_remains006_and_does_not_upgrade_legacy(legacy):
    before = old_rows(legacy['db'])
    migrate(legacy['db'], legacy['root'])
    assert old_rows(legacy['db']) == before
    assert legacy['db'].execute('SELECT max(version) FROM schema_version').fetchone() == (6,)


def test_explicit_fresh_upgrade_is_empty_and_repeatable(tmp_path):
    import shutil
    from astock.paths import get_project_root
    shutil.copytree(get_project_root() / 'sql', tmp_path / 'sql')
    with duckdb.connect(':memory:') as db:
        migrate(db, tmp_path)
        for i in range(2):
            result = apply_receipt_integrity_upgrade(tmp_path, db, verification_sha=SHA)
            assert result['result'] == ('UPGRADED' if i == 0 else 'ALREADY_VALID')
            assert db.execute('SELECT version FROM schema_version ORDER BY version').fetchall() == [(i,) for i in range(1, 8)]
            assert db.execute('SELECT count(*) FROM slice_receipt_completion_binding').fetchone() == (0,)
            assert db.execute('SELECT count(*) FROM slice_receipt_validation_audit').fetchone() == (0,)


def test_populated_upgrade_preserves_every_old_row_and_file_and_repeat(legacy):
    before = old_rows(legacy['db']); inventory = files(legacy['root'])
    for _ in range(2):
        apply_receipt_integrity_upgrade(legacy['root'], legacy['db'], verification_sha='c' * 40)
        after = old_rows(legacy['db'])
        assert after.pop('schema_version')[:6] == before['schema_version']
        assert after == {k: v for k, v in before.items() if k != 'schema_version'}
        assert files(legacy['root']) == inventory
        assert legacy['db'].execute('SELECT count(*) FROM slice_receipt_completion_binding').fetchone() == (1,)
        assert legacy['db'].execute('SELECT count(*) FROM slice_receipt_validation_audit').fetchone() == (1,)
        validate_slice_receipt(legacy['root'], legacy['db'], legacy['req'])


@pytest.mark.parametrize('pattern', ['CREATE TABLE slice_receipt_completion_binding',
                                    'CREATE TABLE slice_receipt_validation_audit',
                                    'INSERT INTO slice_receipt_completion_binding',
                                    'INSERT INTO slice_receipt_validation_audit',
                                    'INSERT INTO schema_version(version'])
def test_ddl_mid_binding_audit_and_version_failure_roll_back_entire_upgrade(legacy, pattern):
    before = old_rows(legacy['db']); inventory = files(legacy['root'])
    with pytest.raises(RuntimeError, match='synthetic injected'):
        apply_receipt_integrity_upgrade(legacy['root'], FaultDB(legacy['db'], pattern), verification_sha=SHA)
    assert old_rows(legacy['db']) == before
    assert files(legacy['root']) == inventory
    assert legacy['db'].execute("SELECT count(*) FROM information_schema.tables WHERE table_name LIKE 'slice_receipt_%'").fetchone() == (0,)
    # A new explicit attempt succeeds on this synthetic DB, without half-applied DDL.
    apply_receipt_integrity_upgrade(legacy['root'], legacy['db'], verification_sha=SHA)
    assert legacy['db'].execute('SELECT max(version) FROM schema_version').fetchone() == (7,)


def test_incomplete_or_conflicting_schema_is_not_silently_accepted(legacy):
    legacy['db'].execute('CREATE TABLE slice_receipt_completion_binding(dummy INTEGER)')
    before = old_rows(legacy['db'])
    with pytest.raises(ReceiptIntegrityError, match='UPGRADE_SCHEMA_CONFLICT'):
        apply_receipt_integrity_upgrade(legacy['root'], legacy['db'], verification_sha=SHA)
    assert old_rows(legacy['db']) == before


@pytest.mark.parametrize('column,value', [('batch_id', 'missing_uuid'),
                                         ('request_id', 'unknown_request'), ('run_id', 'missing_uuid'),
                                         ('object_id', 'missing_uuid')])
def test_binding_foreign_keys_reject_missing_parents(legacy, column, value):
    apply_receipt_integrity_upgrade(legacy['root'], legacy['db'], verification_sha=SHA)
    # Remove only the synthetic accepted row, then attempt a corrupted reference.
    legacy['db'].execute('DELETE FROM slice_receipt_completion_binding')
    proof = validate_slice_receipt(legacy['root'], legacy['db'], legacy['req'], require_binding=False)
    fields = proof.binding_fields()
    fields[column] = str(uuid4()) if value == 'missing_uuid' else value
    values = [*fields.values(), SHA, datetime.now(timezone.utc)]
    with pytest.raises(duckdb.ConstraintException):
        legacy['db'].execute('INSERT INTO slice_receipt_completion_binding VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', values)


def test_unique_binding_and_application_coherence_are_distinct(legacy):
    apply_receipt_integrity_upgrade(legacy['root'], legacy['db'], verification_sha=SHA)
    values = legacy['db'].execute('SELECT * FROM slice_receipt_completion_binding').fetchone()
    with pytest.raises(duckdb.ConstraintException):
        legacy['db'].execute('INSERT INTO slice_receipt_completion_binding VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', values)
    # All parents exist, but a different request is still an invalid application proof.
    other = batch_requests(legacy['db'], legacy['batch'])[2]
    legacy['db'].execute('UPDATE slice_receipt_completion_binding SET request_id=?', [other['request_id']])
    with pytest.raises(ReceiptIntegrityError, match='BINDING_MISMATCH'):
        validate_slice_receipt(legacy['root'], legacy['db'], legacy['req'])
    with pytest.raises(ReceiptIntegrityError):
        apply_receipt_integrity_upgrade(legacy['root'], legacy['db'], verification_sha=SHA)


@pytest.mark.parametrize('pattern', ["UPDATE ingestion_run SET status='SUCCEEDED'",
                                    "UPDATE slice_request SET status='COMPLETE'",
                                    'INSERT INTO slice_receipt_completion_binding',
                                    'INSERT INTO slice_receipt_validation_audit'])
def test_finalize_transaction_failure_preserves_in_flight_without_binding(legacy, pattern):
    db = legacy['db']
    # Synthetic legacy reset prepares an exact candidate; never applied to real data.
    db.execute("UPDATE slice_request SET status='IN_FLIGHT',object_id=NULL WHERE ordinal=1")
    db.execute("UPDATE ingestion_run SET status='RUNNING',finished_at=NULL WHERE run_id=?", [str(legacy['req']['run_id'])])
    apply_receipt_integrity_upgrade(legacy['root'], db, verification_sha=SHA)
    before = old_rows(db); inventory = files(legacy['root'])
    candidate = batch_requests(db, legacy['batch'])[1]
    with pytest.raises(RuntimeError, match='synthetic injected'):
        finalize_receipt(legacy['root'], FaultDB(db, pattern), candidate, legacy['contract'], verification_sha=SHA)
    assert old_rows(db) == before and files(legacy['root']) == inventory
    assert db.execute('SELECT count(*) FROM slice_receipt_completion_binding').fetchone() == (0,)
    assert db.execute('SELECT count(*) FROM slice_receipt_validation_audit').fetchone() == (0,)
