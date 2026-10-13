from copy import deepcopy
import json
from pathlib import Path
import httpx
import pytest
from typer.testing import CliRunner
from astock.cli.main import app
from astock.features.market import ObservationParameters
from astock.research.core import ResearchError, digest, encoded, read_json
from astock.research.inputs import load_bundle
from astock.research.market_capture import MarketCapturePlan
from astock.research.public_results import publish_public, public_snapshot
from astock.research.service import analyze
from astock.research.store import ResearchStore
from astock.research.tushare import decode_response, make_capture_bundle, market_member, validate_member
from astock.reports.research import markdown
from research_fixture import approved_mock, BytesStream, ASOF, rebind_synthetic_raw
from market_fixture import plan, response


@pytest.fixture(scope='module')
def market(tmp_path_factory):
    root=tmp_path_factory.mktemp('v2-market')
    p=plan()
    result,calls,destination=approved_mock(root,p,lambda m,n:httpx.Response(200,stream=BytesStream(encoded(response(p,m)))))
    assert len(calls)==299 and result['complete_this_run']==299,result
    manifest=make_capture_bundle(destination)
    path=destination/f'{digest(manifest)}.bundle.json'
    store=ResearchStore(destination/'research.duckdb')
    bid=store.import_bundle(path)
    parameters=ObservationParameters.model_validate(read_json(Path('config/research/observation-v1.json')))
    report=analyze(store,bid,ASOF,parameters,radar=True)
    return root,destination,store,bid,manifest,report,parameters


def test_market_end_to_end_independent_numbers(market):
    root,destination,store,bid,m,r,p=market
    assert len(m['universe'])==10
    f={s['code']:s for s in r['features']}
    # Normalized corporate-action series goes 20.0 -> 32.7, even after a 2-for-1 split.
    assert f['SYNTHETIC-3']['return_20']==pytest.approx(32.7/30.7-1)
    assert f['SYNTHETIC-3']['ma60']==pytest.approx(sum(20+i*.1 for i in range(68,128))/60/2)
    assert f['SYNTHETIC-3']['return_5']==pytest.approx(32.7/32.2-1)
    assert f['SYNTHETIC-8']['above_ma60'] is None
    assert f['SYNTHETIC-8']['expected_sessions']<60
    assert f['SYNTHETIC-7']['return_20'] is None
    assert f['SYNTHETIC-6']['consecutive_sessions']==4
    assert f['SYNTHETIC-4']['exchange']=='BSE'
    assert f['SYNTHETIC-4']['calendar_basis'].startswith('Tushare doc26')
    metric=r['radar']['market']['metrics']
    assert metric['return_1']['denominator']==9
    assert metric['return_1']['up']==6 and metric['return_1']['down']==2 and metric['return_1']['flat']==1
    assert metric['above_ma60']['denominator']==7
    assert metric['above_ma60']['count']==4
    assert len(r['radar']['boards'])==5
    assert r['radar']['industry_coverage']['classified_current_pool']==10
    bank=next(i for i in r['radar']['industries'] if i['code']=='801780.SI')
    assert bank['candidate_count']==4 and bank['candidate_pool_share']==1
    assert bank['breadth']['pool_count']==4 and bank['diffusion']=='BROAD'
    assert bank['breadth']['metrics']['return_20_distribution']['median']==pytest.approx(32.7/30.7-1)
    assert bank['statistic_basis'].startswith('个股等权')
    assert all(any('共同风险' in x for x in c['counter_evidence']) for c in r['candidates'])
    assert all(c['trade_eligible'] is False and c['risk_budget'] is None for c in r['candidates'])
    assert analyze(ResearchStore(store.path),bid,ASOF,p,radar=True)==r
    assert markdown(r).startswith('# AStockSystem 每日市场与行业雷达')
    assert '合成软件演示' in markdown(r)


def test_every_denominator_and_top_limit(market):
    _,_,store,bid,_,r,p=market
    b=r['radar']['market'];n=b['pool_count']
    for name,v in b['metrics'].items():
        assert v['denominator']+v['excluded']==n
        if name in ('return_1','return_5','return_20'):assert v['up']+v['down']+v['flat']==v['denominator']
    limited=analyze(store,bid,ASOF,p.model_copy(update={'top_n':2}),radar=True)
    assert limited['radar']['candidate_tracking']['eligible_total']==4
    assert limited['radar']['candidate_tracking']['omitted']==2
    assert next(i for i in limited['radar']['industries'] if i['code']=='801780.SI')['candidate_count']==4


