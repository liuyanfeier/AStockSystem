"""Atomic claim/finalize/crash windows; denied-network synthetic subprocesses only."""

import multiprocessing
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest

from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.raw_writer import RawWriter, migrate
from astock.data.receipt_integrity import batch_requests, validate_slice_receipt
from astock.data.receipt_migration import apply_receipt_integrity_upgrade, register_completion
from astock.data.slice_capture import (capture_slices, finalize_receipt, publish_capture_metadata,
                                      fail_batch, identity_state)
from astock.data.slice_errors import ReceiptIntegrityError
from astock.data.slice_plan import claim_request, create_batch
from astock.data.warehouse_lock import (warehouse_connection, warehouse_lock, WarehouseLockError,
                                        WarehouseConnectionProxy)
from test_receipt_migration import old_rows, files
from test_slice_capture import slice_root, settings, SyntheticCaptureClient
from warehouse_worker import crash_worker

SHA = 'a' * 40


def setup_batch(root, *, candidate=False):
    with warehouse_connection(root/'data/warehouse/astock.duckdb') as db:
        identity, _, _ = identity_state(db)
        batch = create_batch(root, db, commit=SHA, identity_hash=identity,
                             knowledge_as_of=datetime.now(timezone.utc))
        if candidate:
            claim_request(db, batch, 1)
            req = batch_requests(db, batch)[1]
            contract = next(c for c in load_contracts(root, catalog_version='v2') if c.dataset == 'daily')
            params = RequestParams.model_validate_json(req['request_params'])
            raw = RawWriter(root, db).write(req['run_id'], 'daily', 0,
                                           SyntheticCaptureClient().fetch_slice(contract, params), params)
            publish_capture_metadata(root, db, req, contract,
                dict(object_id=str(raw.object_id), relative_path=raw.relative_path, sha256=raw.sha256))
        return batch


def crashed(root, batch, action, pattern='', after=False):
    process = multiprocessing.get_context('spawn').Process(
        target=crash_worker, args=(str(root), str(batch), action, pattern, after))
    process.start()
    try:
        process.join(20)
        assert not process.is_alive(), 'Synthetic crash worker hung'
        assert process.exitcode == (72 if pattern else 73)
    finally:
        if process.is_alive(): process.kill()
        process.join(10)


class ClaimFault(WarehouseConnectionProxy):
    def __init__(self, db, fault):
        super().__init__(db)
        self.db, self.fault = db, fault
    def execute(self, sql, *args):
        if "UPDATE slice_request SET status='IN_FLIGHT'" in sql and self.fault == 'zero_claim':
            class NoRows:
                def fetchall(self): return []
            return NoRows()
        if 'UPDATE ingestion_run SET request_count=1' in sql:
            if self.fault == 'exception': raise RuntimeError('synthetic second-write failure')
            class Zero:
                def fetchone(self): return (0,)
            return Zero()
        if sql == 'COMMIT' and self.fault == 'commit':
            raise RuntimeError('synthetic pre-commit failure')
        return self.db.execute(sql, *args)


@pytest.mark.parametrize('fault', ['exception', 'zero_count', 'zero_claim', 'commit'])
def test_claim_failure_rolls_back_both_updates_and_never_fetches(slice_root, fault):
    batch = setup_batch(slice_root)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        before, inventory = old_rows(db), files(slice_root)
        fetched = []
        with pytest.raises((RuntimeError, ReceiptIntegrityError)):
            claim_request(ClaimFault(db, fault), batch, 1)
            fetched.append('forbidden')
        assert fetched == [] and old_rows(db) == before and files(slice_root) == inventory


def test_capture_claim_failure_never_enters_synthetic_fetch(slice_root, monkeypatch):
    batch = setup_batch(slice_root)
    from astock.data import slice_capture
    original = slice_capture.claim_request
    def faulty(db, batch_id, ordinal): original(ClaimFault(db, 'exception'), batch_id, ordinal)
    monkeypatch.setattr(slice_capture, 'claim_request', faulty)
    client = SyntheticCaptureClient()
    with pytest.raises(RuntimeError, match='synthetic second-write'):
        capture_slices(slice_root, settings(), live=True, batch_id=batch, client=client, commit=SHA)
    assert client.calls == []
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        assert db.execute('SELECT sum(attempts) FROM slice_request').fetchone() == (0,)
        assert db.execute('SELECT sum(request_count) FROM ingestion_run').fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM slice_request WHERE status='PENDING'").fetchone() == (133,)


@pytest.mark.parametrize('pattern,after', [('UPDATE ingestion_run SET request_count=1', False),
                                          ('UPDATE ingestion_run SET request_count=1', True), ('COMMIT', False)])
