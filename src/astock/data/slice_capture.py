"""Bounded one-attempt capture, crash reconciliation and private failure evidence."""

import hashlib
import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import duckdb
import pyarrow.parquet as pq

from astock.data.audit import RequestParams
from astock.data.bootstrap import identity_snapshot_hash
from astock.data.contracts import load_contracts
from astock.data.identity import IdentifierHistory, IdentityHistory
from astock.data.probe_audit import canonical_json, records, table_audit
from astock.data.raw_writer import RawWriter, atomic_new_file, migrate, secret_scan, verify_batch
from astock.data.slice_plan import create_batch, claim_request, resume_batch, request_manifest, APPROVED
from astock.data.tushare_client import ProviderTable, ProviderFailure, TushareClient


class SliceStop(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def identity_state(db) -> tuple[str, IdentityHistory, list[dict]]:
    result = db.execute('SELECT * FROM security_identifier_history')
    columns = [c[0] for c in result.description]
    identifiers = [IdentifierHistory(**dict(zip(columns,r,strict=True))) for r in result.fetchall()]
    if not identifiers:
        raise SliceStop('IDENTITY_MISSING')
    history = IdentityHistory(identifiers)
    result = db.execute('SELECT * FROM security_venue_history')
    columns = [c[0] for c in result.description]
    venues = [dict(zip(columns,r,strict=True)) for r in result.fetchall()]
    serial_venues = []
    for v in venues:
        serial_venues.append({k:value.isoformat() if isinstance(value,(datetime,date)) else value for k,value in v.items()})
    q = db.execute('''SELECT provider_identifier,event_date,reason,raw_object_id FROM identity_quarantine
        WHERE curation_run_id IN (SELECT curation_run_id FROM curation_run WHERE partition_key='PHASE1C0_BOOTSTRAP')''').fetchall()
    quarantine = [dict(provider_identifier=r[0],event_date=r[1].isoformat() if r[1] else None,
                       reason=r[2],raw_object_id=str(r[3])) for r in q]
    return identity_snapshot_hash(dict(identifiers=identifiers,venues=serial_venues,quarantine=quarantine)),history,venues


def implementation_commit(root: Path) -> str:
    if subprocess.check_output(['git','status','--porcelain','--','src/astock','sql','config'],cwd=root,text=True).strip():
        raise SliceStop('UNCOMMITTED_IMPLEMENTATION')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()


def batch_requests(db, batch_id: UUID) -> list[dict]:
    result = db.execute('SELECT * FROM slice_request WHERE batch_id=? ORDER BY ordinal',[str(batch_id)])
    columns = [c[0] for c in result.description]
    return [dict(zip(columns,r,strict=True)) for r in result.fetchall()]


def validate_capture(table: ProviderTable, contract, params: RequestParams, slice_name: str) -> dict:
    if table.fields != contract.required_fields and set(table.fields) != set(contract.required_fields):
        raise SliceStop('SCHEMA')
    audit = table_audit(table,contract)
    if audit['potential_truncation']:
        raise SliceStop('ROW_CAP')
    if audit['dq_status'] != 'PASS':
        raise SliceStop('SCHEMA')
    rows = records(table)
    if params.trade_date:
        expected = params.trade_date.strftime('%Y%m%d')
        if any(r['trade_date'] != expected for r in rows):
            raise SliceStop('SCHEMA')
    else:
        expected = set()
        day = params.start_date
        while day <= params.end_date:
            expected.add(day.strftime('%Y%m%d'))
            day += timedelta(days=1)
        if ({r['cal_date'] for r in rows} != expected or len(rows) != len(expected)
                or any(r['exchange']!='SSE' or str(r['is_open']) not in ('0','1') for r in rows)):
            raise SliceStop('CALENDAR')
        open_days={r['cal_date'] for r in rows if str(r['is_open'])=='1'}
        if not {d.replace('-','') for d in APPROVED[slice_name]} <= open_days:
            raise SliceStop('CALENDAR')
    return audit


def _object_table(root: Path, db, request: dict) -> tuple[ProviderTable, dict]:
    result = db.execute('SELECT object_id,relative_path,sha256,retrieved_at FROM raw_object_manifest WHERE run_id=?',[str(request['run_id'])]).fetchall()
    if len(result) != 1:
        raise SliceStop('LINEAGE')
    oid,relative,checksum,retrieved = result[0]
    path=root/relative
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()/'data/raw') or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:
        raise SliceStop('LINEAGE')
    arrow=pq.ParquetFile(path).read()
    table=ProviderTable(fields=arrow.column_names,items=[list(r.values()) for r in arrow.to_pylist()],retrieved_at=retrieved)
    return table,dict(object_id=str(oid),relative_path=relative,sha256=checksum)


