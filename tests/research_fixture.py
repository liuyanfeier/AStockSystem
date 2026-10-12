"""Vendor-shaped SYNTHETIC fixtures, with official 2026 holiday shape, never market facts."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from pydantic import SecretStr

from astock.research.acquisition import CapturePlan, capture, implementation_hash
from astock.research.core import code_fingerprint, digest, encoded, read_json
from astock.research.tushare import CONTRACTS

CAPTURED = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)
ASOF = '2026-10-13T20:00:00+08:00'


def fixture_plan(size=10):
    plan = read_json(Path('config/research/acquisition-proposal.json'))
    if size != 10:
        codes = [f'{100000+i:06d}.SZ' for i in range(size)]
        # Moderate pool profiles partition by series so response cap stays meaningful.
        members=[]
        def add(api, **params):
            fields, cap=CONTRACTS[api]
            members.append(dict(api=api, params=params, fields=fields.split(), row_cap=cap))
        for c in codes:
            add('stock_basic',ts_code=c,list_status='L')
            for a in ('daily','adj_factor','stk_limit'):
                add(a,ts_code=c,start_date='20260401',end_date='20261012')
        for m in plan['members']:
            if m['api'] in ('trade_cal','index_basic','index_daily','stock_st'):
                members.append(m)
        # Profiling is offline and can exceed collector 100-member cap: caller
        # describes raw fixtures directly instead of increasing live budget limits.
        plan.update(universe=codes,members=members,maximum_requests=len(members),maximum_attempts=len(members))
    return plan


def civil_days(plan):
    start,end=date.fromisoformat(plan['window_start']),date.fromisoformat(plan['window_end'])
    return [start+timedelta(days=i) for i in range((end-start).days+1)]


def is_session(d):
    closed = [(date(2026,4,4),date(2026,4,6)),(date(2026,5,1),date(2026,5,5)),
              (date(2026,6,19),date(2026,6,21)),(date(2026,9,25),date(2026,9,27)),
              (date(2026,10,1),date(2026,10,7))]
    return int(d.weekday()<5 and not any(a<=d<=b for a,b in closed))


def response(plan, member, anomalies=True):
    api,p=member['api'],member['params']
    days=[d for d in civil_days(plan) if is_session(d)]
    codes=p.get('ts_code', '').split(',')
    rows=[]
    if api=='trade_cal':
        previous='20260331'
        for d in civil_days(plan):
            rows.append(dict(exchange=p['exchange'],cal_date=d.strftime('%Y%m%d'),is_open=is_session(d),pretrade_date=previous))
            if is_session(d):previous=d.strftime('%Y%m%d')
    elif api=='stock_basic':
        for c in codes:
            rows.append(dict(ts_code=c,name='SYNTHETIC '+c,exchange='SZSE' if c in plan['universe'][:5] else 'SSE',market='主板',list_date=days[-30].strftime('%Y%m%d') if anomalies and c==plan['universe'][6] else '20000101',list_status='L'))
    elif api=='index_basic':
        rows=[dict(ts_code=c,name='SYNTHETIC benchmark',market=p['market'],publisher='SYNTHETIC 中证') for c in codes]
    elif api=='stock_st':
        rows=[dict(ts_code=plan['universe'][5],name='SYNTHETIC ST',trade_date=days[-1].strftime('%Y%m%d'),type='ST',type_name='风险警示板')]
    elif api=='suspend_d':
        rows=[dict(ts_code=plan['universe'][4],trade_date=days[-5].strftime('%Y%m%d'),suspend_type='S',suspend_timing=None)] if anomalies else []
    else:
        for c in codes:
            index=plan['universe'].index(c) if c in plan['universe'] else 0
            for i,d in enumerate(days):
                if anomalies and index==6 and i<len(days)-30:
                    continue
                if anomalies and ((index==4 and i==len(days)-5) or (index==6 and i<len(days)-30)) and api=='daily':
                    continue
                if anomalies and index==7 and i==len(days)-1 and api=='adj_factor':continue
                if c in plan['benchmarks']:
                    base=1000+i
                elif index==1:
                    base=40-i*.1
                elif index==2:
                    base=20
                else:
                    base=10+i*.1
                split=anomalies and index==3
                factor=2 if split and i>=90 else 1
                close=base/factor
                row=dict(ts_code=c,trade_date=d.strftime('%Y%m%d'),open=close,high=close+.01/factor,low=close-.01/factor,close=close,pre_close=close,
                         vol=0 if anomalies and index==8 else 10000,amount=0 if anomalies and index==8 else 20000,
                         adj_factor=factor,up_limit=close*1.1,down_limit=close*.9)
                rows.append(row)
    return dict(request_id='SYNTHETIC',code=0,msg='',data=dict(fields=list(member['fields']),items=[[row[f] for f in member['fields']] for row in rows]))


class BytesStream(httpx.SyncByteStream):
    def __init__(self,body):self.body=body
    def __iter__(self):yield self.body


def approved_mock(root,plan,handler=None):
    destination=root/plan['destination']
    plan_file=root/'plan.json';plan_file.write_bytes(encoded(plan))
    remaining=[digest(m) for m in plan['members'] if not (destination/f'{digest(m)}.claim.json').exists()]
    approval=dict(protocol='RESEARCH_CAPTURE_APPROVAL_V1_1',plan_hash=digest(plan),destination=str(destination.resolve()),
                  implementation_hash=implementation_hash(),authorized_by='SYNTHETIC_TEST',approved_at='2026-10-13T00:00:00+00:00',
                  expires_at='2026-10-14T00:00:00+00:00',member_ids=remaining,fixture_only=True,execution_authorized=True)
    approval_file=root/'approval.json';approval_file.write_bytes(encoded(approval))
    calls=[]
    def request(req):
        payload=__import__('json').loads(req.content)
        m=next(m for m in plan['members'] if m['api']==payload['api_name'] and m['params']==payload['params'])
        calls.append(m)
        if handler:return handler(m,len(calls))
        return httpx.Response(200,stream=BytesStream(encoded(response(plan,m))))
    result=capture(root,plan_file,live=True,approval_file=approval_file,transport=httpx.MockTransport(request),
                   token=SecretStr('SYNTHETIC_TEST_TOKEN_12345'),now=lambda:CAPTURED,sleep=lambda _:None)
    return result,calls,destination
