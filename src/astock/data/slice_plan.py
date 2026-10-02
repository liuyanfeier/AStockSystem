"""Fixed, user-approved Phase 1C.1 plan and durable request lifecycle."""

from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.curation import digest
from astock.data.probe_audit import canonical_json
from astock.data.raw_writer import atomic_new_file

DATASETS = ('daily', 'daily_basic', 'adj_factor', 'stk_limit', 'stock_st', 'suspend_d')
APPROVED = {
    'baseline_2013': ('2013-01-04', '2013-01-07', '2013-01-08'),
    'chinext_boundary': ('2020-08-21', '2020-08-24', '2020-08-25'),
    'bse_opening': ('2021-11-12', '2021-11-15', '2021-11-16'),
    'bse_pilot_switch': ('2025-04-30', '2025-05-06', '2025-05-07'),
    'bse_remaining_switch': ('2025-09-30', '2025-10-09', '2025-10-10'),
    'after_hours_fields': ('2026-07-03', '2026-07-06', '2026-07-07'),
    'latest_sample': ('2026-09-28', '2026-09-29', '2026-09-30'),
}


class Slice(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, hide_input_in_errors=True)
    name: str
    dates: list[date]


class SlicePlan(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, hide_input_in_errors=True)
    version: str
    contract_catalog: str
    curation_version: str
    max_market_dates: int
    max_requests: int
    max_attempts_per_request: int
    minimum_interval_seconds: float
    slices: list[Slice]

    @model_validator(mode='after')
    def approved_bounds(self):
        actual = {s.name: tuple(d.isoformat() for d in s.dates) for s in self.slices}
        if (actual != APPROVED or len(self.slices) != 7 or self.version != '1.0'
                or self.contract_catalog != 'v2' or self.curation_version != 'v2'
                or self.max_market_dates != 21 or self.max_requests != 133
                or self.max_attempts_per_request != 1 or self.minimum_interval_seconds != 1.25):
            raise ValueError('Plan differs from approved Phase 1C.1 bounds')
        return self


def load_slice_plan(root: Path) -> SlicePlan:
    return SlicePlan.model_validate(yaml.safe_load((root/'config/slices/phase1c1.yaml').read_text()))


def request_manifest(root: Path) -> dict:
    plan = load_slice_plan(root)
    contracts = {c.dataset: c for c in load_contracts(root, catalog_version='v2')}
    requests = []
    for section in plan.slices:
        entries = [('trade_cal', RequestParams(exchange='SSE', start_date=min(section.dates), end_date=max(section.dates)))]
        entries += [(dataset, RequestParams(trade_date=day)) for day in section.dates for dataset in DATASETS]
        for dataset, params in entries:
            data = dict(slice_name=section.name, dataset=dataset, contract_catalog='v2',
                        contract_hash=digest(contracts[dataset].model_dump(mode='json')),
                        request_params=params.public_dict())
            requests.append(dict(ordinal=len(requests), request_id=digest(data), **data))
    if len(requests) != plan.max_requests or len({r['request_id'] for r in requests}) != len(requests):
        raise ValueError('Duplicate or out-of-budget request plan')
    return dict(phase='1C.1', version=plan.version, maximum_requests=133, maximum_attempts=133,
                market_dates=21, plan_hash=digest(requests), requests=requests)


def create_batch(root: Path, db, *, commit: str, identity_hash: str,
                 knowledge_as_of: datetime) -> UUID:
    """Publish a private immutable plan before creating execution receipts."""
    manifest = request_manifest(root)
    batch_id = uuid4()
    path = root/f'data/private/phase1c1/{batch_id}/request-manifest.json'
    atomic_new_file(path, lambda p: p.write_bytes(canonical_json(dict(
        batch_id=str(batch_id), code_commit=commit, identity_snapshot_hash=identity_hash,
        knowledge_as_of=knowledge_as_of.isoformat(), **manifest))))
    now = datetime.now(timezone.utc)
    db.execute('BEGIN')
    try:
        db.execute('INSERT INTO slice_batch VALUES (?,?,?,?,?,?,?,?,?,?)',[
            str(batch_id),'1C.1',manifest['plan_hash'],identity_hash,commit,knowledge_as_of,
            now,None,'PLANNED',133])
        for req in manifest['requests']:
            run_id = uuid4()
            params = RequestParams.model_validate(req['request_params'])
            db.execute('''INSERT INTO ingestion_run (run_id,source,dataset,mode,started_at,status,
                code_commit,config_hash,provider_client_version,requested_start,requested_end)
                VALUES (?,'tushare',?,'AUDIT',?,'RUNNING',?,?,'0.1.0',?,?)''',[
                str(run_id),req['dataset'],now,commit,manifest['plan_hash'],
                params.trade_date or params.start_date, params.trade_date or params.end_date])
            db.execute('''INSERT INTO slice_request (batch_id,ordinal,request_id,slice_name,dataset,
                contract_catalog,contract_hash,request_params,run_id,status) VALUES (?,?,?,?,?,?,?,?,?,'PENDING')''',[
                str(batch_id),req['ordinal'],req['request_id'],req['slice_name'],req['dataset'],
                req['contract_catalog'],req['contract_hash'],canonical_json(req['request_params']).decode(),str(run_id)])
        db.execute('COMMIT')
    except Exception:
        db.execute('ROLLBACK')
        raise
    return batch_id


def claim_request(db, batch_id: UUID, ordinal: int) -> None:
    """Durably consume one attempt before any network call; never replay IN_FLIGHT."""
    from astock.data.raw_validation import rows_dict
    from astock.data.receipt_integrity import validate_pending_request

    pending = rows_dict(db, 'SELECT * FROM slice_request WHERE batch_id=? AND ordinal=?',
                       [str(batch_id), ordinal])
    if len(pending) != 1 or pending[0]['status'] != 'PENDING':
        raise ValueError('Request is not pending; never duplicate a capture')
    validate_pending_request(db, pending[0])
    result = db.execute("UPDATE slice_request SET status='IN_FLIGHT',attempts=1 WHERE batch_id=? AND ordinal=? AND status='PENDING' AND attempts=0 RETURNING run_id",[str(batch_id),ordinal]).fetchall()
    if len(result) != 1:
        raise ValueError('Request is not pending; never duplicate a capture')
    db.execute('UPDATE ingestion_run SET request_count=1 WHERE run_id=?',[str(result[0][0])])


def resume_batch(db, batch_id: UUID, *, root: Path, expected_plan_hash: str) -> list[dict]:
    """Interrupted completed receipts resume; uncertain HTTP receipts stop for review."""
    from astock.data.receipt_integrity import validate_slice_batch
    from astock.data.slice_errors import ReceiptIntegrityError

    validate_slice_batch(root, db, batch_id, complete=False)
    batch = db.execute('SELECT plan_hash,status FROM slice_batch WHERE batch_id=?',[str(batch_id)]).fetchone()
    if batch is None or batch[0] != expected_plan_hash or batch[1] == 'BLOCKED':
        raise ReceiptIntegrityError('BATCH_SCOPE_BLOCKED')
    if db.execute("SELECT count(*) FROM slice_request WHERE batch_id=? AND status IN ('IN_FLIGHT','FAILED','UNCERTAIN')",[str(batch_id)]).fetchone()[0]:
        raise ReceiptIntegrityError('UNCERTAIN_CAPTURE')
    result = db.execute("SELECT * FROM slice_request WHERE batch_id=? AND status='PENDING' ORDER BY ordinal",[str(batch_id)])
    columns = [c[0] for c in result.description]
    return [dict(zip(columns, values, strict=True)) for values in result.fetchall()]
