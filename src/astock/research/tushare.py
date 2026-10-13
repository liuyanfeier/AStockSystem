"""Pure research response contracts; independent of frozen Phase1 admission workflows."""
from __future__ import annotations

from datetime import timedelta
import hashlib
import math
from pathlib import Path

from astock.data.raw_validation import strict_json
from astock.research.core import day, digest, encoded, instant, market_day, read_json, require
from astock.research.publication import publish_bytes

# Provider documented caps where published. For factor/calendar/index daily the
# documentation gives no numeric cap: conservative LOCAL ceilings are explicit.
CONTRACTS = {
    'daily': ('ts_code trade_date open high low close pre_close vol amount', 6000),
    'adj_factor': ('ts_code trade_date adj_factor', 2000),
    'stk_limit': ('ts_code trade_date up_limit down_limit', 5800),
    'suspend_d': ('ts_code trade_date suspend_timing suspend_type', 5000),
    'index_daily': ('ts_code trade_date open high low close pre_close vol amount', 2000),
    'index_basic': ('ts_code name market publisher', 8000),
    'trade_cal': ('exchange cal_date is_open pretrade_date', 2000),
    'stock_basic': ('ts_code name exchange market list_date list_status', 6000),
    'stock_st': ('ts_code name trade_date type type_name', 1000),
}
DATASETS = {'stock_basic': 'instruments', 'index_basic': 'instruments', 'trade_cal': 'calendar',
            'stk_limit': 'status', 'suspend_d': 'status', 'stock_st': 'status',
            'daily': 'daily', 'index_daily': 'index_daily', 'adj_factor': 'adj_factor',
            'index_classify': 'industry_classification', 'index_member_all': 'industry_membership'}
PARAMS = {
    'stock_basic': {'ts_code', 'list_status', 'exchange', 'market'},
    'index_basic': {'ts_code', 'market', 'publisher', 'symbol'},
    'trade_cal': {'exchange', 'start_date', 'end_date'},
    **{a: {'ts_code', 'trade_date', 'start_date', 'end_date'} for a in
       ('daily', 'adj_factor', 'stk_limit', 'suspend_d', 'index_daily', 'stock_st')},
}


V2_CONTRACTS = {**CONTRACTS,
    'adj_factor': ('ts_code trade_date adj_factor', 10000),  # LOCAL ceiling, no documented numeric provider cap
    'stock_basic': ('ts_code name exchange market list_date list_status curr_type', 6000),
    'index_classify': ('index_code industry_name parent_code level industry_code is_pub src', 1000),
    'index_member_all': ('l1_code l1_name l2_code l2_name l3_code l3_name ts_code name in_date out_date is_new', 2000)}
V2_PARAMS = {**PARAMS, 'index_classify': {'level', 'src'}, 'index_member_all': {'l1_code', 'is_new'}}


def market_member(api: str, params: dict) -> dict:
    fields, cap = V2_CONTRACTS[api]
    member = dict(api=api, params=params, fields=fields.split(), row_cap=cap, contract_version='RESEARCH_PROVIDER_V2')
    validate_member(member)
    return member


