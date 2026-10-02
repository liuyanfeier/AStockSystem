"""Exact, read-only slice receipt proof; no Settings, transport or automatic migration."""

import hashlib
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

import duckdb

from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.probe_audit import canonical_json
from astock.data.raw_validation import (instant, require, rows_dict, safe_file, same_json,
                                       sha256, strict_json, typed_params, validate_raw_run)
from astock.data.slice_errors import ReceiptIntegrityError
from astock.data.slice_plan import request_manifest
from astock.data.tushare_client import ProviderTable

VALIDATOR_VERSION = 'R1_EXACT_RECEIPT_V1'


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def serial(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def batch_requests(db, batch_id: UUID) -> list[dict]:
    return rows_dict(db, 'SELECT * FROM slice_request WHERE batch_id=? ORDER BY ordinal', [str(batch_id)])


def validate_requests(requests: list[dict], plan: dict) -> None:
    require(len(requests) == len(plan['requests']) == 133, 'REQUEST_CARDINALITY',
            expected=133, observed=len(requests))
    for column in ('request_id', 'run_id', 'ordinal'):
        require(len({r[column] for r in requests}) == len(requests), 'REQUEST_DUPLICATE')
    objects = [r['object_id'] for r in requests if r['object_id'] is not None]
    require(len(set(objects)) == len(objects), 'OBJECT_DUPLICATE')
    for receipt, planned in zip(requests, plan['requests'], strict=True):
        require(type(receipt['ordinal']) is int, 'REQUEST_ORDINAL')
        for key in ('ordinal', 'request_id', 'slice_name', 'dataset', 'contract_catalog', 'contract_hash'):
            require(receipt[key] == planned[key], 'FROZEN_REQUEST_CHANGED')
        require(same_json(typed_params(receipt['request_params']), typed_params(planned['request_params'])),
                'REQUEST_PARAMS')


@dataclass(frozen=True)
class FrozenContext:
    batch: dict
    plan: dict
    contracts: dict
    request_manifest_hash: str


def frozen_context(root: Path, db, batch_id: UUID) -> FrozenContext:
    batches = rows_dict(db, 'SELECT * FROM slice_batch WHERE batch_id=?', [str(batch_id)])
    require(len(batches) == 1, 'BATCH_CARDINALITY', expected=1, observed=len(batches))
    batch = batches[0]
    plan = request_manifest(root)
    path = safe_file(root, f'data/private/phase1c1/{batch_id}/request-manifest.json',
                     under='data/private/phase1c1')
    frozen = strict_json(path.read_bytes())
    require(type(frozen) is dict and set(frozen) == set(plan) | {
        'batch_id', 'code_commit', 'identity_snapshot_hash', 'knowledge_as_of'}, 'FROZEN_MANIFEST_FIELDS')
    require(same_json({k: frozen[k] for k in plan}, plan), 'FROZEN_PLAN_CHANGED')
    require(frozen['batch_id'] == str(batch_id) and frozen['code_commit'] == batch['code_commit']
            and frozen['identity_snapshot_hash'] == batch['identity_snapshot_hash']
            and instant(frozen['knowledge_as_of']) == batch['knowledge_as_of'], 'FROZEN_BATCH_CHANGED')
    require(batch['phase'] == '1C.1' and batch['request_budget'] == 133
            and batch['plan_hash'] == plan['plan_hash'], 'BATCH_PLAN_CHANGED')
    contracts = {c.dataset: c for c in load_contracts(root, catalog_version='v2')}
    validate_requests(batch_requests(db, batch_id), plan)
    return FrozenContext(batch, plan, contracts, sha256(path))


@dataclass(frozen=True)
class ReceiptProof:
    request: dict
    object: dict
    table: ProviderTable
    plan_hash: str
    contract_hash: str
    receipt_hash: str
    evidence_hash: str

    def binding_fields(self) -> dict:
        return dict(batch_id=str(self.request['batch_id']), ordinal=self.request['ordinal'],
                    request_id=self.request['request_id'], run_id=str(self.request['run_id']),
                    object_id=self.object['object_id'], plan_hash=self.plan_hash,
                    contract_hash=self.contract_hash, receipt_hash=self.receipt_hash,
                    evidence_hash=self.evidence_hash, validator_version=VALIDATOR_VERSION)


def binding_schema_exists(db) -> bool:
    return bool(db.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='slice_receipt_completion_binding'").fetchone()[0])


def require_integrity_schema(db) -> None:
    tables = db.execute("SELECT count(*) FROM information_schema.tables WHERE table_name IN ('slice_receipt_completion_binding','slice_receipt_validation_audit')").fetchone()[0]
    version = db.execute('SELECT migration_id FROM schema_version WHERE version=7').fetchall()
    require(tables == 2 and version == [('007_slice_receipt_integrity',)], 'BINDING_SCHEMA_REQUIRED')


def check_binding(db, proof: ReceiptProof) -> None:
    require(binding_schema_exists(db), 'BINDING_SCHEMA_REQUIRED')
    matches = rows_dict(db, 'SELECT * FROM slice_receipt_completion_binding WHERE batch_id=? AND ordinal=?',
                        [str(proof.request['batch_id']), proof.request['ordinal']])
    require(len(matches) == 1, 'BINDING_REQUIRED', expected=1, observed=len(matches))
    actual = serial(matches[0])
    require(same_json({key: actual[key] for key in proof.binding_fields()}, proof.binding_fields()),
            'BINDING_MISMATCH')


def validate_slice_receipt(root: Path, db, request: dict, *, context: FrozenContext | None = None,
                           require_binding: bool = True, candidate: bool = False) -> ReceiptProof:
    """candidate is only for internal IN_FLIGHT local finalization, never admission."""
    try:
        context = context or frozen_context(root, db, request['batch_id'])
        require(context.batch['batch_id'] == request['batch_id'], 'BATCH_IDENTITY')
        actual = rows_dict(db, 'SELECT * FROM slice_request WHERE batch_id=? AND ordinal=?',
                           [str(request['batch_id']), request['ordinal']])
        require(len(actual) == 1, 'RECEIPT_CARDINALITY', expected=1, observed=len(actual))
        require(same_json(serial(actual[0]), serial(request)), 'RECEIPT_CHANGED')
        receipt = actual[0]
        planned = context.plan['requests'][receipt['ordinal']]
        for key in ('ordinal', 'request_id', 'slice_name', 'dataset', 'contract_catalog', 'contract_hash'):
            require(receipt[key] == planned[key], 'FROZEN_REQUEST_CHANGED')
        params = typed_params(receipt['request_params'])
        require(same_json(params, typed_params(planned['request_params'])), 'REQUEST_PARAMS')
        require(receipt['attempts'] == 1 and receipt['failure_code'] is None, 'RECEIPT_ATTEMPT')
        require(receipt['status'] == ('IN_FLIGHT' if candidate else 'COMPLETE'), 'RECEIPT_STATE')
        require(receipt['object_id'] is None if candidate else receipt['object_id'] is not None,
                'RECEIPT_OBJECT_STATE')
        runs = rows_dict(db, 'SELECT * FROM ingestion_run WHERE run_id=?', [str(receipt['run_id'])])
        require(len(runs) == 1, 'RUN_CARDINALITY', expected=1, observed=len(runs))
        run = runs[0]
        model = RequestParams.model_validate(params)
        require(run['source'] == 'tushare' and run['dataset'] == receipt['dataset'] and run['mode'] == 'AUDIT',
                'RUN_IDENTITY')
        require(run['code_commit'] == context.batch['code_commit'] and run['config_hash'] == context.batch['plan_hash']
                and run['provider_client_version'] == '0.1.0'
                and run['requested_start'] == (model.trade_date or model.start_date)
                and run['requested_end'] == (model.trade_date or model.end_date), 'RUN_PROVENANCE')
        require(run['request_count'] == 1 and run['raw_object_count'] == 1
                and run['status'] == ('RUNNING' if candidate else 'SUCCEEDED')
                and all(run[key] is None for key in ('error_category', 'error_http_status', 'error_provider_code')),
                'RUN_STATE')
        raw_count = db.execute('SELECT count(*) FROM raw_object_manifest WHERE run_id=?',
                               [str(receipt['run_id'])]).fetchone()[0]
        require(raw_count == 1, 'RAW_CARDINALITY', expected=1, observed=raw_count)
        checked = validate_raw_run(root, db, receipt['run_id'])[0]
        manifest = checked['manifest']
        require(candidate or manifest['object_id'] == receipt['object_id'], 'RECEIPT_OBJECT_MISMATCH')
        require(manifest['dataset'] == receipt['dataset'] and same_json(typed_params(manifest['request_params']), params),
                'RAW_REQUEST_MISMATCH')
        require(run['row_count'] == manifest['row_count'], 'RUN_ROW_COUNT')
        require(run['started_at'] <= manifest['retrieved_at'], 'RUN_TIME')
        if candidate:
            require(run['finished_at'] is None, 'RUN_TIME')
        else:
            require(run['finished_at'] is not None and manifest['retrieved_at'] <= run['finished_at'], 'RUN_TIME')
        arrow = checked['arrow']
        table = ProviderTable(fields=arrow.column_names,
                              items=[list(r.values()) for r in arrow.to_pylist()],
                              retrieved_at=manifest['retrieved_at'])
        # Lazy import avoids a capture/validator module cycle; this is pure validation.
        from astock.data.slice_capture import validate_capture
        contract = context.contracts[receipt['dataset']]
        require(digest(contract.model_dump(mode='json')) == receipt['contract_hash'], 'CONTRACT_HASH')
        validate_capture(table, contract, model, receipt['slice_name'])
        obj = dict(object_id=str(manifest['object_id']), relative_path=manifest['relative_path'], sha256=manifest['sha256'])
        meta_path = safe_file(root, str(Path(manifest['relative_path']).with_name('capture-contract.json')),
                              under='data/raw')
        metadata = strict_json(meta_path.read_bytes())
        expected = dict(contract_catalog='v2', contract_version=contract.contract_version,
                        contract_hash=receipt['contract_hash'], request_id=receipt['request_id'],
                        request_params=params, **obj)
        require(same_json(metadata, expected), 'CAPTURE_CONTRACT_MISMATCH')
        # Freeze only capture facts. Later curation/batch status is not receipt identity.
        capture_batch = {k: context.batch[k] for k in ('batch_id', 'phase', 'plan_hash', 'identity_snapshot_hash',
                                                      'code_commit', 'knowledge_as_of', 'request_budget')}
        receipt_hash = digest(serial(dict(receipt={**receipt, 'request_params': params}, run=run, batch=capture_batch)))
        evidence_hash = digest(serial(dict(manifest={**manifest, 'request_params': typed_params(manifest['request_params'])},
                                           sidecar_sha256=checked['sidecar_sha256'], capture_contract_sha256=sha256(meta_path),
                                           request_manifest_sha256=context.request_manifest_hash)))
        proof = ReceiptProof(receipt, obj, table, context.batch['plan_hash'], receipt['contract_hash'],
                             receipt_hash, evidence_hash)
        if require_binding:
            require(not candidate, 'CANDIDATE_NOT_ADMISSION')
            require_integrity_schema(db)
            check_binding(db, proof)
        return proof
    except ReceiptIntegrityError:
        raise
    except Exception as error:
        # Preserve stable capture policy codes, never exception text/input.
        from astock.data.slice_errors import SliceStop
        if isinstance(error, SliceStop):
            raise ReceiptIntegrityError(error.code) from None
        raise ReceiptIntegrityError('EVIDENCE_INVALID') from None


def validate_slice_batch(root: Path, db, batch_id: UUID, *, complete: bool = True,
                         require_binding: bool = True, context: FrozenContext | None = None) -> list[ReceiptProof]:
    context = context or frozen_context(root, db, batch_id)
    requests = batch_requests(db, batch_id)
    validate_requests(requests, context.plan)
    if complete:
        require(all(r['status'] == 'COMPLETE' for r in requests), 'BATCH_INCOMPLETE')
    proofs = [validate_slice_receipt(root, db, r, context=context, require_binding=require_binding)
              for r in requests if r['status'] == 'COMPLETE']
    if require_binding:
        require_integrity_schema(db)
    return proofs


def verification_commit(root: Path) -> str:
    try:
        dirty = subprocess.check_output(['git', 'status', '--porcelain', '--', 'src/astock', 'sql', 'config'], cwd=root,
                                        text=True, stderr=subprocess.DEVNULL).strip()
        require(not dirty, 'UNCOMMITTED_VERIFICATION_CODE')
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root,
                                         text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        raise ReceiptIntegrityError('VERIFICATION_COMMIT_REQUIRED') from None
    require(bool(re.fullmatch('[0-9a-f]{40}', commit)), 'VERIFICATION_COMMIT_REQUIRED')
    return commit


def audit_slice_batch(root: Path, batch_id: UUID, *, legacy_preflight: bool = False,
                      verification_sha: str | None = None) -> dict:
    """No migration, token/client construction, claim, source writes or artifact repair."""
    commit = verification_sha or verification_commit(root)
    require(bool(re.fullmatch('[0-9a-f]{40}', commit)), 'VERIFICATION_COMMIT_REQUIRED')
    result = dict(batch_id=str(batch_id), validator_version=VALIDATOR_VERSION,
                  verification_code_commit=commit, validated_at=datetime.now(timezone.utc).isoformat(),
                  purpose='LEGACY_PREFLIGHT' if legacy_preflight else 'VERIFY',
                  verdict='BLOCKED', binding='UNREGISTERED' if legacy_preflight else 'REQUIRED',
                  checked_count=0, failure_count=0, reasons={})
    try:
        path = safe_file(root, 'data/warehouse/astock.duckdb', under='data/warehouse')
        with duckdb.connect(str(path), read_only=True) as db:
            db.execute('BEGIN TRANSACTION')
            context = frozen_context(root, db, batch_id)
            requests = batch_requests(db, batch_id)
            require(all(r['status'] == 'COMPLETE' for r in requests), 'BATCH_INCOMPLETE')
            errors = Counter()
            evidence = []
            for request in requests:
                try:
                    proof = validate_slice_receipt(root, db, request, context=context,
                                                   require_binding=not legacy_preflight)
                    result['checked_count'] += 1
                    evidence.append(proof.evidence_hash)
                except ReceiptIntegrityError as error:
                    errors[error.code] += 1
            db.execute('COMMIT')
        result.update(failure_count=sum(errors.values()), reasons=dict(errors), evidence_hash=digest(evidence))
        if not errors:
            result.update(verdict='LEGACY_PREFLIGHT_EVIDENCE_VALID' if legacy_preflight else 'VALID',
                          binding='UNREGISTERED' if legacy_preflight else 'EXACT')
    except ReceiptIntegrityError as error:
        result.update(failure_count=1, reasons={error.code: 1})
    except Exception:
        result.update(failure_count=1, reasons={'AUDIT_UNAVAILABLE': 1})
    return result