def finalize_receipt(root: Path, db, request: dict, contract) -> None:
    table,obj=_object_table(root,db,request)
    # Validate again for recovery before changing any receipt to COMPLETE.
    validate_capture(table,contract,RequestParams.model_validate_json(request['request_params']),request['slice_name'])
    writer=RawWriter(root,db)
    sidecar=root/f'data/raw/tushare/{request["dataset"]}/run_id={request["run_id"]}/manifest.json'
    if not sidecar.exists():
        writer.sidecar(request['run_id'],request['dataset'])
    if not verify_batch(root,db,[request['run_id']]):
        raise SliceStop('LINEAGE')
    metadata=sidecar.parent/'capture-contract.json'
    body=dict(contract_catalog='v2',contract_version=contract.contract_version,contract_hash=request['contract_hash'],
              request_id=request['request_id'],request_params=json.loads(request['request_params']),**obj)
    if not metadata.exists():
        atomic_new_file(metadata,lambda p:p.write_bytes(canonical_json(body)))
    elif json.loads(metadata.read_bytes())!=body:
        raise SliceStop('LINEAGE')
    db.execute('BEGIN')
    try:
        db.execute("UPDATE ingestion_run SET status='SUCCEEDED',finished_at=? WHERE run_id=?",[datetime.now(timezone.utc),str(request['run_id'])])
        db.execute("UPDATE slice_request SET status='COMPLETE',object_id=? WHERE batch_id=? AND ordinal=?",[obj['object_id'],str(request['batch_id']),request['ordinal']])
        db.execute('COMMIT')
    except Exception:
        db.execute('ROLLBACK')
        raise


def fail_batch(root: Path, db, batch_id: UUID, request: dict, code: str, error=None) -> None:
    now=datetime.now(timezone.utc)
    artifact=root/f'data/private/phase1c1/{batch_id}/failure-{request["ordinal"]:03}.json'
    body=dict(request_id=request['request_id'],dataset=request['dataset'],request_params=json.loads(request['request_params']),
              failure_code=code,observed_at=now.isoformat(),error=error.model_dump(mode='json') if error else None)
    if not artifact.exists():
        atomic_new_file(artifact,lambda p:p.write_bytes(canonical_json(body)))
    sidecar=root/f'data/raw/tushare/{request["dataset"]}/run_id={request["run_id"]}/manifest.json'
    if not sidecar.exists() and db.execute('SELECT count(*) FROM raw_object_manifest WHERE run_id=?',[str(request['run_id'])]).fetchone()[0]:
        RawWriter(root,db).sidecar(request['run_id'],request['dataset'])
    db.execute("UPDATE slice_request SET status='FAILED',failure_code=? WHERE batch_id=? AND ordinal=?",[code,str(batch_id),request['ordinal']])
    db.execute("UPDATE ingestion_run SET status='FAILED',finished_at=?,error_category=?,error_http_status=?,error_provider_code=? WHERE run_id=?",[
        now,error.category.value if error else None,error.http_status if error else None,error.provider_code if error else None,str(request['run_id'])])
    db.execute("UPDATE slice_batch SET status='BLOCKED',finished_at=? WHERE batch_id=?",[now,str(batch_id)])
    db.execute("UPDATE ingestion_run SET status='CANCELLED',finished_at=? WHERE run_id IN (SELECT run_id FROM slice_request WHERE batch_id=? AND status='PENDING')",[now,str(batch_id)])


