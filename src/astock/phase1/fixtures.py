"""Closed nonempty public-entry demonstration; all values are synthetic."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from pydantic import SecretStr

from astock.phase1 import acquisition, contracts, pipeline
from astock.phase1.core import day, digest, encoded, instant, logical_id, require, strict_json


class FixtureClock:
    def __init__(self, at: str = '2025-06-01T00:00:00+00:00'):
        self.at, self.mono = instant(at), 100.0
        self.boot_id = 'CLOSED-' + uuid4().hex

    def utc(self) -> datetime:
        return self.at

    def monotonic(self) -> float:
        return self.mono

    def boot(self) -> str:
        return self.boot_id

    def sleep(self, seconds: float) -> None:
        self.at += timedelta(seconds=seconds)
        self.mono += seconds


def response(member: dict, rows: list[dict], *, diagnostic=True) -> dict:
    value = dict(request_id='synthetic-' + digest(member)[:16], code=0, msg=None,
                 data=dict(fields=member['fields'], items=[[r.get(f) for f in member['fields']] for r in rows]))
    if diagnostic:
        value['detail'] = 'SYNTHETIC_TYPED_DIAGNOSTIC'
        value['data'].update(count=0, has_more=False)
    return value


def calendar_rows(params: dict) -> list[dict]:
    start, end = day(params['start_date']), day(params['end_date'])
    previous = start - timedelta(days=1)
    while previous.weekday() >= 5:
        previous -= timedelta(days=1)
    result = []
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        opened = int(d.weekday() < 5)
        result.append(dict(exchange=params['exchange'], cal_date=d.strftime('%Y%m%d'),
                           is_open=opened, pretrade_date=previous.strftime('%Y%m%d')))
        if opened:
            previous = d
    return result


def proof(at: str) -> dict:
    return dict(namespace='FIXTURE', vintage_verified=True, evidence_hash=digest(dict(synthetic=at)),
                precision='MICROSECOND', published_at=at, available_at=at)


def row(root: Path, ds: str, **values) -> dict:
    result = {}
    for f, spec in contracts.catalog(root)[ds]['fields'].items():
        result[f] = None if spec['nullable'] else 1 if spec['type'] == 'int' else 10.0 if spec['type'] == 'number' else '20250102' if spec['type'] == 'date' else 'SYNTHETIC'
    result.update(values)
    return result


def sample_inputs(root: Path) -> tuple[list, dict, list]:
    members, payloads, packages = [], {}, []
    def add(ds, params, rows, at='2025-01-02T01:00:00+00:00', **metadata):
        member = contracts.request(root, ds, params, metadata=dict(knowledge=proof(at), **metadata))
        value = response(member, rows)
        if contracts.catalog(root)[ds]['source'] == 'TUSHARE':
            members.append(member)
            payloads[(ds, encoded(params))] = value
        else:
            packages.append(dict(namespace='FIXTURE', request=member, response=value,
                                 retrieved_at='2025-06-01T00:00:00+00:00', evidence='SYNTHETIC_NOT_LEGAL_EVIDENCE'))
    for status, code, name in [('L', '000001.SZ', 'SAME_NAME'), ('D', 'T00018.SH', 'SAME_NAME'), ('P', '000002.SZ', 'OTHER_NAME')]:
        add('stock_basic', dict(list_status=status), [row(root, 'stock_basic', ts_code=code, symbol=code.split('.')[0], name=name,
            fullname=name, market='主板', exchange='SSE' if status == 'D' else 'SZSE', curr_type='CNY', list_status=status,
            list_date='20000101', delist_date='20200101' if status == 'D' else None)])
    p = dict(exchange='SZSE', start_date='20250101', end_date='20250110')
    add('trade_cal', p, calendar_rows(p), at='2024-12-31T00:00:00+00:00')
    for ds in sorted(contracts.MARKET):
        r = row(root, ds, ts_code='000001.SZ', trade_date='20250102')
        if ds == 'daily':
            r.update(open=10.0, high=11.0, low=9.0, close=10.5, pre_close=10.0, change=0.5, pct_chg=5.0, vol=1000.0, amount=1050.0)
        if ds == 'adj_factor': r.update(adj_factor=1.0)
        if ds == 'stk_limit': r.update(up_limit=11.0, down_limit=9.0)
        if ds == 'suspend_d': r.update(suspend_type='S', suspend_timing=None)
        if ds == 'stock_st': r.update(type='ST')
        add(ds, dict(trade_date='20250102'), [r], at='2025-01-02T07:05:00+00:00' if ds not in ('stock_st', 'suspend_d') else '2025-01-02T01:00:00+00:00')
    for ds in ('daily', 'adj_factor'):
        r = row(root, ds, ts_code='000001.SZ', trade_date='20250106')
        if ds == 'daily': r.update(open=11.0, high=12.0, low=10.0, close=11.5)
        else: r.update(adj_factor=2.0)
        add(ds, dict(trade_date='20250106'), [r], at='2025-01-06T07:05:00+00:00')
    for date, first, last in [('20250415', '20250414', '20250416'), ('20250515', '20250514', '20250516')]:
        params = dict(exchange='SZSE', start_date=first, end_date=last)
        add('trade_cal', params, calendar_rows(params), at=day(first).isoformat() + 'T00:00:00+00:00')
        for ds in ('daily', 'daily_basic', 'adj_factor', 'stk_limit'):
            r = row(root, ds, ts_code='000001.SZ', trade_date=date)
            if ds == 'daily': r.update(open=10., high=12., low=9., close=11., vol=1000., amount=1100.)
            elif ds == 'adj_factor': r.update(adj_factor=2.)
            elif ds == 'stk_limit': r.update(up_limit=11., down_limit=9.)
            add(ds, dict(trade_date=date), [r], at=day(date).isoformat() + 'T07:05:00+00:00')
    for ds in sorted(contracts.FINANCIAL):
        for ann, amount in [('20250401', 10.0), ('20250501', 12.0)]:
            r = row(root, ds, ts_code='000001.SZ', ann_date=ann, end_date='20241231', update_flag='1')
            if ds != 'fina_indicator':
                r.update(f_ann_date=ann, report_type='1', comp_type='2')
            metric = next(f for f, spec in contracts.catalog(root)[ds]['fields'].items() if spec['type'] == 'number')
            r[metric] = amount
            add(ds, dict(ts_code='000001.SZ', ann_date=ann), [r], at=day(ann).isoformat() + 'T01:00:00+00:00')
    add('index_classify', dict(src='SW2021'), [row(root, 'index_classify', index_code='801010.SI', industry_name='FIXTURE_INDUSTRY', level='L1', industry_code='110000', src='SW2021')])
    add('index_member_all', dict(ts_code='000001.SZ', is_new='N'), [row(root, 'index_member_all', ts_code='000001.SZ',
        name='FIXTURE', l1_code='801010.SI', l1_name='FIXTURE', l2_code='801011.SI', l2_name='FIXTURE',
        l3_code='801012.SI', l3_name='FIXTURE', in_date='20200101', out_date='20250105', is_new='N')], classification_version='SW2021')
    add('index_basic', dict(ts_code='000300.SH'), [row(root, 'index_basic', ts_code='000300.SH', name='FIXTURE_REFERENCE', fullname='FIXTURE_REFERENCE')])
    add('index_daily', dict(ts_code='000300.SH', trade_date='20250102'), [row(root, 'index_daily', ts_code='000300.SH', trade_date='20250102', open=10.0, high=11.0, low=9.0, close=10.5)])
    mapping = []
    for sid, episode, code, exchange, board, start, end, status in [
        ('S1', 'E1', '000001.SZ', 'SZSE', 'MAIN', '20000101', None, 'L'),
        ('S2', 'E2', 'T00018.SH', 'SSE', 'MAIN', '20000101', '20200101', 'D'),
        ('S3', 'E3', '830001.BJ', 'BSE', 'BSE', '20200101', '20250106', 'L'),
        ('S3', 'E3', '920001.BJ', 'BSE', 'BSE', '20250106', None, 'L')]:
        mapping.append(row(root, 'security_identifiers', security_id=sid, episode_id=episode, source='TUSHARE', identifier_type='PROVIDER_NATIVE',
            identifier=code, exchange=exchange, board=board, list_status=status, valid_from=start, valid_to=end, evidence_source='FIXTURE_EXPLICIT_MAPPING'))
    add('security_identifiers', {}, mapping, at='2024-12-31T00:00:00+00:00')
    add('listing_episodes', {}, [row(root, 'listing_episodes', security_id=sid, episode_id=eid, exchange=exchange,
        board=board, asset_type='STK', list_date='20000101', valid_from='20000101', valid_to=end,
        last_trading_date='20191231' if end else None, delist_date=end, evidence_source='FIXTURE_EXPLICIT_EPISODE')
        for sid, eid, exchange, board, end in [('S1', 'E1', 'SZSE', 'MAIN', None), ('S2', 'E2', 'SSE', 'MAIN', '20200101'), ('S3', 'E3', 'BSE', 'BSE', None)]],
        at='2024-12-31T00:00:00+00:00')
    add('bak_basic', dict(ts_code='000001.SZ', trade_date='20250102'), [row(root, 'bak_basic', ts_code='000001.SZ', trade_date='20250102', name='FIXTURE', list_date='20000101', industry='CURRENT_SOURCE_LABEL_NOT_PIT')])
    add('security_status', {}, [row(root, 'security_status', security_id='S1', episode_id='E1', state_type='RISK_WARNING', state_value='ST', exchange='SZSE',
        valid_from='20250101', valid_to='20250106', evidence_source='FIXTURE_STATUS'),
        row(root, 'security_status', security_id='S1', episode_id='E1', state_type='RISK_WARNING', state_value='NORMAL', exchange='SZSE',
        valid_from='20250106', valid_to=None, evidence_source='FIXTURE_STATUS')], at='2024-12-31T00:00:00+00:00')
    add('industry_membership', {}, [row(root, 'industry_membership', security_id='S1', classification_version='SW2021', industry_code=code,
        level='L1', valid_from=start, valid_to=end, evidence_source='FIXTURE_INTERVAL') for code, start, end in
        [('A', '20200101', '20250106'), ('B', '20250106', None)]], at='2024-12-31T00:00:00+00:00')
    add('rule_history', {}, [row(root, 'rule_history', rule_id='FIXTURE-' + str(i), exchange='SZSE', board='MAIN', state='*',
        valid_from=start, valid_to=end, evidence_source='FIXTURE_NOT_ACTUAL_RULE', price_limit_ratio=ratio,
        ipo_no_limit_sessions=0, sell_delay_trading_days=1, min_order_qty=100, order_qty_step=100, price_tick=0.01)
        for i, start, end, ratio in [(1, '20200101', '20250106', 0.1), (2, '20250106', None, 0.2)]], at='2024-12-31T00:00:00+00:00')
    add('market_crosscheck', {}, [row(root, 'market_crosscheck', ts_code='000001.SZ', exchange='SZSE', trade_date='20250102',
        open=10., high=11., low=9., close=10.5, volume_shares=100000., amount_cny=1050000., evidence_source='FIXTURE_SECOND_SOURCE')], at='2025-01-02T08:00:00+00:00')
    return members, payloads, packages


def demo(root: Path, destination: Path) -> dict:
    members, payloads, packages = sample_inputs(root)
    def handler(request):
        wire = strict_json(request.content)
        value = payloads[(wire['api_name'], encoded(wire['params']))]
        return httpx.Response(200, content=encoded(value))
    baseline = dict(protocol='PHASE1_GLOBAL_CONSUMPTION_V1', root=str(root.resolve()), original_paths={}, original_hashes={}, rowset_hashes={}, records=[])
    if (destination / 'catalog.duckdb').exists():
        with acquisition.store(root, destination, read_only=True) as db:
            audited = acquisition.audit(root, destination, db)
            consumed = acquisition.local_consumption(db)
            require({r['logical_id'] for r in consumed} == {logical_id(m) for m in members}
                    and all(r['states'][-1] in ('COMPLETE', 'RAW_RETAINED') for r in consumed), 'STOPPED_DEMO_REQUIRES_EXPLICIT_RECOVERY')
            require(all(r['request'] in members for r in consumed), 'DEMO_INPUTS_CHANGED')
        result = dict(status='RAW_BATCH_VALID', primary_error=None, secondary_errors=[], final_audit=audited,
                      replay='ALREADY_VALID', new_mock_calls=0, real_market_API=0)
    else:
        plan = acquisition.make_plan(root, destination, members, baseline, fixture=True)
        result = acquisition.run_batch(root, destination, plan, baseline, token=SecretStr('closed-synthetic'), transport=httpx.MockTransport(handler), clock=FixtureClock())
    if result['status'] != 'RAW_BATCH_VALID':
        return result
    pipeline.import_evidence(root, destination, packages)
    built = pipeline.build(root, destination)
    return dict(capture=result, build=built, coverage=pipeline.coverage(root, destination),
                queries=[pipeline.query(root, destination, 'S1', date, asof, taxonomy='SW2021') for date, asof in [
                    ('2025-04-15', '2025-04-15T10:00:00+00:00'), ('2025-05-15', '2025-05-15T10:00:00+00:00')]],
                real_market_API=0, original_SQL_writes=0)
