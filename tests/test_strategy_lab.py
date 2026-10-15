"""Shared execution counterexamples; all calendars, quotes and statuses are fictitious."""
from decimal import Decimal
from pathlib import Path

import pytest

from astock.backtest.scenarios import synthetic_scenario
from astock.backtest.strategy_lab import LabSession, ThreeRuleExperiment, compare_strategies
from astock.research.core import encoded, read_json
from astock.screening.strategy_models import StrategyParameters


@pytest.fixture(scope='module')
def experiment():
    return ThreeRuleExperiment.model_validate(read_json(Path(__file__).parents[1]/'config/decision-loop/strategy-lab-v1.json'))


@pytest.fixture(scope='module')
def parameters():
    return StrategyParameters.model_validate(read_json(Path(__file__).parents[1]/'config/research/strategy-research-v1.json'))


@pytest.fixture(scope='module')
def sessions(parameters,experiment):
    return synthetic_scenario(parameters,experiment)


def test_three_variants_use_shared_next_open_net_cost_and_exit_rules(sessions,parameters,experiment):
    value=compare_strategies(sessions,parameters,experiment)
    assert encoded(value) and value['strategy_effectiveness']=='NOT_VALIDATED' and value['actual_user_pnl'] is None
    for variant in parameters.variants:
        result=value['results'][variant]
        assert result['trades'],variant
        trade=result['trades'][0]
        assert trade['entry_date'] < trade['exit_date']
        assert Decimal(trade['pnl_cny'])<0 and trade['reason']=='INITIAL_REFERENCE_BROKEN'
        assert set(trade['all_exit_triggers'])=={'INITIAL_REFERENCE_BROKEN','TREND_REVIEW'}
        assert Decimal(trade['exit_deviation_from_signal'])<0
        assert result['opportunity_counts']['total']==len(sessions)
        assert result['cash_ledger_cny'] is not None
        assert Decimal(value['higher_cost_results'][variant]['average_net_return']) < Decimal(result['average_net_return'])
    assert value['results']['P0']['trades'][0]['entry_date']==sessions[70].date
    assert value['results']['T0']['trades'][0]['entry_date']==sessions[76].date
    assert 'EXIT_PENDING_LIMIT_SUSPENSION_OR_UNKNOWN' in value['results']['T0']['sessions'][78]['actions']


@pytest.mark.parametrize('field,value', [('open',None),('suspended',None),('st',None),
    ('up_limit',None),('liquidity_confirmed',None),('volume',Decimal(50)),('open',Decimal(20))])
def test_unknown_open_constraints_or_insufficient_volume_cancel_entry(sessions,parameters,experiment,field,value):
    values=sessions[:]
    change={field:value}
    if field=='open' and value==Decimal(20):change['high']=Decimal(21)
    values[70]=values[70].model_copy(update=change)
    result=compare_strategies(values,parameters,experiment)['results']['P0']
    assert result['opportunity_counts']['entry_fills']==0 and not result['trades']
    assert any(a.startswith('CANCEL_SETUP') for a in result['sessions'][70]['actions'])
    assert result['cash_ledger_cny']=='100000'


def test_limit_down_exit_does_not_flatten_or_assume_stop_price(sessions,parameters,experiment):
    values=sessions[:73]
    values[-1]=values[-1].model_copy(update={'down_limit':Decimal('9.8')})
    result=compare_strategies(values,parameters,experiment)['results']['P0']
    assert not result['trades'] and result['open_positions']
    assert next(iter(result['pending'].values()))['side']=='SELL'
    assert 'EXIT_PENDING_LIMIT_SUSPENSION_OR_UNKNOWN' in result['sessions'][-1]['actions']


def test_missing_held_price_leaves_equity_and_complete_drawdown_unknown(sessions,parameters,experiment):
    values=sessions[:72]
    values[-1]=values[-1].model_copy(update={'open':None,'close':None,'high':None,'low':None,'frame':None})
    result=compare_strategies(values,parameters,experiment)['results']['P0']
    assert result['open_positions'] and result['daily_equity'][-1]['equity_cny'] is None
    assert result['lab_mark_to_market_max_drawdown'] is None and not result['valuation_complete']
    assert 'HOLDING_PRICE_UNKNOWN' in result['sessions'][-1]['actions']


def test_corporate_action_is_quarantined_without_rewriting_shares_or_cash(sessions,parameters,experiment):
    values=sessions[:74]
    values[71]=values[71].model_copy(update={'adjustment_factor':Decimal(2)})
    result=compare_strategies(values,parameters,experiment)['results']['P0']
    position=next(iter(result['open_positions'].values()))
    assert position['quarantined'] and position['factor_reference']=='1'
    assert not result['trades'] and result['lab_mark_to_market_max_drawdown'] is None
    assert 'CORPORATE_ACTION_OR_FACTOR_UNMODELED' in result['sessions'][71]['actions']


