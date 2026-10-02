"""Full synthetic133 offline audit and all downstream admission entry points."""

import hashlib
import json
from uuid import UUID, uuid4

from astock.data.warehouse_lock import warehouse_connection
import duckdb
import pytest
from typer.testing import CliRunner

from astock.cli.main import app
from astock.data.receipt_integrity import audit_slice_batch
from astock.data.slice_capture import capture_slices
from astock.data.slice_curate import curate_slices
from astock.data.slice_dq import dq_slices
from astock.data.slice_errors import ReceiptIntegrityError
from astock.data.tushare_client import TushareClient
from test_slice_capture import slice_root, SyntheticCaptureClient, settings

SHA = 'a' * 40


@pytest.fixture
def captured(slice_root):
    result = capture_slices(slice_root, settings(), live=True, client=SyntheticCaptureClient(), commit=SHA)
    assert result['status'] == 'CAPTURED'
    return slice_root, UUID(result['batch_id'])


def test_token_free_readonly_cli_and_legacy_mode_are_separate(captured, monkeypatch):
    root, batch = captured; path = root / 'data/warehouse/astock.duckdb'
    (root / '.env').write_text('TUSHARE_TOKEN=synthetic-must-not-be-read\n')
    from astock.cli import main
    from astock.data import receipt_integrity
    calls = []
    def deny(*args, **kwargs):
        calls.append(True)
        raise AssertionError('Forbidden credential/client/claim/migration path')
    monkeypatch.setattr(main, 'get_project_root', lambda: root)
    monkeypatch.setattr(main, 'load_settings', deny)
    monkeypatch.setattr(TushareClient, '__init__', deny)
    monkeypatch.setattr(TushareClient, '_fetch', deny)
    monkeypatch.setattr(TushareClient, 'fetch_slice', deny)
    from astock.data import raw_writer, slice_plan, receipt_migration
    monkeypatch.setattr(raw_writer, 'migrate', deny)
    monkeypatch.setattr(slice_plan, 'claim_request', deny)
    monkeypatch.setattr(receipt_migration, 'apply_receipt_integrity_upgrade', deny)
    monkeypatch.setattr(receipt_integrity, 'verification_commit', lambda _: 'c' * 40)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    files_before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (root / 'data').rglob('*') if p.is_file()}
    command = ['data', 'slice', 'audit', '--batch', str(batch)]
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 0, result.output
    summary = json.loads(result.output)
    assert summary['verdict'] == 'VALID' and summary['checked_count'] == 133 and summary['failure_count'] == 0
    assert summary['verification_code_commit'] == 'c' * 40
    assert before == hashlib.sha256(path.read_bytes()).hexdigest()
    assert files_before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (root / 'data').rglob('*') if p.is_file()}
    with warehouse_connection(str(path)) as db:
        db.execute('DROP TABLE slice_receipt_completion_binding')
        db.execute('DROP TABLE slice_receipt_validation_audit')
        db.execute('DELETE FROM schema_version WHERE version=7')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    blocked = CliRunner().invoke(app, command)
    assert blocked.exit_code == 1
    assert json.loads(blocked.output)['reasons'] == {'BINDING_SCHEMA_REQUIRED': 133}
    legacy = CliRunner().invoke(app, command + ['--legacy-preflight'])
    assert legacy.exit_code == 0
    assert json.loads(legacy.output)['verdict'] == 'LEGACY_PREFLIGHT_EVIDENCE_VALID'
    assert json.loads(legacy.output)['binding'] == 'UNREGISTERED'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before and not calls


def test_audit_missing_evidence_fails_without_creating_database(slice_root):
    path = slice_root / 'data/warehouse/astock.duckdb'
    path.unlink()  # Synthetic fixture only.
    result = audit_slice_batch(slice_root, uuid4(), verification_sha=SHA)
    assert result['verdict'] == 'BLOCKED' and result['reasons'] == {'EVIDENCE_MISSING': 1}
    assert not path.exists()


def test_corrupt_complete_blocks_curate_and_dq_before_any_publication(captured):
    root, batch = captured; path = root / 'data/warehouse/astock.duckdb'
    with warehouse_connection(str(path)) as db:
        db.execute("UPDATE slice_batch SET status='CURATED'")
        # Synthetic legacy-invalid row: FK already protects accepted bindings.
        db.execute('DELETE FROM slice_receipt_completion_binding WHERE ordinal=1')
        db.execute('UPDATE slice_request SET object_id=? WHERE ordinal=1', [str(uuid4())])
        before = {t: db.execute(f'SELECT * FROM {t} ORDER BY ALL').fetchall() for t in (
            'slice_request', 'ingestion_run', 'slice_batch', 'curation_run', 'dataset_date_audit', 'curated_object_manifest')}
    for run in (lambda: curate_slices(root, batch, commit=SHA), lambda: dq_slices(root, batch)):
        with pytest.raises(ReceiptIntegrityError, match='RECEIPT_OBJECT_MISMATCH'): run()
    assert not list((root / 'data/curated').rglob('*.parquet'))
    with warehouse_connection(str(path)) as db:
        assert all(db.execute(f'SELECT * FROM {t} ORDER BY ALL').fetchall() == rows for t, rows in before.items())
    result = audit_slice_batch(root, batch, verification_sha=SHA)
    assert result['checked_count'] == 132 and result['failure_count'] == 1
    assert result['reasons'] == {'RECEIPT_OBJECT_MISMATCH': 1}


def test_counts_alone_cannot_promote_captured_batch(slice_root, monkeypatch):
    from astock.data import slice_capture
    validate = slice_capture.validate_slice_batch
    def corrupt_at_promotion(root, db, batch, **kwargs):
        if kwargs.get('complete', True):
            assert db.execute('SELECT count(*),sum(attempts),count(object_id) FROM slice_request').fetchone() == (133, 133, 133)
            relative = db.execute('SELECT relative_path FROM raw_object_manifest LIMIT 1').fetchone()[0]
            meta = (root / relative).with_name('capture-contract.json')
            body = json.loads(meta.read_bytes()); body['object_id'] = str(uuid4())
            meta.write_text(json.dumps(body))  # Synthetic fault after exact completion.
        return validate(root, db, batch, **kwargs)
    monkeypatch.setattr(slice_capture, 'validate_slice_batch', corrupt_at_promotion)
    client = SyntheticCaptureClient()
    result = capture_slices(slice_root, settings(), live=True, client=client, commit=SHA)
    assert len(client.calls) == 133 and result['status'] == 'BLOCKED'
    assert result['failure'] == 'CAPTURE_CONTRACT_MISMATCH'
    with warehouse_connection(str(slice_root / 'data/warehouse/astock.duckdb')) as db:
        assert db.execute('SELECT status FROM slice_batch').fetchone() == ('RUNNING',)
        assert db.execute("SELECT count(*) FROM slice_request WHERE status='COMPLETE'").fetchone() == (133,)
