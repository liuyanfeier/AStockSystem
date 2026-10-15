"""Three source-bound hypotheses share one synthetic execution ledger."""
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from astock.backtest.execution import run_execution
from astock.decision.paper import Experiment, Session
from astock.research.core import day, digest, instant, require
from astock.screening.strategies import evaluate_strategy, strategy_code_hash
from astock.screening.strategy_models import StrategyFrame, StrategyParameters


class ThreeRuleExperiment(Experiment):
    protocol: Literal['THREE_RULE_SYNTHETIC_LAB_V1']
    simulation_only: Literal[True] = True
    time_exit_sessions: int = Field(default=20, ge=1)
    entry_fee_rate: Decimal = Field(ge=0,lt=1,allow_inf_nan=False)
    exit_fee_rate: Decimal = Field(ge=0,lt=1,allow_inf_nan=False)
    review_sessions: tuple[int,...]
    execution_order: Literal['SAME_OPEN_SELLS_THEN_BUYS_CODE_ORDER']
    higher_cost_multiplier: Decimal = Field(gt=1, allow_inf_nan=False)
    fee_basis: Literal['SYNTHETIC_FIXED_RATE_NO_VERIFIED_MINIMUM_OR_TAX_SCHEDULE']

    @model_validator(mode='after')
    def research_only(self):
        require(self.shares==100,'STRATEGY_LAB_FIXED_100_SHARES')
        require(list(self.review_sessions)==sorted(set(self.review_sessions)) and
                all(0<i<self.time_exit_sessions for i in self.review_sessions),'STRATEGY_LAB_REVIEW_SESSIONS')
        require(self.slippage_rate*self.higher_cost_multiplier<1,'STRATEGY_LAB_COST_SENSITIVITY')
        return self


class LabSession(Session):
    """All execution facts are declared synthetic and available by the stated open."""
    source_grade: Literal['OFFLINE_SYNTHETIC']
    open: Decimal | None = Field(default=None,gt=0,allow_inf_nan=False)
    close: Decimal | None = Field(default=None,gt=0,allow_inf_nan=False)
    high: Decimal | None = Field(default=None,gt=0,allow_inf_nan=False)
    low: Decimal | None = Field(default=None,gt=0,allow_inf_nan=False)
    adjustment_factor: Decimal | None = Field(default=None,gt=0,allow_inf_nan=False)
    frame: StrategyFrame | None = None

    @model_validator(mode='after')
    def frame_binding(self):
        require(self.date==day(self.date).isoformat(),'STRATEGY_LAB_CANONICAL_DATE')
        if self.high is not None and self.low is not None:
            require(self.low<=self.high,'STRATEGY_LAB_HIGH_LOW')
        for quote in (self.open,self.close):
            if quote is not None:
                require((self.high is None or quote<=self.high) and (self.low is None or quote>=self.low),
                        'STRATEGY_LAB_OHLC_BOUNDS')
        if self.frame:
            require(self.frame.knowledge_basis=='OFFLINE_SYNTHETIC','STRATEGY_LAB_FRAME_NOT_SYNTHETIC')
            require(self.frame.code==self.code and self.frame.market_date==self.date and
                    self.frame.as_of==instant(self.available_at),'STRATEGY_LAB_FRAME_TIME_CODE')
            if self.frame.bars:
                require(self.close==self.frame.bars[-1].close,'STRATEGY_LAB_FRAME_CLOSE')
        return self


def _empty_frame(session: LabSession) -> StrategyFrame:
    return StrategyFrame(code=session.code,name='合成缺窗口样本',as_of=session.available_at,
        market_date=session.date,required_market_date=session.date,
        board=session.exchange_board if session.exchange_board in ('SSE_MAIN','SZSE_MAIN') else 'UNMODELED',
        price_basis='UNKNOWN',bars=[],knowledge_basis='OFFLINE_SYNTHETIC',source_hashes=[session.source_hash],
        st=session.st,suspended=session.suspended,up_limit=session.up_limit,down_limit=session.down_limit,volume=session.volume)


