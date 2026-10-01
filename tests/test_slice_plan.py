from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import duckdb
import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from astock.cli.main import app
from astock.data.raw_writer import migrate
from astock.data.slice_plan import load_slice_plan,request_manifest,create_batch,claim_request,resume_batch
from astock.paths import get_project_root

ROOT=get_project_root()


def test_fixed_plan_budget_and_contracts():
    plan=load_slice_plan(ROOT);manifest=request_manifest(ROOT)
    assert sum(len(s.dates) for s in plan.slices)==21
    assert len(manifest['requests'])==133 and manifest['maximum_attempts']==133
    assert sum(r['dataset']=='trade_cal' for r in manifest['requests'])==7
    assert any(r['request_params'].get('trade_date')=='2025-04-30' for r in manifest['requests'])
    assert all(r['contract_catalog']=='v2' for r in manifest['requests'])
    assert manifest==request_manifest(ROOT)
    values=plan.model_dump();values['max_requests']=134
    with pytest.raises(ValidationError):type(plan)(**values)
    values=plan.model_dump();values['slices'][0]['dates'][0]='2012-12-31'
    with pytest.raises(ValidationError):type(plan)(**values)


def test_planner_offline_no_token_or_storage():
    before=set((ROOT/'data').rglob('*'))
    result=CliRunner().invoke(app,['data','slice','plan'])
    assert result.exit_code==0 and '133' in result.output
    assert before==set((ROOT/'data').rglob('*'))


def test_durable_attempt_claim_and_uncertain_resume_fails_closed(tmp_path):
    with duckdb.connect(':memory:') as db:
        migrate(db,ROOT)
        import shutil
        shutil.copytree(ROOT/'config',tmp_path/'config')
        batch=create_batch(tmp_path,db,commit='a'*40,identity_hash='b'*64,knowledge_as_of=datetime.now(timezone.utc))
        manifest=request_manifest(ROOT)
        assert len(resume_batch(db,batch,expected_plan_hash=manifest['plan_hash']))==133
        claim_request(db,batch,0)
        assert db.execute('SELECT sum(request_count) FROM ingestion_run').fetchone()==(1,)
        with pytest.raises(ValueError):claim_request(db,batch,0)
        with pytest.raises(ValueError,match='Uncertain'):resume_batch(db,batch,expected_plan_hash=manifest['plan_hash'])
        assert db.execute('SELECT status FROM slice_batch').fetchone()==('BLOCKED',)
        assert (tmp_path/f'data/private/phase1c1/{batch}/request-manifest.json').is_file()


def test_completed_receipt_is_skipped_on_interruption(tmp_path):
    import shutil
    shutil.copytree(ROOT/'config',tmp_path/'config')
    with duckdb.connect(':memory:') as db:
        migrate(db,ROOT)
        batch=create_batch(tmp_path,db,commit='a'*40,identity_hash='b'*64,knowledge_as_of=datetime.now(timezone.utc))
        claim_request(db,batch,0)
        db.execute("UPDATE slice_request SET status='COMPLETE',object_id=? WHERE ordinal=0",[str(uuid4())])
        db.execute("UPDATE slice_batch SET status='INTERRUPTED'")
        pending=resume_batch(db,batch,expected_plan_hash=request_manifest(ROOT)['plan_hash'])
        assert len(pending)==132 and pending[0]['ordinal']==1
        with pytest.raises(ValueError):resume_batch(db,batch,expected_plan_hash='c'*64)
