"""Append-only local Parquet/lineage writer; never writes curated market tables."""

import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import SecretStr

from astock.data.audit import RawObjectManifest, RequestParams
from astock.data.probe_audit import canonical_json
from astock.data.tushare_client import ProviderTable


def migrate(db, root: Path):
    for name in ('001_foundation_schema', '002_provider_lineage', '003_probe_mode',
                 '004_security_identifier_history', '005_identity_bootstrap_governance', '006_bounded_slice_lifecycle'):
        number = int(name[:3])
        exists = db.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='schema_version'").fetchone()[0]
        if exists and db.execute('SELECT count(*) FROM schema_version WHERE version=?', [number]).fetchone()[0]:
            continue
        db.execute((root / 'sql' / (name+'.sql')).read_text())


def atomic_new_file(path: Path, write):
    """Publish closed bytes atomically without replacing an existing destination.

    POSIX hard-link publication supplies rename-like atomic visibility AND no-clobber;
    os.rename alone could overwrite a destination created between check and rename.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    os.close(handle)
    temporary = Path(temporary)
    try:
        write(temporary)
        with temporary.open('rb') as stream:
            os.fsync(stream.fileno())
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        os.link(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return checksum
    finally:
        temporary.unlink(missing_ok=True)


def schema_digest(table: pa.Table) -> str:
    return hashlib.sha256(canonical_json([(field.name, str(field.type)) for field in table.schema])).hexdigest()


class RawWriter:
    def __init__(self, root: Path, db: duckdb.DuckDBPyConnection):
        self.root, self.db = root.resolve(), db

    def write(self, run_id: UUID, dataset: str, part: int, table: ProviderTable,
              params: RequestParams) -> RawObjectManifest:
        if not 0 <= part <= 999:
            raise ValueError('Invalid part number')
        relative = f'data/raw/tushare/{dataset}/run_id={run_id}/part-{part:03d}.parquet'
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root / 'data/raw'):
            raise ValueError('Raw path escapes local storage')
        arrow = pa.table({name: pa.array([row[i] for row in table.items])
                          for i, name in enumerate(table.fields)})
        dates = []
        for column in ('trade_date', 'cal_date'):
            if column in table.fields:
                for value in arrow[column].to_pylist():
                    if isinstance(value, str) and len(value) == 8 and value.isdigit():
                        try:
                            dates.append(date.fromisoformat(f'{value[:4]}-{value[4:6]}-{value[6:]}'))
                        except ValueError:
                            pass
        # Validate all metadata before publishing; checksum filled after closed-file hashing.
        manifest = RawObjectManifest(object_id=uuid4(), run_id=run_id, dataset=dataset,
            relative_path=relative, sha256='0'*64, schema_hash=schema_digest(arrow),
            retrieved_at=table.retrieved_at, row_count=len(table.items), request_params=params,
            min_event_date=min(dates) if dates else None, max_event_date=max(dates) if dates else None)
        checksum = atomic_new_file(path, lambda temp: pq.write_table(arrow, temp))
        manifest = manifest.model_copy(update={'sha256': checksum})
        try:
            self.db.execute('BEGIN')
            self.db.execute('''INSERT INTO raw_object_manifest VALUES (?,?,?,?,?,?,?,?,?,?,?)''', [
                str(manifest.object_id), str(run_id), dataset, relative, checksum, table.retrieved_at,
                len(table.items), manifest.schema_hash, manifest.min_event_date, manifest.max_event_date,
                json.dumps(params.public_dict()),
            ])
            self.db.execute('''UPDATE ingestion_run SET row_count=row_count+?,
                raw_object_count=raw_object_count+1 WHERE run_id=?''', [len(table.items), str(run_id)])
            self.db.execute('COMMIT')
        except Exception:
            self.db.execute('ROLLBACK')
            # Completed immutable part survives; no sidecar falsely claims successful registration.
            raise
        return manifest

    def sidecar(self, run_id, dataset):
        rows = self.db.execute('''SELECT object_id, relative_path, sha256, retrieved_at, row_count,
            schema_hash, min_event_date, max_event_date, request_params FROM raw_object_manifest
            WHERE run_id=? ORDER BY relative_path''', [str(run_id)]).fetchall()
        objects = [dict(object_id=str(r[0]), relative_path=r[1], sha256=r[2],
                        retrieved_at=r[3].isoformat(), available_at=r[3].isoformat(),
                        availability_basis='OBSERVED_CAPTURE', row_count=r[4], schema_hash=r[5],
                        min_event_date=r[6].isoformat() if r[6] else None,
                        max_event_date=r[7].isoformat() if r[7] else None,
                        request_params=json.loads(r[8])) for r in rows]
        path = self.root/f'data/raw/tushare/{dataset}/run_id={run_id}/manifest.json'
        atomic_new_file(path, lambda temp: temp.write_bytes(canonical_json(
            dict(run_id=str(run_id), dataset=dataset, objects=objects))))
        return path


def secret_scan(token: SecretStr, paths: list[Path]) -> bool:
    secret = token.get_secret_value().encode('utf-8')
    if not secret:
        return False
    for path in paths:
        if not path.is_file() or path.is_symlink():
            return False
        if secret in path.read_bytes():
            return False
        if path.suffix == '.parquet':
            table=pq.ParquetFile(path).read()
            # Scan decoded text/binary recursively; typed dates/timestamps are not JSON scalars.
            # File bytes alone miss credentials inside compressed data pages.
            def contains(value):
                if isinstance(value,str):return secret in value.encode('utf-8')
                if isinstance(value,bytes):return secret in value
                if isinstance(value,dict):return any(contains(k) or contains(v) for k,v in value.items())
                if isinstance(value,(list,tuple)):return any(contains(v) for v in value)
                return False
            if secret in table.schema.serialize().to_pybytes() or contains(table.to_pydict()):
                return False
    return True


def verify_batch(root: Path, db, run_ids) -> bool:
    """Generic all-parts proof; empty/missing runs never constitute completion."""
    from astock.data.raw_validation import validate_raw_run

    try:
        requested = list(run_ids)
        if not requested or len({str(run) for run in requested}) != len(requested):
            return False
        for run_id in requested:
            validate_raw_run(root, db, run_id)
        return True
    except Exception:
        return False
