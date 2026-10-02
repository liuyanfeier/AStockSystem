"""Independent G1 review regressions; synthetic storage and denied network only."""

import shutil
from datetime import datetime, timezone

import duckdb
import pytest

from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.raw_writer import RawWriter, migrate
from astock.data.receipt_integrity import batch_requests, validate_slice_batch, validate_slice_receipt
from astock.data.receipt_migration import apply_receipt_integrity_upgrade
from astock.data.receipt_schema import require_integrity_schema
from astock.data.slice_capture import capture_slices, identity_state
from astock.data.slice_errors import ReceiptIntegrityError
from astock.data.slice_plan import claim_request, create_batch, request_manifest, resume_batch
from astock.paths import get_project_root
from test_receipt_integrity import legacy, SHA
from test_receipt_audit import captured
from test_receipt_migration import old_rows, files
from test_slice_capture import slice_root, settings, SyntheticCaptureClient


def test_legacy_pending_with_existing_capture_blocks_before_upgrade_ddl(legacy):
    db = legacy['db']
    db.execute("UPDATE slice_request SET status='PENDING',attempts=0,object_id=NULL WHERE ordinal=1")
    before, inventory = old_rows(db), files(legacy['root'])
    with pytest.raises(ReceiptIntegrityError, match='PENDING_EXECUTION_CONFLICT'):
        apply_receipt_integrity_upgrade(legacy['root'], db, verification_sha=SHA)
    with pytest.raises(ReceiptIntegrityError, match='PENDING_EXECUTION_CONFLICT'):
        claim_request(db, legacy['batch'], 1)
    assert old_rows(db) == before and files(legacy['root']) == inventory
    assert db.execute("SELECT count(*) FROM information_schema.tables WHERE table_name LIKE 'slice_receipt_%'").fetchone() == (0,)


def test_pending_binding_conflict_is_independent_of_run_counters_and_manifest(legacy):
    db = legacy['db']
    apply_receipt_integrity_upgrade(legacy['root'], db, verification_sha=SHA)
    pending = batch_requests(db, legacy['batch'])[2]
    values = list(db.execute('SELECT * FROM slice_receipt_completion_binding').fetchone())
    # Synthetic FK-valid, application-incoherent binding: pending run has no raw
    # and zero counters, but an accepted row wrongly points to its request/run.
    values[1:4] = [pending['ordinal'], pending['request_id'], pending['run_id']]
    db.execute('DELETE FROM slice_receipt_completion_binding')
    db.execute('INSERT INTO slice_receipt_completion_binding VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', values)
    before, inventory = old_rows(db), files(legacy['root'])
    binding_before = db.execute('SELECT * FROM slice_receipt_completion_binding').fetchall()
    for operation in (
        lambda: validate_slice_batch(legacy['root'], db, legacy['batch'], complete=False),
        lambda: claim_request(db, legacy['batch'], pending['ordinal']),
        lambda: apply_receipt_integrity_upgrade(legacy['root'], db, verification_sha=SHA),
    ):
        with pytest.raises(ReceiptIntegrityError, match='PENDING_EXECUTION_CONFLICT'):
            operation()
    assert old_rows(db) == before and files(legacy['root']) == inventory
    assert db.execute('SELECT * FROM slice_receipt_completion_binding').fetchall() == binding_before


@pytest.mark.parametrize('fault', ['success', 'requests', 'raw_count', 'row_count', 'raw',
                                  'binding', 'finished', 'error'])
