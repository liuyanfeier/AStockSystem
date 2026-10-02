"""Legacy006 corruptions and new exact proofs; exclusively synthetic local data."""

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import duckdb
import pytest
from typer.testing import CliRunner

from astock.cli.main import app
from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.raw_writer import RawWriter, migrate, verify_batch
from astock.data.raw_validation import strict_json, typed_params
from astock.data.receipt_integrity import (audit_slice_batch, batch_requests, frozen_context,
                                         validate_requests, validate_slice_batch, validate_slice_receipt)
from astock.data.receipt_migration import apply_receipt_integrity_upgrade
from astock.data.slice_capture import (capture_slices, finalize_receipt, identity_state,
                                      publish_capture_metadata, _object_table)
from astock.data.slice_errors import ReceiptIntegrityError
from astock.data.slice_plan import claim_request, create_batch, request_manifest, resume_batch
from astock.data.tushare_client import ProviderTable, TushareClient
from astock.paths import get_project_root
from test_slice_capture import slice_root, settings, SyntheticCaptureClient

ROOT = get_project_root()
SHA = 'a' * 40


@pytest.fixture
def legacy(tmp_path):
    shutil.copytree(ROOT / 'config', tmp_path / 'config')
    shutil.copytree(ROOT / 'sql', tmp_path / 'sql')
    with duckdb.connect(':memory:') as db:
        migrate(db, tmp_path)
        batch = create_batch(tmp_path, db, commit=SHA, identity_hash='b' * 64,
                             knowledge_as_of=datetime.now(timezone.utc))
        claim_request(db, batch, 1)
        req = batch_requests(db, batch)[1]
        contract = next(c for c in load_contracts(tmp_path, catalog_version='v2') if c.dataset == 'daily')
        params = RequestParams.model_validate_json(req['request_params'])
        table = ProviderTable(fields=contract.required_fields, items=[], retrieved_at=datetime.now(timezone.utc))
        raw = RawWriter(tmp_path, db).write(req['run_id'], 'daily', 0, table, params)
        obj = dict(object_id=str(raw.object_id), relative_path=raw.relative_path, sha256=raw.sha256)
        publish_capture_metadata(tmp_path, db, req, contract, obj)
        db.execute("UPDATE ingestion_run SET status='SUCCEEDED',finished_at=? WHERE run_id=?",
                   [datetime.now(timezone.utc), str(req['run_id'])])
        db.execute("UPDATE slice_request SET status='COMPLETE',object_id=? WHERE ordinal=1", [str(raw.object_id)])
        yield dict(root=tmp_path, db=db, batch=batch, req=batch_requests(db, batch)[1], raw=raw,
                   contract=contract, params=params, table=table)


def prove(env, **kwargs):
    req = batch_requests(env['db'], env['batch'])[1]
    return validate_slice_receipt(env['root'], env['db'], req, require_binding=False, **kwargs)


def test_valid_empty_object_is_exact_legacy_evidence_but_not_admitted(legacy):
    proof = prove(legacy)
    assert proof.table.items == [] and proof.object['object_id'] == str(legacy['raw'].object_id)
    assert verify_batch(legacy['root'], legacy['db'], [legacy['req']['run_id']])
    with pytest.raises(ReceiptIntegrityError, match='BINDING_SCHEMA_REQUIRED'):
        validate_slice_receipt(legacy['root'], legacy['db'], legacy['req'])
    before = legacy['db'].execute('SELECT * FROM slice_request').fetchall()
    apply_receipt_integrity_upgrade(legacy['root'], legacy['db'], verification_sha='c' * 40)
    assert legacy['db'].execute('SELECT * FROM slice_request').fetchall() == before
    assert validate_slice_receipt(legacy['root'], legacy['db'], legacy['req']).table.items == []
    assert legacy['db'].execute('SELECT verification_code_commit FROM slice_receipt_completion_binding').fetchone() == ('c' * 40,)
    assert legacy['db'].execute('SELECT DISTINCT code_commit FROM ingestion_run').fetchall() == [(SHA,)]


