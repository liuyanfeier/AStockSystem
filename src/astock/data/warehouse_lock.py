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


@dataclass(frozen=True)
class _Guard:
    path: Path
    descriptor: int
    exclusive: bool
    pid: int
    thread: int


_held: ContextVar[tuple[_Guard, ...]] = ContextVar('warehouse_guards', default=())


def _after_fork() -> None:
    # Close child copies without LOCK_UN (which would unlock the parent's open
    # file description). The child must acquire independently, never inherit ownership.
    for guard in _held.get():
        try:
            os.close(guard.descriptor)
        except OSError:
            pass
    _held.set(())


os.register_at_fork(after_in_child=_after_fork)


def _owner(path: Path) -> _Guard | None:
    return next((guard for guard in _held.get() if guard.path == path
                 and guard.pid == os.getpid() and guard.thread == threading.get_ident()), None)


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
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
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
        if token is not None and os.getpid() == pid:
            _held.reset(token)
        if descriptor is not None and os.getpid() == pid:
            os.close(descriptor)  # OS releases ownership; persistent inode is retained.


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
            yield db
        finally:
            db.close()


def require_writer(db) -> None:
    """Disk helpers reject late locking/unmanaged connections; memory tests are explicit."""
    for _, _, filename in db.execute('PRAGMA database_list').fetchall():
        if filename:
            owner = _owner(Path(filename).resolve())
            if owner is None or not owner.exclusive:
                raise WarehouseLockError('WAREHOUSE_LOCK_REQUIRED')