def test_pending_execution_conflict_blocks_resume_claim_and_provider_before_mutation(slice_root, monkeypatch, fault):
    path = slice_root / 'data/warehouse/astock.duckdb'
    with duckdb.connect(str(path)) as db:
        identity, _, _ = identity_state(db)
        batch = create_batch(slice_root, db, commit=SHA, identity_hash=identity,
                             knowledge_as_of=datetime.now(timezone.utc))
        req = batch_requests(db, batch)[1]
        run_id = str(req['run_id'])
        if fault in ('raw', 'binding'):
            contract = next(c for c in load_contracts(
                slice_root, catalog_version='v2') if c.dataset == 'daily')
            params = RequestParams.model_validate_json(req['request_params'])
            table = SyntheticCaptureClient().fetch_slice(contract, params)
            raw_run = (next(r['run_id'] for r in batch_requests(db, batch)
                            if r['dataset'] == 'daily' and r['ordinal'] != req['ordinal'])
                       if fault == 'binding' else req['run_id'])
            raw = RawWriter(slice_root, db).write(raw_run, 'daily', 0, table, params)
            if fault == 'binding':
                db.execute('INSERT INTO slice_receipt_completion_binding VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    [str(batch), req['ordinal'], req['request_id'], run_id, str(raw.object_id),
                     request_manifest(slice_root)['plan_hash'], req['contract_hash'], 'c' * 64, 'd' * 64,
                     'R1_EXACT_RECEIPT_V1', SHA, datetime.now(timezone.utc)])
            # A manifest/binding must independently block even with reset run counters.
            db.execute("UPDATE ingestion_run SET status='RUNNING',finished_at=NULL,request_count=0,raw_object_count=0,row_count=0 WHERE run_id=?", [run_id])
        else:
            assignments = dict(success="status='SUCCEEDED',finished_at=current_timestamp", requests='request_count=1',
                               raw_count='raw_object_count=1', row_count='row_count=1',
                               finished="status='CANCELLED',finished_at=current_timestamp", error="error_category='INVALID_RESPONSE'")
            db.execute(f'UPDATE ingestion_run SET {assignments[fault]} WHERE run_id=?', [run_id])
        before, inventory = old_rows(db), files(slice_root)
        binding_before = db.execute('SELECT * FROM slice_receipt_completion_binding ORDER BY ALL').fetchall()
        audit_before = db.execute('SELECT * FROM slice_receipt_validation_audit ORDER BY ALL').fetchall()
        for operation in (
            lambda: validate_slice_batch(slice_root, db, batch, complete=False),
            lambda: resume_batch(db, batch, root=slice_root, expected_plan_hash=request_manifest(slice_root)['plan_hash']),
            lambda: claim_request(db, batch, 1),
            lambda: apply_receipt_integrity_upgrade(slice_root, db, verification_sha=SHA),
        ):
            with pytest.raises(ReceiptIntegrityError, match='PENDING_EXECUTION_CONFLICT'):
                operation()
        assert old_rows(db) == before
        assert files(slice_root) == inventory
    inventory = files(slice_root)  # Snapshot the checkpointed synthetic DB, without a transient WAL.
    calls = []
    def deny(*args, **kwargs):
        calls.append(True)
        raise AssertionError('Preflight must precede provider/claim/fetch')
    from astock.data import slice_capture
    monkeypatch.setattr(slice_capture, 'TushareClient', deny)
    monkeypatch.setattr(slice_capture, 'claim_request', deny)
    monkeypatch.setattr(SyntheticCaptureClient, 'fetch_slice', deny)
    result = capture_slices(slice_root, settings(), live=True, batch_id=batch, commit=SHA)
    assert result['status'] == 'BLOCKED' and result['failure'] == 'PENDING_EXECUTION_CONFLICT'
    assert calls == []
    with duckdb.connect(str(path)) as db:
        assert old_rows(db) == before
        assert db.execute('SELECT * FROM slice_receipt_completion_binding ORDER BY ALL').fetchall() == binding_before
        assert db.execute('SELECT * FROM slice_receipt_validation_audit ORDER BY ALL').fetchall() == audit_before
    # Only a new, private operation-block artifact is permitted; old files identical.
    assert all(files(slice_root)[name] == value for name, value in inventory.items())
    assert set(files(slice_root)) - set(inventory) == {
        str(p.relative_to(slice_root)) for p in (slice_root / f'data/private/phase1c1/{batch}').glob('operation-block-*.json')}


@pytest.fixture
def empty007(tmp_path):
    shutil.copytree(get_project_root() / 'sql', tmp_path / 'sql')
    with duckdb.connect(':memory:') as db:
        migrate(db, tmp_path)
        yield tmp_path, db


@pytest.mark.parametrize('fault', ['migration_id', 'dummy_tables', 'nullable', 'type', 'binding_pk',
                                  'audit_pk', 'run_unique', 'object_unique', 'run_fk', 'request_fk',
                                  'audit_fk', 'ordinal_check', 'hash_check', 'audit_check', 'shadow_schema',
                                  'temporary_shadow'])