@pytest.mark.parametrize('requested', ['empty', 'missing', 'duplicate', 'zero_manifest'])
def test_generic_verify_rejects_empty_missing_duplicate_zero_object(legacy, requested):
    runs = {'empty': [], 'missing': [uuid4()], 'duplicate': [legacy['req']['run_id']] * 2,
            'zero_manifest': [batch_requests(legacy['db'], legacy['batch'])[0]['run_id']]}
    assert verify_batch(legacy['root'], legacy['db'], runs[requested]) is False


def test_generic_multipart_valid_but_slice_rejects_two_objects(legacy):
    db = legacy['db']
    RawWriter(legacy['root'], db).write(legacy['req']['run_id'], 'daily', 1, legacy['table'], legacy['params'])
    path = legacy['root'] / legacy['raw'].relative_path
    path.with_name('manifest.json').unlink()  # Synthetic fixture publication only.
    RawWriter(legacy['root'], db).sidecar(legacy['req']['run_id'], 'daily')
    assert verify_batch(legacy['root'], db, [legacy['req']['run_id']])
    with pytest.raises(ReceiptIntegrityError):
        prove(legacy)


@pytest.mark.parametrize('kind', ['fake_object', 'foreign_object', 'wrong_dataset', 'wrong_params',
                                  'wrong_contract', 'wrong_run_mode', 'wrong_run_commit', 'wrong_count',
                                  'wrong_finished_time', 'wrong_event_bounds', 'zero_objects'])
def test_legacy_invalid_receipt_cannot_be_saved_by_binding(legacy, kind):
    db = legacy['db']; req = legacy['req']
    if kind in ('fake_object', 'foreign_object'):
        oid = uuid4()
        if kind == 'foreign_object':
            other = batch_requests(db, legacy['batch'])[2]
            raw = RawWriter(legacy['root'], db).write(other['run_id'], 'daily_basic', 0,
                ProviderTable(fields=['synthetic'], items=[], retrieved_at=datetime.now(timezone.utc)), legacy['params'])
            oid = raw.object_id
        db.execute('UPDATE slice_request SET object_id=? WHERE ordinal=1', [str(oid)])
    elif kind == 'wrong_dataset':
        db.execute("UPDATE slice_request SET dataset='daily_basic' WHERE ordinal=1")
    elif kind == 'wrong_params':
        db.execute('UPDATE slice_request SET request_params=? WHERE ordinal=1', ['{"trade_date":"2013-01-07"}'])
    elif kind == 'wrong_contract':
        db.execute('UPDATE slice_request SET contract_hash=? WHERE ordinal=1', ['d' * 64])
    elif kind == 'wrong_run_mode':
        db.execute("UPDATE ingestion_run SET mode='PROBE' WHERE run_id=?", [str(req['run_id'])])
    elif kind == 'wrong_run_commit':
        db.execute('UPDATE ingestion_run SET code_commit=? WHERE run_id=?', ['d' * 40, str(req['run_id'])])
    elif kind == 'wrong_count':
        db.execute('UPDATE ingestion_run SET row_count=9 WHERE run_id=?', [str(req['run_id'])])
    elif kind == 'wrong_finished_time':
        started = db.execute('SELECT started_at FROM ingestion_run WHERE run_id=?', [str(req['run_id'])]).fetchone()[0]
        db.execute('UPDATE ingestion_run SET finished_at=? WHERE run_id=?', [started, str(req['run_id'])])
    elif kind == 'wrong_event_bounds':
        db.execute("UPDATE raw_object_manifest SET min_event_date='2013-01-04',max_event_date='2013-01-04'")
    else:
        db.execute('DELETE FROM raw_object_manifest')
    before = db.execute('SELECT * FROM slice_request').fetchall()
    with pytest.raises(ReceiptIntegrityError):
        prove(legacy)
    with pytest.raises(ReceiptIntegrityError):
        apply_receipt_integrity_upgrade(legacy['root'], db, verification_sha='c' * 40)
    assert db.execute('SELECT * FROM slice_request').fetchall() == before
    assert db.execute('SELECT max(version) FROM schema_version').fetchone() == (6,)


@pytest.mark.parametrize('kind', ['file_missing', 'file_bytes', 'schema', 'count', 'sidecar_missing',
                                  'sidecar_uuid', 'sidecar_run', 'sidecar_dataset', 'sidecar_extra',
                                  'sidecar_duplicate', 'sidecar_time', 'sidecar_schema', 'sidecar_bool_count',
                                  'contract_missing', 'contract_hash', 'contract_params', 'contract_object',
                                  'contract_unknown', 'contract_duplicate_key', 'sidecar_unknown'])