def validate_member(member: dict) -> None:
    v2 = member.get('contract_version') == 'RESEARCH_PROVIDER_V2'
    require(set(member) == {'api', 'params', 'fields', 'row_cap'} | ({'contract_version'} if v2 else set()), 'REQUEST_SHAPE')
    contracts, allowed = (V2_CONTRACTS, V2_PARAMS) if v2 else (CONTRACTS, PARAMS)
    api = member['api']
    require(api in contracts, 'RESEARCH_API_UNKNOWN')
    fields, cap = contracts[api]
    require(member['fields'] == fields.split() and member['row_cap'] == cap, 'REQUEST_CONTRACT_CHANGED')
    params = member['params']
    require(isinstance(params, dict) and bool(params) and set(params) <= allowed[api], 'REQUEST_PARAMS')
    require(all(isinstance(v, str) and v.strip() == v and v for v in params.values()), 'REQUEST_PARAM_TYPE')
    if 'start_date' in params or 'end_date' in params:
        require('start_date' in params and 'end_date' in params and day(params['start_date']) <= day(params['end_date']), 'REQUEST_WINDOW')
    if 'trade_date' in params:
        day(params['trade_date'])
        require('start_date' not in params and 'end_date' not in params, 'REQUEST_DATE_AXES')
    if api == 'trade_cal':
        require(params.get('exchange') in {'SSE', 'SZSE'}, 'CALENDAR_REQUEST_EXCHANGE')
    elif api == 'stock_basic' and v2:
        require(set(params) == {'exchange', 'list_status'} and params['exchange'] in {'SSE', 'SZSE', 'BSE'} and params['list_status'] == 'L', 'CURRENT_POOL_REQUEST')
    elif api == 'index_classify':
        require(params == {'level': 'L1', 'src': 'SW2021'}, 'INDUSTRY_VERSION')
    elif api == 'index_member_all':
        require(set(params) == {'l1_code', 'is_new'} and params['is_new'] == 'Y', 'INDUSTRY_CURRENT_MEMBERS')
    elif api in {'stock_basic', 'index_basic', 'index_daily'}:
        require('ts_code' in params, 'EXACT_IDENTITY_REQUEST_REQUIRED')
    if v2 and api in {'daily', 'adj_factor'}:
        require(set(params) == {'trade_date'}, 'MARKET_DAY_BATCH_REQUIRED')
    if 'ts_code' in params:
        codes = params['ts_code'].split(',')
        require(len(set(codes)) == len(codes) and all(c and c.strip() == c for c in codes), 'REQUEST_CODES')
        require(len(codes) == 1 or api in {'daily', 'suspend_d'}, 'MULTI_CODE_UNDOCUMENTED')


def decode_response(body: bytes, member: dict) -> list[dict]:
    validate_member(member)
    value = strict_json(body)
    require(isinstance(value, dict) and set(value) <= {'request_id', 'code', 'msg', 'detail', 'data'}, 'PROVIDER_ENVELOPE')
    require(all(value.get(k) is None or isinstance(value[k], str) for k in ('msg', 'detail')),
            'PROVIDER_METADATA_TYPE')
    require(type(value.get('code')) is int and value['code'] == 0, 'PROVIDER_ERROR')
    data = value.get('data')
    require(isinstance(data, dict) and set(data) <= {'fields', 'items', 'has_more', 'count'}, 'PROVIDER_DATA')
    # Actual responses contain count=0 even with nonempty items. It is retained
    # metadata, NOT a row count/completeness assertion; inspect actual dates and
    # rows, explicit has_more and the conservative cap instead.
    require('count' not in data or type(data['count']) is int and data['count'] >= 0,
            'PROVIDER_COUNT_TYPE')
    require(data.get('has_more', False) is False, 'PROVIDER_TRUNCATED')
    fields, items = data.get('fields'), data.get('items')
    require(isinstance(fields, list) and all(isinstance(f, str) for f in fields) and
            len(set(fields)) == len(fields) and set(fields) == set(member['fields']), 'PROVIDER_FIELDS')
    require(isinstance(items, list) and len(items) < member['row_cap'], 'PROVIDER_CAP_OR_TRUNCATION')
    result, keys = [], set()
    for item in items:
        require(isinstance(item, list) and len(item) == len(fields), 'PROVIDER_ROW_SHAPE')
        row = dict(zip(fields, item, strict=True))
        numeric = {'open', 'high', 'low', 'close', 'pre_close', 'vol', 'amount', 'adj_factor', 'up_limit', 'down_limit'}
        nullable = {'pre_close', 'up_limit', 'down_limit'}
        for field in set(row) & numeric:
            v = row[field]
            require(v is None and field in nullable or type(v) in (int, float) and math.isfinite(v), 'PROVIDER_NUMERIC_TYPE')
        params = member['params']
        if 'ts_code' in row:
            require(isinstance(row['ts_code'], str) and bool(row['ts_code']), 'NATIVE_CODE_REQUIRED')
            if 'ts_code' in params:
                require(row['ts_code'] in params['ts_code'].split(','), 'RESPONSE_CODE_OUTSIDE_REQUEST')
        if 'exchange' in params:
            require(row.get('exchange') == params['exchange'], 'RESPONSE_EXCHANGE_OUTSIDE_REQUEST')
        if 'market' in params:
            require(row.get('market') == params['market'], 'RESPONSE_MARKET_OUTSIDE_REQUEST')
        if 'list_status' in params:
            require(row.get('list_status') == params['list_status'], 'RESPONSE_LIST_STATUS')
        event = row.get('trade_date', row.get('cal_date'))
        if event is not None:
            require(isinstance(event, str) and len(event) == 8 and event.isdigit(), 'PROVIDER_DATE_TYPE')
            d = day(event)
            if 'trade_date' in params:
                require(d == day(params['trade_date']), 'RESPONSE_DATE_OUTSIDE_REQUEST')
            if 'start_date' in params:
                require(day(params['start_date']) <= d <= day(params['end_date']), 'RESPONSE_DATE_OUTSIDE_REQUEST')
        if member['api'] == 'index_classify':
            require(row.get('level') == 'L1' and row.get('src') == 'SW2021' and all(isinstance(row.get(f), str) and row[f] for f in ('index_code', 'industry_name')), 'INDUSTRY_VERSION')
        if member['api'] == 'index_member_all':
            require(row.get('l1_code') == params['l1_code'] and row.get('is_new') == 'Y' and row.get('out_date') in (None, ''), 'INDUSTRY_MEMBERSHIP_SCOPE')
        key = (row.get('index_code') if member['api'] == 'index_classify' else row.get('ts_code'), row.get('exchange'), event)
        if member['api'] == 'suspend_d':
            require(row.get('suspend_timing') is None or isinstance(row['suspend_timing'], str), 'SUSPENSION_TIMING_TYPE')
            key += (row.get('suspend_type'), row.get('suspend_timing'))
        require(key not in keys, 'PROVIDER_DUPLICATE_OR_CONFLICT')
        keys.add(key)
        result.append(row)
    if member['api'] in {'stock_basic', 'index_basic', 'trade_cal'}:
        require(bool(result), 'IDENTITY_CALENDAR_EMPTY')
    return result


