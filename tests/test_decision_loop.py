"""Business counterexamples: changes/unknown/time, account scope and immutable review history."""
from copy import deepcopy
from pathlib import Path

import pytest

from astock.company.models import ResearchCatalog
from astock.decision.models import RunInput, PositionScope
from astock.decision.workflow import compare, persist
from astock.decision.portfolio import portfolio_report
from astock.decision.report import public_projection, publish_public
from astock.research.core import digest, encoded
from astock.research.journal import append_event, journal_snapshot
from astock.research.store import ResearchStore
from test_company_research import catalog_input


def inputs():
    raw=catalog_input();raw['companies'][0]['code']='600036.SH';raw['sources'][0]['code']='600036.SH'
    previous=ResearchCatalog.model_validate(raw)
    newer=deepcopy(raw);newer['as_of']='2026-10-14T02:00:00+00:00'
    latest=ResearchCatalog.model_validate(newer)
    plan=dict(code='600036.SH',baseline_catalog_hash=digest(previous.model_dump(mode='json')),
              baseline_market_hash='a'*64,baseline_market_date='2026-10-12',baseline_market_bundle_id='b',
              thesis='合成研究逻辑',attention_reason='测试',no_trade_reasons=['未核实估值'],
              observable_checks=['核对下一份收入原表'],invalidation_conditions=['收入逻辑被推翻'],
              criteria=[dict(id='growth',metric_id='revenue',expectation='NOT_LOWER',reason='收入检查',failure='INVALIDATION_REVIEW')],
              created_at='2026-10-14T01:30:00+00:00',review_due='2026-10-15T00:00:00+00:00')
    run=dict(protocol='DECISION_LOOP_V0',mode='REAL_EVIDENCE',observed_at='2026-10-14T03:00:00+00:00',required_market_date='2026-10-13',plans=[plan])
    market=dict(bundle_id='b',as_of='2026-10-14T01:00:00+00:00',window_end='2026-10-12',
                features=[dict(code='600036.SH',name='合成公司',close=10,last_date='2026-10-12')],
                radar={'market':{'metrics':{}},'industries':[]})
    plan['baseline_market_hash']=digest(market)
    return raw,previous,latest,run,market


def report():
    _,old,new,run,market=inputs()
    return compare(RunInput.model_validate(run),old,new,market,[dict(code='600036.SH',industry_code='BANK')])


def add(store,tmp_path,**changes):
    event=dict(event_id='p1',kind='POSITION',code='600036.SH',event_at='2026-10-14T01:00:00+00:00',
               recorded_at='2026-10-14T01:00:00+00:00',shares=100,confirmed=False,notes='synthetic')
    event.update(changes);path=tmp_path/(event['event_id']+'.json');path.write_bytes(encoded(event));append_event(store,path)


def test_same_evidence_support_is_not_new_disclosure_or_trade():
    result=report();card=result['cards'][0]
    assert card['state']=='CONTINUE_WATCH' and card['no_new_disclosures']
    assert not card['trade_eligible'] and not result['market_fresh']
    assert card['previous_research']==card['latest_research']
    assert card['risk_budget'] is None and card['sources']==card['previous_sources']


def test_changed_fact_preserves_before_after_and_invalidation_is_not_sell():
    raw,old,new,run,market=inputs()
    raw['as_of']=new.as_of;raw['companies'][0]['financials'][0]['value']='80'
    raw['companies'][0]['financials'][0]['reported_change_percent']='-20'
    new=ResearchCatalog.model_validate(raw)
    result=compare(RunInput.model_validate(run),old,new,market)
    card=result['cards'][0]
    assert card['state']=='INVALIDATION_REVIEW' and card['order'] is None
    assert card['evidence_changes'][0]['previous']['value']=='120'
    assert card['evidence_changes'][0]['latest']['value']=='80'
    assert old.companies[0].financials[0].value==120