def capture_slices(root: Path, settings, *, live: bool=False, batch_id: UUID|None=None,
                   stop_after: int|None=None, client=None, commit: str|None=None) -> dict:
    """Actual calls require --live. The injectable client is for synthetic tests only."""
    if not live or not settings.token_configured:
        raise SliceStop('LIVE_CONFIGURATION_REQUIRED')
    if stop_after is not None and not 1<=stop_after<=133:
        raise SliceStop('INVALID_INTERRUPTION_BOUND')
    manifest=request_manifest(root)
    commit=commit or implementation_commit(root)
    contracts={c.dataset:c for c in load_contracts(root,catalog_version='v2')}
    client=client or TushareClient(settings.tushare_token)
    # Use only this checkout's ignored storage, never an external path.
    db_path=root/'data/warehouse/astock.duckdb'
    db_path.parent.mkdir(parents=True,exist_ok=True)
    with duckdb.connect(str(db_path)) as db:
        migrate(db,root)
        snapshot,_,_=identity_state(db)
        if batch_id is None:
            if db.execute('SELECT count(*) FROM slice_batch').fetchone()[0]:
                raise SliceStop('EXISTING_BATCH_REQUIRES_EXPLICIT_RESUME')
            batch_id=create_batch(root,db,commit=commit,identity_hash=snapshot,knowledge_as_of=datetime.now(timezone.utc))
        prior=db.execute('SELECT identity_snapshot_hash,code_commit FROM slice_batch WHERE batch_id=?',[str(batch_id)]).fetchone()
        if prior is None or prior!=(snapshot,commit):
            raise SliceStop('FROZEN_INPUT_CHANGED')
        # A stored capture can finish its receipt after a crash, without HTTP replay.
        for req in batch_requests(db,batch_id):
            contract=contracts[req['dataset']]
            if req['contract_hash']!=hashlib.sha256(canonical_json(contract.model_dump(mode='json'))).hexdigest():
                raise SliceStop('FROZEN_INPUT_CHANGED')
            if req['status']=='IN_FLIGHT':
                try:
                    finalize_receipt(root,db,req,contract)
                except (SliceStop,OSError):
                    fail_batch(root,db,batch_id,req,'UNCERTAIN_CAPTURE')
                    return dict(batch_id=str(batch_id),status='BLOCKED',failure='UNCERTAIN_CAPTURE')
            if req['status']=='COMPLETE':
                if not verify_batch(root,db,[req['run_id']]):
                    fail_batch(root,db,batch_id,req,'LINEAGE')
                    return dict(batch_id=str(batch_id),status='BLOCKED',failure='LINEAGE')
        pending=resume_batch(db,batch_id,expected_plan_hash=manifest['plan_hash'])
        db.execute("UPDATE slice_batch SET status='RUNNING',finished_at=NULL WHERE batch_id=?",[str(batch_id)])
        completed_now=0
        for req in pending:
            claim_request(db,batch_id,req['ordinal'])
            try:
                contract=contracts[req['dataset']]
                params=RequestParams.model_validate_json(req['request_params'])
                table=client.fetch_slice(contract,params)
                # Keep even rejected cap/schema responses as immutable local evidence.
                raw=RawWriter(root,db).write(req['run_id'],req['dataset'],0,table,params)
                finalize_receipt(root,db,req,contract)
                files=[p for p in (root/raw.relative_path).parent.iterdir() if p.is_file()]
                if not secret_scan(settings.tushare_token,files):
                    raise SliceStop('INVALID_RESPONSE')
            except ProviderFailure as exc:
                fail_batch(root,db,batch_id,req,exc.error.category.value,exc.error)
                return dict(batch_id=str(batch_id),status='BLOCKED',failure=exc.error.category.value)
            except Exception as exc:
                code=exc.code if isinstance(exc,SliceStop) else 'LINEAGE'
                fail_batch(root,db,batch_id,req,code)
                return dict(batch_id=str(batch_id),status='BLOCKED',failure=code)
            completed_now+=1
            if req['ordinal']%19==18:
                print(f'Slice {req["slice_name"]}: 19 captures complete',flush=True)
            if stop_after is not None and completed_now>=stop_after:
                db.execute("UPDATE slice_batch SET status='INTERRUPTED' WHERE batch_id=?",[str(batch_id)])
                return dict(batch_id=str(batch_id),status='INTERRUPTED',completed_this_invocation=completed_now)
        counts=db.execute("SELECT count(*),sum(attempts),count(object_id) FROM slice_request WHERE batch_id=?",[str(batch_id)]).fetchone()
        if counts!=(133,133,133):
            raise SliceStop('LINEAGE')
        db.execute("UPDATE slice_batch SET status='CAPTURED',finished_at=? WHERE batch_id=?",[datetime.now(timezone.utc),str(batch_id)])
        return dict(batch_id=str(batch_id),status='CAPTURED',logical_requests=133,http_attempts=133,raw_objects=133)
