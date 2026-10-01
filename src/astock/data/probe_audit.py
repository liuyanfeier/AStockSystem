"""Deterministic aggregate-only audits. Raw values stay in memory/local captures."""

import hashlib
import json
import math
from datetime import datetime
from collections import Counter

from astock.data.contracts import DatasetContract
from astock.data.tushare_client import ProviderTable
from astock.data.identity import is_native_identifier, is_normalized_ashare_identifier


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def records(table: ProviderTable) -> list[dict]:
    return [dict(zip(table.fields, row, strict=True)) for row in table.items]


def logical_fingerprint(table: ProviderTable, contract: DatasetContract) -> str:
    columns = sorted(table.fields)
    rows = records(table)
    # Canonical JSON key encoding handles null keys; full row breaks duplicate-key ties.
    rows.sort(key=lambda r: (canonical_json([r[k] for k in contract.natural_key]),
                             canonical_json([r[k] for k in columns])))
    digest = hashlib.sha256(canonical_json(columns) + b'\n')
    for row in rows:
        digest.update(canonical_json([row[k] for k in columns]) + b'\n')
    return digest.hexdigest()


def key_set(table, contract):
    return {canonical_json([r[k] for k in contract.natural_key]) for r in records(table)}


def table_audit(table: ProviderTable, contract: DatasetContract) -> dict:
    rows = records(table)
    cap_hit = contract.max_rows is not None and len(rows) >= contract.max_rows
    duplicates = len(rows) - len(key_set(table, contract))
    result = dict(requested_fields=contract.required_fields, observed_fields=table.fields,
                  observed_types={f: sorted({type(r[f]).__name__ for r in rows}) for f in table.fields},
                  row_count=len(rows), documented_cap=contract.max_rows,
                  distance_to_cap=None if contract.max_rows is None else contract.max_rows-len(rows),
                  potential_truncation=cap_hit, natural_key_duplicates=duplicates,
                  null_counts={f: sum(r[f] is None for r in rows) for f in table.fields},
                  logical_sha256=logical_fingerprint(table, contract))
    result['invalid_source_identifier_count'] = sum(
        not is_native_identifier(r['ts_code']) for r in rows) if 'ts_code' in table.fields else 0
    result['non_normalized_identifier_count'] = sum(
        not is_normalized_ashare_identifier(r['ts_code']) for r in rows) if 'ts_code' in table.fields else 0
    # Compatibility metric: normalization findings, not raw rejection.
    result['invalid_identity_count'] = result['non_normalized_identifier_count']
    result['identity_status'] = 'REVIEW_REQUIRED' if result['non_normalized_identifier_count'] else 'PASS'
    result['invalid_event_date_count'] = 0
    for r in rows:
        for field in ('trade_date', 'cal_date'):
            if field in r:
                try:
                    if not isinstance(r[field], str) or len(r[field]) != 8:
                        raise ValueError('Invalid date')
                    datetime.strptime(r[field], '%Y%m%d')
                except ValueError:
                    result['invalid_event_date_count'] += 1
    if contract.dataset == 'stk_limit':
        result['asset_type_counts'] = dict(sorted(Counter(str(r['asset_type']) for r in rows).items()))
        result['exchange_counts'] = dict(sorted(Counter(str(r['exchange']) for r in rows).items()))
    if contract.dataset == 'daily':
        def number(v):
            return type(v) in (int, float) and math.isfinite(v)

        result['daily'] = dict(ohlc_invalid=0, price_nonpositive_or_null=0,
                               negative_or_null_volume_amount=0, change_mismatch=0,
                               pct_chg_mismatch=0, change_max_error=0.0, pct_chg_max_error=0.0)
        audit = result['daily']
        for r in rows:
            prices = [r[k] for k in ('open', 'high', 'low', 'close', 'pre_close')]
            if not all(number(v) and v > 0 for v in prices):
                audit['price_nonpositive_or_null'] += 1
                continue
            audit['ohlc_invalid'] += int(r['high'] < max(r['open'], r['close'], r['low']) or
                                         r['low'] > min(r['open'], r['close'], r['high']))
            audit['negative_or_null_volume_amount'] += int(any(
                not number(r[k]) or r[k] < 0 for k in ('vol', 'amount')))
            for label, observed, expected in (
                ('change', r['change'], r['close']-r['pre_close']),
                ('pct_chg', r['pct_chg'], 100*r['change']/r['pre_close'] if number(r['change']) else None),
            ):
                if not number(observed) or expected is None:
                    audit[label+'_mismatch'] += 1
                else:
                    error = abs(observed-expected)
                    audit[label+'_max_error'] = max(audit[label+'_max_error'], error)
                    audit[label+'_mismatch'] += int(error > 0.011)
    result['dq_status'] = ('ERROR' if cap_hit or duplicates or result['invalid_source_identifier_count'] or result['invalid_event_date_count']
        or (contract.dataset == 'stk_limit' and (result['null_counts']['asset_type'] or result['null_counts']['exchange'])) else 'PASS')
    if 'daily' in result and any(result['daily'][k] for k in (
        'ohlc_invalid', 'price_nonpositive_or_null', 'negative_or_null_volume_amount',
        'change_mismatch', 'pct_chg_mismatch',
    )):
        result['dq_status'] = 'ERROR'
    return result