def test_process_death_before_claim_commit_rolls_back_and_is_pending(slice_root, pattern, after):
    batch = setup_batch(slice_root)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db: before = old_rows(db)
    crashed(slice_root, batch, 'claim', pattern, after)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        assert old_rows(db) == before
        claim_request(db, batch, 1)
        assert db.execute('SELECT sum(attempts) FROM slice_request').fetchone() == (1,)
        assert db.execute('SELECT sum(request_count) FROM ingestion_run').fetchone() == (1,)


def test_committed_claim_before_transport_is_uncertain_and_never_retried(slice_root, monkeypatch):
    batch = setup_batch(slice_root)
    crashed(slice_root, batch, 'claim')
    from astock.data.tushare_client import TushareClient
    constructed = []
    def deny(*args, **kwargs): constructed.append(True); raise AssertionError('Unexpected provider')
    monkeypatch.setattr(TushareClient, '__init__', deny)
    client = SyntheticCaptureClient()
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db: before = old_rows(db)
    result = capture_slices(slice_root, settings(), live=True, batch_id=batch, client=client, commit=SHA)
    assert result['failure'] == 'UNCERTAIN_CAPTURE' and client.calls == [] and constructed == []
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        assert old_rows(db) == before
        assert db.execute('SELECT sum(attempts) FROM slice_request').fetchone() == (1,)
        assert db.execute('SELECT sum(request_count) FROM ingestion_run').fetchone() == (1,)


@pytest.mark.parametrize('stage', ['orphan', 'registered', 'metadata'])
def test_crash_after_publication_blocks_or_reconciles_only_exact_evidence(slice_root, monkeypatch, stage):
    batch = setup_batch(slice_root)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db: claim_request(db, batch, 1)
    if stage == 'orphan': crashed(slice_root, batch, 'raw', 'INSERT INTO raw_object_manifest')
    else: crashed(slice_root, batch, 'metadata' if stage == 'metadata' else 'raw')
    from astock.data.tushare_client import TushareClient
    forbidden = []
    def deny(*args, **kwargs): forbidden.append(True); raise AssertionError('Must not call provider')
    monkeypatch.setattr(TushareClient, '__init__', deny)
    monkeypatch.setattr(TushareClient, 'fetch_slice', deny)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        before, inventory = old_rows(db), files(slice_root)
        req = batch_requests(db, batch)[1]
        if stage == 'metadata':
            contract = next(c for c in load_contracts(slice_root, catalog_version='v2') if c.dataset == 'daily')
            finalize_receipt(slice_root, db, req, contract, verification_sha=SHA)
            current = batch_requests(db, batch)[1]
            assert validate_slice_receipt(slice_root, db, current).object['object_id'] == str(current['object_id'])
            assert db.execute('SELECT count(*) FROM slice_receipt_completion_binding').fetchone() == (1,)
            times = db.execute('SELECT finished_at FROM ingestion_run WHERE run_id=?', [str(req['run_id'])]).fetchone()
            finalize_receipt(slice_root, db, current, contract, verification_sha=SHA)
            assert db.execute('SELECT finished_at FROM ingestion_run WHERE run_id=?', [str(req['run_id'])]).fetchone() == times
            after = files(slice_root)
            assert all(after[name] == checksum for name, checksum in inventory.items()
                       if not name.startswith('data/warehouse/')) and forbidden == []
            return
    client = SyntheticCaptureClient()
    result = capture_slices(slice_root, settings(), live=True, batch_id=batch, client=client, commit=SHA)
    assert result['failure'] == ('ORPHAN_LOCAL_EVIDENCE' if stage == 'orphan' else 'UNCERTAIN_CAPTURE')
    assert client.calls == [] and forbidden == []
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        assert old_rows(db) == before
        assert db.execute('SELECT count(*) FROM slice_receipt_completion_binding').fetchone() == (0,)
    after = files(slice_root)
    assert all(after[name] == digest for name, digest in inventory.items()
               if not name.startswith('data/warehouse/'))


@pytest.mark.parametrize('extra', ['part-001.parquet', '.pending-orphan', 'unknown.json'])
def test_unregistered_extra_files_block_exact_local_recovery(slice_root, extra):
    batch = setup_batch(slice_root, candidate=True)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        req = batch_requests(db, batch)[1]
        directory = slice_root / f"data/raw/tushare/daily/run_id={req['run_id']}"
        (directory/extra).write_bytes(b'synthetic orphan evidence')
        before = old_rows(db)
    client = SyntheticCaptureClient()
    result = capture_slices(slice_root, settings(), live=True, batch_id=batch, client=client, commit=SHA)
    assert result['failure'] == 'ORPHAN_LOCAL_EVIDENCE' and client.calls == []
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db: assert old_rows(db) == before
    assert (directory/extra).read_bytes() == b'synthetic orphan evidence'