def _run(sessions: list[LabSession], parameters: StrategyParameters,
          experiment: ThreeRuleExperiment, variant: str) -> dict:
    normalized=[]
    for session in sessions:
        frame=session.frame or _empty_frame(session)
        value=evaluate_strategy(frame,parameters,variant)
        low=min(b.low for b in frame.bars[-parameters.return_sessions-1:-1]) if len(frame.bars)>=parameters.return_sessions+1 else None
        normalized.append(session.model_copy(update={'ma20':Decimal(value['metrics']['ma_fast']) if value['metrics']['ma_fast'] else None,
            'ma60':Decimal(value['metrics']['ma_slow']) if value['metrics']['ma_slow'] else None,'prior_low20':low}))
    def entry(session: LabSession,active: bool) -> dict:
        frame=session.frame or _empty_frame(session)
        observation=evaluate_strategy(frame,parameters,variant,already_active=active)
        buy=None
        if observation['paper_ready'] and session.close is not None and session.prior_low20 is not None:
            buy=dict(stop_reference=session.prior_low20,signal_close=session.close,signal_id=observation['id'])
        return dict(observation=observation,buy=buy,action=f'{variant}_CLOSE_OBSERVATION')
    result=run_execution(normalized,experiment,entry,review_sessions=experiment.review_sessions)
    observations=[record['setup'] for record in result['sessions']]
    return dict(variant=variant,experiment=experiment.model_dump(mode='json'),
        opportunity_counts=dict(total=len(observations),unknown=sum(o['condition_match'] is None for o in observations),
            matching=sum(o['condition_match'] is True for o in observations),first=sum(o['first_match'] is True for o in observations),
            canceled=sum(a.startswith('CANCEL_SETUP') for r in result['sessions'] for a in r['actions']),
            entry_fills=sum('SIMULATED_BUY_NEXT_OPEN' in r['actions'] for r in result['sessions']),
            closed_trades=len(result['trades'])),**result)


def compare_strategies(sessions: list[LabSession], parameters: StrategyParameters,
                        experiment: ThreeRuleExperiment) -> dict:
    require(bool(sessions),'PAPER_EMPTY_SESSIONS')
    # model_copy(update=...) bypasses Pydantic validation; bind all packets again at the execution boundary.
    sessions=[LabSession.model_validate(s.model_dump(mode='json')) for s in sessions]
    parameters=StrategyParameters.model_validate(parameters.model_dump(mode='json'))
    experiment=ThreeRuleExperiment.model_validate(experiment.model_dump(mode='json'))
    require(instant(experiment.frozen_at)>=parameters.frozen_at,'STRATEGY_LAB_PARAMETER_ORDER')
    require([(s.date,s.code) for s in sessions]==sorted({(s.date,s.code) for s in sessions}),'STRATEGY_LAB_SESSION_ORDER')
    # A missing quote must be an explicit missing-price session, not an omitted held day.
    codes={s.code for s in sessions}
    dates={s.date for s in sessions}
    require(len(sessions)==len(codes)*len(dates),'STRATEGY_LAB_COMPLETE_SYNTHETIC_GRID')
    require(all(s.frame is None or s.frame.knowledge_basis=='OFFLINE_SYNTHETIC' for s in sessions),
            'STRATEGY_LAB_FRAME_NOT_SYNTHETIC')
    high=ThreeRuleExperiment.model_validate({**experiment.model_dump(mode='json'),
        'entry_fee_rate':str(experiment.entry_fee_rate*experiment.higher_cost_multiplier),
        'exit_fee_rate':str(experiment.exit_fee_rate*experiment.higher_cost_multiplier),
        'slippage_rate':str(experiment.slippage_rate*experiment.higher_cost_multiplier)})
    results={v:_run(sessions,parameters,experiment,v) for v in parameters.variants}
    sensitivity={v:_run(sessions,parameters,high,v) for v in parameters.variants}
    package=Path(__file__).resolve().parents[1]
    execution_hash=digest({name:sha256((package/name).read_bytes()).hexdigest() for name in
        ('backtest/execution.py','backtest/strategy_lab.py','decision/paper.py')})
    return dict(protocol='THREE_RULE_LAB_RESULT_V1',mode='OFFLINE_SYNTHETIC_MECHANICS_ONLY',
        strategy_parameters=parameters.model_dump(mode='json'),parameters_hash=digest(parameters.model_dump(mode='json')),
        code_hash=strategy_code_hash(),execution_code_hash=execution_hash,experiment=experiment.model_dump(mode='json'),
        experiment_hash=digest(experiment.model_dump(mode='json')),input_hash=digest([s.model_dump(mode='json') for s in sessions]),
        results=results,higher_cost_results=sensitivity,actual_user_pnl=None,strategy_effectiveness='NOT_VALIDATED',
        limitations=['全部为合成机制验证，不是历史回测、真实前瞻收益或用户成交',
            '三组共用同一规则计算与执行内核，各有独立实验现金；同开盘先卖后买、代码优先占用资金',
            '实验100股单位；不加仓、不透支、不模型化部分成交或真实订单簿',
            '费用/滑点是假设，未核实最低佣金、税费和有效日期；较高成本结果同时保留',
            '未知开盘/状态拒绝入场；退出阻断保留持仓，T+1和跳空不假设止损价成交',
            '公司行为/因子变化未建模时隔离持仓，组合估值和回撤保持未知；不自动重算股数或现金',
            '高低价缺失时完整MFE/MAE未知，只保留已观察价格界限；退出日只使用开盘，不偷看卖出后价格',
            '组合回撤只按每日收盘估值计算，不是盘中最大回撤；任何持仓日估值未知则完整回撤未知',
            '未加入行业择时或AI回填；真实验证需逐日来源/可知时间、完整交易规则和样本外证据'])