def test_physical_and_sidecar_capture_contract_corruptions(legacy, kind):
    root = legacy['root']; db = legacy['db']; path = root / legacy['raw'].relative_path
    side = path.with_name('manifest.json'); meta = path.with_name('capture-contract.json')
    if kind == 'file_missing': path.unlink()
    elif kind == 'file_bytes': path.write_bytes(b'synthetic-corruption')
    elif kind == 'schema': db.execute('UPDATE raw_object_manifest SET schema_hash=?', ['d' * 64])
    elif kind == 'count': db.execute('UPDATE raw_object_manifest SET row_count=3')
    elif kind == 'sidecar_missing': side.unlink()
    elif kind == 'contract_missing': meta.unlink()
    elif kind == 'contract_duplicate_key':
        meta.write_text(meta.read_text().replace('"contract_hash":', '"contract_hash":"duplicate","contract_hash":'))
    elif kind.startswith('sidecar_'):
        body = json.loads(side.read_bytes())
        if kind == 'sidecar_uuid': body['objects'][0]['object_id'] = str(uuid4())
        elif kind == 'sidecar_run': body['run_id'] = str(uuid4())
        elif kind == 'sidecar_dataset': body['dataset'] = 'daily_basic'
        elif kind == 'sidecar_extra': body['objects'].append({**body['objects'][0], 'object_id': str(uuid4())})
        elif kind == 'sidecar_duplicate': body['objects'].append(body['objects'][0])
        elif kind == 'sidecar_time': body['objects'][0]['available_at'] = '2026-01-01T00:00:00+00:00'
        elif kind == 'sidecar_schema': body['objects'][0]['schema_hash'] = 'd' * 64
        elif kind == 'sidecar_bool_count': body['objects'][0]['row_count'] = False
        else: body['unknown'] = 'synthetic'
        side.write_text(json.dumps(body))
    else:
        body = json.loads(meta.read_bytes())
        field = {'contract_hash': 'contract_hash', 'contract_params': 'request_params',
                 'contract_object': 'object_id', 'contract_unknown': 'unknown'}[kind]
        body[field] = {'trade_date': '2013-01-07'} if field == 'request_params' else 'synthetic-wrong'
        meta.write_text(json.dumps(body))
    with pytest.raises(ReceiptIntegrityError): prove(legacy)


@pytest.mark.parametrize('kind', ['file', 'parent', 'sidecar', 'contract', 'traversal', 'outside', 'frozen_manifest'])
def test_unsafe_paths_and_metadata_symlinks(legacy, kind, tmp_path):
    root = legacy['root']; path = root / legacy['raw'].relative_path
    if kind in ('traversal', 'outside'):
        from astock.data.raw_validation import safe_file
        with pytest.raises(ReceiptIntegrityError):
            safe_file(root, '../outside' if kind == 'traversal' else str(path), under='data/raw')
        return
    target = path if kind == 'file' else path.parent if kind == 'parent' else path.with_name(
        'manifest.json' if kind == 'sidecar' else 'capture-contract.json')
    if kind == 'frozen_manifest':
        target = root / f'data/private/phase1c1/{legacy["batch"]}/request-manifest.json'
    backup = tmp_path / ('synthetic-' + kind)
    target.rename(backup)
    target.symlink_to(backup, target_is_directory=backup.is_dir())
    with pytest.raises(ReceiptIntegrityError, match='UNSAFE_PATH'): prove(legacy)


@pytest.mark.parametrize('params', ['{"trade_date":20130104}', '{"trade_date":true}',
                                  '{"trade_date":"20130104"}', '{"trade_date":"2013-1-4"}',
                                  '{"trade_date":"2013-01-04","trade_date":"2013-01-04"}',
                                  '{"trade_date":"2013-01-04","unknown":"x"}'])
def test_typed_json_does_not_coerce_or_drop_fields(params):
    with pytest.raises(ReceiptIntegrityError): typed_params(params)


