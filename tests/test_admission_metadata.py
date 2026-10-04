"""Finite metadata wire plan and approval materials; no live market path."""

import copy
import json
from datetime import timedelta
from pathlib import Path

import pytest

from astock.data import admission_metadata as m, admission_offline as a
from astock.data.reconstruction import checksum
from astock.data.warehouse_lock import warehouse_connection

ROOT = Path(__file__).parents[1]


def payload(request):
    start = m._day(request['wire']['params']['start_date'])
    return json.dumps(dict(fields=m.FIELDS, items=[
        ['SZSE', (start+timedelta(days=i)).strftime('%Y%m%d'), 1,
         (start+timedelta(days=i-1)).strftime('%Y%m%d')]
        for i in range(request['expected_civil_rows'])])).encode()


def test_exact_plan_wire_format_contract_and_no_execution_license():
    plan = m.build_plan(ROOT)
    m.validate_plan(ROOT, plan)
    assert len(plan['requests']) == 7
    assert sum(r['expected_civil_rows'] for r in plan['requests']) == 42
    assert len({r['request_id'] for r in plan['requests']}) == 7
    assert plan['execution_license'] is False
    for r in plan['requests']:
        assert r['wire']['params']['exchange'] == 'SZSE'
        assert r['wire']['fields'] == 'exchange,cal_date,is_open,pretrade_date'
        assert '-' not in r['wire']['params']['start_date']
        assert r['max_attempts'] == 1


@pytest.mark.parametrize('change', ['venue', 'date', 'fields', 'contract', 'license', 'budget', 'member'])
def test_rehashed_or_unhashed_plan_tamper_rejected(change):
    plan = m.build_plan(ROOT)
    if change=='license': plan['execution_license']=True
    elif change=='budget': plan['market_request_budget']=8
    elif change=='member': plan['requests'].pop()
    elif change=='venue': plan['requests'][0]['wire']['params']['exchange']='SSE'
    elif change=='date': plan['requests'][0]['wire']['params']['start_date']='2013-01-04'
    elif change=='fields': plan['requests'][0]['wire']['fields']='cal_date'
    elif change=='contract': plan['requests'][0]['wire']['contract_canonical_hash']='f'*64
    with pytest.raises(ValueError): m.validate_plan(ROOT,plan)


@pytest.mark.parametrize('change', ['partial', 'extra', 'duplicate', 'venue', 'flag', 'previous', 'width'])
def test_calendar_completeness_and_scalar_contract_rejection(change):
    request=m.build_plan(ROOT)['requests'][0]
    table=json.loads(payload(request))
    if change=='partial': table['items'].pop()
    elif change=='extra': table['items'].append(['SZSE','20130109',1,'20130108'])
    elif change=='duplicate': table['items'][1]=table['items'][0]
    elif change=='venue': table['items'][0][0]='BSE'
    elif change=='flag': table['items'][0][2]=True
    elif change=='previous': table['items'][0][3]=table['items'][0][1]
    elif change=='width': table['items'][0].pop()
    with pytest.raises(ValueError): m.validate_response(request,json.dumps(table).encode())


def test_managed_fake_metadata_reopen_no_resend_and_sidecar_tamper(tmp_path):
    db_path=tmp_path/'synthetic.duckdb'; outputs=tmp_path/'metadata'
    plan=m.build_plan(ROOT); request=plan['requests'][0]
    with warehouse_connection(db_path) as db:
        a.initialize(ROOT,db)
        with pytest.raises(ValueError,match='fake'): m.capture_fake(ROOT,db,outputs,plan,request['request_id'],object())
        def observed():
            assert db.execute('SELECT state FROM offline_attempt_event ORDER BY ordinal').fetchall()==[('RUNNING',),('CALL_ENTERED',)]
        assert m.capture_fake(ROOT,db,outputs,plan,request['request_id'],a.FakeTransport(payload(request)),observe_claim=observed)=='COMPLETE'
        times=db.execute('SELECT * FROM offline_attempt_event ORDER BY ordinal').fetchall()
    with warehouse_connection(db_path) as db:
        assert m.capture_fake(ROOT,db,outputs,plan,request['request_id'],a.FakeTransport(fail=True))=='ALREADY_VALID'
        assert db.execute('SELECT * FROM offline_attempt_event ORDER BY ordinal').fetchall()==times
        sidecar=next(outputs.glob('*.metadata.json')); v=json.loads(sidecar.read_text());v['rows']+=1;sidecar.write_text(json.dumps(v))
        with pytest.raises(ValueError,match='sidecar'): m.capture_fake(ROOT,db,outputs,plan,request['request_id'],a.FakeTransport())


def test_uncertain_fake_metadata_cannot_resend_after_reopen(tmp_path):
    path=tmp_path/'synthetic.duckdb'; plan=m.build_plan(ROOT);r=plan['requests'][0];out=tmp_path/'outputs'
    with warehouse_connection(path) as db:
        a.initialize(ROOT,db)
        with pytest.raises(RuntimeError):m.capture_fake(ROOT,db,out,plan,r['request_id'],a.FakeTransport(fail=True))
    with warehouse_connection(path) as db:
        with pytest.raises(ValueError,match='no resend'):m.capture_fake(ROOT,db,out,plan,r['request_id'],a.FakeTransport(payload(r)))
        assert db.execute('SELECT count(*) FROM offline_raw_manifest').fetchone()[0]==0


def test_backfill_gross_verified_reuse_net_and_pacing_is_lower_bound():
    no=m.full_history_budget(0);all_=m.full_history_budget(126)
    assert no['gross_base']==no['net_base']==30126
    assert all_['net_base']==30000 and all_['reserve']==0
    assert all_['pacing_start_span_lower_bound_seconds']==29999*1.25
    assert all_['response_latency_and_runtime']=='UNKNOWN'
    for invalid in [True,-1,127,1.2]:
        with pytest.raises(ValueError):m.full_history_budget(invalid)


def fixture_packet():
    context=dict(implementation_sha='a'*40,design_hash='b'*64,policy_hash='c'*64,input_set_hash='d'*64,
                 candidate_resolver_hash='e'*64,delta_hash='f'*64,approved_at=None,review_ref=None,reviewed_sha=None,execution_license=False)
    ref=dict(path='context-final.json',bytes_sha256='1'*64,canonical_hash=checksum(context))
    packet=dict(context_proposal=ref,pins={k:context[k] for k in ('implementation_sha','design_hash','policy_hash','input_set_hash','candidate_resolver_hash','delta_hash')},
                execution_license=False,approved_at=None,review_ref=None,reviewed_sha=None)
    checklist=dict(items=[dict(condition='Original preservation',status='AUTHOR_VERIFIED_PASS',evidence=['before.json','after.json'])])
    return packet,context,checklist,ref


@pytest.mark.parametrize('change', ['none','oldpointer','pin','pending','approval','license','noimpl'])
def test_final_packet_rejects_stale_entry_pin_or_manufactured_approval(change):
    packet,context,checklist,ref=fixture_packet()
    if change=='none':m.validate_packet(packet,context,checklist,ref);return
    if change=='oldpointer':packet['context_proposal']=dict(ref,path='context-old.json')
    if change=='pin':packet['pins']['policy_hash']='0'*64
    if change=='pending':checklist['items'][0]['status']='PENDING_FINAL_CHECK'
    if change=='approval':packet['review_ref']='engineering PASS cannot approve case'
    if change=='license':context['execution_license']=True
    if change=='noimpl':context['implementation_sha']=None
    with pytest.raises(ValueError):m.validate_packet(packet,context,checklist,ref)
