"""Bounded Phase 1B orchestration. No backfill or curated persistence."""

import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import duckdb
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from astock.data.audit import ErrorCategory, RequestParams, SafeError
from astock.data.contracts import load_contracts
from astock.data.probe_audit import (
    canonical_json, cross_audit, cross_has_findings, key_set, records, table_audit,
)
from astock.data.raw_writer import RawWriter, atomic_new_file, migrate, secret_scan, verify_batch
from astock.data.tushare_client import CLIENT_VERSION, PROBE_DATASETS, ProviderFailure, TushareClient


class ProbePlan(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)
    version: str
    endpoints: list[str]
    fixed_anchors: list[date]
    recent_calendar: RequestParams
    stock_exchanges: list[str]
    stock_statuses: list[str]
    repeat_daily_date: date
    minimum_interval_seconds: float = Field(ge=1.25)
    max_attempts: int
    price_tolerance: float
    percent_tolerance: float

    @model_validator(mode='after')
    def bounded(self):
        if (self.version != '1.0' or self.endpoints != list(PROBE_DATASETS)
                or self.fixed_anchors != [date(2015, 7, 8), date(2019, 6, 25), date(2020, 8, 24), date(2025, 8, 13)]
                or self.recent_calendar.public_dict() != {
                    'start_date': '2026-09-01', 'end_date': '2026-09-30', 'exchange': 'SSE'}
                or self.stock_exchanges != ['SSE', 'SZSE', 'BSE']
                or self.stock_statuses != ['L', 'D', 'P', 'G', 'UN']
                or self.repeat_daily_date != date(2019, 6, 25) or self.max_attempts != 2
                or self.minimum_interval_seconds != 1.25
                or self.price_tolerance != 0.011 or self.percent_tolerance != 0.011):
            raise ValueError('Plan exceeds approved Phase 1B bounds or changes audited tolerances')
        return self


def load_plan(root: Path) -> ProbePlan:
    return ProbePlan.model_validate(yaml.safe_load((root/'config/probes/phase1b.yaml').read_text()))


def _commit(root):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()


def _recent_anchor(table):
    rows = records(table)
    expected = {date(2026, 9, day).strftime('%Y%m%d') for day in range(1, 31)}
    if ({r['cal_date'] for r in rows} != expected or len(rows) != 30
            or any(r['exchange'] != 'SSE' or str(r['is_open']) not in ('0', '1') for r in rows)):
        raise ProviderFailure(SafeError(category=ErrorCategory.INVALID_RESPONSE))
    open_dates = [date.fromisoformat(f"{r['cal_date'][:4]}-{r['cal_date'][4:6]}-{r['cal_date'][6:]}")
                  for r in rows if str(r['is_open']) == '1']
    if not open_dates:
        raise ProviderFailure(SafeError(category=ErrorCategory.INVALID_RESPONSE))
    return max(open_dates)


