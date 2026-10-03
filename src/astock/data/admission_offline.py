"""New synthetic-only lifecycle and full-scale publication; no live entry point."""

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from astock.data.provider_identity import DATASETS
from astock.data.raw_validation import sha256
from astock.data.raw_writer import atomic_new_file
from astock.data.reconstruction import checksum, transaction
from astock.data.warehouse_lock import require_writer

PROTOCOL = 'ADMISSION_SYNTHETIC_V1'
SCHEMA = pa.schema([('member_id', pa.string()), ('source_ordinal', pa.int64()), ('value', pa.float64())])


def clock() -> datetime:
    return datetime.now(timezone.utc)


def initialize(root: Path, db) -> None:
    """Reject populated warehouses; this draft schema cannot migrate a real store."""
    require_writer(db)
    if db.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='main'").fetchone()[0]:
        raise ValueError('Synthetic store must be empty')
    transaction(db, lambda: db.execute((root / 'sql/offline/admission_v1.sql').read_text()))


def plan(db, plan_id: str) -> None:
    if not plan_id.strip():
        raise ValueError('Empty plan identity')
    transaction(db, lambda: db.execute('INSERT INTO offline_plan VALUES (?,?,false)', [plan_id, clock()]))


def events(db, plan_id: str) -> list:
    return db.execute('SELECT state,occurred_at,payload FROM offline_attempt_event WHERE plan_id=? ORDER BY ordinal', [plan_id]).fetchall()


def _event(db, plan_id: str, state: str, payload: dict) -> None:
    history = events(db, plan_id)
    transition = {None: 'RUNNING', 'RUNNING': 'CALL_ENTERED'}
    prior = history[-1][0] if history else None
    if state not in ('UNCERTAIN', 'COMPLETE'):
        if transition.get(prior) != state:
            raise ValueError('No repeat claim or automatic resend')
    elif prior not in ('CALL_ENTERED', 'UNCERTAIN') or (state == 'UNCERTAIN' and prior == state):
        raise ValueError('Invalid terminal/reconciliation transition')
    transaction(db, lambda: db.execute('INSERT INTO offline_attempt_event VALUES (?,?,?,?,?)',
        [plan_id, len(history), state, clock(), json.dumps(payload, sort_keys=True)]))


@dataclass(frozen=True)
class FakeTransport:
    """Closed injected synthetic transport. No token/client/socket integration."""
    payload: bytes = b'synthetic-captured-rows'
    fail: bool = False

    def send(self, observe_claim):
        observe_claim()
        if self.fail:
            raise RuntimeError('Synthetic uncertain transport')
        return self.payload


def capture(db, root: Path, plan_id: str, transport: FakeTransport, *, observe_claim=lambda: None) -> str:
    if type(transport) is not FakeTransport:
        raise ValueError('Only the closed fake transport is supported')
    _event(db, plan_id, 'RUNNING', {})  # committed before injected transport
    _event(db, plan_id, 'CALL_ENTERED', {'meaning': 'LOCAL_ENTRY_NOT_REMOTE_RECEIPT'})
    try:
        payload = transport.send(observe_claim)
        if not payload:
            raise ValueError('Empty raw content cannot complete')
        path = root / (checksum(plan_id) + '.raw')
        atomic_new_file(path, lambda p: p.write_bytes(payload))
        retrieved = clock()
        transaction(db, lambda: db.execute('INSERT INTO offline_raw_manifest VALUES (?,?,?,?,?,?,?)',
            [plan_id, uuid4(), path.name, sha256(path), retrieved, clock(), clock()]))
        return complete_capture(db, root, plan_id)
    except BaseException:
        if events(db, plan_id)[-1][0] != 'COMPLETE':
            _event(db, plan_id, 'UNCERTAIN', {'automatic_resend': False})
        raise


def complete_capture(db, root: Path, plan_id: str) -> str:
    row = db.execute('SELECT * FROM offline_raw_manifest WHERE plan_id=?', [plan_id]).fetchone()
    if row is None:
        raise ValueError('No exact raw manifest')
    path = root / row[2]
    if path.parent.resolve() != root.resolve() or path.is_symlink() or not path.is_file() or path.stat().st_size == 0 or sha256(path) != row[3]:
        raise ValueError('Raw bytes changed or invalid')
    history = events(db, plan_id)
    if history and history[-1][0] == 'COMPLETE':
        if json.loads(history[-1][2]) != {'object_id': str(row[1]), 'sha256': row[3]}:
            raise ValueError('Completion manifest changed')
        return 'ALREADY_VALID'
    _event(db, plan_id, 'COMPLETE', {'object_id': str(row[1]), 'sha256': row[3]})
    return 'COMPLETE'