@pytest.mark.parametrize('mutation',['missing','unit','period','basis'])
def test_unknown_and_incomparable_do_not_assert_logic_or_failure(mutation):
    raw,old,new,run,market=inputs();f=raw['companies'][0]['financials'][0]
    if mutation=='missing':f.update(value=None,comparison_value=None,reported_change_percent=None)
    if mutation=='unit':f['unit']='CNY_MILLION'
    if mutation=='period':f.update(period_end='2026-03-31',comparison_period_end='2025-03-31')
    if mutation=='basis':f['accounting_basis']='ASBE_PARENT'
    raw['as_of']=new.as_of
    card=compare(RunInput.model_validate(run),old,ResearchCatalog.model_validate(raw),market)['cards'][0]
    assert card['state']=='WAIT_EVIDENCE' and card['hypothesis_state']=='UNKNOWN'


def test_source_version_changed_even_with_same_numbers():
    raw,old,new,run,market=inputs();raw['sources'][0]['sha256']='f'*64;raw['as_of']=new.as_of
    card=compare(RunInput.model_validate(run),old,ResearchCatalog.model_validate(raw),market)['cards'][0]
    assert card['evidence_changes'][0]['type']=='SOURCE_VERSION'
    assert card['previous_sources'][0]['sha256']!=card['sources'][0]['sha256']


def test_future_research_market_and_baseline_binding_rejected():
    raw,old,new,run,market=inputs();bad=deepcopy(run);bad['plans'][0]['baseline_catalog_hash']='f'*64
    with pytest.raises(ValueError,match='DECISION_BASELINE_CHANGED'):compare(RunInput.model_validate(bad),old,new,market)
    raw['as_of']='2026-10-16T00:00:00+00:00'
    with pytest.raises(ValueError,match='DECISION_RESEARCH_TIME'):compare(RunInput.model_validate(run),old,ResearchCatalog.model_validate(raw),market)
    market['as_of']='2026-10-15T00:00:00+00:00'
    with pytest.raises(ValueError,match='DECISION_MARKET_TIME'):compare(RunInput.model_validate(run),old,new,market)


def test_simulated_events_and_end_watch_are_explicit():
    _,old,new,run,market=inputs()
    event=dict(code='600036.SH',criterion_id='growth',state='UNKNOWN',explanation='合成缺证据',available_at=run['observed_at'],provenance='OFFLINE_SIMULATION_NOT_DISCLOSURE')
    run['simulation_events']=[event]
    with pytest.raises(ValueError,match='DECISION_SIMULATION_IN_REAL'):RunInput.model_validate(run)
    run['mode']='OFFLINE_SIMULATION'
    r=compare(RunInput.model_validate(run),old,new,market)
    assert r['cards'][0]['state']=='WAIT_EVIDENCE' and r['cards'][0]['checks'][0]['evidence_class']=='OFFLINE_SIMULATION_NOT_DISCLOSURE'
    run['review_actions']=[dict(code='600036.SH',action='END_WATCH',reason='离线演练退出研究',recorded_at=run['observed_at'],confirmed=True,provenance='OFFLINE_SIMULATION_NOT_USER_ACTION')]
    assert compare(RunInput.model_validate(run),old,new,market)['cards'][0]['state']=='END_WATCH'
    run['simulation_events'][0]['available_at']='2026-10-16T00:00:00+00:00'
    with pytest.raises(ValueError,match='DECISION_FUTURE_EVENT'):RunInput.model_validate(run)


def test_due_review_and_plan_review_events_idempotent_no_original_write(tmp_path):
    r=report();r['as_of']='2026-10-16T00:00:00+00:00'
    store=ResearchStore(tmp_path/'loop.duckdb');before=deepcopy(r)
    key=persist(r,store,tmp_path/'events');assert persist(r,store,tmp_path/'events')==key
    snapshot=journal_snapshot(store,r['as_of'],{})
    assert [e['kind'] for e in snapshot['events']]==['PLAN','REVIEW']
    assert all(not e['confirmed'] for e in snapshot['events'])
    r['window_end']='2026-10-13';r['as_of']='2026-10-17T00:00:00+00:00';persist(r,store,tmp_path/'events')
    assert [e['kind'] for e in journal_snapshot(store,r['as_of'],{})['events']].count('PLAN')==1
    assert before['window_end']=='2026-10-12'
    assert r['cards'][0]['previous_observation']['as_of']=='2026-10-16T00:00:00+00:00'
    assert r['cards'][0]['changes_since_prior']==[]