def run_probe(root, settings, *, client=None):
    # Missing credentials cause no HTTP, directories or database changes.
    if not settings.token_configured:
        raise ValueError('TUSHARE_TOKEN is not configured. Configure it locally outside chat/model input.')
    plan = load_plan(root)
    contracts = {c.dataset: c for c in load_contracts(root, catalog_version="v1")}
    client = client or TushareClient(settings.tushare_token)
    commit = _commit(root)
    config_hash = hashlib.sha256(canonical_json({
        'plan': plan.model_dump(mode='json'),
        'contracts': [contracts[d].model_dump(mode='json') for d in plan.endpoints],
    })).hexdigest()
    # Public probe uses only the default ignored warehouse, never a user-configured external DB.
    db_path = root/'data/warehouse/astock.duckdb'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    summary = dict(phase='1B', status='PARTIAL', code_commit=commit, batch_id=str(uuid4()),
                   resolved_recent_date=None, anchors=[d.isoformat() for d in plan.fixed_anchors],
                   runs={}, captures=[], errors=[], cross_audits={}, repeat_consistency=None,
                   secret_scan='NOT_RUN', availability_basis='OBSERVED_CAPTURE',
                   backtest_eligible=False)
    run_ids, parts, failures = {}, Counter(), {}
    stopped = False
    with duckdb.connect(str(db_path)) as db:
        db.execute("SET TimeZone='UTC'")
        migrate(db, root)
        writer = RawWriter(root, db)

        def capture(dataset, params):
            nonlocal stopped
            if stopped:
                return None
            if dataset not in run_ids:
                run_id = uuid4()
                run_ids[dataset] = run_id
                db.execute('''INSERT INTO ingestion_run (run_id,source,dataset,mode,started_at,status,
                    code_commit,config_hash,provider_client_version,requested_start,requested_end)
                    VALUES (?,?,?,'PROBE',?,'RUNNING',?,?,?,?,?)''', [str(run_id),'tushare',dataset,
                    datetime.now(timezone.utc),commit,config_hash,CLIENT_VERSION,
                    params.start_date or params.trade_date, params.end_date or params.trade_date])
            run_id = run_ids[dataset]
            before = client.request_count
            try:
                table = client.fetch(contracts[dataset], params)
            except ProviderFailure as exc:
                error = exc.error
                failures[dataset] = error
                summary['errors'].append(dict(dataset=dataset, params=params.public_dict(),
                                              error=error.model_dump(mode='json')))
                # Transient retries exhausted are also a stop; no fallback or repeated probing.
                if error.category in (ErrorCategory.AUTH, ErrorCategory.REDIRECT, ErrorCategory.TRANSPORT):
                    stopped = True
                    summary['status'] = 'BLOCKED'
                return None
            finally:
                db.execute('UPDATE ingestion_run SET request_count=request_count+? WHERE run_id=?',
                           [client.request_count-before, str(run_id)])
            try:
                manifest = writer.write(run_id, dataset, parts[dataset], table, params)
            except Exception:
                stopped = True
                error = SafeError(category=ErrorCategory.INVALID_RESPONSE)
                failures[dataset] = error
                summary['status'] = 'BLOCKED'
                summary['errors'].append(dict(dataset=dataset, error=error.model_dump(mode='json')))
                return None
            parts[dataset] += 1
            audit = table_audit(table, contracts[dataset])
            rows = records(table)
            audit['request_scope_mismatch'] = sum(any(
                field in row and row[field] != expected
                for field, expected in (
                    ('trade_date', params.trade_date.strftime('%Y%m%d') if params.trade_date else None),
                    ('exchange', params.exchange), ('list_status', params.list_status),
                ) if expected is not None) for row in rows)
            if audit['request_scope_mismatch']:
                audit['dq_status'] = 'ERROR'
            audit.update(dataset=dataset, run_id=str(run_id), object_id=str(manifest.object_id),
                         params=params.public_dict())
            summary['captures'].append(audit)
            return table

        try:
            calendar = capture('trade_cal', plan.recent_calendar)
            if calendar is None:
                # First-request permission/schema failure also blocks the handshake.
                stopped = True
                summary['status'] = 'BLOCKED'
            else:
                try:
                    recent = _recent_anchor(calendar)
                except ProviderFailure as exc:
                    failures['trade_cal'] = exc.error
                    stopped = True
                    summary['status'] = 'BLOCKED'
                    summary['errors'].append(dict(dataset='trade_cal', error=exc.error.model_dump(mode='json')))
                else:
                    summary['resolved_recent_date'] = recent.isoformat()
                    anchors = [*plan.fixed_anchors, recent]
                    summary['anchors'] = [d.isoformat() for d in anchors]
            universe, stock_counts, market_labels, bse_patterns = set(), {}, Counter(), Counter()
            all_stock_codes = []
            bse_unexpected = 0
            if not stopped:
                for exchange in plan.stock_exchanges:
                    for status in plan.stock_statuses:
                        table = capture('stock_basic', RequestParams(exchange=exchange, list_status=status))
                        if table is None:
                            continue
                        rows = records(table)
                        stock_counts[f'{exchange}/{status}'] = len(rows)
                        all_stock_codes.extend(r['ts_code'] for r in rows)
                        universe.update(r['ts_code'] for r in rows if isinstance(r['ts_code'], str))
                        market_labels.update(str(r['market']) for r in rows)
                        for r in rows if exchange == 'BSE' else []:
                            code = r['ts_code']
                            match = re.fullmatch(r'([0-9]+)\.([A-Z]+)', code or '')
                            if match:
                                bse_patterns[f'{len(match[1])}digits.{match[2]}'] += 1
                            else:
                                bse_unexpected += 1
                summary['stock_basic'] = dict(partition_counts=stock_counts,
                    observed_market_labels=dict(market_labels), bse_patterns=dict(bse_patterns),
                    bse_unexpected_pattern_count=bse_unexpected,
                    cross_partition_code_duplicates=len(all_stock_codes)-len(set(all_stock_codes)))
                original_repeat = None
                for anchor in anchors:
                    tables = {}
                    for dataset in plan.endpoints[2:]:
                        table = capture(dataset, RequestParams(trade_date=anchor))
                        if table is not None:
                            tables[dataset] = table
                            if dataset == 'daily' and anchor == plan.repeat_daily_date:
                                original_repeat = table
                    summary['cross_audits'][anchor.isoformat()] = cross_audit(tables, universe)
                repeated = capture('daily', RequestParams(trade_date=plan.repeat_daily_date))
                if original_repeat is not None and repeated is not None:
                    contract = contracts['daily']
                    from astock.data.probe_audit import logical_fingerprint
                    summary['repeat_consistency'] = dict(
                        fields_match=original_repeat.fields == repeated.fields,
                        row_count_match=len(original_repeat.items) == len(repeated.items),
                        natural_keys_match=key_set(original_repeat, contract) == key_set(repeated, contract),
                        logical_hash_match=logical_fingerprint(original_repeat, contract) == logical_fingerprint(repeated, contract))
        except Exception:
            stopped = True
            summary['status'] = 'BLOCKED'
            error = SafeError(category=ErrorCategory.INVALID_RESPONSE)
            summary['errors'].append(dict(error=error.model_dump(mode='json')))
            for dataset in run_ids:
                failures.setdefault(dataset, error)
        finally:
            for dataset, run_id in run_ids.items():
                error = failures.get(dataset)
                status = 'FAILED' if error else 'CANCELLED' if stopped and dataset != 'trade_cal' else 'SUCCEEDED'
                db.execute('''UPDATE ingestion_run SET status=?,finished_at=?,error_category=?,
                    error_http_status=?,error_provider_code=? WHERE run_id=?''', [status,
                    datetime.now(timezone.utc),error.category.value if error else None,
                    error.http_status if error else None,error.provider_code if error else None,str(run_id)])
                writer.sidecar(run_id, dataset)
                values = db.execute('''SELECT status,request_count,row_count,raw_object_count FROM
                    ingestion_run WHERE run_id=?''', [str(run_id)]).fetchone()
                summary['runs'][dataset] = dict(run_id=str(run_id),status=values[0],
                    request_count=values[1],row_count=values[2],raw_object_count=values[3])
            total_rows, total_objects = db.execute('''SELECT coalesce(sum(row_count),0),count(*)
                FROM raw_object_manifest WHERE run_id IN (SELECT unnest(?::UUID[]))''',
                [[str(v) for v in run_ids.values()]]).fetchone()
            summary['lineage_reconciled'] = (total_rows == sum(r['row_count'] for r in summary['runs'].values())
                and total_objects == sum(r['raw_object_count'] for r in summary['runs'].values()))
            summary['raw_reconstruction_verified'] = verify_batch(root, db, run_ids.values())
    if summary['status'] != 'BLOCKED':
        summary['status'] = 'PASS' if (
            not failures and len(summary['runs']) == 8 and summary['lineage_reconciled']
            and summary['raw_reconstruction_verified']
            and all(c['dq_status'] == 'PASS' for c in summary['captures'])
            and all(c['identity_status'] == 'PASS' for c in summary['captures'])
            and not any(cross_has_findings(a) for a in summary['cross_audits'].values())
            and summary['repeat_consistency'] and all(summary['repeat_consistency'].values())
            and not bse_unexpected and not summary['stock_basic']['cross_partition_code_duplicates']) else 'PARTIAL'
    summary_path = root/f'data/private/phase1b/{summary["batch_id"]}.json'
    summary['secret_scan'] = 'PASS'  # Only publish this value after a successful scan below.
    atomic_new_file(summary_path, lambda path: path.write_bytes(canonical_json(summary)))
    paths = [summary_path]
    for dataset, run_id in run_ids.items():
        paths.extend((root/f'data/raw/tushare/{dataset}/run_id={run_id}').glob('*'))
    if not secret_scan(settings.tushare_token, paths):
        # Mark this isolated batch as quarantined; never generate public review evidence.
        quarantine = summary_path.with_suffix('.quarantined')
        summary_path.rename(quarantine)
        raise ValueError('SECRET_SCAN: FAIL')
    return summary, summary_path


def probe_status(root):
    directory = root/'data/private/phase1b'
    return [json.loads(path.read_bytes()) for path in sorted(directory.glob('*.json'))] if directory.exists() else []
