import hashlib
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from astock.features.market import ObservationParameters
from astock.research.acquisition import capture, read_capture, implementation_hash
from astock.research.core import ResearchError, encoded, read_json
from astock.research.service import analyze
from astock.research.store import ResearchStore
from astock.research.tushare import decode_response, make_capture_bundle, merge_status
from research_fixture import ASOF, BytesStream, approved_mock, fixture_plan, response


@pytest.fixture
def full_capture(tmp_path):
    plan=fixture_plan()
    result,calls,destination=approved_mock(tmp_path,plan)
    assert result['complete_this_run']==len(calls)==39
    bundle=destination/'bundle.json'
    make_capture_bundle(destination,bundle)
    store=ResearchStore(destination/'research.duckdb')
    bid=store.import_bundle(bundle)
    p=ObservationParameters.model_validate(read_json(Path('config/research/observation-v1.json')))
    return plan,destination,bundle,store,bid,p


def test_full_default_window_e2e(full_capture,tmp_path):
    plan,dest,bundle,store,bid,p=full_capture
    s=analyze(store,bid,ASOF,p,plan['universe'])
    f=s['features'][0]
    assert f['consecutive_sessions']>=120
    n=f['consecutive_sessions']
    final=10+(n-1)*.1
    assert f['close']==pytest.approx(final)
    assert f['window_return']==pytest.approx(final/(10+(n-21)*.1)-1)
    assert f['ma']==pytest.approx(sum(10+i*.1 for i in range(n-60,n))/60)
    assert f['prior_high']==pytest.approx(10+(n-2)*.1+.01)
    assert f['relative_return']==pytest.approx(f['window_return']-((1000+n-1)/(1000+n-21)-1))
    assert f['mean_amount_cny']==20_000_000
    assert f['activity_ratio']==1
    split=s['features'][3]
    assert split['window_return']==pytest.approx(f['window_return'])
    assert split['ma']==pytest.approx(f['ma']/2)
    assert split['close']==pytest.approx(final/2)
    assert s['features'][4]['consecutive_sessions']==4
    assert s['features'][6]['consecutive_sessions']==30
    assert s['features'][7]['window_return'] is None
    assert s['market']['scope']=='观察池内，非全市场'
    assert any(c['code']==plan['universe'][0] for c in s['candidates'])
    assert any(e['code']==plan['universe'][1] for e in s['excluded'])
    st=next(c for c in s['candidates']+s['manual_cards'] if c['code']==plan['universe'][5])
    assert st['status']['st']=='YES' and st['trade_eligible'] is False
    normal=next(c for c in s['candidates'] if c['code']==plan['universe'][0])
    assert normal['status']['st']==normal['status']['suspended']=='UNKNOWN'
    second=ResearchStore(tmp_path/'rebuild'/'research.duckdb')
    assert second.import_bundle(bundle)==bid
    assert analyze(second,bid,ASOF,p,plan['universe'])==s
    from astock.reports.research import publish,markdown
    run=publish(s,dest/'reports')
    assert publish(s,dest/'reports')==run
    assert '非全市场' in markdown(s) and 'UNKNOWN' in markdown(s)
    _,rows=store.snapshot(bid,ASOF)
    assert rows['daily'][0]['volume']==1_000_000
    indices=[r for r in rows['instruments'] if r['kind']=='INDEX']
    assert all(r['exchange']=='UNKNOWN' and r['calendar_exchange']=='SSE' for r in indices)
    assert all(r['evidence_grade']=='SYNTHETIC' for r in indices)
    assert s['journal']['positions']==[]


def test_dry_run_and_missing_approval(tmp_path):
    path=tmp_path/'plan.json';path.write_bytes(encoded(fixture_plan()))
    dry=capture(tmp_path,path)
    assert dry['mode']=='DRY_RUN' and dry['market_requests']==0
    assert list(tmp_path.iterdir())==[path]
    with pytest.raises(ResearchError,match='HUMAN_APPROVAL_REQUIRED'):
        capture(tmp_path,path,live=True)


