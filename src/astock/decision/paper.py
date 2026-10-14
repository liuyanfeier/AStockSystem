"""A fixed prospective Breakout experiment; simulation fills only, no broker interface."""
from decimal import Decimal

from pydantic import Field, model_validator
from astock.company.models import Strict
from astock.research.core import day, instant, market_day, require


class Experiment(Strict):
    protocol: str = 'BREAKOUT_FORWARD_LAB_V0'
    frozen_at: str
    simulation_only: bool = True
    shares: int = Field(default=100, ge=100)
    entry_fee_rate: Decimal = Field(default=Decimal('0.0003'), ge=0)
    exit_fee_rate: Decimal = Field(default=Decimal('0.0008'), ge=0)
    slippage_rate: Decimal = Field(default=Decimal('0.001'), ge=0, lt=1)
    time_exit_sessions: int = Field(default=5, ge=1)
    nominal_lab_cash: Decimal = Field(default=Decimal('100000'), gt=0)

    @model_validator(mode='after')
    def lab_boundary(self):
        instant(self.frozen_at)
        require(self.simulation_only and self.shares % 100 == 0, 'PAPER_ONLY_MAIN_BOARD_LOT')
        for v in (self.entry_fee_rate,self.exit_fee_rate,self.slippage_rate,self.nominal_lab_cash):
            require(v.is_finite(), 'PAPER_NONFINITE_PARAMETER')
        return self


