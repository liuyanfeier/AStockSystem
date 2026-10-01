import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import duckdb
import pyarrow.parquet as pq
import pytest
from pydantic import SecretStr

from astock.data.audit import RequestParams
from astock.data.raw_writer import RawWriter, atomic_new_file, migrate, secret_scan, verify_batch
from astock.data.tushare_client import ProviderTable
from astock.paths import get_project_root


RUN=UUID('00000000-0000-0000-0000-000000000001')
NOW=datetime(2024,1,3,tzinfo=timezone.utc)


@pytest.fixture
def db():
    with duckdb.connect(':memory:') as db:
        migrate(db,get_project_root())
        db.execute('''INSERT INTO ingestion_run (run_id,source,dataset,mode,started_at,status,
            code_commit,config_hash,provider_client_version) VALUES (?,'tushare','daily','PROBE',?,
            'RUNNING',?,?,'0.1.0')''',[str(RUN),NOW,'a'*40,'b'*64])
        yield db


def table():
    return ProviderTable(fields=['ts_code','trade_date','close'],items=[['000001.SZ','20240103',10.0]],
                         retrieved_at=NOW)


def test_populated_migration_preserves_parent_child_rows_and_reruns():
    with duckdb.connect(':memory:') as db:
        root=get_project_root()
        db.execute((root/'sql/001_foundation_schema.sql').read_text())
        db.execute((root/'sql/002_provider_lineage.sql').read_text())
        db.execute('''INSERT INTO ingestion_run (run_id,source,dataset,mode,started_at,status,
            code_commit,config_hash,provider_client_version) VALUES (?,'tushare','daily','AUDIT',?,
            'RUNNING',?,?,'0.0.1')''',[str(RUN),NOW,'a'*40,'b'*64])
        db.execute('''INSERT INTO raw_object_manifest VALUES (?,?,?,?,?,?,?,?,?,?,?)''',[
            '00000000-0000-0000-0000-000000000002',str(RUN),'daily',
            f'data/raw/tushare/daily/run_id={RUN}/part-000.parquet','a'*64,NOW,1,'b'*64,None,None,'{}'])
        parents=db.execute('SELECT * FROM ingestion_run').fetchall()
        children=db.execute('SELECT * FROM raw_object_manifest').fetchall()
        for _ in range(2):
            db.execute((root/'sql/003_probe_mode.sql').read_text())
            assert db.execute('SELECT * FROM ingestion_run').fetchall()==parents
            assert db.execute('SELECT * FROM raw_object_manifest').fetchall()==children
        db.execute("UPDATE ingestion_run SET mode='PROBE',error_category='PERMISSION' WHERE run_id=?",[str(RUN)])
        parents=db.execute('SELECT * FROM ingestion_run').fetchall()
        for _ in range(2):
            db.execute((root/'sql/004_security_identifier_history.sql').read_text())
            assert db.execute('SELECT * FROM ingestion_run').fetchall()==parents
            assert db.execute('SELECT * FROM raw_object_manifest').fetchall()==children
            assert db.execute('SELECT count(*) FROM security_identifier_history').fetchone()==(0,)
        with pytest.raises(duckdb.Error):
            db.execute('DELETE FROM ingestion_run WHERE run_id=?',[str(RUN)])


def test_atomic_writer_checksum_lineage_no_overwrite_and_sidecar(tmp_path,db):
    writer=RawWriter(tmp_path,db)
    manifest=writer.write(RUN,'daily',0,table(),RequestParams())
    path=tmp_path/manifest.relative_path
    assert manifest.sha256==hashlib.sha256(path.read_bytes()).hexdigest()
    assert pq.read_table(path)['close'].to_pylist()==[10.0]
    assert db.execute('SELECT row_count,raw_object_count FROM ingestion_run').fetchone()==(1,1)
    assert not list(path.parent.glob('.pending-*'))
    with pytest.raises(FileExistsError):writer.write(RUN,'daily',0,table(),RequestParams())
    assert db.execute('SELECT count(*) FROM raw_object_manifest').fetchone()==(1,)
    sidecar=json.loads(writer.sidecar(RUN,'daily').read_bytes())
    assert sidecar['objects'][0]['availability_basis']=='OBSERVED_CAPTURE'
    assert sidecar['objects'][0]['available_at']==sidecar['objects'][0]['retrieved_at']
    assert verify_batch(tmp_path,db,[RUN])
    path.write_bytes(b'tampered synthetic file')
    assert not verify_batch(tmp_path,db,[RUN])


def test_failed_temp_write_leaves_no_final_or_partial_file(tmp_path):
    def fail(path):
        path.write_bytes(b'synthetic partial content')
        raise RuntimeError('synthetic failure')
    with pytest.raises(RuntimeError):atomic_new_file(tmp_path/'part.parquet',fail)
    assert list(tmp_path.iterdir())==[]


def test_manifest_insert_failure_retains_completed_file_without_false_lineage(tmp_path,db):
    writer=RawWriter(tmp_path,db)
    wrong=UUID('00000000-0000-0000-0000-000000000099')
    with pytest.raises(duckdb.Error):writer.write(wrong,'daily',0,table(),RequestParams())
    assert len(list(tmp_path.rglob('*.parquet')))==1
    assert db.execute('SELECT count(*) FROM raw_object_manifest').fetchone()==(0,)


def test_scan_checks_decoded_compressed_parquet_and_never_prints(tmp_path,capsys):
    secret=SecretStr('synthetic-unique-sensitive-token')
    p=tmp_path/'value.parquet'
    import pyarrow as pa
    pq.write_table(pa.table({'value':[secret.get_secret_value()]}),p,compression='gzip')
    assert not secret_scan(secret,[p])
    assert not capsys.readouterr().out
    p.write_bytes(b'nonsecret')
    assert secret_scan(secret,[p.with_suffix('.txt')]) is False
