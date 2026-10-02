"""Real spawned-process exclusion and OS release; temporary synthetic warehouses only."""

import hashlib
import multiprocessing
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest

from astock.data.warehouse_lock import warehouse_connection, warehouse_lock, WarehouseLockError
from astock.data.receipt_integrity import audit_slice_batch
from astock.data.slice_capture import identity_state
from astock.data.slice_plan import create_batch
from test_slice_capture import slice_root
from warehouse_worker import lock_worker, contender, capture_owner, publication_owner


@pytest.fixture
def processes():
    owned = []
    def start(target, *args):
        parent, child = multiprocessing.get_context('spawn').Pipe()
        process = multiprocessing.get_context('spawn').Process(target=target, args=(child, *args))
        process.start(); child.close(); owned.append((process, parent))
        return process, parent
    yield start
    for process, pipe in owned:
        if process.is_alive():
            process.kill()
        process.join(10); pipe.close()
        assert not process.is_alive()


def receive(pipe):
    assert pipe.poll(15), 'Synthetic child did not reach the expected barrier'
    return pipe.recv()


def new_batch(root):
    with warehouse_connection(root/'data/warehouse/astock.duckdb') as db:
        identity, _, _ = identity_state(db)
        return create_batch(root, db, commit='a' * 40, identity_hash=identity,
                            knowledge_as_of=datetime.now(timezone.utc))


def test_concurrent_capture_claim_and_publish_have_one_owner(slice_root, processes):
    batch = new_batch(slice_root)
    owner, pipe = processes(capture_owner, str(slice_root), str(batch))
    entered = receive(pipe)
    assert entered == dict(event='FETCH_ENTERED', attempts=1, request_count=1)
    for action in ('claim', 'capture', 'publish', 'curate'):
        other, result = processes(contender, str(slice_root), str(batch), action)
        assert receive(result) == dict(event='BLOCKED', code='WAREHOUSE_BUSY',
                                       constructed=0, fetched=0, claimed=0, preflight=0)
        other.join(10); assert other.exitcode == 0
    assert not (slice_root/'data/private/publisher-should-not-run.json').exists()
    pipe.send('finish')
    finished = receive(pipe)
    assert finished['event'] == 'FINISHED' and finished['fetched'] == 1
    assert finished['result']['status'] == 'INTERRUPTED'
    owner.join(10); assert owner.exitcode == 0
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        assert db.execute('SELECT sum(attempts) FROM slice_request').fetchone() == (1,)
        assert db.execute('SELECT sum(request_count) FROM ingestion_run').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM raw_object_manifest').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM slice_receipt_completion_binding').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM slice_receipt_validation_audit').fetchone() == (1,)


def test_owner_holds_exclusion_during_actual_raw_publication(slice_root, processes):
    batch = new_batch(slice_root)
    owner, pipe = processes(publication_owner, str(slice_root), str(batch))
    assert receive(pipe)['event'] == 'PUBLICATION_PAUSED'
    for action in ('publish', 'capture'):
        other, result = processes(contender, str(slice_root), str(batch), action)
        assert receive(result) == dict(event='BLOCKED', code='WAREHOUSE_BUSY',
                                       constructed=0, fetched=0, claimed=0, preflight=0)
        other.join(10); assert other.exitcode == 0
    pipe.send('finish'); assert receive(pipe)['event'] == 'FINISHED'
    owner.join(10); assert owner.exitcode == 0
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        assert db.execute('SELECT sum(attempts) FROM slice_request').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM raw_object_manifest').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM slice_receipt_completion_binding').fetchone() == (1,)


@pytest.mark.parametrize('action', ['capture', 'curate', 'dq', 'bootstrap', 'probe', 'upgrade', 'claim', 'publish'])
def test_all_writer_entrypoints_block_before_preflight_client_or_mutation(slice_root, processes, action):
    batch = new_batch(slice_root)
    path = slice_root/'data/warehouse/astock.duckdb'
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with warehouse_lock(path):
        other, pipe = processes(contender, str(slice_root), str(batch), action)
        assert receive(pipe) == dict(event='BLOCKED', code='WAREHOUSE_BUSY',
                                     constructed=0, fetched=0, claimed=0, preflight=0)
        other.join(10); assert other.exitcode == 0
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert not (slice_root/'data/private/publisher-should-not-run.json').exists()