@pytest.mark.parametrize('mutation,code',[
    (lambda p:p.update(markets=['SSE','SZSE']), 'MARKET_PLAN_EXCHANGES'),
    (lambda p:p['members'][0]['params'].update(list_status='D'), 'CURRENT_POOL_REQUEST'),
    (lambda p:p['members'][6]['params'].update(is_new='N'), 'INDUSTRY_CURRENT_MEMBERS'),
    (lambda p:p['members'][5]['params'].update(src='SW2014'), 'INDUSTRY_VERSION'),
    (lambda p:p['members'][41]['params'].update(ts_code='MADE_UP'), 'MARKET_DAY_BATCH_REQUIRED'),
    (lambda p:p.update(universe=['GUESSED_STOCK']), None),
])
def test_plan_scope_refuses_expansion(mutation,code):
    p=plan();mutation(p)
    with pytest.raises(ValueError,match=code):MarketCapturePlan.model_validate(p)


@pytest.mark.parametrize('kind', ['has_more','cap','duplicate','outside','status','currency','classification','membership'])
def test_response_contract_and_pool_quality(kind):
    p=plan()
    m=next(m for m in p['members'] if m['api']==('index_classify' if kind=='classification' else 'index_member_all' if kind=='membership' else 'stock_basic'))
    body=response(p,m)
    data=body['data']
    if kind=='has_more':data['has_more']=True
    elif kind=='cap':data['items']=[data['items'][0]]*m['row_cap']
    elif kind=='duplicate':data['items']+=data['items'][:1]
    elif kind=='outside':data['items'][0][data['fields'].index('exchange')]='SZSE'
    elif kind=='status':data['items'][0][data['fields'].index('list_status')]='D'
    elif kind=='currency':data['items'][0][data['fields'].index('curr_type')]='USD'
    elif kind=='classification':data['items'][0][data['fields'].index('src')]='SW2014'
    elif kind=='membership':
        assert data['items']
        data['items'][0][data['fields'].index('is_new')]='N'
    if kind=='currency':
        from astock.research.acquisition import payload_rows
        with pytest.raises(ResearchError,match='CURRENT_POOL_IDENTITY'):payload_rows(MarketCapturePlan.model_validate(p),m,encoded(body),ASOF)
    else:
        with pytest.raises(ResearchError):decode_response(encoded(body),m)


def test_current_pool_grade_and_forged_scope_rejected(market,tmp_path):
    _,_,_,_,original,_,_=market
    m=deepcopy(original)
    m['universe']=m['universe'][:-1]
    with pytest.raises(ResearchError,match='CURRENT_POOL_UNIVERSE_CHANGED'):load_bundle(tmp_path/'bundle.json',m)
    m=deepcopy(original)
    f=next(f for f in m['files'] if f['request']['api']=='stock_basic')
    f['evidence_grade']='USER_DECLARED';f['evidence']=[]
    with pytest.raises(ResearchError,match='CURRENT_POOL_CAPTURE_REQUIRED'):load_bundle(tmp_path/'bundle.json',m)
    m=deepcopy(original)
    m['bse_calendar_reference']='UNKNOWN'
    with pytest.raises(ResearchError,match='CAPTURE_SCOPE_BINDING'):load_bundle(tmp_path/'bundle.json',m)


def test_asof_filters_identity_and_industry(market):
    _,_,store,bid,_,_,p=market
    early=analyze(store,bid,'2026-10-13T00:01:00+08:00',p,radar=True)
    assert early['radar']['scope']=='CURRENT_POOL_WITH_GAPS'
    assert early['radar']['market']['metrics']['return_1']['denominator']==0
    assert not early['radar']['industries']


