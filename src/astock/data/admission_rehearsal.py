"""Explicit candidate-only isolation boundary; production pipeline stays unchanged."""

import shutil
from pathlib import Path

from astock.data.raw_validation import sha256
from astock.data.reconstruction import Approval, Context, register_context
from astock.data.warehouse_lock import require_writer, warehouse_connection

NAMESPACE = 'CANDIDATE_REHEARSAL_ONLY:'


def safe_isolation(root: Path, destination: Path):
    root, destination = root.absolute(), destination.absolute()
    allowed = root / 'data/private/phase1c1-combined-remediation-b-rehearsal'
    if not destination.is_relative_to(allowed) or destination == allowed:
        raise ValueError('Dedicated isolated destination required')
    for path in (destination, *destination.parents):
        if path.is_symlink():
            raise ValueError('Symlink isolation path')
    if destination.exists():
        for path in destination.rglob('*'):
            if path.is_symlink() or path.is_file() and path.stat().st_nlink != 1:
                raise ValueError('Linked isolation evidence')
    return destination


def copy_snapshot(root: Path, destination: Path, db_path: Path) -> dict:
    """One shared owner/snapshot while copying; refuses any prior destination."""
    destination = safe_isolation(root, destination)
    original = root / 'data/warehouse/astock.duckdb'
    if db_path.absolute() != original.absolute() or original.is_symlink() or original.stat().st_nlink != 1:
        raise ValueError('Exact original database required')
    if destination.exists():
        raise ValueError('Fresh isolation root required')
    if original.with_suffix('.duckdb.wal').exists():
        raise ValueError('Original WAL blocks snapshot')
    inventory = []
    def copy(source):
        if source.is_symlink() or not source.is_file() or source.stat().st_nlink != 1:
            raise ValueError('Nonregular snapshot source')
        relative = source.relative_to(root)
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        before = sha256(source)
        shutil.copyfile(source, output)
        if before != sha256(output) or before != sha256(source) or output.stat().st_nlink != 1:
            raise ValueError('Snapshot bytes changed')
        inventory.append(dict(path=str(relative), sha256=before, bytes=source.stat().st_size))
    with warehouse_connection(original, read_only=True) as db:
        versions = db.execute('SELECT version FROM schema_version ORDER BY version').fetchall()
        if versions != [(i,) for i in range(1, 11)]:
            raise ValueError('Original schema changed')
        destination.mkdir(parents=True, exist_ok=False)
        copy(original)
        for relative in ('config', 'data/raw', 'data/curated', 'data/private/phase1c1'):
            for source in sorted((root/relative).rglob('*')):
                if source.is_symlink():
                    raise ValueError('Linked snapshot source')
                if source.is_file() and not source.name.endswith('.lock'):
                    copy(source)
        for source in sorted((root/'docs/remediation/phase1c1').glob('r2-a-design*.md')):
            copy(source)
        copy(root/'docs/remediation/phase1c1/combined-remediation-b-rehearsal/concrete-design-v1.md')
        if original.with_suffix('.duckdb.wal').exists():
            raise ValueError('Original WAL appeared')
    return dict(status='CONSISTENT_READ_ONLY_SNAPSHOT', original_writes=0,
                files=inventory, database_sha256=sha256(original))


def admit_fixture(root, db, context: Context, envelope: dict):
    """Only explicit isolated admission; bind new design/external evidence to Context."""
    require_writer(db)
    context = Context.model_validate(context)
    if not context.fixture_only or not context.approval.review_ref.startswith(NAMESPACE):
        raise ValueError('Candidate fixture namespace required')
    if len(context.inputs) != 133 or sum(i.is_output for i in context.inputs) != 126:
        raise ValueError('Exact original133/126 required even for rehearsal')
    if envelope != dict(namespace=NAMESPACE.removesuffix(':'), fixture_only=True,
                        implementation_sha=context.implementation_sha, context_hash=context.context_hash,
                        combined_design_hash=sha256(root/'docs/remediation/phase1c1/combined-remediation-b-rehearsal/concrete-design-v1.md'),
                        external_evidence_hash=envelope.get('external_evidence_hash')):
        raise ValueError('Fixture envelope differs')
    if not isinstance(envelope['external_evidence_hash'], str) or len(envelope['external_evidence_hash']) != 64:
        raise ValueError('External evidence digest required')
    paths = [Path(p).absolute() for _, _, p in db.execute('PRAGMA database_list').fetchall() if p]
    if paths != [(root/'data/warehouse/astock.duckdb').absolute()]:
        raise ValueError('Fixture database must be rooted inside isolation')
    parts = root.absolute().parts
    if 'phase1c1-combined-remediation-b-rehearsal' not in parts or 'isolated-root' != parts[-1]:
        raise ValueError('Dedicated fixture root required')
    for path in (root, *root.parents):
        if path.is_symlink():
            raise ValueError('Symlink fixture root')
    return register_context(root, db, context, allow_fixture=True)
