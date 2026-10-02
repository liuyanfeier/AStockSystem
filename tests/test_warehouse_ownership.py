"""G2 review regressions: managed handle lifetimes and process-wide fork cleanup."""

import contextvars
import os
import select
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import duckdb
import pytest

from astock.data.raw_writer import RawWriter, migrate
from astock.data.slice_plan import claim_request, create_batch
from astock.data.slice_capture import identity_state
from astock.data.warehouse_lock import (WarehouseConnectionProxy, WarehouseLockError,
                                        require_writer, warehouse_connection, warehouse_lock)
from test_slice_capture import slice_root
from test_receipt_migration import old_rows, files


@pytest.mark.parametrize('helper', ['require', 'claim', 'raw', 'migrate', 'explicit_proxy'])
def test_unmanaged_connection_opened_before_same_path_lock_cannot_write(slice_root, helper):
    path = slice_root/'data/warehouse/astock.duckdb'
    with warehouse_connection(path) as managed:
        identity, _, _ = identity_state(managed)
        batch = create_batch(slice_root, managed, commit='a'*40, identity_hash=identity,
                             knowledge_as_of=datetime.now(timezone.utc))
    with duckdb.connect(str(path)) as unmanaged:
        before = old_rows(unmanaged)
        with warehouse_lock(path):
            inventory = files(slice_root)
            with pytest.raises(WarehouseLockError, match='WAREHOUSE_LOCK_REQUIRED'):
                if helper == 'require': require_writer(unmanaged)
                elif helper == 'claim': claim_request(unmanaged, batch, 0)
                elif helper == 'raw': RawWriter(slice_root, unmanaged)
                elif helper == 'explicit_proxy': require_writer(WarehouseConnectionProxy(unmanaged))
                else: migrate(unmanaged, slice_root)
            assert old_rows(unmanaged) == before and files(slice_root) == inventory


@pytest.mark.parametrize('handle', ['connection', 'result', 'cursor', 'proxy'])
def test_escaped_handle_cannot_be_revived_by_a_new_guard(tmp_path, handle):
    path = tmp_path/'test.duckdb'
    with warehouse_connection(path) as db:
        db.execute('CREATE TABLE evidence(n INTEGER)')
        escaped = {'connection': db, 'result': db.execute('SELECT 1'),
                   'cursor': db.cursor(), 'proxy': WarehouseConnectionProxy(db)}[handle]
        require_writer(escaped)
    with warehouse_connection(path) as new:
        with pytest.raises(WarehouseLockError, match='WAREHOUSE_LOCK_REQUIRED'):
            require_writer(escaped)
        with pytest.raises(WarehouseLockError, match='WAREHOUSE_LOCK_REQUIRED'):
            escaped.execute('INSERT INTO evidence VALUES(1)')
        assert new.execute('SELECT count(*) FROM evidence').fetchone() == (0,)


@pytest.mark.parametrize('method', ['execute', 'executemany', 'fetchone', 'fetchall',
                                  'fetchmany', 'description', 'cursor'])
def test_connection_results_and_methods_do_not_escape_lifetime(tmp_path, method):
    with warehouse_connection(tmp_path/'test.duckdb') as db:
        assert db.execute('SELECT 1') is db
        cursor = db.cursor()
        assert cursor.execute('SELECT 2') is cursor
    with pytest.raises(WarehouseLockError, match='WAREHOUSE_LOCK_REQUIRED'):
        if method == 'execute': db.execute('SELECT 1')
        elif method == 'executemany': db.executemany('SELECT ?', [[1]])
        elif method == 'description': _ = db.description
        else: getattr(db, method)()


def test_early_root_close_invalidates_all_cursors_and_proxies(tmp_path):
    path = tmp_path/'test.duckdb'
    with warehouse_connection(path) as db:
        cursor = db.cursor(); proxy = WarehouseConnectionProxy(cursor)
        db.close(); db.close()
        for handle in (db, cursor, proxy):
            with pytest.raises(WarehouseLockError): require_writer(handle)
        # Early native close must not release the outer publication lock.
        def competitor():
            with pytest.raises(WarehouseLockError, match='WAREHOUSE_BUSY'):
                with warehouse_lock(path): pytest.fail('owner released early')
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(competitor).result(timeout=5)
    with warehouse_connection(path) as db: require_writer(db)


def test_cursor_close_does_not_invalidate_root_and_cursors_are_scoped(tmp_path):
    with warehouse_connection(tmp_path/'test.duckdb') as db:
        db.execute('CREATE TABLE evidence(n INTEGER)')
        cursor = db.cursor()
        require_writer(cursor)
        cursor.execute('INSERT INTO evidence VALUES(1)')
        cursor.close()
        with pytest.raises(WarehouseLockError): require_writer(cursor)
        require_writer(db)
        assert db.execute('SELECT count(*) FROM evidence').fetchone() == (1,)


def test_connection_rejects_foreign_thread_even_with_copied_context(tmp_path):
    with warehouse_connection(tmp_path/'test.duckdb') as db:
        context = contextvars.copy_context()
        def foreign():
            for operation in (lambda: require_writer(db), lambda: db.execute('SELECT 1'), db.close):
                with pytest.raises(WarehouseLockError): operation()
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(context.run, foreign).result(timeout=5)
        assert db.execute('SELECT 1').fetchone() == (1,)


