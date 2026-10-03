"""Persistent isolated proof, injected local transport; no market clients."""

import json
from datetime import date
from pathlib import Path

import pytest

from astock.data import admission_offline as a
from astock.data.warehouse_lock import warehouse_connection

ROOT = Path(__file__).parents[1]


@pytest.fixture
def store(tmp_path):
    path = tmp_path/'fixture.duckdb'
    with warehouse_connection(path) as db:
        a.initialize(ROOT, db)
    return path, tmp_path/'outputs'


def test_plan_claim_is_durable_before_local_call_and_completion_times_are_stable(store):
    path, outputs = store
    with warehouse_connection(path) as db:
        a.plan(db, 'exact-plan')
        assert a.events(db, 'exact-plan') == []
        def observe():
            with warehouse_connection(path) as independent:
                assert [r[0] for r in a.events(independent, 'exact-plan')] == ['RUNNING','CALL_ENTERED']
                assert independent.execute('SELECT count(*) FROM offline_raw_manifest').fetchone()[0] == 0
        assert a.capture(db, outputs, 'exact-plan', a.FakeTransport(), observe_claim=observe) == 'COMPLETE'
        times = a.events(db,'exact-plan')
        raw = db.execute('SELECT * FROM offline_raw_manifest').fetchall()
    with warehouse_connection(path) as db:
        assert a.complete_capture(db, outputs, 'exact-plan') == 'ALREADY_VALID'
        assert a.events(db,'exact-plan') == times
        assert db.execute('SELECT * FROM offline_raw_manifest').fetchall() == raw
        created = db.execute('SELECT created_at FROM offline_plan').fetchone()[0]
        assert created <= times[0][1] <= times[1][1] <= raw[0][4] <= raw[0][5] <= raw[0][6] <= times[2][1]


@pytest.mark.parametrize('prior', ('missing','claimed','uncertain','empty'))
def test_no_transport_after_failed_claim_or_crash_and_no_random_completion(store, prior):
    path, outputs = store
    calls = []
    with warehouse_connection(path) as db:
        if prior != 'missing':
            a.plan(db, 'p')
        if prior == 'claimed':
            a._event(db,'p','RUNNING',{})
        if prior == 'uncertain':
            with pytest.raises(RuntimeError):
                a.capture(db, outputs, 'p', a.FakeTransport(fail=True))
        if prior == 'empty':
            with pytest.raises(ValueError):
                a.capture(db, outputs,'p',a.FakeTransport(payload=b''))
        with pytest.raises(Exception):
            a.capture(db, outputs,'p',a.FakeTransport(),observe_claim=lambda:calls.append(1))
        assert calls == []
        with pytest.raises(ValueError,match='No exact raw manifest'):
            a.complete_capture(db,outputs,'p')
    with warehouse_connection(path) as db:
        assert db.execute('SELECT count(*) FROM offline_raw_manifest').fetchone()[0] == 0


def test_real_transport_and_populated_warehouse_are_rejected(store):
    path, outputs = store
    with warehouse_connection(path) as db:
        with pytest.raises(ValueError,match='empty'):
            a.initialize(ROOT,db)
        a.plan(db,'p')
        with pytest.raises(ValueError,match='closed fake'):
            a.capture(db,outputs,'p',object())
        assert a.events(db,'p') == []


@pytest.mark.parametrize('fault',('file','sidecar','registration','promotion'))
def test_exact_resume_across_dataset_year_partial_and_fault_boundaries(store,fault):
    path, outputs = store
    members = a.stress_members(date(2024,12,31),date(2025,1,1))
    with warehouse_connection(path) as db:
        pin = a.register_manifest(db,members)
        first = members[0]
        if fault != 'promotion':
            with pytest.raises(RuntimeError):
                a.publish_member(db,outputs,pin,first,fault=fault)
        with pytest.raises(ValueError,match='Partial'):
            a.select_complete(db,outputs,members)
    with warehouse_connection(path) as db:
        assert a.register_manifest(db,members)==pin
        for m in members:a.publish_member(db,outputs,pin,m)
        if fault=='promotion':
            with pytest.raises(RuntimeError):a.promote(db,outputs,members,fault=True)
            with pytest.raises(ValueError,match='Partial'):a.select_complete(db,outputs,members)
        assert a.promote(db,outputs,members)=='COMPLETE'
    with warehouse_connection(path) as db:
        for m in members:assert a.publish_member(db,outputs,pin,m)=='ALREADY_VALID'
        assert a.promote(db,outputs,members)=='ALREADY_VALID'
        assert a.select_complete(db,outputs,members)==pin
        assert db.execute('SELECT count(*) FROM offline_output').fetchone()[0]==12
        assert db.execute('SELECT sum(source_rows) FROM offline_member').fetchone()[0]==18


@pytest.mark.parametrize('tamper',('sidecar','bytes','unknown','member','extra','source'))
def test_tamper_unknown_and_orphans_cannot_be_selected(store,tamper):
    path,outputs=store;members=a.stress_members(date(2025,1,1),date(2025,1,1))
    with warehouse_connection(path) as db:
        pin=a.register_manifest(db,members)
        for m in members:a.publish_member(db,outputs,pin,m)
        assert a.promote(db,outputs,members)=='COMPLETE'
        file,sidecar=a._paths(outputs,members[0])
        if tamper=='sidecar':sidecar.write_text('{}')
        if tamper=='bytes':file.write_bytes(b'tampered')
        if tamper=='extra':(outputs/'unknown.parquet').write_bytes(b'orphan')
        if tamper=='member':db.execute('UPDATE offline_member SET source_rows=0 WHERE member_id=?',[members[0]['member_id']])
        if tamper=='source':members[0]['source_hash']='0'*64
        if tamper=='unknown':
            unknown=dict(members[0],event_date='2025-01-02',member_id='daily/2025/2025-01-02')
            with pytest.raises(ValueError,match='Unknown'):a.publish_member(db,outputs,pin,unknown)
            return
        with pytest.raises(Exception):a.select_complete(db,outputs,members)


def test_full_manifest_bound_and_duplicate_rejection():
    members=a.stress_members()
    assert len(members)==5021*6
    assert len({(m['dataset'],m['event_date'][:4]) for m in members})==84
    assert a.manifest_hash(members)
    with pytest.raises(ValueError,match='duplicate'):a.manifest_hash([members[0],members[0]])


def test_completed_raw_bytes_are_revalidated(store):
    path,outputs=store
    with warehouse_connection(path) as db:
        a.plan(db,'p');a.capture(db,outputs,'p',a.FakeTransport())
        relative=db.execute('SELECT relative_path FROM offline_raw_manifest').fetchone()[0]
        (outputs/relative).write_bytes(b'changed')
        with pytest.raises(ValueError,match='Raw bytes changed'):a.complete_capture(db,outputs,'p')
