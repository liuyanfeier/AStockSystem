"""Candidate snapshot boundaries; original SQL and production guards unchanged."""

from pathlib import Path

import pytest

from astock.data.admission_rehearsal import copy_snapshot, safe_isolation
from astock.data.raw_validation import sha256
from astock.data.warehouse_lock import warehouse_connection


def original(tmp_path):
    root=tmp_path/'project';root.mkdir()
    path=root/'data/warehouse/astock.duckdb';path.parent.mkdir(parents=True)
    with warehouse_connection(path) as db:
        db.execute('CREATE TABLE schema_version(version INTEGER)')
        db.executemany('INSERT INTO schema_version VALUES (?)',[(i,) for i in range(1,11)])
    d=root/'docs/remediation/phase1c1/combined-remediation-b-rehearsal';d.mkdir(parents=True)
    (d/'concrete-design-v1.md').write_text('fixture-design')
    for rel in ('config','data/raw','data/curated','data/private/phase1c1'):
        p=root/rel;p.mkdir(parents=True);(p/'fixture.txt').write_text(rel)
    return root,path,root/'data/private/phase1c1-combined-remediation-b-rehearsal/run/isolated-root'


def test_consistent_snapshot_regular_copy_original_unchanged_and_no_overwrite(tmp_path):
    root,db,dest=original(tmp_path);before=sha256(db)
    result=copy_snapshot(root,dest,db)
    assert result['original_writes']==0 and result['database_sha256']==before
    for f in result['files']:
        output=dest/f['path'];assert sha256(output)==f['sha256'] and output.stat().st_nlink==1
    assert sha256(db)==before
    with pytest.raises(ValueError,match='Fresh'):copy_snapshot(root,dest,db)


@pytest.mark.parametrize('kind',['escape','symlink','hardlink','wal','version','source-link','wrong-db'])
def test_snapshot_failures_preserve_original(tmp_path,kind):
    root,db,dest=original(tmp_path)
    if kind=='escape':dest=tmp_path/'escaped'
    elif kind=='symlink':
        target=tmp_path/'external';target.mkdir();dest.parent.mkdir(parents=True);dest.symlink_to(target)
    elif kind=='hardlink':__import__('os').link(db,tmp_path/'linked.duckdb')
    elif kind=='wal':db.with_suffix('.duckdb.wal').write_bytes(b'unknown')
    elif kind=='version':
        with warehouse_connection(db) as connection:connection.execute('DELETE FROM schema_version WHERE version=10')
    elif kind=='source-link':(root/'config/link').symlink_to(root/'config/fixture.txt')
    elif kind=='wrong-db':db=tmp_path/'wrong.duckdb'
    before=sha256(root/'data/warehouse/astock.duckdb')
    with pytest.raises(ValueError):copy_snapshot(root,dest,db)
    assert sha256(root/'data/warehouse/astock.duckdb')==before


def test_existing_isolated_link_refused(tmp_path):
    root,db,dest=original(tmp_path);dest.mkdir(parents=True)
    (dest/'escape').symlink_to(db)
    with pytest.raises(ValueError,match='Linked'):safe_isolation(root,dest)


def test_preexisting_readonly_legacy_backup_links_copy_to_independent_files(tmp_path):
    root,db,dest=original(tmp_path)
    source=root/'data/curated/fixture.txt';old_backup=root/'data/private/phase1c1/legacy-backup.txt'
    __import__('os').link(source,old_backup)
    inode=source.stat().st_ino;assert source.stat().st_nlink==2
    result=copy_snapshot(root,dest,db)
    assert source.stat().st_ino==inode and source.stat().st_nlink==2
    assert (dest/'data/curated/fixture.txt').stat().st_nlink==1
    assert (dest/'data/private/phase1c1/legacy-backup.txt').stat().st_nlink==1
    linked=[f for f in result['files'] if f['existing_source_links']==2]
    assert len(linked)==2 and all(f['destination_links']==1 for f in linked)