def stress_members(start=date(2013, 1, 1), end=date(2026, 9, 30)) -> list[dict]:
    """All civil days are an upper bound, never a real trading-calendar claim."""
    if start > end:
        raise ValueError('Invalid interval')
    result = []
    for offset in range((end-start).days+1):
        day = start + timedelta(days=offset)
        for dataset in DATASETS:
            key = f'{dataset}/{day.year}/{day.isoformat()}'
            # Nonempty representatives span every dataset/year.
            n = 3 if day.day == 1 and day.month == 1 else 0
            rows = [dict(member_id=key, source_ordinal=i, value=float(i+1)) for i in range(n)]
            result.append(dict(member_id=key, dataset=dataset, event_date=day.isoformat(),
                source_hash=checksum({'synthetic': True, 'rows': rows}), source_rows=n, row_hash=checksum(rows)))
    return result


def manifest_hash(members: list[dict]) -> str:
    if not members or len({m['member_id'] for m in members}) != len(members):
        raise ValueError('Empty or duplicate member set')
    for m in members:
        if m['dataset'] not in DATASETS or m['member_id'] != f"{m['dataset']}/{date.fromisoformat(m['event_date']).year}/{m['event_date']}":
            raise ValueError('Invalid dataset-year membership')
        rows = synthetic_rows(m)
        if m['row_hash'] != checksum(rows) or m['source_hash'] != checksum({'synthetic': True, 'rows': rows}):
            raise ValueError('Source/member content pin changed')
    return checksum(dict(protocol=PROTOCOL, execution_license=False,
                         calendar_basis='ALL_CIVIL_DAYS_SYNTHETIC_UPPER_BOUND', members=sorted(members, key=lambda m: m['member_id'])))


def synthetic_rows(member: dict) -> list[dict]:
    n = member['source_rows']
    if type(n) is not int or n not in (0, 3):
        raise ValueError('Invalid synthetic source population')
    return [dict(member_id=member['member_id'], source_ordinal=i, value=float(i+1)) for i in range(n)]


def register_manifest(db, members: list[dict]) -> str:
    pin = manifest_hash(members)
    row = db.execute('SELECT member_count,execution_license FROM offline_generation WHERE manifest_hash=?', [pin]).fetchone()
    expected = sorted([tuple(m[k] for k in ('member_id','dataset','event_date','source_hash','source_rows','row_hash')) for m in members])
    if row:
        current = db.execute('SELECT member_id,dataset,CAST(event_date AS VARCHAR),source_hash,source_rows,row_hash FROM offline_member WHERE manifest_hash=? ORDER BY member_id', [pin]).fetchall()
        if row != (len(members), False) or current != expected:
            raise ValueError('Persisted membership differs')
        return pin
    def insert():
        db.execute('INSERT INTO offline_generation VALUES (?,?,false,NULL)', [pin, len(members)])
        db.executemany('INSERT INTO offline_member VALUES (?,?,?,?,?,?,?)', [(pin, *row) for row in expected])
    transaction(db, insert)
    return pin


def _paths(root: Path, member: dict) -> tuple[Path, Path]:
    # Digest filenames avoid path injection and per-directory 999-member limits.
    directory = root / member['dataset'] / str(date.fromisoformat(member['event_date']).year)
    name = checksum(member['member_id'])
    return directory / (name+'.parquet'), directory / (name+'.json')


def verify_output(root: Path, member: dict) -> dict:
    path, sidecar = _paths(root, member)
    if path.is_symlink() or sidecar.is_symlink():
        raise ValueError('Symlink output rejected')
    meta = json.loads(sidecar.read_text())
    table = pq.ParquetFile(path).read()
    if table.schema != SCHEMA or table.to_pylist() != synthetic_rows(member):
        raise ValueError('Typed content or row conservation changed')
    expected = dict(protocol=PROTOCOL, member=member, schema_hash=checksum(str(SCHEMA)), bytes_sha256=sha256(path))
    if meta != expected:
        raise ValueError('Sidecar/source/hash changed')
    return dict(bytes_sha256=sha256(path), sidecar_sha256=sha256(sidecar))