def _by_code(table):
    # Duplicate counts are separately errors; do not hide duplicate ambiguity in joins.
    return {r['ts_code']: r for r in records(table)}


def _compare(left, right, field, tolerance=0.011):
    common = left.keys() & right.keys()
    mismatches = sum(type(left[k][field]) not in (int, float) or
                     type(right[k][field]) not in (int, float) or
                     abs(left[k][field]-right[k][field]) > tolerance for k in common)
    return dict(intersection=len(common), only_daily=len(left.keys()-right.keys()),
                only_other=len(right.keys()-left.keys()), mismatch=mismatches)


def cross_audit(tables: dict[str, ProviderTable], universe: set[str]) -> dict:
    result = {}
    daily = _by_code(tables['daily']) if 'daily' in tables else None
    if daily is not None and 'daily_basic' in tables:
        other = _by_code(tables['daily_basic'])
        value = _compare(daily, other, 'close')
        result['daily_basic'] = dict(intersection=value['intersection'], only_daily=value['only_daily'],
                                     only_daily_basic=value['only_other'], close_mismatch=value['mismatch'])
    if daily is not None and 'stk_limit' in tables:
        stk = {r['ts_code']: r for r in records(tables['stk_limit']) if r['asset_type'] == 'STK'}
        result['stk_limit'] = _compare(daily, stk, 'pre_close')
        result['stk_limit']['by_exchange'] = {
            exchange: _compare({k: v for k, v in daily.items() if k in subset}, subset, 'pre_close')
            for exchange in sorted({str(r['exchange']) for r in stk.values()})
            if (subset := {k: v for k, v in stk.items() if str(v['exchange']) == exchange})
        }
    if daily is not None and 'adj_factor' in tables:
        other = _by_code(tables['adj_factor'])
        result['adj_factor'] = dict(intersection=len(daily.keys() & other.keys()),
            only_daily=len(daily.keys()-other.keys()), only_adj=len(other.keys()-daily.keys()),
            null_nonpositive_factor=sum(type(r['adj_factor']) not in (int, float) or
                                       r['adj_factor'] <= 0 for r in other.values()))
    if 'stock_st' in tables:
        rows = records(tables['stock_st'])
        # Controlled type labels only; arbitrary provider text must not become public prose.
        names_by_type = {}
        for row in rows:
            names_by_type.setdefault(str(row['type']), set()).add(str(row['type_name']))
        result['stock_st'] = dict(type_name_inconsistency=sum(len(v)>1 for v in names_by_type.values()),
            unresolved_codes=sum(r['ts_code'] not in universe for r in rows),
            type_type_name_counts=dict(sorted(Counter(
                json.dumps([r['type'], r['type_name']], ensure_ascii=False) for r in rows).items())))
    if 'suspend_d' in tables:
        rows = records(tables['suspend_d'])
        result['suspend_d'] = dict(s_count=sum(r['suspend_type']=='S' for r in rows),
            r_count=sum(r['suspend_type']=='R' for r in rows),
            timing_null=sum(r['suspend_timing'] is None for r in rows),
            timing_nonnull=sum(r['suspend_timing'] is not None for r in rows),
            full_day_s_with_daily=None if daily is None else sum(
                r['suspend_type']=='S' and r['suspend_timing'] is None and r['ts_code'] in daily for r in rows))
    return result


def cross_has_findings(result):
    return any(value.get(key, 0) for value in result.values() for key in (
        'close_mismatch', 'mismatch', 'null_nonpositive_factor', 'unresolved_codes', 'full_day_s_with_daily', 'type_name_inconsistency',
    ) if value.get(key) is not None)