def test_missing_account_never_means_empty_even_if_position_events_exist(tmp_path):
    store=ResearchStore(tmp_path/'loop.duckdb');store.initialize();_,_,_,_,market=inputs()
    assert portfolio_report(store,market,report(),None)['positions_state']=='UNKNOWN_NOT_EMPTY'
    add(store,tmp_path)
    assert portfolio_report(store,market,report(),None)['positions_state']=='UNKNOWN_NOT_EMPTY'


def test_partial_cash_unknown_and_stale_prices_do_not_invent_account_weights(tmp_path):
    store=ResearchStore(tmp_path/'loop.duckdb');add(store,tmp_path)
    _,_,_,_,market=inputs()
    scope=PositionScope(mode='SIMULATED',snapshot_at='2026-10-14T01:30:00+00:00',position_event_ids=['p1'])
    result=portfolio_report(store,market,report(),scope)
    assert result['mode']=='SIMULATED' and result['reported_stock_value_cny']=='1000'
    assert result['account_assets_cny'] is None and result['account_weights'] is None
    assert result['industry_exposure']['BANK']['reported_stock_value_share']=='1'
    assert not result['positions'][0]['confirmed'] and not result['positions'][0]['price_fresh']


def test_complete_confirmed_manual_snapshot_weights_require_cash_and_fresh_price(tmp_path):
    store=ResearchStore(tmp_path/'loop.duckdb');add(store,tmp_path,confirmed=True)
    _,_,_,_,market=inputs();market['features'][0]['last_date']='2026-10-13'
    scope=PositionScope(mode='USER_MANUAL',snapshot_at='2026-10-14T01:30:00+00:00',position_event_ids=['p1'],complete_positions_confirmed=True,cash_cny=1000,cash_confirmed=True)
    result=portfolio_report(store,market,report(),scope)
    assert result['account_assets_cny']=='2000' and result['account_weights']['600036.SH']=='0.5'
    assert result['risk_parameters'] is None and result['order'] is None
    scope.position_event_ids=[]
    with pytest.raises(ValueError,match='PORTFOLIO_SCOPE_EVENTS'):portfolio_report(store,market,report(),scope)


def test_missing_price_prevents_subset_renormalization(tmp_path):
    store=ResearchStore(tmp_path/'loop.duckdb');add(store,tmp_path);add(store,tmp_path,event_id='p2',code='000002.SZ')
    _,_,_,_,market=inputs();scope=PositionScope(mode='SIMULATED',snapshot_at='2026-10-14T01:30:00+00:00',position_event_ids=['p1','p2'])
    r=portfolio_report(store,market,report(),scope)
    assert r['reported_stock_value_cny'] is None and all(p['reported_stock_value_share'] is None for p in r['positions'])


def test_public_projection_excludes_private_holdings_actions_and_notes(tmp_path):
    r=report();r['portfolio']={'account_id':'secret-account','cash_cny':123,'positions':[{'notes':'private'}]}
    r['cards'][0]['manual_action']={'reason':'private reason'}
    public=public_projection(r)
    assert b'secret-account' not in encoded(public) and 'portfolio' not in public
    assert 'manual_action' not in public['cards'][0]
    r['cards'][0]['next_actions']=['/Users/private-account']
    assert b'/Users/' not in encoded(public_projection(r))
    r['cards'][0]['sources'][0]['title']='/Users/private-account'
    assert b'/Users/' not in encoded(public_projection(r))
    r['cards'][0]['checks'][0]['latest']['reference']['locator']='/Users/private-account'
    with pytest.raises(ValueError,match='DECISION_PUBLIC_PRIVATE_TEXT'):public_projection(r)