def test_json_key_order_is_equivalent_but_null_and_missing_differ(legacy):
    from astock.data.raw_validation import same_json
    assert same_json(typed_params('{"end_date":"2013-01-08","start_date":"2013-01-04"}'),
                     typed_params('{"start_date":"2013-01-04","end_date":"2013-01-08"}'))
    assert not same_json(typed_params('{"trade_date":"2013-01-04","exchange":null}'),
                         typed_params('{"trade_date":"2013-01-04"}'))
    with pytest.raises(ReceiptIntegrityError): strict_json('{"x":NaN}')
    meta = (legacy['root'] / legacy['raw'].relative_path).with_name('capture-contract.json')
    meta.write_text(json.dumps(dict(reversed(list(json.loads(meta.read_bytes()).items())))))
    assert prove(legacy).object['object_id'] == str(legacy['raw'].object_id)


@pytest.mark.parametrize('kind', ['missing', 'duplicate', 'ordinal', 'null_params', 'manifest_bytes'])
def test_batch_frozen_plan_cannot_be_replaced(legacy, kind):
    rows = batch_requests(legacy['db'], legacy['batch']); plan = request_manifest(legacy['root'])
    if kind == 'missing': rows.pop()
    elif kind == 'duplicate': rows[2] = rows[1]
    elif kind == 'ordinal': rows[1]['ordinal'] = 2
    elif kind == 'null_params': rows[1]['request_params'] = '{"trade_date":"2013-01-04","exchange":null}'
    else:
        p = legacy['root'] / f'data/private/phase1c1/{legacy["batch"]}/request-manifest.json'
        body = json.loads(p.read_bytes()); body['code_commit'] = 'd' * 40; p.write_text(json.dumps(body))
        with pytest.raises(ReceiptIntegrityError): frozen_context(legacy['root'], legacy['db'], legacy['batch'])
        return
    with pytest.raises(ReceiptIntegrityError): validate_requests(rows, plan)


def test_object_table_and_resume_share_proof_even_for_legacy(legacy):
    legacy['db'].execute('UPDATE slice_request SET object_id=? WHERE ordinal=1', [str(uuid4())])
    req = batch_requests(legacy['db'], legacy['batch'])[1]
    for operation in (lambda: _object_table(legacy['root'], legacy['db'], req),
                      lambda: resume_batch(legacy['db'], legacy['batch'], root=legacy['root'],
                                           expected_plan_hash=request_manifest(legacy['root'])['plan_hash'])):
        with pytest.raises(ReceiptIntegrityError, match='RECEIPT_OBJECT_MISMATCH'): operation()


def test_bad_complete_blocks_pending_before_client_and_preserves_history(slice_root, monkeypatch):
    first = capture_slices(slice_root, settings(), live=True, stop_after=1,
                           client=SyntheticCaptureClient(), commit=SHA)
    batch = UUID(first['batch_id']); path = slice_root / 'data/warehouse/astock.duckdb'
    with duckdb.connect(str(path)) as db:
        # Synthetic legacy-invalid row: FK already protects accepted bindings.
        db.execute('DELETE FROM slice_receipt_completion_binding WHERE ordinal=0')
        db.execute('UPDATE slice_request SET object_id=? WHERE ordinal=0', [str(uuid4())])
        before = db.execute('SELECT * FROM slice_request').fetchall()
        ingestion = db.execute('SELECT * FROM ingestion_run').fetchall()
    constructed = []
    monkeypatch.setattr(TushareClient, '__init__', lambda *a, **k: constructed.append(True))
    client = SyntheticCaptureClient()
    rejected = capture_slices(slice_root, settings(), live=True, batch_id=batch, client=client, commit=SHA)
    assert rejected['status'] == 'BLOCKED' and not client.calls and not constructed
    # Also verify the default constructor path is never reached.
    capture_slices(slice_root, settings(), live=True, batch_id=batch, commit=SHA)
    assert not constructed
    with duckdb.connect(str(path)) as db:
        assert db.execute('SELECT * FROM slice_request').fetchall() == before
        assert db.execute('SELECT * FROM ingestion_run').fetchall() == ingestion
    assert list((slice_root / f'data/private/phase1c1/{batch}').glob('operation-block-*.json'))