@pytest.mark.parametrize('failure',['permission','redirect','timeout','cap','fields','duplicate','future','ohlc','truncated','secret'])
def test_stop_and_resume_unattempted(tmp_path,failure):
    plan=fixture_plan()
    def handler(m,count):
        if count!=2:return httpx.Response(200,stream=BytesStream(encoded(response(plan,m))))
        if failure=='timeout':raise httpx.ReadTimeout('private details')
        if failure in {'permission','redirect'}:return httpx.Response(403 if failure=='permission' else 302)
        if failure=='cap':return httpx.Response(200,stream=BytesStream(b'x'*(plan['max_body_bytes']+1)))
        value=response(plan,m)
        if failure=='fields':value['data']['fields'].pop()
        elif failure=='duplicate':value['data']['items']*=2
        elif failure=='future':value['data']['items'][0][m['fields'].index('list_date')]='20990101'
        elif failure=='ohlc':value['code']=1  # provider refusal stops before price requests
        elif failure=='truncated':value['data']['has_more']=True
        elif failure=='secret':value['msg']='SYNTHETIC_TEST_TOKEN_12345'
        return httpx.Response(200,stream=BytesStream(encoded(value)))
    result,calls,dest=approved_mock(tmp_path,plan,handler)
    if failure=='future':
        # future listing identity must be rejected, rather than becoming current.
        assert result['stopped']=='FAILED'
    else:
        assert result['stopped'] in {'FAILED','UNKNOWN'}
    assert len(calls)==2 and result['unattempted']==37
    # A NEW matching mock approval resumes only the 37 never claimed requests.
    resumed,new_calls,_=approved_mock(tmp_path,plan)
    assert resumed['consumed_total']==39 and len(new_calls)==37
    assert all(c not in calls for c in new_calls)
    _,receipts=read_capture(dest)
    assert len(receipts)==38


@pytest.mark.parametrize('mutate',[lambda v:v['data']['items'].append(v['data']['items'][0]),
                                   lambda v:v['data']['fields'].pop(),
                                   lambda v:v['data'].update(has_more=True)])
def test_decoder_rejects_shape(mutate):
    plan=fixture_plan();m=next(m for m in plan['members'] if m['api']=='daily')
    v=response(plan,m);mutate(v)
    with pytest.raises(ResearchError):decode_response(encoded(v),m)


def test_status_sparse_and_conflict():
    row=dict(code='A',date='2026-10-12',st='UNKNOWN',suspended='UNKNOWN',up_limit=11,down_limit=9)
    result=merge_status([row,{**row,'st':'YES'}])
    assert result[('A','2026-10-12')]['st']=='YES'
    with pytest.raises(ResearchError,match='STATUS_SOURCE_CONFLICT'):
        merge_status([row,{**row,'up_limit':12}])


def test_late_sources_asof_and_stale(full_capture):
    plan,dest,bundle,store,bid,p=full_capture
    spec=read_json(bundle)
    daily=next(f for f in spec['files'] if f['dataset']=='daily')
    daily['available_at']='2026-10-14T20:00:00+08:00'
    late=dest/'late-bundle.json';late.write_bytes(encoded(spec))
    late_id=store.import_bundle(late)
    before=analyze(store,late_id,ASOF,p)
    assert before['candidates']==[] and all(f['close'] is None for f in before['features'])
    assert any('不可知' in s for s in before['limitations'])
    after=analyze(store,late_id,'2026-10-14T20:00:00+08:00',p)
    assert after['candidates']
    stale=analyze(store,bid,'2026-11-01T20:00:00+08:00',p)
    assert stale['candidates']==[] and all(any('陈旧' in x for x in e['reasons']) for e in stale['excluded'] if e['code']!=plan['universe'][4])


def test_response_cap_empty_status_and_invalid_price():
    plan=fixture_plan()
    st=next(m for m in plan['members'] if m['api']=='stock_st')
    value=response(plan,st);value['data']['items']=[]
    assert decode_response(encoded(value),st)==[]
    value['data']['items']=[[f'SYNTHETIC{i}','N','20261012','ST','warning'] for i in range(st['row_cap'])]
    with pytest.raises(ResearchError,match='PROVIDER_CAP_OR_TRUNCATION'):decode_response(encoded(value),st)
    daily=next(m for m in plan['members'] if m['api']=='daily')
    value=response(plan,daily)
    value['data']['items'][0][daily['fields'].index('low')]=-1
    from astock.research.acquisition import CapturePlan,payload_rows
    with pytest.raises(ResearchError,match='OHLC_RELATION'):
        payload_rows(CapturePlan.model_validate(plan),daily,encoded(value),ASOF)
    value=response(plan,daily)
    value['data']['items'][0][daily['fields'].index('trade_date')]='20990101'
    with pytest.raises(ResearchError,match='RESPONSE_DATE_OUTSIDE_REQUEST'):decode_response(encoded(value),daily)


