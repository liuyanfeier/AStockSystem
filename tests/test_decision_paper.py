"""Prospective lab mechanics: no lookahead, T+1, unknown state, limit fills and fees."""
from decimal import Decimal
import pytest
from astock.decision.paper import Experiment, Session, simulate


def sessions():
    result=[]
    for date,op,close,ma in [('2026-10-15',10,12,9),('2026-10-16',12,9,10),('2026-10-19',8,8,10)]:
        result.append(Session(date=date,available_at=date+'T16:00:00+08:00',execution_status_available_at=date+'T09:00:00+08:00',
                              code='600036.SH',exchange_board='SSE_MAIN',open=op,close=close,ma20=ma,ma60=9,
                              prior_high20=11,prior_low20=8,market_allowed=True,suspended=False,st=False,
                              up_limit=20,down_limit=5,volume=100000,liquidity_confirmed=True,
                              source_grade='OFFLINE_SYNTHETIC',source_hash='a'*64))
    return result


def experiment():return Experiment(frozen_at='2026-10-14T00:00:00+08:00')


def test_next_open_t_plus_one_gap_and_net_fee_loss():
    r=simulate(sessions(),experiment())
    assert r['trades'][0]['entry_date']=='2026-10-16' and r['trades'][0]['exit_date']=='2026-10-19'
    assert Decimal(r['trades'][0]['pnl_cny']) < -400
    assert r['strategy_effectiveness']=='NOT_VALIDATED' and r['actual_user_pnl'] is None
    assert r['win_rate']=='0' and Decimal(r['lab_mark_to_market_max_drawdown'])>0
    from astock.research.core import encoded
    assert encoded(r) and Decimal(r['trades'][0]['exit_deviation_from_signal'])<0


@pytest.mark.parametrize('field,value',[('suspended',True),('suspended',None),('st',None),('up_limit',None),('liquidity_confirmed',None),('volume',0),('up_limit',12)])
def test_unknown_suspension_liquidity_limit_gap_cancel_entry(field,value):
    s=sessions();s[1]=s[1].model_copy(update={field:value})
    r=simulate(s,experiment());assert not r['trades']
    assert r['sessions'][1]['actions'][0].startswith('CANCEL_SETUP')


def test_limit_down_or_suspension_keeps_exit_pending_not_filled_at_stop():
    s=sessions();s[2]=s[2].model_copy(update={'down_limit':Decimal(8)})
    r=simulate(s,experiment())
    assert not r['trades'] and r['unclosed_position']
    assert 'EXIT_PENDING_LIMIT_SUSPENSION_OR_UNKNOWN' in r['sessions'][2]['actions']


def test_real_history_and_retrospective_parameters_rejected():
    s=sessions();s[0]=s[0].model_copy(update={'source_grade':'LOCAL_CAPTURE_BOUND'})
    with pytest.raises(ValueError,match='PAPER_REAL_HISTORY_NOT_ADMITTED'):simulate(s,experiment())
    with pytest.raises(ValueError,match='PAPER_PARAMETERS_AFTER_SAMPLE'):simulate(sessions(),Experiment(frozen_at='2026-10-16T00:00:00+08:00'))
    raw=sessions()[0].model_dump();raw['available_at']='2026-10-15T12:00:00+08:00'
    with pytest.raises(ValueError,match='PAPER_LOOKAHEAD_STATUS_OR_CLOSE'):Session.model_validate(raw)
    raw=sessions()[0].model_dump();raw['execution_status_available_at']='2026-10-15T16:00:00+08:00'
    with pytest.raises(ValueError,match='PAPER_LOOKAHEAD_STATUS_OR_CLOSE'):Session.model_validate(raw)