def test_empty_repeat_and_normal_admission_reject_wrong_schema_without_repair(empty007, fault):
    root, db = empty007
    ddl = (get_project_root() / 'sql/007_slice_receipt_integrity.sql').read_text()
    changes = dict(nullable=('request_id VARCHAR NOT NULL', 'request_id VARCHAR'),
                   type=('checked_count INTEGER', 'checked_count BIGINT'),
                   binding_pk=('PRIMARY KEY (batch_id,ordinal),', 'UNIQUE (batch_id,ordinal),'),
                   audit_pk=('audit_id UUID PRIMARY KEY', 'audit_id UUID NOT NULL'),
                   run_unique=('run_id UUID NOT NULL UNIQUE', 'run_id UUID NOT NULL'),
                   object_unique=('object_id UUID NOT NULL UNIQUE', 'object_id UUID NOT NULL'),
                   run_fk=(' REFERENCES ingestion_run(run_id)', ''),
                   request_fk=(',\n    FOREIGN KEY (batch_id,request_id) REFERENCES slice_request(batch_id,request_id)', ''),
                   audit_fk=(' REFERENCES slice_batch(batch_id)', ''),
                   ordinal_check=('CHECK (ordinal BETWEEN 0 AND 132)', 'CHECK (ordinal >= 0)'),
                   hash_check=("CHECK (regexp_full_match(plan_hash,'[0-9a-f]{64}'))", "CHECK (length(plan_hash)>0)"),
                   audit_check=('CHECK (checked_count>=0)', 'CHECK (checked_count>=-1)'))
    if fault == 'dummy_tables':
        db.execute('CREATE TABLE slice_receipt_completion_binding(dummy INTEGER); CREATE TABLE slice_receipt_validation_audit(dummy INTEGER)')
    else:
        if fault in changes:
            old, new = changes[fault]
            assert old in ddl
            ddl = ddl.replace(old, new)
        db.execute(ddl)
    db.execute("INSERT INTO schema_version(version,migration_id,description) VALUES (7,?,'synthetic')",
               ['wrong' if fault == 'migration_id' else '007_slice_receipt_integrity'])
    if fault == 'shadow_schema':
        db.execute('CREATE SCHEMA shadow; CREATE TABLE shadow.slice_receipt_validation_audit(dummy INTEGER)')
    if fault == 'temporary_shadow':
        db.execute('CREATE TEMP TABLE slice_receipt_validation_audit(dummy INTEGER)')
    before = db.execute('SELECT * FROM schema_version ORDER BY version').fetchall()
    catalog_before = db.execute('SELECT database_name,schema_name,table_name,sql FROM duckdb_tables() ORDER BY ALL').fetchall()
    for operation in (lambda: require_integrity_schema(db),
                      lambda: apply_receipt_integrity_upgrade(root, db, verification_sha=SHA)):
        with pytest.raises(ReceiptIntegrityError, match='BINDING_SCHEMA_REQUIRED|UPGRADE_SCHEMA_CONFLICT'):
            operation()
    assert db.execute('SELECT * FROM schema_version ORDER BY version').fetchall() == before
    assert db.execute('SELECT database_name,schema_name,table_name,sql FROM duckdb_tables() ORDER BY ALL').fetchall() == catalog_before


def test_full_complete_batch_does_not_hide_wrong_audit_table(captured):
    root, batch = captured
    with duckdb.connect(str(root / 'data/warehouse/astock.duckdb')) as db:
        db.execute('DROP TABLE slice_receipt_validation_audit; CREATE TABLE slice_receipt_validation_audit(dummy INTEGER)')
        before, inventory = old_rows(db), files(root)
        binding_before = db.execute('SELECT * FROM slice_receipt_completion_binding ORDER BY ALL').fetchall()
        assert len(binding_before) == 133
        for operation in (lambda: validate_slice_receipt(root, db, batch_requests(db, batch)[1]),
                          lambda: validate_slice_batch(root, db, batch),
                          lambda: apply_receipt_integrity_upgrade(root, db, verification_sha=SHA)):
            with pytest.raises(ReceiptIntegrityError, match='BINDING_SCHEMA_REQUIRED'):
                operation()
        assert old_rows(db) == before and files(root) == inventory
        assert db.execute('SELECT * FROM slice_receipt_completion_binding ORDER BY ALL').fetchall() == binding_before
        assert db.execute('SELECT * FROM slice_receipt_validation_audit').fetchall() == []


def test_catalog_normalization_accepts_whitespace_and_named_constraints(empty007):
    root, db = empty007
    ddl = (get_project_root() / 'sql/007_slice_receipt_integrity.sql').read_text()
    ddl = ddl.replace('PRIMARY KEY (batch_id,ordinal)', 'CONSTRAINT named_pk PRIMARY KEY (batch_id, ordinal)')
    ddl = ddl.replace("plan_hash,'[0-9a-f]{64}'", "plan_hash , '[0-9a-f]{64}'")
    db.execute(ddl)
    db.execute("INSERT INTO schema_version(version,migration_id,description) VALUES (7,'007_slice_receipt_integrity','synthetic')")
    require_integrity_schema(db)
    assert apply_receipt_integrity_upgrade(root, db, verification_sha=SHA)['result'] == 'ALREADY_VALID'


def test_wrong_deployment_ddl_rolls_back_before_schema_publication(empty007):
    root, db = empty007
    path = root / 'sql/007_slice_receipt_integrity.sql'
    path.write_text(path.read_text().replace('CHECK (checked_count>=0)', 'CHECK (checked_count>=-1)'))
    before = old_rows(db)
    with pytest.raises(ReceiptIntegrityError, match='BINDING_SCHEMA_REQUIRED'):
        apply_receipt_integrity_upgrade(root, db, verification_sha=SHA)
    assert old_rows(db) == before
    assert db.execute("SELECT count(*) FROM information_schema.tables WHERE table_name LIKE 'slice_receipt_%'").fetchone() == (0,)