def response_rows(spec, body: bytes) -> list[dict]:
    rows = decode_response(body, spec.request)
    api = spec.request['api']
    if api == 'suspend_d':
        from collections import Counter
        multiplicity = Counter((r['ts_code'], r['trade_date']) for r in rows)
        for row in rows:
            if multiplicity[(row['ts_code'], row['trade_date'])] > 1:
                row['event_key'] = digest([row['suspend_type'], row['suspend_timing']])
    for row in rows:
        if api in {'index_basic', 'stock_basic'}:
            required = ('name', 'market', 'publisher') if api == 'index_basic' else ('name', 'exchange', 'market', 'list_date', 'list_status')
            require(all(isinstance(row.get(f), str) and bool(row[f].strip()) for f in required), 'IDENTITY_FIELD_VALUE')
        if api == 'index_basic':
            # Provider identity retained independently of the research calendar.
            row.update(kind='INDEX', exchange='UNKNOWN', calendar_exchange=spec.calendar_exchange,
                       identity_basis='index_basic:ts_code/market/publisher')
        elif api == 'stock_basic':
            require(row['exchange'] in {'SSE', 'SZSE', 'BSE'}, 'STOCK_EXCHANGE_EVIDENCE')
            row.update(kind='STOCK', identity_basis='stock_basic:ts_code/exchange')
            require(day(row['list_date']) <= market_day(instant(spec.retrieved_at)), 'FUTURE_LIST_DATE')
        elif api in {'stk_limit', 'suspend_d', 'stock_st'}:
            row.update(st='UNKNOWN', suspended='UNKNOWN', up_limit=row.get('up_limit'), down_limit=row.get('down_limit'))
            if api == 'stock_st':
                require(row['type'] == 'ST', 'UNKNOWN_WARNING_TYPE')
                row['st'] = 'YES'
            if api == 'suspend_d':
                require(row['suspend_type'] in {'S', 'R'}, 'SUSPENSION_EVENT_TYPE')
                # An S event (including intraday) establishes a suspension observation.
                # R proves resumption event only, not an entire normal trading day.
                row['suspended'] = 'YES' if row['suspend_type'] == 'S' else 'UNKNOWN'
    return rows


def merge_status(rows: list[dict]) -> dict[tuple[str, str], dict]:
    result = {}
    for row in rows:
        key = (row['code'], row['date'])
        current = result.setdefault(key, dict(st='UNKNOWN', suspended='UNKNOWN', up_limit=None,
                                             down_limit=None, source_hashes=[], events=[]))
        for field in ('st', 'suspended', 'up_limit', 'down_limit'):
            value, old = row.get(field), current[field]
            if value not in (None, 'UNKNOWN'):
                require(old in (None, 'UNKNOWN') or old == value, 'STATUS_SOURCE_CONFLICT')
                current[field] = value
        if row.get('source_hash'):
            current['source_hashes'].append(row['source_hash'])
        if row.get('status_event'):
            current['events'].append(row['status_event'])
        current['source_hashes'] = sorted(set(current['source_hashes']))
    return result


