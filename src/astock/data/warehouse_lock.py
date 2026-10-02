"""Cooperating macOS/Linux processes guard a warehouse before connecting to it."""

import fcntl
import math
import os
import stat
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

import duckdb

from astock.data.slice_errors import ReceiptIntegrityError


class WarehouseLockError(ReceiptIntegrityError):
    """Stable diagnostics; never expose database paths/native exception bodies."""


@dataclass
class _Guard:
    path: Path
    descriptor: int
    exclusive: bool
    pid: int
    thread: int
    active: bool = True


_held: ContextVar[tuple[_Guard, ...]] = ContextVar('warehouse_guards', default=())
_registry_lock = threading.RLock()
_descriptors: set[int] = set()


def _before_fork() -> None:
    # Synchronize fork with open/register and unregister/close in ALL threads.
    _registry_lock.acquire()


def _parent_after_fork() -> None:
    _registry_lock.release()


def _after_fork() -> None:
    global _registry_lock
    # Close child copies without LOCK_UN (which would unlock the parent's open
    # file description). The child must acquire independently, never inherit ownership.
    for descriptor in _descriptors:
        try:
            os.close(descriptor)
        except OSError:
            pass
    _held.set(())
    _descriptors.clear()
    _registry_lock = threading.RLock()


os.register_at_fork(before=_before_fork, after_in_parent=_parent_after_fork,
                    after_in_child=_after_fork)


def _owner(path: Path) -> _Guard | None:
    return next((guard for guard in _held.get() if guard.path == path
                 and guard.active and guard.pid == os.getpid()
                 and guard.thread == threading.get_ident()), None)