def test_due_and_material_risk_are_review_not_automatic_orders():
    _,old,new,run,market=inputs();run['observed_at']='2026-10-16T00:00:00+00:00'
    run['plans'][0]['unresolved_material_risk']='合成未决债务风险'
    r=compare(RunInput.model_validate(run),old,new,market)['cards'][0]
    assert r['state']=='WAIT_EVIDENCE' and r['review_overdue'] and r['order'] is None


def test_new_announcement_requires_evidence_bound_manual_acknowledgement():
    raw,old,new,run,market=inputs();raw['as_of']=new.as_of
    raw['companies'][0]['events']=[dict(id='announcement',kind='FACT',text='合成新风险公告',references=[dict(source_id='s1',locator='第2页')])]
    latest=ResearchCatalog.model_validate(raw)
    assert compare(RunInput.model_validate(run),old,latest,market)['cards'][0]['state']=='WAIT_EVIDENCE'
    run['review_actions']=[dict(code='600036.SH',action='ACKNOWLEDGE_CHANGED_EVIDENCE',reason='合成人工已核对，仍不交易',recorded_at=run['observed_at'],confirmed=True,provenance='USER_MANUAL',evidence_hashes=[])]
    with pytest.raises(ValueError,match='DECISION_ACKNOWLEDGEMENT_SOURCE_BINDING'):compare(RunInput.model_validate(run),old,latest,market)
    run['review_actions'][0]['evidence_hashes']=[latest.sources[0].sha256]
    card=compare(RunInput.model_validate(run),old,latest,market)['cards'][0]
    assert card['state']=='CONTINUE_WATCH' and not card['trade_eligible']


@pytest.mark.parametrize('counterexample',['account_mode','future_real_observation'])
def test_close_cli_rejects_invalid_real_observation_before_events(tmp_path,monkeypatch,counterexample):
    from typer.testing import CliRunner
    from astock.cli.main import app
    import astock.cli.research as cli
    import astock.decision.increment as increments
    import astock.company.workflow as company
    raw,old,new,run,market=inputs()
    if counterexample=='future_real_observation':run['observed_at']='2999-10-14T03:00:00+00:00'
    monkeypatch.setattr(cli,'get_project_root',lambda:tmp_path)
    monkeypatch.setattr(increments,'market_context',lambda *a,**kw:(market,[]))
    monkeypatch.setattr(company,'verified_market_context',lambda *a:[])
    documents=tmp_path/'data/private/research-v3/test';documents.mkdir(parents=True)
    (documents/'s1.pdf').write_bytes(b'%PDF-mock')
    files={}
    for name,value in [('run',run),('old',old.model_dump(mode='json')),('new',new.model_dump(mode='json')),('market',market)]:
        path=tmp_path/(name+'.json');path.write_bytes(encoded(value));files[name]=path
    scope=tmp_path/'data/private/research-v1/scope.json';scope.parent.mkdir(parents=True,exist_ok=True)
    scope.write_bytes(encoded(dict(mode='SIMULATED',snapshot_at=run['observed_at'],position_event_ids=[])))
    journal=tmp_path/'data/private/research-v1/decision-loop-v0/real/journal.duckdb'
    args=['research','decision-close','--run',str(files['run']),'--previous',str(files['old']),'--latest',str(files['new']),
          '--documents',str(documents),'--baseline-market',str(files['market']),'--bundle','b',
          '--store',str(tmp_path/'data/private/research-v1/test.duckdb'),'--journal-store',str(journal),
          '--output',str(tmp_path/'reports/private/research-v1/test'),'--position-scope',str(scope)]
    result=CliRunner().invoke(app,args)
    assert result.exit_code==1 and 'private details suppressed' in result.output and not journal.exists()