def test_registered_raw_without_metadata_is_not_reconstructed(slice_root):
    path = slice_root / 'data/warehouse/astock.duckdb'
    with duckdb.connect(str(path)) as db:
        identity, _, _ = identity_state(db)
        batch = create_batch(slice_root, db, commit=SHA, identity_hash=identity,
                             knowledge_as_of=datetime.now(timezone.utc))
        claim_request(db, batch, 1)
        req = batch_requests(db, batch)[1]
        c = next(c for c in load_contracts(slice_root, catalog_version='v2') if c.dataset == 'daily')
        raw = RawWriter(slice_root, db).write(req['run_id'], 'daily', 0,
            ProviderTable(fields=c.required_fields, items=[], retrieved_at=datetime.now(timezone.utc)),
            RequestParams.model_validate_json(req['request_params']))
    client = SyntheticCaptureClient()
    result = capture_slices(slice_root, settings(), live=True, batch_id=batch, client=client, commit=SHA)
    assert result['status'] == 'BLOCKED' and not client.calls
    assert not (slice_root / raw.relative_path).with_name('manifest.json').exists()
    assert not (slice_root / raw.relative_path).with_name('capture-contract.json').exists()


def test_finalization_is_idempotent_and_rejects_other_object(slice_root):
    result = capture_slices(slice_root, settings(), live=True, stop_after=2,
                            client=SyntheticCaptureClient(), commit=SHA)
    batch = UUID(result['batch_id'])
    with duckdb.connect(str(slice_root / 'data/warehouse/astock.duckdb')) as db:
        req = batch_requests(db, batch)[1]
        c = next(c for c in load_contracts(slice_root, catalog_version='v2') if c.dataset == 'daily')
        before = db.execute('SELECT * FROM ingestion_run').fetchall()
        bindings = db.execute('SELECT * FROM slice_receipt_completion_binding').fetchall()
        finalize_receipt(slice_root, db, req, c, verification_sha='d' * 40)
        assert db.execute('SELECT * FROM ingestion_run').fetchall() == before
        assert db.execute('SELECT * FROM slice_receipt_completion_binding').fetchall() == bindings
        with pytest.raises(ReceiptIntegrityError):
            finalize_receipt(slice_root, db, {**req, 'object_id': uuid4()}, c, verification_sha='d' * 40)
        db.execute('UPDATE slice_receipt_completion_binding SET evidence_hash=? WHERE ordinal=1', ['d' * 64])
        with pytest.raises(ReceiptIntegrityError, match='BINDING_MISMATCH'):
            validate_slice_receipt(slice_root, db, req)


def test_pending_only_legacy_batch_cannot_reach_client_without007(slice_root, monkeypatch):
    path = slice_root / 'data/warehouse/astock.duckdb'
    with duckdb.connect(str(path)) as db:
        db.execute('DROP TABLE slice_receipt_completion_binding')
        db.execute('DROP TABLE slice_receipt_validation_audit')
        db.execute('DELETE FROM schema_version WHERE version=7')
        identity, _, _ = identity_state(db)
        batch = create_batch(slice_root, db, commit=SHA, identity_hash=identity,
                             knowledge_as_of=datetime.now(timezone.utc))
    constructors = []
    monkeypatch.setattr(TushareClient, '__init__', lambda *a, **k: constructors.append(True))
    result = capture_slices(slice_root, settings(), live=True, batch_id=batch, commit=SHA)
    assert result['failure'] == 'BINDING_SCHEMA_REQUIRED' and not constructors
    with duckdb.connect(str(path)) as db:
        assert db.execute('SELECT sum(attempts) FROM slice_request').fetchone() == (0,)
        assert db.execute('SELECT max(version) FROM schema_version').fetchone() == (6,)


def test_binding_digest_is_independent_of_database_timezone(legacy):
    apply_receipt_integrity_upgrade(legacy['root'], legacy['db'], verification_sha=SHA)
    before = validate_slice_receipt(legacy['root'], legacy['db'], legacy['req'])
    legacy['db'].execute("SET TimeZone='Pacific/Auckland'")
    after = validate_slice_receipt(legacy['root'], legacy['db'], legacy['req'])
    assert before.receipt_hash == after.receipt_hash and before.evidence_hash == after.evidence_hash
    legacy['db'].execute('DELETE FROM schema_version WHERE version=7')
    with pytest.raises(ReceiptIntegrityError, match='BINDING_SCHEMA_REQUIRED'):
        validate_slice_receipt(legacy['root'], legacy['db'], legacy['req'])