def test_stranded_claim_is_never_resent(tmp_path):
    plan=fixture_plan()
    # Stop one call as UNKNOWN, remove only its SYNTHETIC terminal to model a
    # process dying between durable claim and terminal publication.
    def timeout(m,n):raise httpx.ReadTimeout('synthetic')
    result,calls,dest=approved_mock(tmp_path,plan,timeout)
    from astock.research.core import digest
    (dest/f'{digest(calls[0])}.result.json').unlink()
    resumed,new_calls,_=approved_mock(tmp_path,plan)
    assert resumed['consumed_total']==39 and calls[0] not in new_calls
    assert len(read_capture(dest)[1])==38


def test_holdings_original_thesis_correction_and_review(full_capture):
    from astock.research.journal import append_event,journal_snapshot
    plan,dest,bundle,store,bid,p=full_capture
    snapshot=analyze(store,bid,ASOF,p)
    report=store.save_report(snapshot)
    event=dict(event_id='manual-original',kind='POSITION',code=plan['universe'][0],event_at=ASOF,recorded_at=ASOF,
               shares=100,thesis='user original hypothesis',invalidation='user evidence reversal',exit_conditions='manual review',
               review_due='2026-10-14T20:00:00+08:00',research_report_id=report)
    path=dest/'event.json';path.write_bytes(encoded(event));append_event(store,path)
    update={**event,'event_id':'manual-update','event_at':'2026-10-15T20:00:00+08:00',
            'recorded_at':'2026-10-15T20:00:00+08:00','shares':200,'thesis':'updated thesis'}
    path.write_bytes(encoded(update));append_event(store,path)
    later=journal_snapshot(store,'2026-10-25T20:00:00+08:00',{})
    h=later['positions'][0]
    assert h['original_thesis']=='user original hypothesis' and h['thesis']=='updated thesis'
    assert h['research_stale'] and h['review_overdue'] and h['risk_plan'] is None
    assert h['exit_condition_state']=='PENDING_VERIFICATION' and h['confirmed'] is False
    assert later['pending_confirmation']==['manual-original','manual-update']
    correction={**update,'event_id':'manual-correction','correction_of':'manual-update',
                'recorded_at':'2026-10-16T20:00:00+08:00','shares':150,'confirmed':True}
    path.write_bytes(encoded(correction));append_event(store,path)
    assert journal_snapshot(store,'2026-10-15T21:00:00+08:00',{})['positions'][0]['shares']==200
    assert journal_snapshot(store,'2026-10-16T21:00:00+08:00',{})['positions'][0]['shares']==150
    incomplete=dict(event_id='no-thesis',kind='POSITION',code=plan['universe'][1],event_at=ASOF,recorded_at=ASOF,shares=10)
    path.write_bytes(encoded(incomplete));append_event(store,path)
    h=next(h for h in journal_snapshot(store,ASOF,{})['positions'] if h['code']==plan['universe'][1])
    assert h['original_thesis'] is None and any('原始逻辑' in g for g in h['gaps'])


def test_capture_cli_and_pipeline(full_capture,monkeypatch):
    from astock.cli.main import app
    from astock.cli import research as cli
    plan,dest,bundle,store,bid,p=full_capture
    root=dest.parents[3]
    monkeypatch.setattr(cli,'get_project_root',lambda:root)
    runner=CliRunner()
    result=runner.invoke(app,['research','capture'])
    assert result.exit_code==0 and 'DRY_RUN' in result.stdout and 'market_requests' in result.stdout
    result=runner.invoke(app,['research','capture','--live'])
    assert result.exit_code==1
    result=runner.invoke(app,['research','capture-import','--capture-dir',str(dest)])
    assert result.exit_code==0 and bid in result.stdout
    result=runner.invoke(app,['research','report','--store',str(store.path),'--bundle',bid,'--as-of',ASOF,
                             '--output',str(dest/'reports')])
    assert result.exit_code==0 and 'OBSERVATION_ONLY' in result.stdout


@pytest.mark.parametrize('change',[lambda a:a.update(plan_hash='0'*64),lambda a:a.update(fixture_only=False),
                                  lambda a:a.update(member_ids=[]),lambda a:a.update(implementation_hash='0'*64),
                                  lambda a:a.update(expires_at='2026-10-12T00:00:00+00:00')])