def test_public_whitelist_and_cli(market,monkeypatch,tmp_path):
    root,_,store,bid,_,report,_=market
    fake=deepcopy(report)
    fake['journal']['positions']=[dict(code='PRIVATE_ACCOUNT_SECURITY',shares=12345678,thesis='PRIVATE_NOTE')]
    published=public_snapshot(fake)
    body=encoded(published)
    assert b'PRIVATE_NOTE' not in body and b'PRIVATE_ACCOUNT_SECURITY' not in body and b'/Users/' not in body
    assert all('path' not in f and 'evidence' not in f for f in published['sources'])
    assert publish_public(fake,tmp_path,Path('docs/research/results/test'))
    with pytest.raises(ResearchError):publish_public(fake,tmp_path,Path('reports/private/test'))
    import astock.cli.research as commands
    monkeypatch.setattr(commands,'get_project_root',lambda:root)
    run=CliRunner().invoke(app,['research','radar','--bundle',bid,'--store',str(store.path),'--as-of',ASOF,
                              '--output',str(root/'reports/private/research-v1/v2'), '--public-output','docs/research/results/v2'])
    assert run.exit_code==0,run.output
    assert list((root/'docs/research/results/v2').glob('*.md'))


def test_industry_overlap_and_missing_rejected():
    from astock.research.radar import industry_cohorts
    rows={'industry_classification':[dict(industry_code='I',source_hash='a',name='x')],
          'industry_membership':[dict(code='C',industry_code='I',in_date=None,source_hash='b')]*2}
    with pytest.raises(ResearchError,match='INDUSTRY_OVERLAP'):industry_cohorts(rows,{'C'})
    rows['industry_membership']=[dict(code='C',industry_code='UNKNOWN',in_date=None,source_hash='b')]
    with pytest.raises(ResearchError,match='INDUSTRY_CLASSIFICATION_MISSING'):industry_cohorts(rows,{'C'})


def test_cache_rechecks_raw_database_and_asof(market,monkeypatch):
    _,_,store,bid,_,_,_=market
    import astock.research.store as module
    fresh=ResearchStore(store.path)
    original=module.records
    count=[]
    def tracked(*args,**kwargs):
        count.append(1)
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'records',tracked)
    first=fresh.snapshot(bid,ASOF)
    calls=len(count)
    assert calls==299
    assert fresh.snapshot(bid,ASOF)==first
    assert len(count)==calls
    # A new as-of must rederive; cache does not grant earlier knowledge.
    fresh.snapshot(bid,'2026-10-13T12:01:00+00:00')
    assert len(count)==2*calls


def test_day_partitions_and_no_undocumented_pagination():
    p=plan();m=next(m for m in p['members'] if m['api']=='daily')
    m['params']['offset']='0'
    with pytest.raises(ValueError,match='REQUEST_PARAMS'):MarketCapturePlan.model_validate(p)
    p=plan();m=next(m for m in p['members'] if m['api']=='adj_factor')
    m['params']['trade_date']='20260402'
    with pytest.raises(ValueError):MarketCapturePlan.model_validate(p)


def test_narrow_leaders_and_equal_weight_not_index():
    from astock.research.radar import distribution,breadth
    values=[dict(return_20=v,return_1=v,return_5=v,above_ma20=v>0,above_ma60=v>0,
                 new_high20=False,new_low20=False,expected_sessions=128,last_date='2026-10-12',
                 price_basis='FACTOR_ADJUSTED_PRICE_NOT_TOTAL_RETURN',activity_ratio=1,volatility_daily=0,
                 amount_today_cny=100,amount_change_1=0) for v in [1,-.1,-.1,None] if v is not None]
    d=distribution(values,'return_20')
    assert d['median']==-.1 and d['equal_weight_mean']==pytest.approx(.8/3)
    b=breadth(values)
    assert b['metrics']['return_20']['up_ratio']==pytest.approx(1/3)
    assert b['metrics']['amount_cny']['total']==300


def test_partial_full_pool_does_not_claim_market(market,tmp_path):
    _,_,_,_,original,_,p=market
    m=deepcopy(original)
    missing=next(f for f in m['files'] if f['request']['api']=='daily' and f['request']['params']['trade_date']=='20261012')
    m['files'].remove(missing)
    path=tmp_path/'partial.json';path.write_bytes(encoded(m))
    store=ResearchStore(tmp_path/'partial.duckdb');bid=store.import_bundle(path)
    r=analyze(store,bid,ASOF,p,radar=True)
    assert r['radar']['scope']=='CURRENT_POOL_WITH_GAPS'
    assert r['radar']['market']['metrics']['return_1']['denominator']==0
    assert len(r['radar']['source_coverage']['by_session'][-1]['missing_prices'])==10
    assert not r['candidates']