def make_capture_bundle(capture: Path, output: Path | None = None, *,
                        supplemental_captures: list[Path] | None = None) -> dict:
    """Describe raw bytes directly; no duplicated curated CSV/Parquet staging."""
    from astock.research.acquisition import read_capture
    from astock.research.inputs import load_bundle
    plan, receipts = read_capture(capture)
    retained = [(capture, receipt) for receipt in receipts]
    scope = ('purpose', 'window_start', 'window_end', 'universe', 'benchmarks', 'benchmark_calendars')
    for other in supplemental_captures or []:
        other_plan, other_receipts = read_capture(other)
        require(all(getattr(plan, key) == getattr(other_plan, key) for key in scope), 'CAPTURE_MERGE_SCOPE')
        retained.extend((other, receipt) for receipt in other_receipts)
    keys = [digest(receipt['member']) for _, receipt in retained]
    require(len(keys) == len(set(keys)), 'CAPTURE_DUPLICATE_MEMBER')
    files = []
    for origin, receipt in retained:
        member = receipt['member']
        api = member['api']
        body = (origin / receipt['object']).read_bytes()
        require(hashlib.sha256(body).hexdigest() == receipt['sha256'], 'CAPTURE_OBJECT_CHANGED')
        decode_response(body, member)
        spec = dict(path=str((origin / receipt['object']).absolute()), sha256=receipt['sha256'],
                    dataset=DATASETS[api], format='json', adapter='tushare-response-v1',
                    source='Tushare research capture', retrieved_at=receipt['retrieved_at'],
                    available_at=receipt['available_at'], request=member,
                    evidence_grade='LOCAL_CAPTURE_BOUND' if receipt['transport'] == 'HTTPS_TLS' else 'SYNTHETIC',
                    evidence=[dict(path=str((origin / receipt['receipt_file']).absolute()), sha256=receipt['receipt_hash']),
                              dict(path=str((origin / 'plan.json').absolute()), sha256=hashlib.sha256((origin / 'plan.json').read_bytes()).hexdigest())])
        claim_path = origin / f"{digest(member)}.claim.json"
        claim = read_json(claim_path)
        for proof in (claim_path, origin / f"{claim['approval_hash']}.approval.json"):
            spec['evidence'].append(dict(path=str(proof.absolute()), sha256=hashlib.sha256(proof.read_bytes()).hexdigest()))
        if api == 'index_basic':
            spec['calendar_exchange'] = plan.benchmark_calendars[member['params']['ts_code']]
        if api in {'daily', 'index_daily'}:
            spec.update(volume_unit='lots100', amount_unit='thousand_CNY')
        files.append(spec)
    v2 = plan.protocol == 'RESEARCH_CAPTURE_V2'
    if v2:
        universe = sorted({r['ts_code'] for s in files if s['request']['api'] == 'stock_basic'
                           for r in decode_response(Path(s['path']).read_bytes(), s['request'])})
        full_pool = {s['request']['params']['exchange'] for s in files if s['request']['api'] == 'stock_basic'} == set(plan.markets)
    else:
        universe, full_pool = plan.universe, False
    bundle = dict(protocol='RESEARCH_INPUT_V2' if v2 else 'RESEARCH_INPUT_V1', purpose='CURRENT_OBSERVATION', window_start=plan.window_start.isoformat(),
                  window_end=plan.window_end.isoformat(), universe=universe, benchmarks=plan.benchmarks,
                  universe_scope=('CURRENT_A_SHARE_L' if full_pool else 'PROVIDER_SAMPLE') if v2 else 'WATCHLIST', files=files)
    if v2:
        bundle['bse_calendar_reference'] = plan.bse_calendar_reference
    # Validate before publishing, so an incomplete capture cannot strand an
    # invalid final manifest. Later additive receipts get another immutable ID.
    target = output or capture / f"{digest(bundle)}.bundle.json"
    load_bundle(target, manifest=bundle)
    publish_bytes(target, encoded(bundle))
    return bundle
