"""Bounded one-attempt capture, crash reconciliation and private failure evidence."""

import hashlib
import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import duckdb

from astock.data.audit import RequestParams
from astock.data.bootstrap import identity_snapshot_hash
from astock.data.contracts import load_contracts
from astock.data.identity import IdentifierHistory, IdentityHistory
from astock.data.probe_audit import canonical_json, records, table_audit
from astock.data.raw_writer import RawWriter, atomic_new_file, migrate, secret_scan
from astock.data.slice_plan import create_batch, claim_request, resume_batch, request_manifest, APPROVED
from astock.data.tushare_client import ProviderTable, ProviderFailure, TushareClient
from astock.data.slice_errors import SliceStop, ReceiptIntegrityError
from astock.data.receipt_integrity import (batch_requests, frozen_context, validate_requests,
                                         validate_slice_receipt, validate_slice_batch)
from astock.data.receipt_migration import apply_receipt_integrity_upgrade, register_completion


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
    proof = validate_slice_receipt(root, db, request)
    return proof.table, proof.object


def publish_capture_metadata(root: Path, db, request: dict, contract, obj: dict) -> None:
    """Active capture publication only; recovery/audit never create missing proof."""
    RawWriter(root, db).sidecar(request['run_id'], request['dataset'])
    metadata = (root / obj['relative_path']).with_name('capture-contract.json')
    body = dict(contract_catalog='v2', contract_version=contract.contract_version,
                contract_hash=request['contract_hash'], request_id=request['request_id'],
                request_params=json.loads(request['request_params']), **obj)
    atomic_new_file(metadata, lambda path: path.write_bytes(canonical_json(body)))


def finalize_receipt(root: Path, db, request: dict, contract, *, verification_sha: str) -> None:
    """Conditional, exact and idempotent completion; no metadata repair."""
    db.execute('BEGIN TRANSACTION')
    try:
        context = frozen_context(root, db, request['batch_id'])
        current = next(r for r in batch_requests(db, request['batch_id']) if r['ordinal'] == request['ordinal'])
        if contract.model_dump(mode='json') != context.contracts[current['dataset']].model_dump(mode='json'):
            raise ReceiptIntegrityError('CONTRACT_HASH')
        if current['status'] == 'COMPLETE':
            proof = validate_slice_receipt(root, db, current, context=context)
            if request['object_id'] is not None and str(request['object_id']) != proof.object['object_id']:
                raise ReceiptIntegrityError('RECEIPT_OBJECT_MISMATCH')
            if current != request:
                raise ReceiptIntegrityError('RECEIPT_CHANGED')
            db.execute('COMMIT')
            return
        if current != request:
            raise ReceiptIntegrityError('RECEIPT_CHANGED')
        proof = validate_slice_receipt(root, db, current, context=context, require_binding=False, candidate=True)
        now = datetime.now(timezone.utc)
        updated = db.execute("UPDATE ingestion_run SET status='SUCCEEDED',finished_at=? WHERE run_id=? AND status='RUNNING' AND request_count=1 AND raw_object_count=1",
                             [now, str(current['run_id'])]).fetchone()[0]
        if updated != 1:
            raise ReceiptIntegrityError('FINALIZE_STATE')
        updated = db.execute("UPDATE slice_request SET status='COMPLETE',object_id=? WHERE batch_id=? AND ordinal=? AND status='IN_FLIGHT' AND attempts=1 AND object_id IS NULL",
                             [proof.object['object_id'], str(current['batch_id']), current['ordinal']]).fetchone()[0]
        if updated != 1:
            raise ReceiptIntegrityError('FINALIZE_STATE')
        completed = next(r for r in batch_requests(db, request['batch_id']) if r['ordinal'] == request['ordinal'])
        register_completion(root, db, completed, verification_sha=verification_sha, context=context)
        db.execute('COMMIT')
    except Exception:
        db.execute('ROLLBACK')
        raise


def operation_block(root: Path, batch_id: UUID, code: str) -> dict:
    """Append new failure evidence without modifying contradictory old receipts."""
    from uuid import uuid4
    path = root / f'data/private/phase1c1/{batch_id}/operation-block-{uuid4()}.json'
    atomic_new_file(path, lambda p: p.write_bytes(canonical_json(dict(
        batch_id=str(batch_id), verdict='BLOCKED', reason_code=code,
        observed_at=datetime.now(timezone.utc).isoformat()))))
    return dict(batch_id=str(batch_id), status='BLOCKED', failure=code)


