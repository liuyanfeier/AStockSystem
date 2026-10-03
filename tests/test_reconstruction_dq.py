from datetime import date,timedelta
from pathlib import Path
from uuid import uuid4
import pytest
from astock.data.reconstruction_dq import (load_policy,coverage_observation,reference_check,bse_transition,
    venue_causal_audit,session_basis,local_status,batch_status)
from astock.data.provider_identity import ProviderResolver
from test_provider_identity import fixture,resolve
from test_slice_dq import bar

ROOT=Path(__file__).parents[1];DAY=date(2025,4,30)


def test_frozen_policy_hash_and_tolerance():
    p,h=load_policy(ROOT)
    assert len(h)==64 and p['price_tolerance']==p['causal_tolerance_percentage_points']==0.011
    assert p['null_imputation'] is False


def test_observed_bar_not_hidden_by_delist_metadata():
    e,_,_=fixture();e=e.model_copy(update={'provider_delist_date':DAY})
    r=coverage_observation(e,dataset='daily',event_date=DAY,bar_observed=True,suspensions=[],session='CERTIFIED')
    assert r['observation']=='OBSERVED_BAR' and r['disposition']=='VERIFIED_IN_SCOPE'
    assert r['findings'][0]['rule']=='UNCLASSIFIED_DELIST_METADATA'
    assert not r['findings'][0]['blocking']


def test_termination_conflict_not_last_trading_plus_one():
    e,_,_=fixture();e=e.model_copy(update={'last_trading_date':DAY-timedelta(days=10),'valid_to':DAY})
    r=coverage_observation(e,dataset='daily',event_date=DAY,bar_observed=True,suspensions=[],session='CERTIFIED')
    assert r['observation']=='OBSERVED_BAR' and r['disposition']=='CONFLICT' and r['batch_gate_status']=='BLOCKED'
    r=coverage_observation(e,dataset='daily',event_date=DAY-timedelta(days=1),bar_observed=True,suspensions=[],session='CERTIFIED')
    assert r['disposition']=='VERIFIED_IN_SCOPE'


@pytest.mark.parametrize('susp,explained',[
    ([{'suspend_type':'S','suspend_timing':'全天'}],True),
    ([{'suspend_type':'S','suspend_timing':None,'whole_day_certified':True}],True),
    ([{'suspend_type':'S','suspend_timing':None}],False),
    ([{'suspend_type':'S','suspend_timing':'09:30-10:00'}],False),
    ([{'suspend_type':'S','suspend_timing':'全天'},{'suspend_type':'R'}],False)])
def test_full_day_suspension_needs_evidence_and_no_sr_conflict(susp,explained):
    e,_,_=fixture();r=coverage_observation(e,dataset='daily',event_date=DAY,bar_observed=False,suspensions=susp,session='CERTIFIED')
    assert (r['disposition']=='EXPLAINED_FULL_DAY_SUSPENSION') is explained


def test_survivorship_no_current_list_and_identity_repair_observation():
    e,_,_=fixture();e=e.model_copy(update={'provider_delist_date':date(2026,1,1)})
    before=coverage_observation(e,dataset='daily',event_date=DAY,bar_observed=False,suspensions=[],session='CERTIFIED')
    after=coverage_observation(e,dataset='daily',event_date=DAY,bar_observed=True,suspensions=[],session='CERTIFIED')
    assert before['universe_basis']=='HISTORICAL_EPISODE' and before['batch_gate_status']=='BLOCKED'
    assert after['local_status']=='PASS'


def test_null_not_imputed_and_exception_exact_negative_scopes():
    args=dict(dataset='stk_limit',event_date=DAY,raw_object_id=str(uuid4()),raw_row_number=0,episode_id=str(uuid4()))
    assert reference_check(10,None,**args)[0]['rule']=='MISSING_REFERENCE_PRICE'
    exception=dict(**args,field='pre_close',decision='APPROVED_NOT_APPLICABLE',approval_ref='synthetic-review',evidence_ids=['synthetic-product'])
    assert reference_check(10,None,**args,approved_exceptions=[exception])[0]['rule']=='REFERENCE_NOT_APPLICABLE'
    for key,value in [('event_date',DAY-timedelta(days=1)),('raw_row_number',1),('dataset','daily'),('episode_id',str(uuid4()))]:
        bad={**exception,key:value}
        assert reference_check(10,None,**args,approved_exceptions=[bad])[0]['blocking']
    assert reference_check(10,10.02,**args)[0]['rule']=='NUMERIC_REFERENCE_MISMATCH'
    assert reference_check(10,10.01,**args)==[]


def test_unknown_bse_session_and_retrospective_native_transition():
    e,c,b=fixture();left=resolve(ProviderResolver([e],c,[b]),b)
    bo=b.model_copy(update={'binding_id':uuid4(),'observations':(b.observations[0].model_copy(update={'event_date':date(2025,5,6)}),)})
    right=resolve(ProviderResolver([e],c,[bo]),bo)
    r=bse_transition(left,right,old_code='830001.BJ',new_code='920001.BJ',switch_date=date(2025,5,6),episode_id=e.episode_id,sessions_certified=False)
    assert r['official']==r['provider']==r['continuity']=='VALID' and r['session']=='NOT_CERTIFIED'
    assert batch_status(r['findings'])=='BLOCKED'
    missing=bse_transition(None,right,old_code='830001.BJ',new_code='920001.BJ',switch_date=date(2025,5,6),episode_id=e.episode_id,sessions_certified=False)
    assert missing['continuity']=='NOT_OBSERVED'


def test_venue_calendar_cannot_inherit_sse_certification():
    ep=str(uuid4());next_day=date(2025,5,6)
    sessions={('BSE',ep,next_day):dict(previous_session=DAY,certified=True,evidence_venue='SSE',evidence_ref='wrong-venue')}
    assert session_basis(venue='BSE',episode_id=ep,event_date=next_day,sessions=sessions)==('NOT_CERTIFIED',None)
    sessions[('SSE_DIAGNOSTIC',ep,next_day)]=dict(previous_session=DAY)
    assert session_basis(venue='BSE',episode_id=ep,event_date=next_day,sessions=sessions)[0]=='PROVISIONAL_SSE_BASIS'


def test_causal_prefix_keeps_method_and_resets_cross_episode_unknown_sessions():
    ep=str(uuid4());d2=date(2025,5,6);d3=date(2025,5,7)
    rows=[dict(**bar(DAY,10,10,0),episode_id=ep,venue='SSE'),dict(**bar(d2,5.5,5,10),episode_id=ep,venue='SSE')]
    sessions={('SSE',ep,d2):dict(previous_session=DAY,certified=True,evidence_venue='SSE',evidence_ref='synthetic-capture')}
    factors={('synthetic',ep,DAY):1,('synthetic',ep,d2):2}
    stats,prefix=venue_causal_audit(rows,factors,sessions)
    assert stats['certified_pairs']==1 and stats['causal_mismatch']==stats['factor_mismatch']==0
    extra=dict(**bar(d3,2.2,2.2,0),episode_id=ep,venue='SSE')
    stats,extended=venue_causal_audit([*rows,extra],{**factors,('synthetic',ep,d3):99},sessions)
    assert extended[:2]==prefix and stats['excluded_unknown_pairs']==1
    other=rows[1].copy();other['episode_id']=str(uuid4())
    assert venue_causal_audit([rows[0],other],factors,sessions)[0]['certified_pairs']==0


def test_local_pass_can_coexist_with_batch_blocked():
    assert local_status([])=='PASS'
    assert batch_status([{'blocking':True,'severity':'REVIEW'}])=='BLOCKED'
