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
    from astock.backtest.execution import run_execution
    def entry(session, active):
        executable = (session.suspended is False and session.st is False and session.liquidity_confirmed is True and
                      session.up_limit is not None and session.down_limit is not None and session.volume is not None and session.volume > 0)
        signal = (not active and executable and session.market_allowed is True and session.prior_high20 is not None and
                  session.prior_low20 is not None and session.ma60 is not None and
                  session.close > session.prior_high20 and session.close > session.ma60)
        return dict(buy=dict(stop_reference=session.prior_low20, signal_close=session.close) if signal else None,
                    action='BREAKOUT_CLOSE_OBSERVATION')
    result = run_execution(sessions, experiment, entry)
    trade_fields = ('entry_date', 'exit_date', 'pnl_cny', 'return_net', 'reason',
                    'entry_deviation_from_signal', 'exit_deviation_from_signal')
    pending_fields = {'side', 'reason', 'signal_close', 'stop_reference'}
    legacy_sessions = [{**record, 'actions':[action for action in record['actions'] if action != 'HOLDING_TREND_CHECK_UNKNOWN'],
                        'pending':{k:v for k,v in record['pending'].items() if k in pending_fields}
                        if record['pending'] else None} for record in result['sessions']]
    return dict(protocol='BREAKOUT_FORWARD_LAB_RESULT_V0', mode='OFFLINE_SYNTHETIC_MECHANICS_ONLY',
                experiment=experiment.model_dump(mode='json'),
                trades=[{key:trade[key] for key in trade_fields} for trade in result['trades']], sessions=legacy_sessions,
                win_rate=result['win_rate'], average_net_return=result['average_net_return'],
                lab_mark_to_market_max_drawdown=result['lab_mark_to_market_max_drawdown'],
                unclosed_position=bool(result['open_positions']), actual_user_pnl=None, strategy_effectiveness='NOT_VALIDATED',
                limitations=['合成输入只证明流程；非历史回测/真实成交', '费用及滑点为固定实验假设，不是核实的券商费率',
                             '涨跌停附近/停牌/未知状态拒绝成交；跳空仍按可执行下一开盘计价，不假设止损价成交',
                             '实验100股、名义本金及5交易日复核只适用模拟主板案例，未授权用户仓位与风险',
                             '前瞻实行情验证仍需新数据、交易状态及规则；当前上市池不证明无幸存者偏差'])