def test_direct_store_revision_pipeline_and_old_rebuild(market,tmp_path):
    from astock.research.increment import revision_key
    _,_,store,bid,original,report,p=market
    m=deepcopy(original)
    f=next(f for f in m['files'] if f['request']['api']=='adj_factor' and f['request']['params']['trade_date']=='20261012')
    source=read_json(Path(f['path']))
    # Independent, explicitly synthetic replacement evidence set.
    proof_root=tmp_path/'proofs';proof_root.mkdir()
    for spec in m['files']:
        for evidence in spec['evidence']:
            src=Path(evidence['path']);target=proof_root/src.name
            if not target.exists():target.write_bytes(src.read_bytes())
            evidence['path']=str(target)
    path=tmp_path/'revised-factor.json';path.write_bytes(encoded(source));f['path']=str(path)
    row=source['data']['items'][0];row[2]=2
    path.write_bytes(encoded(source));f['sha256']=__import__('hashlib').sha256(path.read_bytes()).hexdigest()
    rebind_synthetic_raw(f)
    revised=tmp_path/'revised.json';revised.write_bytes(encoded(m))
    # Same Store, append new source bundle. Existing reports and sources are untouched.
    revision_id=store.import_bundle(revised)
    with pytest.raises(ResearchError,match='INCREMENT_REVISION_SELECTION_REQUIRED'):
        analyze(store,revision_id,ASOF,p,radar=True,components=[bid])
    key=revision_key('adj_factor',dict(code=row[0],date='2026-10-12'))
    r=analyze(store,revision_id,ASOF,p,radar=True,components=[bid],revisions={key:f['sha256']})
    assert r['composition']['revisions']=={key:f['sha256']}
    rebuilt=analyze(store,bid,ASOF,p,radar=True)
    assert rebuilt==report
    assert next(s for s in r['features'] if s['code']==row[0])['return_20'] != next(s for s in report['features'] if s['code']==row[0])['return_20']


def test_one_day_market_increment_plan_is_runnable():
    p=plan()
    p['window_start']=p['window_end']
    p['expected_min_sessions']=1
    p['members']=[m for m in p['members'] if 'trade_date' not in m['params'] or m['params']['trade_date']=='20261012']
    for m in p['members']:
        if 'start_date' in m['params']:m['params']['start_date']='20261012'
    p['maximum_requests']=p['maximum_attempts']=len(p['members'])
    p['max_total_body_bytes']=len(p['members'])*p['max_body_bytes']
    validated=MarketCapturePlan.model_validate(p)
    assert validated.maximum_requests==45 and validated.expected_min_sessions==1
    assert [m['api'] for m in validated.members].count('daily')==1


def test_stale_candidate_counts_do_not_revive_old_prices(market):
    _,_,store,bid,_,_,p=market
    r=analyze(store,bid,'2026-10-25T20:00:00+08:00',p,radar=True)
    assert not r['candidates'] and r['radar']['candidate_tracking']['eligible_total']==0


def test_neutral_breadth_and_missing_industry_not_false_alignment(market):
    from astock.research.radar import attach_radar
    _,_,store,bid,m,original,p=market
    _,rows=store.snapshot(bid,ASOF)
    r=deepcopy(original)
    stocks=r['features']
    for i,s in enumerate(stocks):
        s['above_ma60']=i<5
        s['return_20']=0
        s['return20_dates']=stocks[0]['return20_dates']
    benchmarks=r['market']['benchmarks']
    for b in benchmarks:b['above_ma60']=False
    previous={s['code']:deepcopy(s) for s in stocks}
    attach_radar(r,m,rows,stocks,benchmarks,previous,p)
    assert r['radar']['market']['metrics']['above_ma60']['ratio']==.5
    assert r['radar']['index_breadth_alignment']=='UNKNOWN'
    assert r['radar']['trend']=='MIXED_OR_UNKNOWN'  # 100% flat is not contraction.
    for s in stocks:
        if s['code'] in {'SYNTHETIC-0','SYNTHETIC-3','SYNTHETIC-4','SYNTHETIC-5'}:s['return_20']=.1
    next(s for s in stocks if s['code']=='SYNTHETIC-0')['return_20']=None
    attach_radar(r,m,rows,stocks,benchmarks,previous,p)
    bank=next(i for i in r['radar']['industries'] if i['code']=='801780.SI')
    assert bank['diffusion']=='INSUFFICIENT_COVERAGE'
