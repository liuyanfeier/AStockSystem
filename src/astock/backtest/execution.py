"""One synthetic execution ledger for frozen V0 and three-rule V1 experiments."""
from collections import defaultdict
from decimal import Decimal
from typing import Callable

from astock.research.core import instant, require


def _wire(value):
    if isinstance(value,Decimal):
        return str(value)
    if isinstance(value,dict):
        return {k:_wire(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [_wire(v) for v in value]
    return value


def run_execution(sessions: list, experiment, entry_decision: Callable, *, review_sessions: tuple[int,...] = ()) -> dict:
    """Synthetic only. Same-open exits precede buys, then codes define cash priority."""
    require(bool(sessions),'PAPER_EMPTY_SESSIONS')
    require(all(s.source_grade == 'OFFLINE_SYNTHETIC' for s in sessions),'PAPER_REAL_HISTORY_NOT_ADMITTED')
    require(all(instant(experiment.frozen_at) < instant(s.available_at) for s in sessions),'PAPER_PARAMETERS_AFTER_SAMPLE')
    require(len({(s.date,s.code) for s in sessions})==len(sessions),'PAPER_DUPLICATE_SESSION')
    grouped=defaultdict(list)
    for session in sessions:
        grouped[session.date].append(session)
    pending,positions={},{}
    indices=defaultdict(lambda:-1)
    cash=experiment.nominal_lab_cash
    peak,drawdown=cash,Decimal(0)
    trades,logs,daily=[],[],[]
    valuation_complete=True
    for date,values in sorted(grouped.items()):
        values=sorted(values,key=lambda s:s.code)
        records={s.code:dict(date=date,code=s.code,source_hash=s.source_hash,actions=[]) for s in values}
        today={s.code:s for s in values}
        for s in values:
            indices[s.code]+=1
            position=positions.get(s.code)
            factor=getattr(s,'adjustment_factor',Decimal(1))
            if position and (factor is None or factor != position['factor_reference']):
                position['quarantined']=True
                position['excursions_complete']=False
                records[s.code]['actions'].append('CORPORATE_ACTION_OR_FACTOR_UNMODELED')
        account_blocked=any(p['quarantined'] for p in positions.values())
        ordered=sorted(values,key=lambda s:(0 if pending.get(s.code,{}).get('side')=='SELL' else 1,s.code))
        for s in ordered:
            code=s.code;record=records[code];position=positions.get(code);order=pending.get(code)
            if not order:
                continue
            factor=getattr(s,'adjustment_factor',Decimal(1))
            executable=(s.exchange_board in ('SSE_MAIN','SZSE_MAIN') and s.open is not None and
                s.suspended is False and s.st is False and s.liquidity_confirmed is True and
                s.up_limit is not None and s.down_limit is not None and s.volume is not None and s.volume>=experiment.shares and
                factor is not None and not (position and position['quarantined']))
            if order['side']=='BUY':
                if factor is None or factor != order['factor_reference'] or account_blocked:
                    record['actions'].append('CANCEL_SETUP_UNMODELED_ACTION_OR_ACCOUNT')
                    pending.pop(code)
                elif not executable:
                    record['actions'].append('CANCEL_SETUP_UNKNOWN_OR_UNTRADABLE')
                    pending.pop(code)
                else:
                    fill=s.open*(1+experiment.slippage_rate)
                    cost=fill*experiment.shares*(1+experiment.entry_fee_rate)
                    if fill>=s.up_limit or fill<=s.down_limit or cost>cash:
                        record['actions'].append('CANCEL_SETUP_LIMIT_GAP_OR_LAB_CASH')
                        pending.pop(code)
                    else:
                        positions[code]=dict(entry_date=date,entry_i=indices[code],entry=fill,cost=cost,
                            quantity=experiment.shares,entry_fee=fill*experiment.shares*experiment.entry_fee_rate,
                            entry_slippage=(fill-s.open)*experiment.shares,
                            stop_reference=order['stop_reference'],factor_reference=factor,quarantined=False,
                            signal_id=order.get('signal_id'),entry_gap_from_signal=fill/order['signal_close']-1,
                            maximum_favorable=Decimal(0),maximum_adverse=Decimal(0),excursions_complete=True)
                        cash-=cost;pending.pop(code)
                        record['actions'].append('SIMULATED_BUY_NEXT_OPEN')
            elif position and date>position['entry_date']:
                fill=s.open*(1-experiment.slippage_rate) if s.open is not None else None
                if not executable or fill<=s.down_limit or fill>=s.up_limit:
                    record['actions'].append('EXIT_PENDING_LIMIT_SUSPENSION_OR_UNKNOWN')
                else:
                    proceeds=fill*experiment.shares*(1-experiment.exit_fee_rate)
                    pnl=proceeds-position['cost'];cash+=proceeds
                    position['maximum_favorable']=max(position['maximum_favorable'],s.open/position['entry']-1)
                    position['maximum_adverse']=min(position['maximum_adverse'],s.open/position['entry']-1)
                    trades.append(dict(code=code,entry_date=position['entry_date'],exit_date=date,
                        quantity=experiment.shares,entry_price=str(position['entry']),exit_price=str(fill),
                        entry_cost_cny=str(position['cost']),exit_proceeds_cny=str(proceeds),
                        entry_fee_cny=str(position['entry_fee']),exit_fee_cny=str(fill*experiment.shares*experiment.exit_fee_rate),
                        entry_slippage_cny=str(position['entry_slippage']),exit_slippage_cny=str((s.open-fill)*experiment.shares),
                        pnl_cny=str(pnl),return_net=str(pnl/position['cost']),reason=order['reason'],
                        all_exit_triggers=order.get('all_exit_triggers',[order['reason']]),
                        holding_sessions=indices[code]-position['entry_i'],signal_id=position['signal_id'],
                        entry_deviation_from_signal=str(position['entry_gap_from_signal']),
                        exit_deviation_from_signal=str(fill/order['signal_close']-1) if order['signal_close'] else None,
                        maximum_favorable_price_return=str(position['maximum_favorable']) if position['excursions_complete'] else None,
                        maximum_adverse_price_return=str(position['maximum_adverse']) if position['excursions_complete'] else None,
                        observed_mfe_lower_bound=str(position['maximum_favorable']),
                        observed_mae_upper_bound=str(position['maximum_adverse']),
                        excursions_complete=position['excursions_complete']))
                    positions.pop(code);pending.pop(code)
                    record['actions'].append('SIMULATED_SELL_T_PLUS_1')
        for s in values:
            code=s.code;record=records[code];position=positions.get(code)
            if position:
                # Excursions use only sessions while exposed; no exit-day post-sale high/low.
                high=getattr(s,'high',None) or s.close
                low=getattr(s,'low',None) or s.close
                if getattr(s,'high',None) is None or getattr(s,'low',None) is None:
                    position['excursions_complete']=False
                if not position['quarantined'] and high is not None and low is not None:
                    position['maximum_favorable']=max(position['maximum_favorable'],high/position['entry']-1)
                    position['maximum_adverse']=min(position['maximum_adverse'],low/position['entry']-1)
                age=indices[code]-position['entry_i']+1
                if age in review_sessions:
                    record['actions'].append(f'RESEARCH_REVIEW_DUE_{age}')
                if s.close is None:
                    record['actions'].append('HOLDING_PRICE_UNKNOWN')
                elif s.ma20 is None:
                    record['actions'].append('HOLDING_TREND_CHECK_UNKNOWN')
                if code not in pending and not position['quarantined']:
                    reasons=[]
                    if s.close is not None and position['stop_reference'] is not None and s.close<position['stop_reference']:
                        reasons.append('INITIAL_REFERENCE_BROKEN')
                    if s.close is not None and s.ma20 is not None and s.close<s.ma20:
                        reasons.append('TREND_REVIEW')
                    if age>=experiment.time_exit_sessions:
                        reasons.append('TIME_REVIEW')
                    if reasons:
                        pending[code]=dict(side='SELL',reason=reasons[0],all_exit_triggers=reasons,signal_close=s.close)
            decision=entry_decision(s,code in positions or code in pending)
            if decision.get('observation') is not None:
                record['setup']=decision['observation']
            if code not in positions and code not in pending and decision.get('buy') is not None:
                order=decision['buy']
                factor=getattr(s,'adjustment_factor',Decimal(1))
                if factor is None or account_blocked:
                    record['actions'].append('CANCEL_SETUP_UNMODELED_ACTION_OR_ACCOUNT')
                else:
                    pending[code]={**order,'side':'BUY','factor_reference':factor}
                    record['actions'].append(decision.get('action','STRATEGY_CLOSE_OBSERVATION'))
        unknown=[]
        for code,position in positions.items():
            s=today.get(code)
            if s is None or s.close is None or position['quarantined']:
                unknown.append(code)
        equity=None if unknown else cash+sum((today[code].close*experiment.shares for code in positions),Decimal(0))
        if equity is not None:
            peak=max(peak,equity);drawdown=max(drawdown,(peak-equity)/peak)
        else:
            valuation_complete=False
        daily.append(dict(date=date,cash_ledger_cny=str(cash),equity_cny=str(equity) if equity is not None else None,
                          unknown_valuation_codes=sorted(unknown)))
        for s in values:
            record=records[s.code]
            record.update(marked_lab_equity_cny=str(equity) if equity is not None else None,
                          pending=_wire(pending.get(s.code)))
            logs.append(record)
    returns=[Decimal(t['return_net']) for t in trades]
    return dict(trades=trades,sessions=logs,daily_equity=daily,cash_ledger_cny=str(cash),
        open_positions=_wire(positions),pending=_wire(pending),
        win_rate=str(Decimal(sum(r>0 for r in returns))/len(returns)) if returns else None,
        average_net_return=str(sum(returns)/len(returns)) if returns else None,
        lab_mark_to_market_max_drawdown=str(drawdown) if valuation_complete else None,
        known_marks_drawdown_lower_bound=str(drawdown),valuation_complete=valuation_complete,
        execution_convention='SAME_OPEN_SELLS_THEN_BUYS_CODE_ORDER; FIXED_LOT; NO_PARTIAL_FILLS',
        actual_user_pnl=None,strategy_effectiveness='NOT_VALIDATED')