class Session(Strict):
    date: str
    available_at: str
    execution_status_available_at: str
    code: str
    exchange_board: str
    open: Decimal = Field(gt=0, allow_inf_nan=False)
    close: Decimal = Field(gt=0, allow_inf_nan=False)
    ma20: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    ma60: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    prior_high20: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    prior_low20: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    market_allowed: bool | None
    suspended: bool | None
    st: bool | None
    up_limit: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    down_limit: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    volume: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    liquidity_confirmed: bool | None
    source_grade: str
    source_hash: str = Field(pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def session_time(self):
        from datetime import datetime, time
        from zoneinfo import ZoneInfo
        require(market_day(instant(self.available_at)) == day(self.date), 'PAPER_SESSION_TIME')
        local_day=day(self.date)
        close=datetime.combine(local_day,time(15),ZoneInfo('Asia/Shanghai'))
        opening=datetime.combine(local_day,time(9,30),ZoneInfo('Asia/Shanghai'))
        require(instant(self.available_at)>=instant(close) and instant(self.execution_status_available_at)<=instant(opening), 'PAPER_LOOKAHEAD_STATUS_OR_CLOSE')
        return self


def simulate(sessions: list[Session], experiment: Experiment) -> dict:
    require(bool(sessions) and len({s.code for s in sessions}) == 1, 'PAPER_SINGLE_COMPANY')
    require(all(s.exchange_board in ('SSE_MAIN','SZSE_MAIN') for s in sessions), 'PAPER_BOARD_NOT_MODELED')
    require([s.date for s in sessions] == sorted({s.date for s in sessions}), 'PAPER_SESSION_ORDER')
    require(all(instant(experiment.frozen_at) < instant(s.available_at) for s in sessions), 'PAPER_PARAMETERS_AFTER_SAMPLE')
    # This V0 lab proves mechanics with marked synthetic sessions, never reports a historical strategy return.
    require(all(s.source_grade == 'OFFLINE_SYNTHETIC' for s in sessions), 'PAPER_REAL_HISTORY_NOT_ADMITTED')
    pending, position, trades, log = None, None, [], []
    cash = experiment.nominal_lab_cash
    peak, drawdown = cash, Decimal(0)
    for i,s in enumerate(sessions):
        record = dict(date=s.date, code=s.code, source_hash=s.source_hash, actions=[])
        executable = (s.suspended is False and s.st is False and s.liquidity_confirmed is True and
                      s.up_limit is not None and s.down_limit is not None and s.volume is not None and s.volume > 0)
        if pending:
            side = pending['side']
            # Orders are based solely on the preceding close; unknown states never imply executable.
            if side == 'BUY' and not executable:
                record['actions'].append('CANCEL_SETUP_UNKNOWN_OR_UNTRADABLE');pending=None
            elif side == 'BUY':
                fill = s.open*(1+experiment.slippage_rate)
                cost = fill*experiment.shares*(1+experiment.entry_fee_rate)
                if fill >= s.up_limit or fill <= s.down_limit or cost > cash:
                    record['actions'].append('CANCEL_SETUP_LIMIT_GAP_OR_LAB_CASH');pending=None
                else:
                    position=dict(entry_date=s.date, entry_i=i, entry=fill, cost=cost, stop_reference=pending['stop_reference'],
                                  entry_gap_from_signal=fill/pending['signal_close']-1)
                    cash-=cost;pending=None;record['actions'].append('SIMULATED_BUY_NEXT_OPEN')
            elif position and s.date > position['entry_date']:
                fill=s.open*(1-experiment.slippage_rate)
                if not executable or fill <= s.down_limit or fill >= s.up_limit:
                    record['actions'].append('EXIT_PENDING_LIMIT_SUSPENSION_OR_UNKNOWN')
                else:
                    proceeds=fill*experiment.shares*(1-experiment.exit_fee_rate)
                    pnl=proceeds-position['cost'];cash+=proceeds
                    trades.append(dict(entry_date=position['entry_date'], exit_date=s.date,
                                       pnl_cny=str(pnl), return_net=str(pnl/position['cost']), reason=pending['reason'],
                                       entry_deviation_from_signal=str(position['entry_gap_from_signal']),
                                       exit_deviation_from_signal=str(fill/pending['signal_close']-1)))
                    position=None;pending=None;record['actions'].append('SIMULATED_SELL_T_PLUS_1')
        if position and pending is None:
            reason = ('INITIAL_REFERENCE_BROKEN' if position['stop_reference'] is not None and s.close < position['stop_reference']
                      else 'TREND_REVIEW' if s.ma20 is not None and s.close < s.ma20
                      else 'TIME_REVIEW' if i-position['entry_i']+1 >= experiment.time_exit_sessions else None)
            if reason:pending=dict(side='SELL',reason=reason,signal_close=s.close)
        elif position is None and pending is None:
            signal=(executable and s.market_allowed is True and s.prior_high20 is not None and s.prior_low20 is not None and s.ma60 is not None
                    and s.close > s.prior_high20 and s.close > s.ma60)
            if signal:pending=dict(side='BUY',stop_reference=s.prior_low20,signal_close=s.close);record['actions'].append('BREAKOUT_CLOSE_OBSERVATION')
        equity=cash+(s.close*experiment.shares if position else 0)
        peak=max(peak,equity);drawdown=max(drawdown,(peak-equity)/peak)
        record.update(marked_lab_equity_cny=str(equity), pending={k:str(v) if isinstance(v,Decimal) else v for k,v in pending.items()} if pending else None)
        log.append(record)
    returns=[Decimal(t['return_net']) for t in trades]
    return dict(protocol='BREAKOUT_FORWARD_LAB_RESULT_V0', mode='OFFLINE_SYNTHETIC_MECHANICS_ONLY',
                experiment=experiment.model_dump(mode='json'), trades=trades, sessions=log,
                win_rate=str(Decimal(sum(r>0 for r in returns))/len(returns)) if returns else None,
                average_net_return=str(sum(returns)/len(returns)) if returns else None,
                lab_mark_to_market_max_drawdown=str(drawdown), unclosed_position=position is not None,
                actual_user_pnl=None, strategy_effectiveness='NOT_VALIDATED',
                limitations=['合成输入只证明流程；非历史回测/真实成交', '费用及滑点为固定实验假设，不是核实的券商费率',
                             '涨跌停附近/停牌/未知状态拒绝成交；跳空仍按可执行下一开盘计价，不假设止损价成交',
                             '实验100股、名义本金及5交易日复核只适用模拟主板案例，未授权用户仓位与风险',
                             '前瞻实行情验证仍需新数据、交易状态及规则；当前上市池不证明无幸存者偏差'])
