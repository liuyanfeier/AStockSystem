"""Company evidence/time, financial interpretation and conditional decision regressions."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from astock.company.models import ResearchCatalog
from astock.company.workflow import arithmetic, build, publish, shortlist, verify_documents
from astock.features.market import ObservationParameters
from astock.research.core import digest


def catalog_input():
    source = dict(id='s1', code='600001.SH', title='合成半年报',
                  url='https://static.cninfo.com.cn/finalpage/2026-08-01/test.PDF',
                  published_on='2026-08-01', retrieved_at='2026-10-14T00:00:00+00:00',
                  available_at='2026-10-14T00:00:00+00:00', hosting='DISCLOSURE_PLATFORM',
                  state='RETRIEVED', audit='UNAUDITED', sha256=sha256(b'%PDF-mock').hexdigest())
    figure = dict(id='revenue', name='营业收入', value='120', unit='CNY', period_start='2026-01-01',
                  period_end='2026-06-30', reference=dict(source_id='s1', locator='PDF第2页表1'),
                  comparison_value='100', comparison_period_start='2025-01-01',
                  comparison_period_end='2025-06-30', reported_change_percent='20')
    fact = dict(id='f1', kind='FACT', text='公司披露收入', references=[dict(source_id='s1', locator='第2页')])
    company = dict(code='600001.SH', profile=[fact], financials=[figure], events=[],
                   support=[dict(id='i1', kind='INFERENCE', text='需要进一步跟踪', supports=['f1'])],
                   counter=[dict(id='h1', kind='HYPOTHESIS', text='增长可能不持续', supports=['f1'])],
                   unknowns=[dict(id='u1', kind='UNKNOWN', text='未核实新订单')], status='普通跟踪',
                   priority_reason='仅研究', next_checks=['下一次原始财报'], thesis_invalidations=['事实推翻收入逻辑'])
    return dict(protocol='COMPANY_RESEARCH_V1', as_of='2026-10-14T01:00:00+00:00', sources=[source], companies=[company])


def market_input():
    params = ObservationParameters(version='TEST', return_sessions=20, trend_sessions=60, breakout_sessions=20,
                                    activity_sessions=20, top_n=10, min_mean_amount_cny=100, max_stale_calendar_days=3)
    stocks = [dict(code=f'60000{n}.SH', name=f'样本{n}', kind='STOCK', exchange='SSE', provider_market='主板',
                   last_date='2026-10-12', window_return=n/100, return_20=n/100, above_ma=True, above_ma60=True,
                   mean_amount_cny=1000, close=10, ma=9, ma60=9, gaps=[], prior_high=11, breakout=False,
                   relative_return=0, activity_ratio=1) for n in range(1, 9)]
    sectors = [dict(code=f'I{n}', name=f'行业{n}', strength='STRONG', breadth={'metrics':{'return_20_distribution':{'median':.01}}}) for n in range(1,9)]
    memberships = [dict(code=s['code'], industry_code=f'I{n}', source_hash='a'*64) for n,s in enumerate(stocks,1)]
    snapshot = dict(purpose='CURRENT_OBSERVATION', bundle_id='b', as_of='2026-10-14T00:00:00+00:00',
                    window_end='2026-10-12', parameters=params.model_dump(mode='json'), parameters_hash=digest(params.model_dump(mode='json')),
                    features=stocks, radar=dict(industries=sectors, industry_coverage={'source_hashes':['a'*64]},
                        market={'metrics':{'return_20':{'up':8,'denominator':8},'above_ma60':{'count':8,'denominator':8}}}),
                    market={'benchmarks':[]})
    policy = dict(size=10, maximum_per_industry=3, extreme_return20=.5, not_extended_return20=.1,
                  representative_codes=['600001.SH'])
    return snapshot, memberships, policy


def test_valid_time_and_research_only_no_unknown_upgrade(tmp_path):
    raw = catalog_input(); catalog = ResearchCatalog.model_validate(raw)
    (tmp_path/'s1.pdf').write_bytes(b'%PDF-mock')
    s,m,p = market_input(); selection = shortlist(s,m,p)
    report = build(s,selection,catalog,tmp_path)
    assert report['cards'][0]['decision_draft']['trade_eligible'] is False
    assert report['cards'][0]['decision_draft']['risk_budget'] is None
    assert report['cards'][0]['research']['unknowns'][0]['kind'] == 'UNKNOWN'
    assert report['cards'][0]['published_before_price_date'] == ['s1']
    assert report['sources'][0]['available_at'] > s['as_of'][:10]  # not historical local knowledge
    assert report['market_parameters_hash'] == s['parameters_hash']
    assert publish(report,tmp_path/'out') == publish(report,tmp_path/'out')
    assert '20日上涨8/8' in (tmp_path/'out/DECISION_BRIEF.md').read_text()


@pytest.mark.parametrize('mutation', ['future_publish', 'backdated_available', 'future_retrieved', 'unknown_source',
                                      'cross_entity', 'unknown_as_fact', 'hypothesis_chain', 'source_url_password',
                                      'extra_journal', 'unknown_number', 'future_period'])
def test_evidence_and_time_counterexamples(mutation):
    x=catalog_input(); c=x['companies'][0]; s=x['sources'][0]
    if mutation=='future_publish':s.update(published_on='2026-10-15',available_at='2026-10-15T16:00:00+00:00')
    elif mutation=='backdated_available':s['available_at']='2026-08-01T00:00:00+00:00'
    elif mutation=='future_retrieved':s['retrieved_at']='2026-10-15T00:00:00+00:00'
    elif mutation=='unknown_source':s.update(state='UNAVAILABLE',sha256=None)
    elif mutation=='cross_entity':s['code']='600002.SH'
    elif mutation=='unknown_as_fact':c['unknowns'][0]['kind']='FACT'
    elif mutation=='hypothesis_chain':c['support'][0]['supports']=['u1']
    elif mutation=='source_url_password':s['url']='https://user:password@static.cninfo.com.cn/test.pdf'
    elif mutation=='extra_journal':c['journal']={'holding':1}
    elif mutation=='unknown_number':c['financials'][0]['reference']=None
    elif mutation=='future_period':c['financials'][0]['period_end']='2026-12-31'
    with pytest.raises(ValueError):ResearchCatalog.model_validate(x)


def test_hash_tamper_and_missing_bytes_cannot_publish(tmp_path):
    catalog=ResearchCatalog.model_validate(catalog_input())
    with pytest.raises(ValueError,match='COMPANY_DOCUMENT_MISSING'):verify_documents(catalog,tmp_path)
    (tmp_path/'s1.pdf').write_bytes(b'%PDF-changed')
    with pytest.raises(ValueError,match='COMPANY_DOCUMENT_CHANGED'):verify_documents(catalog,tmp_path)


def test_negative_base_and_bank_percent_are_not_growth():
    x=ResearchCatalog.model_validate(catalog_input()).companies[0].financials[0].model_dump(mode='json')
    assert arithmetic(x)['validation']=='MATCHES_REPORTED_ROUNDING'
    x.update(value='-120',comparison_value='-100',reported_change_percent=None)
    assert arithmetic(x)['change_percent'] is None
    assert arithmetic(x)['absolute_change']=='-20'
    x.update(value='0.94',comparison_value='0.94',unit='PERCENT')
    assert arithmetic(x)['change_percent'] is None
    x.update(value='2',comparison_value='0',unit='CNY')
    assert arithmetic(x)['change_percent'] is None


def test_quarter_vs_half_year_and_wrong_arithmetic_rejected():
    x=ResearchCatalog.model_validate(catalog_input()).companies[0].financials[0].model_dump(mode='json')
    x['comparison_period_end']='2025-03-31'
    assert arithmetic(x)['validation']=='INCOMPARABLE_PERIODS'
    x['comparison_period_end']='2025-06-30';x['reported_change_percent']='50'
    with pytest.raises(ValueError,match='COMPANY_REPORTED_ARITHMETIC_MISMATCH'):arithmetic(x)


def test_shortlist_concentration_downgrade_st_and_source_lineage():
    s,m,p=market_input();p['maximum_per_industry']=1;p['representative_codes']=['600001.SH','600002.SH']
    m[1]['industry_code']='I1'
    s['features'][2]['name']='ST样本';s['features'][3]['mean_amount_cny']=1
    result=shortlist(s,m,p)
    assert sum(r['industry_code']=='I1' for r in result['selected'])==1
    denied=next(r for r in result['audit'] if r['code']=='600002.SH')
    assert denied['eligible'] and '行业集中度' in denied['allocation_reason']
    low=next(r for r in result['audit'] if r['code']=='600004.SH')
    assert not low['eligible'] and low['exclusions']
    assert 'QUALITY_LIQUIDITY_OR_ST_REVIEW' in result['audit'][2]['tags']
    m[0]['source_hash']='b'*64
    with pytest.raises(ValueError,match='COMPANY_MEMBERSHIP_LINEAGE'):shortlist(s,m,p)


def test_public_private_text_and_immutable_output(tmp_path):
    (tmp_path/'s1.pdf').write_bytes(b'%PDF-mock')
    s,m,p=market_input();c=ResearchCatalog.model_validate(catalog_input())
    r=build(s,shortlist(s,m,p),c,tmp_path)
    r['cards'][0]['research']['priority_reason']='/Users/private/holdings'
    with pytest.raises(ValueError,match='COMPANY_PUBLIC_PRIVATE_TEXT'):publish(r,tmp_path/'out')
    r['cards'][0]['research']['priority_reason']='研究'
    publish(r,tmp_path/'out');r['cards'][0]['research']['priority_reason']='changed'
    with pytest.raises(ValueError,match='IMMUTABLE_OBJECT_CHANGED'):publish(r,tmp_path/'out')