@pytest.mark.parametrize('release', ['normal', 'exception', 'kill'])
def test_stable_inode_releases_on_exception_exit_and_process_death(slice_root, processes, release):
    path = slice_root/'data/warehouse/astock.duckdb'
    lock = path.with_name(path.name+'.lock')
    inode = lock.stat().st_ino
    owner, pipe = processes(lock_worker, str(path), 'exclusive')
    assert receive(pipe)['event'] == 'READY'
    with pytest.raises(WarehouseLockError, match='WAREHOUSE_BUSY'):
        with warehouse_lock(path):
            pytest.fail('Cannot enter a second exclusive owner')
    if release == 'kill':
        owner.kill(); owner.join(10); assert owner.exitcode != 0
    else:
        pipe.send(release)
        assert receive(pipe)['event'] == ('RELEASED_AFTER_EXCEPTION' if release == 'exception' else 'RELEASED')
        if release == 'normal':
            owner.join(10); assert owner.exitcode == 0
        else:
            assert owner.is_alive()
    with warehouse_connection(path) as db:
        assert db.execute('SELECT 1').fetchone() == (1,)
    assert lock.is_file() and lock.stat().st_ino == inode
    if release == 'exception':
        pipe.send('exit'); owner.join(10); assert owner.exitcode == 0


def test_aliases_share_canonical_lock_and_wait_is_bounded(slice_root, processes, tmp_path):
    path = slice_root/'data/warehouse/astock.duckdb'
    alias = tmp_path/'warehouse-alias'; alias.symlink_to(path.parent, target_is_directory=True)
    file_alias = tmp_path/'db-alias'; file_alias.symlink_to(path)
    owner, pipe = processes(lock_worker, str(path), 'exclusive')
    assert receive(pipe)['event'] == 'READY'
    for candidate in (alias/'astock.duckdb', file_alias, path.parent/'..'/'warehouse'/'astock.duckdb'):
        started = time.monotonic()
        with pytest.raises(WarehouseLockError, match='WAREHOUSE_BUSY'):
            with warehouse_lock(candidate, wait_seconds=0.15):
                pytest.fail('Alias bypassed ownership')
        assert 0.12 <= time.monotonic()-started < 2
    pipe.send('normal'); assert receive(pipe)['event'] == 'RELEASED'
    owner.join(10); assert owner.exitcode == 0
    assert not (tmp_path/'db-alias.lock').exists()


def test_native_uncooperative_writer_fails_closed_and_releases_guard(slice_root, processes):
    path = slice_root/'data/warehouse/astock.duckdb'
    owner, pipe = processes(lock_worker, str(path), 'native')
    assert receive(pipe)['event'] == 'READY'
    with pytest.raises(WarehouseLockError, match='WAREHOUSE_NATIVE_LOCKED_OR_OPEN_FAILED'):
        with warehouse_connection(path):
            pytest.fail('Native DB conflict must not be swallowed')
    other, result = processes(contender, str(slice_root), '00000000-0000-0000-0000-000000000000', 'capture')
    assert receive(result) == dict(event='BLOCKED', code='WAREHOUSE_NATIVE_LOCKED_OR_OPEN_FAILED',
                                   constructed=0, fetched=0, claimed=0, preflight=0)
    other.join(10); assert other.exitcode == 0
    pipe.send('normal'); owner.join(10); assert owner.exitcode == 0
    with warehouse_connection(path) as db:
        assert db.execute('SELECT 1').fetchone() == (1,)


def test_shared_readers_exclude_writers_and_never_upgrade(slice_root, processes):
    path = slice_root/'data/warehouse/astock.duckdb'
    batch = new_batch(slice_root)
    with warehouse_lock(path, shared=True):
        other, pipe = processes(lock_worker, str(path), 'shared')
        assert receive(pipe)['event'] == 'READY'
        with pytest.raises(WarehouseLockError, match='WAREHOUSE_LOCK_REQUIRED'):
            with warehouse_lock(path):
                pytest.fail('Shared lock must not upgrade')
        writer, result = processes(contender, str(slice_root), str(batch), 'claim')
        assert receive(result)['code'] == 'WAREHOUSE_BUSY'
        writer.join(10); assert writer.exitcode == 0
        pipe.send('normal'); assert receive(pipe)['event'] == 'RELEASED'
        other.join(10); assert other.exitcode == 0


