"""A deterministic fictitious calendar and prices for mechanism demonstration only."""
from datetime import timedelta
from decimal import Decimal

from astock.backtest.strategy_lab import LabSession, ThreeRuleExperiment
from astock.features.strategy import strategy_frames
from astock.research.core import digest, instant, market_day
from astock.screening.strategy_models import StrategyParameters


def synthetic_scenario(parameters: StrategyParameters, experiment: ThreeRuleExperiment,
                       *, closes: list[Decimal] | None = None) -> list[LabSession]:
    """Not provider-shaped fake facts: every record and calendar is explicitly synthetic."""
    start=market_day(max(parameters.frozen_at,instant(experiment.frozen_at)))+timedelta(days=1)
    default_path = closes is None
    closes=closes if closes is not None else [Decimal(10)]*45+[Decimal(11)]*24+[Decimal('11.3'),Decimal('11.5'),Decimal('10.2'),
        Decimal('9.9'),Decimal('10.1'),Decimal('10.2'),Decimal('11.3'),Decimal('11.5'),
        Decimal(9),Decimal('8.5'),Decimal('8.4')]
    code='SYNTHETIC-STOCK-1'
    identity=dict(code=code,name='全合成公司（非真实行情）',kind='STOCK',exchange='SSE',
                  provider_market='主板',list_date=start.isoformat(),source_hash=digest(['SYNTHETIC_IDENTITY',code]))
    index=dict(code='SYNTHETIC_INDEX',name='全合成基准',kind='INDEX',exchange='SSE',source_hash=digest(['SYNTHETIC_INDEX']))
    rows=dict(instruments=[identity,index],calendar=[],daily=[],adj_factor=[],index_daily=[],status=[])
    sessions=[]
    for i,close in enumerate(closes):
        date=(start+timedelta(days=i)).isoformat()
        # Every civil day is explicitly declared an open day in this fictitious calendar.
        rows['calendar'].append(dict(exchange='SSE',date=date,is_open=1,source_hash=digest(['SYNTHETIC_CALENDAR',date])))
        opening=closes[i-1] if i else close
        if default_path and i==72:opening=Decimal('9.8')
        if default_path and i==79:opening=Decimal('8.4')
        high=max(opening,close)+Decimal('0.1');low=min(opening,close)-Decimal('0.1')
        body=dict(code=code,date=date,open=opening,high=high,low=low,close=close,volume=2000000,amount=close*2000000)
        rows['daily'].append({**body,'source_hash':digest(['SYNTHETIC_PRICE',date,{k:str(v) for k,v in body.items()}])})
        rows['adj_factor'].append(dict(code=code,date=date,adj_factor=1,source_hash=digest(['SYNTHETIC_FACTOR',date,1])))
        rows['index_daily'].append(dict(code=index['code'],date=date,open=10,close=10,high=Decimal('10.1'),low=Decimal('9.9'),
            volume=2000000,amount=20000000,source_hash=digest(['SYNTHETIC_BENCHMARK',date])))
        rows['status'].append(dict(code=code,date=date,st='NO',suspended='NO',up_limit=20,down_limit=5,
                                   source_hash=digest(['SYNTHETIC_CLOSE_STATUS',date])))
        manifest=dict(purpose='CURRENT_OBSERVATION',window_start=start.isoformat(),window_end=date,
                      universe=[code],benchmarks=[index['code']])
        frame=strategy_frames(manifest,rows,date+'T16:00:00+08:00',date,parameters)[0]
        frame=frame.model_copy(update={'knowledge_basis':'OFFLINE_SYNTHETIC'})
        sessions.append(LabSession(date=date,available_at=date+'T16:00:00+08:00',
            execution_status_available_at=date+'T09:00:00+08:00',code=code,exchange_board='SSE_MAIN',
            open=opening,close=close,high=high,low=low,market_allowed=True,adjustment_factor=1,
            suspended=default_path and i==78,st=False,up_limit=20,down_limit=5,volume=2000000,liquidity_confirmed=True,
            source_grade='OFFLINE_SYNTHETIC',source_hash=digest(['SYNTHETIC_EXECUTION_PACKET',date]),frame=frame))
    return sessions