def fail_batch(root: Path, db, batch_id: UUID, request: dict, code: str, error=None) -> None:
    current=db.execute('SELECT status FROM slice_request WHERE batch_id=? AND ordinal=?',[str(batch_id),request['ordinal']]).fetchone()
    if current and current[0]=='COMPLETE':
        return operation_block(root,batch_id,code)
    now=datetime.now(timezone.utc)
    artifact=root/f'data/private/phase1c1/{batch_id}/failure-{request["ordinal"]:03}.json'
    body=dict(request_id=request['request_id'],dataset=request['dataset'],request_params=json.loads(request['request_params']),
              failure_code=code,observed_at=now.isoformat(),error=error.model_dump(mode='json') if error else None)
    if not artifact.exists():
        atomic_new_file(artifact,lambda p:p.write_bytes(canonical_json(body)))
    # 006 retains its frozen reason enum; new diagnostics remain in private evidence.
    stored_code = code if code in ('TRANSPORT','REDIRECT','AUTH','PERMISSION','PROVIDER','INVALID_RESPONSE',
                                  'ROW_CAP','SCHEMA','LINEAGE','UNCERTAIN_CAPTURE','CALENDAR') else 'LINEAGE'
    db.execute("UPDATE slice_request SET status='FAILED',failure_code=? WHERE batch_id=? AND ordinal=?",[stored_code,str(batch_id),request['ordinal']])
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
    # Use only this checkout's ignored storage, never an external path.
    db_path=root/'data/warehouse/astock.duckdb'
    db_path.parent.mkdir(parents=True,exist_ok=True)
    with duckdb.connect(str(db_path)) as db:
        migrate(db,root)
        snapshot,_,_=identity_state(db)
        if batch_id is None:
            if db.execute('SELECT count(*) FROM slice_batch').fetchone()[0]:
                raise SliceStop('EXISTING_BATCH_REQUIRES_EXPLICIT_RESUME')
            apply_receipt_integrity_upgrade(root,db,verification_sha=commit)
            batch_id=create_batch(root,db,commit=commit,identity_hash=snapshot,knowledge_as_of=datetime.now(timezone.utc))
        prior=db.execute('SELECT identity_snapshot_hash,code_commit FROM slice_batch WHERE batch_id=?',[str(batch_id)]).fetchone()
        if prior is None or prior!=(snapshot,commit):
            raise SliceStop('FROZEN_INPUT_CHANGED')
        try:
            context = frozen_context(root, db, batch_id)
            # Prove every existing COMPLETE before any reconciliation or pending HTTP.
            validate_slice_batch(root, db, batch_id, complete=False, context=context)
            for req in batch_requests(db, batch_id):
                if req['status'] == 'IN_FLIGHT':
                    try:
                        finalize_receipt(root, db, req, contracts[req['dataset']], verification_sha=commit)
                    except (SliceStop, OSError):
                        return operation_block(root, batch_id, 'UNCERTAIN_CAPTURE')
            pending = resume_batch(db, batch_id, root=root, expected_plan_hash=manifest['plan_hash'])
        except ReceiptIntegrityError as error:
            return operation_block(root, batch_id, error.code)
        client = client or (TushareClient(settings.tushare_token) if pending else None)
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
                current = next(r for r in batch_requests(db,batch_id) if r['ordinal']==req['ordinal'])
                obj = dict(object_id=str(raw.object_id), relative_path=raw.relative_path, sha256=raw.sha256)
                publish_capture_metadata(root,db,current,contract,obj)
                files=[p for p in (root/raw.relative_path).parent.iterdir() if p.is_file()]
                if not secret_scan(settings.tushare_token,files):
                    raise SliceStop('INVALID_RESPONSE')
                finalize_receipt(root,db,current,contract,verification_sha=commit)
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
        try:
            validate_slice_batch(root, db, batch_id)
        except ReceiptIntegrityError as error:
            return operation_block(root, batch_id, error.code)
        db.execute("UPDATE slice_batch SET status='CAPTURED',finished_at=? WHERE batch_id=?",[datetime.now(timezone.utc),str(batch_id)])
        return dict(batch_id=str(batch_id),status='CAPTURED',logical_requests=133,http_attempts=133,raw_objects=133)