def test_actual_audit_takes_shared_lock_before_open_and_preserves_snapshot(slice_root, processes, monkeypatch):
    path = slice_root/'data/warehouse/astock.duckdb'
    batch = new_batch(slice_root)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    owner, pipe = processes(lock_worker, str(path), 'exclusive')
    assert receive(pipe)['event'] == 'READY'
    calls = []
    def deny(*args, **kwargs):
        calls.append(True)
        raise AssertionError('Read-only audit must acquire shared ownership before connect')
    with monkeypatch.context() as patch:
        patch.setattr(duckdb, 'connect', deny)
        blocked = audit_slice_batch(slice_root, batch, verification_sha='a' * 40)
    assert blocked['reasons'] == {'WAREHOUSE_BUSY': 1} and calls == []
    pipe.send('normal'); assert receive(pipe)['event'] == 'RELEASED'
    owner.join(10); assert owner.exitcode == 0
    unblocked = audit_slice_batch(slice_root, batch, verification_sha='a' * 40)
    assert unblocked['reasons'] == {'BATCH_INCOMPLETE': 1}
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize('unsafe', ['symlink', 'hardlink', 'directory'])
def test_lock_path_is_regular_stable_and_not_redirectable(tmp_path, unsafe):
    path = tmp_path/'test.duckdb'; lock = tmp_path/'test.duckdb.lock'; target = tmp_path/'target'
    target.write_text('preserve')
    if unsafe == 'symlink': lock.symlink_to(target)
    elif unsafe == 'hardlink': os.link(target, lock)
    else: lock.mkdir()
    with pytest.raises(WarehouseLockError, match='WAREHOUSE_LOCK_PATH'):
        with warehouse_lock(path):
            pytest.fail('Unsafe lock path accepted')
    assert target.read_text() == 'preserve'


@pytest.mark.parametrize('wait', [-1, 6, float('nan'), float('inf')])
def test_wait_cannot_be_unbounded(tmp_path, wait):
    with pytest.raises(WarehouseLockError, match='WAREHOUSE_LOCK_WAIT'):
        with warehouse_lock(tmp_path/'test.duckdb', wait_seconds=wait):
            pytest.fail('Invalid wait accepted')
    assert not list(tmp_path.iterdir())


def test_bounded_wait_acquires_after_owner_releases(slice_root, processes):
    import threading
    path = slice_root/'data/warehouse/astock.duckdb'
    owner, pipe = processes(lock_worker, str(path), 'exclusive')
    assert receive(pipe)['event'] == 'READY'
    timer = threading.Timer(0.05, lambda: pipe.send('normal'))
    timer.start()
    try:
        with warehouse_lock(path, wait_seconds=1):
            assert receive(pipe)['event'] == 'RELEASED'
    finally:
        timer.join(2)
    owner.join(10); assert owner.exitcode == 0


def test_body_io_failure_preserves_error_and_releases_ownership(tmp_path):
    path = tmp_path/'test.duckdb'
    with pytest.raises(OSError, match='synthetic publication error'):
        with warehouse_lock(path):
            raise OSError('synthetic publication error')
    with warehouse_lock(path):
        assert path.with_name(path.name+'.lock').is_file()


def test_fork_child_cannot_reuse_parent_guard(tmp_path):
    path = tmp_path/'test.duckdb'
    with warehouse_lock(path):
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            try:
                with warehouse_lock(path):
                    os.write(write_fd, b'BYPASS')
            except WarehouseLockError as error:
                os.write(write_fd, error.code.encode())
            finally:
                os.close(write_fd); os._exit(0)
        os.close(write_fd)
        try:
            import select
            assert select.select([read_fd], [], [], 5)[0]
            assert os.read(read_fd, 100) == b'WAREHOUSE_BUSY'
        finally:
            os.close(read_fd)
            assert os.waitpid(pid, 0)[1] == 0
