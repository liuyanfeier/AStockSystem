"""Causal source windows and three frozen hypotheses; synthetic data, no market calls."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from astock.features.market import ObservationParameters, features
from astock.features.strategy import strategy_frames
from astock.research.core import digest, encoded, read_json
from astock.screening.strategies import evaluate_strategy
from astock.screening.strategy_models import StrategyFrame, StrategyParameters
from test_research_v1 import sample


@pytest.fixture
def parameters():
    root = Path(__file__).resolve().parents[1]
    return StrategyParameters.model_validate(read_json(root/'config/research/strategy-research-v1.json'))


def source_rows(*, stock_exchange='SSE'):
    stock = '600036.SH' if stock_exchange == 'SSE' else '000001.SZ'
    start = date(2026,10,16)
    dates = [(start+timedelta(days=i)).isoformat() for i in range(70)]
    stocks, indices, factors, calendars = [], [], [], []
    closes = [10]*45 + [11]*24 + [11.3]
    for exchange in {'SSE',stock_exchange}:
        calendars += [dict(exchange=exchange,date=day,is_open=1,source_hash=('c' if exchange == 'SSE' else 'd')*64) for day in dates]
    for i,day in enumerate(dates):
        close = closes[i]
        stocks.append(dict(code=stock,date=day,open=close,close=close,high=close+.1,low=close-.1,
                           volume=100000,amount=20000000,source_hash='a'*64))
        indices.append(dict(code='BENCH',date=day,open=10,close=10,high=10.1,low=9.9,
                            volume=100000,amount=20000000,source_hash='b'*64))
        factors.append(dict(code=stock,date=day,adj_factor=1,source_hash='e'*64))
    manifest=dict(purpose='CURRENT_OBSERVATION',window_end=dates[-1],window_start=dates[0],
                  universe=[stock],benchmarks=['BENCH'])
    rows=dict(instruments=[dict(code=stock,name='合成公司',kind='STOCK',exchange=stock_exchange,
                   provider_market='主板',list_date=dates[0],source_hash='f'*64),
              dict(code='BENCH',name='合成指数',kind='INDEX',exchange='SSE',source_hash='0'*64)],
              daily=stocks,index_daily=indices,adj_factor=factors,calendar=calendars,
              status=[dict(code=stock,date=dates[-1],st='NO',suspended='NO',up_limit=15,down_limit=8,source_hash='1'*64)])
    return manifest,rows


def frame(parameters, *, synthetic=True, **changes):
    manifest,rows=source_rows()
    result=strategy_frames(manifest,rows,'2026-12-31T16:00:00+08:00',manifest['window_end'],parameters)[0]
    values={**result.model_dump(mode='json'),
            'knowledge_basis':'OFFLINE_SYNTHETIC' if synthetic else 'CURRENT_OBSERVATION',**changes}
    return StrategyFrame.model_validate(values)


def test_pullback_breakout_and_trend_share_declared_rules(parameters):
    sample=frame(parameters)
    p0=evaluate_strategy(sample,parameters,'P0')
    b0=evaluate_strategy(sample,parameters,'B0')
    t0=evaluate_strategy(sample,parameters,'T0')
    assert p0['condition_match'] is True and p0['first_match'] is True
    assert p0['metrics']['touch_date']==sample.bars[-1].date
    assert b0['first_match'] is True and t0['condition_match'] is False
    assert p0['paper_ready'] and b0['paper_ready']
    assert p0['real_trade_eligible'] is False and p0['risk_budget'] is None and p0['order'] is None
    assert encoded(p0) and p0['parameters_hash']==digest(parameters.model_dump(mode='json'))


def test_trend_cross_requires_previous_close_not_above_previous_ma(parameters):
    sample=frame(parameters)
    bars=[b.model_copy(update={'close':Decimal(10),'high':Decimal('10.1'),'low':Decimal('9.9')}) for b in sample.bars]
    bars[-1]=bars[-1].model_copy(update={'close':Decimal(11),'high':Decimal('11.1'),'low':Decimal('10.9')})
    sample=sample.model_copy(update={'bars':bars})
    result=evaluate_strategy(sample,parameters,'T0')
    assert result['condition_match'] and result['first_match']
    bars[-2]=bars[-2].model_copy(update={'close':Decimal('10.5'),'high':Decimal('10.6'),'low':Decimal('10.4')})
    assert evaluate_strategy(sample.model_copy(update={'bars':bars}),parameters,'T0')['condition_match'] is False


def test_most_recent_touch_is_used_and_extension_blocks_pullback(parameters):
    sample=frame(parameters)
    values=sample.bars[:]
    values[-1]=values[-1].model_copy(update={'close':Decimal('11.6'),'high':Decimal('11.7'),'low':Decimal('11.5')})
    sample=sample.model_copy(update={'bars':values})
    result=evaluate_strategy(sample,parameters,'P0')
    assert result['metrics']['touch_date']==values[-2].date
    assert result['first_match']
    values[-1]=values[-1].model_copy(update={'close':Decimal(13),'high':Decimal('13.1'),'low':Decimal('12.9')})
    result=evaluate_strategy(sample.model_copy(update={'bars':values}),parameters,'P0')
    assert result['checks']['not_extended'] is False and not result['first_match']


@pytest.mark.parametrize('field,value,blocker',[
    ('st',None,'ST_OR_UNKNOWN'),('suspended',None,'SUSPENDED_OR_UNKNOWN'),
    ('up_limit',None,'LIMIT_RULE_UNKNOWN'),('board','UNMODELED','BOARD_NOT_MODELED'),
    ('volume',Decimal(0),'NO_CONFIRMED_ACTIVITY'),
    ('knowledge_basis','CURRENT_OBSERVATION','REAL_PROSPECTIVE_EXECUTION_NOT_ADMITTED')])
def test_shape_is_preserved_but_unknown_execution_stays_blocked(parameters,field,value,blocker):
    result=evaluate_strategy(frame(parameters,**{field:value}),parameters,'P0')
    assert result['first_match'] is True
    assert not result['paper_ready'] and blocker in result['paper_blockers']


def test_missing_factor_relative_or_source_is_unknown_not_zero(parameters):
    sample=frame(parameters)
    for change in ({'price_basis':'UNKNOWN'},{'relative_return':None},{'source_hashes':[]}):
        result=evaluate_strategy(sample.model_copy(update=change),parameters,'P0')
        assert result['condition_match'] is None and result['first_match'] is None
    result=evaluate_strategy(sample,parameters,'P0',already_active=True)
    assert result['condition_match'] is True and result['first_match'] is False
    assert 'EXISTING_PLAN_OR_PAPER_POSITION' in result['rejection_reasons']


def test_rising_edge_and_previous_unknown_do_not_create_duplicate_setups(parameters):
    sample=frame(parameters)
    bars=sample.bars[:]
    bars[-2]=bars[-2].model_copy(update={'close':Decimal('11.2'),'high':Decimal('11.21'),'low':Decimal('11.1')})
    bars[-1]=bars[-1].model_copy(update={'close':Decimal('11.4'),'high':Decimal('11.5'),'low':Decimal('11.3')})
    result=evaluate_strategy(sample.model_copy(update={'bars':bars}),parameters,'B0')
    assert result['condition_match'] is True and result['previous_condition_match'] is True
    assert result['first_match'] is False and 'CONDITION_ALREADY_PRESENT' in result['rejection_reasons']
    result=evaluate_strategy(sample.model_copy(update={'previous_relative_return':None}),parameters,'P0')
    assert result['condition_match'] is True and result['first_match'] is None


def test_windows_do_not_bridge_price_gaps_and_old_irrelevant_factors_do_not_block(parameters):
    manifest,rows=source_rows()
    rows['daily'].pop(-3)
    sample=strategy_frames(manifest,rows,'2026-12-31T16:00:00+08:00',manifest['window_end'],parameters)[0]
    assert len(sample.bars)==2
    assert evaluate_strategy(sample,parameters,'B0')['condition_match'] is None
    manifest,rows=source_rows()
    rows['adj_factor']=rows['adj_factor'][5:]
    sample=strategy_frames(manifest,rows,'2026-12-31T16:00:00+08:00',manifest['window_end'],parameters)[0]
    assert len(sample.bars)==65 and sample.price_basis!='UNKNOWN'
    rows['adj_factor'].pop()
    sample=strategy_frames(manifest,rows,'2026-12-31T16:00:00+08:00',manifest['window_end'],parameters)[0]
    assert sample.price_basis=='UNKNOWN' and not sample.bars


def test_stock_and_benchmark_windows_must_match_and_both_calendar_hashes_are_bound(parameters):
    manifest,rows=source_rows(stock_exchange='SZSE')
    sample=strategy_frames(manifest,rows,'2026-12-31T16:00:00+08:00',manifest['window_end'],parameters)[0]
    assert 'c'*64 in sample.source_hashes and 'd'*64 in sample.source_hashes
    target=rows['index_daily'][-10]['date']
    rows['index_daily']=[r for r in rows['index_daily'] if r['date']!=target]
    next(r for r in rows['calendar'] if r['exchange']=='SSE' and r['date']==target)['is_open']=0
    sample=strategy_frames(manifest,rows,'2026-12-31T16:00:00+08:00',manifest['window_end'],parameters)[0]
    assert sample.relative_return is None
    assert evaluate_strategy(sample,parameters,'B0')['condition_match'] is None


def test_split_transform_matches_existing_price_basis_and_blocks_missing_last_price(parameters):
    manifest,rows=source_rows()
    stock=manifest['universe'][0]
    for name in ('open','close','high','low'):
        rows['daily'][-1][name]/=2
    rows['adj_factor'][-1]['adj_factor']=2
    sample=strategy_frames(manifest,rows,'2026-12-31T16:00:00+08:00',manifest['window_end'],parameters)[0]
    assert sample.bars[-1].close==Decimal('5.65')
    existing=features(stock,rows['instruments'][0],rows['daily'],rows['adj_factor'],rows['calendar'],
        date.fromisoformat(manifest['window_end']),ObservationParameters.model_validate(read_json(Path(__file__).parents[1]/'config/research/observation-v1.json')),radar=True)
    assert float(sum(b.close for b in sample.bars[-20:])/20)==pytest.approx(existing['ma20'])
    assert evaluate_strategy(sample,parameters,'P0')['condition_match'] is True
    rows['daily'].pop()
    sample=strategy_frames(manifest,rows,'2026-12-31T16:00:00+08:00',manifest['window_end'],parameters)[0]
    assert not sample.bars and 'LATEST_PRICE_MISSING' in sample.gaps


def test_parameters_or_dates_cannot_imply_past_knowledge_or_real_risk(parameters):
    sample=frame(parameters)
    with pytest.raises(ValueError,match='PARAMETERS_AFTER_ASOF'):
        evaluate_strategy(sample,parameters.model_copy(update={'frozen_at':sample.as_of+timedelta(days=1)}),'P0')
    raw=parameters.model_dump(mode='json');raw['real_risk_budget']='0.01'
    with pytest.raises(ValueError):StrategyParameters.model_validate(raw)
    with pytest.raises(ValueError,match='ALL_VARIANTS_REQUIRED'):
        StrategyParameters.model_validate({**parameters.model_dump(mode='json'),'variants':['P0']})
    raw=sample.model_dump(mode='json');raw['required_market_date']='2027-01-01'
    with pytest.raises(ValueError,match='FUTURE_REQUIRED_DATE'):StrategyFrame.model_validate(raw)


def test_native_setup_cli_does_not_require_company_or_account_files(sample,parameters,tmp_path,monkeypatch):
    from datetime import datetime, timezone
    from hashlib import sha256
    from typer.testing import CliRunner
    from astock.cli.main import app
    import astock.cli.strategies as cli
    from astock.research.store import ResearchStore
    store=ResearchStore(tmp_path/'data/private/research-v1/source/research.duckdb')
    bundle=store.import_bundle(sample[0])
    config=tmp_path/'config';config.mkdir()
    policy=parameters.model_copy(update={'version':'SYNTHETIC_CLI_FIXTURE',
                                         'frozen_at':datetime(2026,9,1,tzinfo=timezone.utc)})
    (config/'strategy.json').write_bytes(encoded(policy.model_dump(mode='json')))
    profile=dict(protocol='DAILY_PROFILE_V1',run='config/absent-run.json',previous='config/absent-old.json',
        latest='config/absent-new.json',documents='data/private/research-v3/not-present',
        baseline_market='config/absent-market.json',bundle=bundle,
        store='data/private/research-v1/source/research.duckdb',
        journal_store='data/private/research-v1/decision-loop-v0/real/not-created.duckdb',
        output='reports/private/research-v1/strategy-fixture')
    path=config/'daily.json';path.write_bytes(encoded(profile))
    before=sha256(store.path.read_bytes()).hexdigest()
    monkeypatch.setattr(cli,'get_project_root',lambda:tmp_path)
    monkeypatch.setattr(ResearchStore,'initialize',lambda *a:pytest.fail('scan must not initialize or write a Store'))
    args=['research','setups','--profile',str(path),'--parameters','config/strategy.json',
          '--as-of','2026-09-15T20:00:00+08:00','--market-date','2026-09-11']
    runner=CliRunner();result=runner.invoke(app,args)
    assert result.exit_code==0,result.output
    outputs=list((tmp_path/profile['output']/'strategies').glob('*.json'))
    assert len(outputs)==1
    report=read_json(outputs[0])
    assert all(v['pool']==2 and v['unknown']==2 for v in report['summary'].values())
    assert not report['observations'] and report['real_trade_eligible'] is False
    assert sha256(store.path.read_bytes()).hexdigest()==before
    assert not (tmp_path/profile['journal_store']).exists()
    original=outputs[0].read_bytes()
    assert runner.invoke(app,args).exit_code==0
    assert outputs[0].read_bytes()==original


def test_setup_cli_rejects_ambiguous_observation_before_outputs(parameters,tmp_path,monkeypatch):
    from typer.testing import CliRunner
    from astock.cli.main import app
    import astock.cli.strategies as cli
    monkeypatch.setattr(cli,'get_project_root',lambda:tmp_path)
    for extra in ([],['--as-of','2026-10-15T16:00:00+08:00','--observe-now']):
        result=CliRunner().invoke(app,['research','setups','--profile','config/missing.json',
                                     '--market-date','2026-10-14',*extra])
        assert result.exit_code==1 and '策略观察失败' in result.output
    assert not (tmp_path/'reports').exists()