def publish_member(db, root: Path, pin: str, member: dict, *, fault=None) -> str:
    row = db.execute('SELECT dataset,CAST(event_date AS VARCHAR),source_hash,source_rows,row_hash FROM offline_member WHERE manifest_hash=? AND member_id=?', [pin,member['member_id']]).fetchone()
    if row != tuple(member[k] for k in ('dataset','event_date','source_hash','source_rows','row_hash')):
        raise ValueError('Unknown or changed exact member')
    existing = db.execute('SELECT bytes_sha256,sidecar_sha256 FROM offline_output WHERE manifest_hash=? AND member_id=?', [pin,member['member_id']]).fetchone()
    path, sidecar = _paths(root, member)
    if existing:
        verified = verify_output(root, member)
        if tuple(verified.values()) != existing:
            raise ValueError('Registered output changed')
        return 'ALREADY_VALID'
    if sidecar.exists() and not path.exists():
        raise ValueError('Orphan sidecar without bytes')
    if not path.exists():
        table = pa.Table.from_pylist(synthetic_rows(member), schema=SCHEMA)
        atomic_new_file(path, lambda p: pq.write_table(table, p))
    # File-only crash recovery is allowed ONLY after independent exact content validation.
    table = pq.ParquetFile(path).read()
    if path.is_symlink() or table.schema != SCHEMA or table.to_pylist() != synthetic_rows(member):
        raise ValueError('Orphan content differs')
    if fault == 'file':
        raise RuntimeError('Injected file publication failure')
    meta = dict(protocol=PROTOCOL, member=member, schema_hash=checksum(str(SCHEMA)), bytes_sha256=sha256(path))
    if not sidecar.exists():
        atomic_new_file(sidecar, lambda p: p.write_text(json.dumps(meta, sort_keys=True)+'\n'))
    verified = verify_output(root, member)
    if fault == 'sidecar':
        raise RuntimeError('Injected sidecar failure')
    def register():
        db.execute('INSERT INTO offline_output VALUES (?,?,?,?)', [pin,member['member_id'],*verified.values()])
        if fault == 'registration':
            raise RuntimeError('Injected registration failure')
    transaction(db, register)
    return 'REGISTERED'


def promote(db, root: Path, members: list[dict], *, fault=False) -> str:
    pin = register_manifest(db, members)
    stored = db.execute('SELECT member_id,bytes_sha256,sidecar_sha256 FROM offline_output WHERE manifest_hash=? ORDER BY member_id', [pin]).fetchall()
    if {r[0] for r in stored} != {m['member_id'] for m in members}:
        raise ValueError('Partial generation cannot promote/select')
    expected = []
    for m in sorted(members, key=lambda m:m['member_id']):
        verified = verify_output(root, m)
        expected.append((m['member_id'], *verified.values()))
    if stored != expected:
        raise ValueError('Registered hashes changed')
    expected_paths = {p.resolve() for m in members for p in _paths(root, m)}
    actual_paths = {p.resolve() for p in root.rglob('*') if p.is_file()}
    if actual_paths != expected_paths:
        raise ValueError('Unknown/orphan output file outside exact membership')
    completion = checksum(expected)
    current = db.execute('SELECT complete_hash FROM offline_generation WHERE manifest_hash=?', [pin]).fetchone()[0]
    if current is not None:
        if current != completion:
            raise ValueError('Completion changed')
        return 'ALREADY_VALID'
    def apply():
        db.execute('UPDATE offline_generation SET complete_hash=? WHERE manifest_hash=? AND complete_hash IS NULL', [completion,pin])
        if fault:
            raise RuntimeError('Injected promotion failure')
    transaction(db, apply)
    return 'COMPLETE'


def select_complete(db, root: Path, members: list[dict]) -> str:
    pin = manifest_hash(members)
    current = db.execute('SELECT complete_hash FROM offline_generation WHERE manifest_hash=?', [pin]).fetchone()
    if current is None or current[0] is None:
        raise ValueError('Partial generation cannot promote/select')
    promote(db, root, members)  # revalidate immutable membership and all typed bytes
    return pin