def test_empty_context_cannot_use_connection_and_stale_context_cannot_reuse_guard(tmp_path):
    path = tmp_path/'test.duckdb'
    with warehouse_connection(path) as db:
        stale = contextvars.copy_context()
        with pytest.raises(WarehouseLockError): contextvars.Context().run(require_writer, db)
    # A copied guard from an ended scope cannot grant a new lock or handle.
    with warehouse_lock(path):
        def stale_owner():
            with pytest.raises(WarehouseLockError, match='WAREHOUSE_BUSY'):
                with warehouse_lock(path): pytest.fail('inactive guard reused')
            with pytest.raises(WarehouseLockError): require_writer(db)
        stale.run(stale_owner)


@pytest.mark.parametrize('connection', [False, True])
def test_cross_context_exit_reports_error_but_does_not_strand_descriptor(tmp_path, connection):
    path = tmp_path/'test.duckdb'
    owner = warehouse_connection(path) if connection else warehouse_lock(path)
    handle = owner.__enter__()
    with pytest.raises(WarehouseLockError, match='WAREHOUSE_LOCK_CONTEXT'):
        contextvars.Context().run(owner.__exit__, None, None, None)
    with warehouse_connection(path) as new:
        require_writer(new)
        if connection:
            with pytest.raises(WarehouseLockError): require_writer(handle)


def test_generic_or_fabricated_memory_proxy_is_not_an_owner(tmp_path):
    class FakeMemory:
        def execute(self, *args): return self
        def fetchall(self): return []
    with warehouse_lock(tmp_path/'test.duckdb'):
        with pytest.raises(WarehouseLockError): require_writer(FakeMemory())
        with pytest.raises(WarehouseLockError): WarehouseConnectionProxy(FakeMemory())
    with duckdb.connect(':memory:') as memory:
        require_writer(memory)
        require_writer(WarehouseConnectionProxy(memory))
        memory.execute(f"ATTACH '{tmp_path/'attached.duckdb'}' AS attached")
        with pytest.raises(WarehouseLockError): require_writer(memory)


def test_managed_connection_cannot_grant_ownership_to_an_attached_disk(tmp_path):
    with warehouse_connection(tmp_path/'test.duckdb') as db:
        db.execute(f"ATTACH '{tmp_path/'attached.duckdb'}' AS attached")
        with pytest.raises(WarehouseLockError): require_writer(db)


def read_pipe(fd):
    assert select.select([fd], [], [], 5)[0], 'Fork barrier timed out'
    return os.read(fd, 100)


@pytest.mark.parametrize('origin', ['other_thread', 'other_context'])
def test_fork_closes_all_inherited_descriptors_without_unlocking_parent(tmp_path, origin):
    path = tmp_path/'test.duckdb'
    ready, release = threading.Event(), threading.Event()
    failures = []
    def holder():
        try:
            with warehouse_lock(path):
                ready.set()
                assert release.wait(10)
        except BaseException as error: failures.append(error)
    if origin == 'other_thread':
        thread = threading.Thread(target=holder); thread.start()
        assert ready.wait(5)
        owner = None
    else:
        owner = warehouse_lock(path); owner.__enter__()
        thread = None
    output_read, output_write = os.pipe()
    command_read, command_write = os.pipe()
    pid = None
    try:
        pid = contextvars.Context().run(os.fork)
        if pid == 0:
            os.close(output_read); os.close(command_write)
            try:
                try:
                    with warehouse_lock(path): os.write(output_write, b'BYPASS')
                except WarehouseLockError as error:
                    os.write(output_write, error.code.encode())
                os.read(command_read, 1)  # Keep child alive after parent releases owner.
                with warehouse_lock(path): os.write(output_write, b'CHILD_ACQUIRED')
                os.read(command_read, 1)
            finally:
                os._exit(0)
        os.close(output_write); os.close(command_read)
        assert read_pipe(output_read) == b'WAREHOUSE_BUSY'
        inode = path.with_name(path.name+'.lock').stat().st_ino
        # Child cleanup must not unlock the still-live parent owner's OFD.
        def contender():
            with pytest.raises(WarehouseLockError, match='WAREHOUSE_BUSY'):
                with warehouse_lock(path): pytest.fail('child unlocked parent')
        contextvars.Context().run(contender)
        if thread:
            release.set(); thread.join(5); assert not thread.is_alive() and not failures
        else:
            owner.__exit__(None, None, None); owner = None
        # Child is still blocked on pipe, but its inherited descriptor is closed.
        with warehouse_lock(path):
            assert path.with_name(path.name+'.lock').stat().st_ino == inode
        os.write(command_write, b'1')
        assert read_pipe(output_read) == b'CHILD_ACQUIRED'
        os.write(command_write, b'2')
        assert os.waitpid(pid, 0)[1] == 0; pid = None
    finally:
        release.set()
        if thread: thread.join(5)
        if owner: owner.__exit__(None, None, None)
        if pid:
            os.kill(pid, 9); os.waitpid(pid, 0)
        for fd in (output_read, output_write, command_read, command_write):
            try: os.close(fd)
            except OSError: pass


def test_fork_child_cannot_use_managed_connection(tmp_path):
    with warehouse_connection(tmp_path/'test.duckdb') as db:
        read, write = os.pipe(); pid = os.fork()
        if pid == 0:
            os.close(read)
            try:
                try: db.execute('SELECT 1')
                except WarehouseLockError: os.write(write, b'REJECTED')
            finally: os._exit(0)
        os.close(write)
        try:
            assert read_pipe(read) == b'REJECTED'
            assert os.waitpid(pid, 0)[1] == 0
        finally: os.close(read)
        assert db.execute('SELECT 1').fetchone() == (1,)