def test_pending_with_local_orphan_blocks_before_claim_and_client(slice_root, monkeypatch):
    batch = setup_batch(slice_root)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db: req = batch_requests(db, batch)[1]
    path = slice_root/f"data/raw/tushare/daily/run_id={req['run_id']}/part-000.parquet"
    path.parent.mkdir(parents=True); path.write_bytes(b'synthetic orphan')
    from astock.data import slice_capture
    calls = []
    def deny(*args, **kwargs): calls.append(True); raise AssertionError('Before ownership/preflight')
    monkeypatch.setattr(slice_capture, 'claim_request', deny)
    monkeypatch.setattr(slice_capture, 'TushareClient', deny)
    result = capture_slices(slice_root, settings(), live=True, batch_id=batch, commit=SHA)
    assert result['failure'] == 'ORPHAN_LOCAL_EVIDENCE' and calls == []
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        assert db.execute('SELECT sum(attempts) FROM slice_request').fetchone() == (0,)


@pytest.mark.parametrize('pattern,after', [("UPDATE ingestion_run SET status='SUCCEEDED'", True),
    ("UPDATE slice_request SET status='COMPLETE'", True), ('INSERT INTO slice_receipt_completion_binding', True),
    ('INSERT INTO slice_receipt_validation_audit', True), ('COMMIT', False), ('COMMIT', True)])
def test_finalize_process_death_rolls_back_or_leaves_one_exact_committed_binding(slice_root, pattern, after):
    batch = setup_batch(slice_root, candidate=True)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        before = old_rows(db)
        req = batch_requests(db, batch)[1]
    crashed(slice_root, batch, 'finalize', pattern, after)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        committed = pattern == 'COMMIT' and after
        if not committed:
            assert old_rows(db) == before
            assert db.execute('SELECT count(*) FROM slice_receipt_completion_binding').fetchone() == (0,)
        current = batch_requests(db, batch)[1]
        assert current['status'] == ('COMPLETE' if committed else 'IN_FLIGHT')
        contract = next(c for c in load_contracts(slice_root, catalog_version='v2') if c.dataset == 'daily')
        finalize_receipt(slice_root, db, current, contract, verification_sha=SHA)
        current = batch_requests(db, batch)[1]
        validate_slice_receipt(slice_root, db, current)
        finalized = old_rows(db)
        finalize_receipt(slice_root, db, current, contract, verification_sha=SHA)
        assert old_rows(db) == finalized
        assert db.execute('SELECT count(*) FROM slice_receipt_completion_binding').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM slice_receipt_validation_audit').fetchone() == (1,)
        assert db.execute('SELECT sum(attempts) FROM slice_request').fetchone() == (1,)
        assert db.execute('SELECT sum(request_count) FROM ingestion_run').fetchone() == (1,)


@pytest.mark.parametrize('helper', ['migrate', 'raw', 'claim', 'create', 'finalize', 'register', 'upgrade',
                                  'identity', 'admission', 'mapping', 'failure'])
@pytest.mark.parametrize('late_lock', [False, True])
def test_disk_helpers_reject_unmanaged_connections_before_any_write(slice_root, helper, late_lock):
    from contextlib import nullcontext
    from astock.data.identity import IdentityHistory
    from astock.data.bootstrap import admit_bootstrap, capture_mapping
    # Open the unmanaged connection FIRST, then actually take the same-path guard.
    with duckdb.connect(str(slice_root/'data/warehouse/astock.duckdb')) as db:
        before = old_rows(db)
        owner = warehouse_lock(slice_root/'data/warehouse/astock.duckdb') if late_lock else nullcontext()
        with owner, pytest.raises(WarehouseLockError, match='WAREHOUSE_LOCK_REQUIRED'):
            if helper == 'migrate': migrate(db, slice_root)
            elif helper == 'raw': RawWriter(slice_root, db)
            elif helper == 'claim': claim_request(db, None, 0)
            elif helper == 'create': create_batch(slice_root, db, commit=SHA, identity_hash='b'*64, knowledge_as_of=datetime.now(timezone.utc))
            elif helper == 'finalize': finalize_receipt(slice_root, db, None, None, verification_sha=SHA)
            elif helper == 'register': register_completion(slice_root, db, None, verification_sha=SHA)
            elif helper == 'upgrade': apply_receipt_integrity_upgrade(slice_root, db, verification_sha=SHA)
            elif helper == 'identity': IdentityHistory.append(db, None)
            elif helper == 'admission': admit_bootstrap(db, {}, commit=SHA, config_hash='b'*64, input_hash='c'*64, observed_at=datetime.now(timezone.utc))
            elif helper == 'mapping': capture_mapping(slice_root, db, settings(), live=False, commit=SHA)
            else: fail_batch(slice_root, db, None, None, 'LINEAGE')
        assert old_rows(db) == before