def test_shared_cash_code_priority_and_no_double_entry(sessions,parameters,experiment):
    first=sessions[:71]
    other=[]
    for session in first:
        frame=session.frame.model_copy(update={'code':'SYNTHETIC-STOCK-2'})
        other.append(session.model_copy(update={'code':frame.code,'frame':frame}))
    values=sorted([*first,*other],key=lambda s:(s.date,s.code))
    small=experiment.model_copy(update={'nominal_lab_cash':Decimal(1200)})
    result=compare_strategies(values,parameters,small)['results']['P0']
    assert len(result['open_positions'])==1 and 'SYNTHETIC-STOCK-1' in result['open_positions']
    assert result['opportunity_counts']['entry_fills']==1 and result['opportunity_counts']['canceled']==1
    assert Decimal(result['cash_ledger_cny'])>=0


def test_missing_session_grid_and_real_source_cannot_be_relabelled(sessions,parameters,experiment):
    raw=sessions[0].model_dump(mode='json');raw['source_grade']='LOCAL_CAPTURE_BOUND'
    with pytest.raises(ValueError):LabSession.model_validate(raw)
    raw=sessions[0].model_dump(mode='json');raw['frame']['knowledge_basis']='CURRENT_OBSERVATION'
    with pytest.raises(ValueError,match='FRAME_NOT_SYNTHETIC'):LabSession.model_validate(raw)
    other=sessions[0].model_copy(update={'code':'other','frame':None})
    with pytest.raises(ValueError,match='COMPLETE_SYNTHETIC_GRID'):
        compare_strategies(sorted([*sessions,other],key=lambda s:(s.date,s.code)),parameters,experiment)
    raw=sessions[0].model_dump(mode='json');raw['frame']['as_of']=sessions[1].available_at
    with pytest.raises(ValueError,match='FRAME_TIME_CODE'):LabSession.model_validate(raw)


def test_replay_is_deterministic_and_input_objects_are_preserved(sessions,parameters,experiment):
    before=encoded([s.model_dump(mode='json') for s in sessions])
    first=compare_strategies(sessions,parameters,experiment)
    assert encoded(compare_strategies(sessions,parameters,experiment))==encoded(first)
    assert encoded([s.model_dump(mode='json') for s in sessions])==before


def test_reviews_and_twentieth_close_exit_with_fee_reconciliation(parameters,experiment):
    values=synthetic_scenario(parameters,experiment,
        closes=[Decimal(10)]*45+[Decimal(11)]*24+[Decimal('11.3')]+[Decimal('11.5')]*25)
    result=compare_strategies(values,parameters,experiment)['results']['P0']
    trade=result['trades'][0]
    assert trade['reason']=='TIME_REVIEW' and trade['all_exit_triggers']==['TIME_REVIEW']
    assert trade['entry_date']==values[70].date and trade['exit_date']==values[90].date
    assert 'RESEARCH_REVIEW_DUE_5' in result['sessions'][74]['actions']
    assert 'RESEARCH_REVIEW_DUE_10' in result['sessions'][79]['actions']
    assert Decimal(trade['exit_proceeds_cny'])-Decimal(trade['entry_cost_cny'])==Decimal(trade['pnl_cny'])
    assert Decimal(trade['entry_fee_cny'])>0 and Decimal(trade['exit_fee_cny'])>0


def test_copied_packets_are_revalidated_before_execution(sessions,parameters,experiment):
    bad=sessions[:]
    bad[0]=bad[0].model_copy(update={'high':Decimal(1)})
    with pytest.raises(ValueError,match='STRATEGY_LAB_'):
        compare_strategies(bad,parameters,experiment)
    bad=sessions[:]
    bad[-1]=bad[-1].model_copy(update={'frame':bad[0].frame})
    with pytest.raises(ValueError,match='FRAME_TIME_CODE'):
        compare_strategies(bad,parameters,experiment)


def test_publication_is_immutable_and_cli_does_not_need_market_or_account(tmp_path,parameters,experiment,monkeypatch):
    from typer.testing import CliRunner
    from astock.cli.main import app
    from astock.cli import paper_lab
    from astock.backtest.report import publish_lab
    for path,value in [('config/research/strategy-research-v1.json',parameters),
                       ('config/decision-loop/strategy-lab-v1.json',experiment)]:
        target=tmp_path/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(encoded(value.model_dump(mode='json')))
    monkeypatch.setattr(paper_lab,'get_project_root',lambda:tmp_path)
    runner=CliRunner()
    first=runner.invoke(app,['research','paper-demo'])
    assert first.exit_code==0,first.output
    again=runner.invoke(app,['research','paper-demo'])
    assert again.exit_code==0 and again.output==first.output
    report_path=next((tmp_path/'reports/private/research-v1/strategy-lab-v1').glob('*.json'))
    report=read_json(report_path)
    assert report['mode']=='OFFLINE_SYNTHETIC_MECHANICS_ONLY' and len(report['results'])==3
    assert '所有公司、价格' in report_path.with_suffix('.md').read_text()
    rejected=runner.invoke(app,['research','paper-demo','--output','docs/research/results'])
    assert rejected.exit_code==1 and not (tmp_path/'docs').exists()
    report_path.with_suffix('.md').write_text('changed')
    with pytest.raises(ValueError,match='IMMUTABLE_OBJECT_CHANGED'):
        publish_lab(report,report_path.parent)