def test_approval_mismatch_makes_zero_calls(tmp_path,change):
    from research_fixture import CAPTURED
    from astock.research.core import code_fingerprint,digest
    from astock.research.acquisition import capture
    from pydantic import SecretStr
    plan=fixture_plan();p=tmp_path/'plan.json';p.write_bytes(encoded(plan))
    a=dict(protocol='RESEARCH_CAPTURE_APPROVAL_V1_1',plan_hash=digest(plan),destination=str((tmp_path/plan['destination']).resolve()),
           implementation_hash=implementation_hash(),authorized_by='SYNTHETIC_TEST',approved_at='2026-10-13T00:00:00+00:00',
           expires_at='2026-10-14T00:00:00+00:00',member_ids=[digest(m) for m in plan['members']],fixture_only=True,execution_authorized=True)
    change(a);approval=tmp_path/'approval.json';approval.write_bytes(encoded(a))
    calls=[]
    def handler(req):calls.append(req);raise AssertionError('must not send')
    with pytest.raises(ResearchError):capture(tmp_path,p,live=True,approval_file=approval,transport=httpx.MockTransport(handler),
                                            token=SecretStr('test'),now=lambda:CAPTURED,sleep=lambda _:None)
    assert calls==[]


def test_database_key_tamper_rejected(full_capture):
    from astock.data.warehouse_lock import warehouse_connection
    plan,dest,bundle,store,bid,p=full_capture
    with warehouse_connection(store.path) as db:
        key=db.execute("SELECT record_key FROM research_observation WHERE dataset='daily' LIMIT 1").fetchone()[0]
        db.execute("UPDATE research_observation SET record_key='tampered' WHERE record_key=? AND dataset='daily'",[key])
    with pytest.raises(ResearchError,match='STORED_OBSERVATIONS_CHANGED'):
        analyze(store,bid,ASOF,p)


def test_conflict_and_calendar_mismatch_before_store(full_capture):
    from astock.research.inputs import load_bundle
    plan,dest,bundle,store,bid,p=full_capture
    b=read_json(bundle)
    f=next(f for f in b['files'] if f['request']['api']=='stk_limit')
    raw=read_json(Path(f['path']))
    raw['data']['items'][0][f['request']['fields'].index('up_limit')]=999
    changed=dest/'conflicting.json';changed.write_bytes(encoded(raw))
    b['files'].append({**f,'path':str(changed),'sha256':hashlib.sha256(changed.read_bytes()).hexdigest()})
    m=dest/'conflict-bundle.json';m.write_bytes(encoded(b))
    with pytest.raises(ResearchError,match='STATUS_SOURCE_CONFLICT'):
        load_bundle(m)
    b=read_json(bundle)
    f=next(f for f in b['files'] if f['request']['api']=='trade_cal' and f['request']['params']['exchange']=='SZSE')
    raw=read_json(Path(f['path']))
    # Changing an explicit weekend to open produces unequal cross-market calendar evidence.
    raw['data']['items'][3][f['request']['fields'].index('is_open')]=1
    changed=dest/'calendar-mismatch.json';changed.write_bytes(encoded(raw))
    f.update(path=str(changed),sha256=hashlib.sha256(changed.read_bytes()).hexdigest())
    m.write_bytes(encoded(b))
    with pytest.raises(ResearchError,match='BENCHMARK_CALENDAR_DISAGREEMENT'):load_bundle(m)


def test_partial_capture_then_additive_bundle_recovery(tmp_path):
    plan=fixture_plan()
    def handler(m,n):
        if n==36:return httpx.Response(403)
        return httpx.Response(200,stream=BytesStream(encoded(response(plan,m))))
    result,calls,dest=approved_mock(tmp_path,plan,handler)
    assert result['complete_this_run']==35
    first=make_capture_bundle(dest)
    from astock.research.core import digest
    first_path=dest/f'{digest(first)}.bundle.json'
    original=first_path.read_bytes()
    _,new_calls,_=approved_mock(tmp_path,plan)
    assert len(new_calls)==3
    second=make_capture_bundle(dest)
    assert first!=second and first_path.read_bytes()==original
    assert (dest/f'{digest(second)}.bundle.json').is_file()


def test_incomplete_capture_does_not_publish_invalid_bundle(tmp_path):
    plan=fixture_plan()
    def handler(m,n):
        if n==2:return httpx.Response(403)
        return httpx.Response(200,stream=BytesStream(encoded(response(plan,m))))
    _,_,dest=approved_mock(tmp_path,plan,handler)
    with pytest.raises(ResearchError,match='IDENTITY_EVIDENCE_REQUIRED'):
        make_capture_bundle(dest)
    assert not list(dest.glob('*.bundle.json'))