@contextmanager
def warehouse_lock(path: Path | str, *, shared: bool = False, wait_seconds: float = 0):
    """Stable sibling .lock inode; no unlink, PID/mtime/existence-based acquisition.

    Helpers reuse their owner's guard. Shared ownership cannot upgrade to exclusive.
    Contention is immediate by default; an explicit wait is bounded to five seconds.
    """
    if not math.isfinite(wait_seconds) or not 0 <= wait_seconds <= 5:
        raise WarehouseLockError('WAREHOUSE_LOCK_WAIT')
    resolved = Path(path).expanduser().resolve()
    owner = _owner(resolved)
    if owner:
        if not shared and not owner.exclusive:
            raise WarehouseLockError('WAREHOUSE_LOCK_REQUIRED')
        yield owner
        return
    lock_path = resolved.with_name(resolved.name + '.lock')
    descriptor = None
    token = None
    pid = os.getpid()
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with _registry_lock:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            _descriptors.add(descriptor)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise WarehouseLockError('WAREHOUSE_LOCK_PATH')
        deadline = time.monotonic() + wait_seconds
        while True:
            try:
                fcntl.flock(descriptor, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WarehouseLockError('WAREHOUSE_BUSY') from None
                time.sleep(min(0.05, remaining))
        current = os.stat(lock_path, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise WarehouseLockError('WAREHOUSE_LOCK_PATH')
        guard = _Guard(resolved, descriptor, not shared, pid, threading.get_ident())
        token = _held.set((*_held.get(), guard))
        yield guard
    except OSError:
        if token is not None:
            raise
        raise WarehouseLockError('WAREHOUSE_LOCK_PATH') from None
    finally:
        try:
            if token is not None and os.getpid() == pid:
                guard.active = False
                try:
                    _held.reset(token)
                except ValueError:
                    raise WarehouseLockError('WAREHOUSE_LOCK_CONTEXT') from None
        finally:
            # Even an invalid cross-context exit must not strand an OS lock.
            if descriptor is not None and os.getpid() == pid:
                with _registry_lock:
                    _descriptors.remove(descriptor)
                    os.close(descriptor)  # OS release; persistent inode is retained.


@dataclass
class _ConnectionScope:
    guard: _Guard
    read_only: bool
    active: bool = True


class WarehouseConnection:
    """Scoped connection/cursor: no native connection escapes via execute results.

    Only warehouse_connection creates these handles. Native SQL remains a trusted
    application operation, not a sandbox for arbitrary caller-supplied SQL.
    """

    def __init__(self, native, scope: _ConnectionScope, handles: list):
        self._native, self._scope, self._handles = native, scope, handles
        self._closed = False
        handles.append(self)

    def _check(self, *, writer: bool = False) -> None:
        guard = self._scope.guard
        if (self._closed or not self._scope.active or not guard.active
                or guard.pid != os.getpid() or guard.thread != threading.get_ident()
                or _owner(guard.path) is not guard
                or (writer and (self._scope.read_only or not guard.exclusive))):
            raise WarehouseLockError('WAREHOUSE_LOCK_REQUIRED')

    def execute(self, *args, **kwargs):
        self._check()
        self._native.execute(*args, **kwargs)
        return self

    def executemany(self, *args, **kwargs):
        self._check()
        self._native.executemany(*args, **kwargs)
        return self

    def fetchone(self):
        self._check()
        return self._native.fetchone()

    def fetchall(self):
        self._check()
        return self._native.fetchall()

    def fetchmany(self, size=1):
        self._check()
        return self._native.fetchmany(size)

    @property
    def description(self):
        self._check()
        return self._native.description

    def cursor(self):
        self._check()
        return WarehouseConnection(self._native.cursor(), self._scope, self._handles)

    def close(self) -> None:
        if self._closed:
            return
        self._check()
        if self is self._handles[0]:
            self._close_scope()
        else:
            self._closed = True
            self._native.close()

    def _close_scope(self) -> None:
        self._scope.active = False
        failure = None
        for handle in reversed(self._handles):
            if not handle._closed:
                handle._closed = True
                try:
                    handle._native.close()
                except Exception as error:
                    failure = failure or error
        if failure is not None:
            raise failure


class WarehouseConnectionProxy:
    """Explicit fault/delegation adapter; delegates ownership to a checked handle.

    Arbitrary duck-typed proxies cannot establish disk or memory ownership.
    Subclasses may intercept execute for synthetic faults; helpers validate the
    registered base handle, never an adapter's simulated PRAGMA result.
    """

    def __init__(self, db):
        if not isinstance(db, (WarehouseConnection, WarehouseConnectionProxy,
                               duckdb.DuckDBPyConnection)):
            raise WarehouseLockError('WAREHOUSE_LOCK_REQUIRED')
        self._connection = db

    def execute(self, *args, **kwargs):
        require_writer(self)
        return self._connection.execute(*args, **kwargs)


@contextmanager
def warehouse_connection(path: Path | str, *, read_only: bool = False, wait_seconds: float = 0):
    """Lock-before-connect, held through connection close and file publication."""
    with warehouse_lock(path, shared=read_only, wait_seconds=wait_seconds) as guard:
        try:
            db = duckdb.connect(str(guard.path), read_only=read_only)
        except duckdb.IOException:
            # Native locking/open failure is also closed, even for an uncooperative writer.
            raise WarehouseLockError('WAREHOUSE_NATIVE_LOCKED_OR_OPEN_FAILED') from None
        try:
            scope = _ConnectionScope(guard, read_only)
            handles: list[WarehouseConnection] = []
            yield WarehouseConnection(db, scope, handles)
        finally:
            # Invalidate escaped handles/contexts BEFORE closing all native cursors,
            # while ownership is still held. Never call inherited DuckDB in child.
            if guard.pid == os.getpid():
                scope.active = False
                try:
                    handles[0]._close_scope()
                finally:
                    db.close()


def require_writer(db) -> None:
    """Prove managed lifetime AND exclusive ownership; only native memory bypasses."""
    while isinstance(db, WarehouseConnectionProxy):
        db = db._connection
    if isinstance(db, WarehouseConnection):
        db._check(writer=True)
        databases = db._native.execute('PRAGMA database_list').fetchall()
        if all(not filename or Path(filename).resolve() == db._scope.guard.path
               for _, _, filename in databases):
            return
    elif type(db) is duckdb.DuckDBPyConnection:
        # Never trust a generic proxy's fabricated empty/memory PRAGMA response.
        databases = db.execute('PRAGMA database_list').fetchall()
        if databases and all(not filename for _, _, filename in databases):
            return
    raise WarehouseLockError('WAREHOUSE_LOCK_REQUIRED')
