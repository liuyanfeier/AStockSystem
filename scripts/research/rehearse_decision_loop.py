"""Finite offline delivery rehearsal from retained V2/V3, no HTTP or old-store writes.

Run once to prepare versioned inputs; reruns use the frozen public input files.
The generated simulated positions/events are invented lab records, never user records.
"""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from pathlib import Path

from astock.company.models import ResearchCatalog
from astock.company.workflow import verified_market_context
from astock.decision.models import RunInput, PositionScope
from astock.decision.workflow import compare, persist, verified_catalog
from astock.decision.portfolio import portfolio_report
from astock.decision.report import publish_public, publish_private
from astock.decision.paper import Experiment, Session, simulate
from astock.research.core import digest, encoded, read_json
from astock.research.store import ResearchStore
from astock.research.publication import publish_bytes
from astock.research.journal import append_event

ROOT=Path(__file__).resolve().parents[2]
PUBLIC=ROOT/'docs/research/results/2026-10-14-decision-loop-v0'
PRIVATE=ROOT/'data/private/research-v1/decision-loop-v0'
CONFIG=ROOT/'config/decision-loop'
BASE_CATALOG=ROOT/'config/research/company-evidence-20261014.json'
DOCUMENTS=ROOT/'data/private/research-v3/2026-10-14-documents'
MARKET_FILE=ROOT/'docs/research/results/2026-10-14-real-market-v2/0d235e75a112e3e3a03da497c51fd550ea3551e9c80d3f247dd92a5e363db9ef.json'
BASE_STORE=ROOT/'data/private/research-v1/market-v2-20261013-002/research.duckdb'


def freeze(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);publish_bytes(path,encoded(value)+b'\n')


def prepare():
    if (CONFIG/'real-run.json').exists():return
    previous=ResearchCatalog.model_validate(read_json(BASE_CATALOG));market=read_json(MARKET_FILE)
    now=datetime.now(timezone.utc);created=now.isoformat();due=(now+timedelta(days=1)).isoformat()
    latest=previous.model_dump(mode='json');latest['as_of']=created
    # A new observation of retained documents, explicitly not a new disclosure or a historical judgment.
    freeze(CONFIG/'rechecked-catalog.json',latest)
    plans=[]
    specs={
        '600036.SH':('研究资产质量与盈利韧性是否持续；目前仅有限指标支持，不证明无信用风险',
                    [('asset_quality','H1_npl','NOT_HIGHER','不良率是否恶化','INVALIDATION_REVIEW'),('capital','H1_cet1','NOT_LOWER','资本约束是否恶化','CHALLENGED')],None),
        '000002.SZ':('研究风险处置能否改善偿债与交付；不预设困境反转成功',
                    [('cash_delivery','H1_cfo','POSITIVE','现金回款是否足以支撑经营需要进一步核查','INVALIDATION_REVIEW')],
                    '持续经营重大不确定性、展期履约与受限现金尚未充分核实'),
        '601872.SH':('研究周期盈利能否转为持续现金回款，不能将半年利润直接年化',
                    [('cash_conversion','H1_cfo','POSITIVE','现金回款是否保持正向','CHALLENGED'),('earning','H1_parent_profit','POSITIVE','周期盈利是否持续','CHALLENGED')],None)}
    for code,(thesis,criteria,pending) in specs.items():
        company=next(c for c in previous.companies if c.code==code)
        plans.append(dict(code=code,baseline_catalog_hash=digest(previous.model_dump(mode='json')),
                          baseline_market_hash=digest(market),baseline_market_date=market['window_end'],baseline_market_bundle_id=market['bundle_id'],
                          thesis=thesis,attention_reason=company.priority_reason,
                          no_trade_reasons=['没有审核完成的估值/可交易性与用户风险计划'],
                          observable_checks=company.next_checks,invalidation_conditions=company.thesis_invalidations,
                          unresolved_material_risk=pending,
                          criteria=[dict(id=i,metric_id=m,expectation=e,reason=r,failure=f) for i,m,e,r,f in criteria],
                          created_at=created,review_due=due))
    run=dict(protocol='DECISION_LOOP_V0',mode='REAL_EVIDENCE',observed_at=datetime.now(timezone.utc).isoformat(),
             required_market_date='2026-10-14',plans=plans)
    freeze(CONFIG/'real-run.json',run)
    simulated=deepcopy(run);simulated.update(mode='OFFLINE_SIMULATION',observed_at=(now+timedelta(days=2)).isoformat())
    simulated['simulation_events']=[
        dict(code='601872.SH',criterion_id='cash_conversion',state='UNKNOWN',explanation='离线模拟：新回款信息未取得；不认定实际发生',available_at=simulated['observed_at'],provenance='OFFLINE_SIMULATION_NOT_DISCLOSURE'),
        dict(code='000002.SZ',criterion_id='cash_delivery',state='INVALIDATION_REVIEW',explanation='离线模拟：重要债务条款未履行，挑战现金交付逻辑；并非真实公告',available_at=simulated['observed_at'],provenance='OFFLINE_SIMULATION_NOT_DISCLOSURE')]
    freeze(CONFIG/'simulated-run.json',simulated)
    ended=deepcopy(simulated);ended['observed_at']=(now+timedelta(days=3)).isoformat()
    ended['review_actions']=[dict(code='601872.SH',action='END_WATCH',reason='离线模拟：在证据缺口未解决时结束本轮观察，保留复盘',recorded_at=ended['observed_at'],confirmed=True,provenance='OFFLINE_SIMULATION_NOT_USER_ACTION')]
    freeze(CONFIG/'simulated-end-run.json',ended)
    freeze(CONFIG/'breakout-forward-protocol.json',Experiment(frozen_at=created).model_dump(mode='json'))


def main():
    prepare()
    if not (CONFIG/'simulated-baseline-run.json').exists():
        initial=read_json(CONFIG/'real-run.json');initial['mode']='OFFLINE_SIMULATION'
        freeze(CONFIG/'simulated-baseline-run.json',initial)
    store_hash=sha256(BASE_STORE.read_bytes()).hexdigest()
    market=read_json(MARKET_FILE);members=verified_market_context(market,ResearchStore(BASE_STORE))
    previous=verified_catalog(read_json(BASE_CATALOG),DOCUMENTS)
    latest=verified_catalog(read_json(CONFIG/'rechecked-catalog.json'),DOCUMENTS)
    checks=[]
    for scenario in ('real','simulated-baseline','simulated','simulated-end'):
        run=RunInput.model_validate(read_json(CONFIG/f'{scenario}-run.json'))
        mode='real' if scenario=='real' else 'simulated'
        working=PRIVATE/mode/'v3'
        loop=ResearchStore(working/'journal.duckdb')
        report=compare(run,previous,latest,market,members)
        review_id=persist(report,loop,working/'events')
        scope=None
        if mode=='simulated':
            ids=[]
            for code,shares in [('600036.SH',100),('000002.SZ',200),('601872.SH',100)]:
                event=dict(event_id='SIMULATED_POSITION_'+code,kind='POSITION',code=code,shares=shares,
                           event_at=run.plans[0].created_at,recorded_at=run.plans[0].created_at,
                           thesis='离线模拟持仓，非用户持仓',invalidation='以对应研究计划复核',exit_conditions='逻辑失效只提醒',
                           review_due=run.plans[0].review_due,confirmed=False,notes='OFFLINE_SIMULATED_NOT_USER_ACCOUNT')
                path=working/(event['event_id']+'.json');freeze(path,event);append_event(loop,path);ids.append(event['event_id'])
            scope=PositionScope(mode='SIMULATED',snapshot_at=run.plans[0].created_at,position_event_ids=ids,
                                complete_positions_confirmed=False,cash_cny=None)
            freeze(working/'scope.json',scope.model_dump(mode='json'))
            for card in report['cards']:
                manual=dict(event_id=digest([review_id,card['code'],'SIMULATED_MANUAL_REVIEW']),kind='REVIEW',code=card['code'],
                            event_at=report['as_of'],recorded_at=report['as_of'],research_report_id=review_id,
                            confirmed=False,notes='OFFLINE_SIMULATED_MANUAL_CHECK_NOT_USER_ACTION；'+card['state_text']+'；不产生实际订单')
                path=working/'events'/f"{manual['event_id']}.json";freeze(path,manual);append_event(loop,path)
        report['portfolio']=portfolio_report(loop,market,report,scope)
        if scenario=='simulated-end':
            reviewed_at=(datetime.fromisoformat(report['as_of'])+timedelta(minutes=2)).isoformat()
            for card in report['cards']:
                review=dict(event_id=digest([review_id,card['code'],'SIMULATED_POST_ACTION_REVIEW']),kind='REVIEW',code=card['code'],
                            event_at=reviewed_at,recorded_at=reviewed_at,research_report_id=review_id,confirmed=False,
                            notes='OFFLINE_SIMULATED_POST_ACTION_REVIEW_NOT_USER_HISTORY；变化原因归于证据缺口/研究检查；无真实交易，盈利归因和实际执行偏差UNKNOWN；下一步核查原始披露与新价格')
                path=working/'events'/f"{review['event_id']}.json";freeze(path,review);append_event(loop,path)
        private_hash=publish_private(report,working/scenario)
        public_hash=publish_public(report,ROOT,PUBLIC/scenario)
        checks.append(dict(scenario=scenario,mode=run.mode,public_hash=public_hash,private_hash=private_hash,
                           states={c['code']:c['state'] for c in report['cards']},portfolio_mode=report['portfolio']['mode'],
                           account_assets_computed=report['portfolio']['account_assets_cny'] is not None,
                           simulated_manual_actions={c['code']:c['state_text'] for c in report['cards']} if mode=='simulated' else {},
                           true_user_actions=0,orders=0))
    experiment=Experiment.model_validate(read_json(CONFIG/'breakout-forward-protocol.json'))
    values=[('2026-10-15',10,12,9),('2026-10-16',12,9,10),('2026-10-19',8,8,10)]
    sessions=[Session(date=d,available_at=d+'T16:00:00+08:00',execution_status_available_at=d+'T09:00:00+08:00',code='600036.SH',exchange_board='SSE_MAIN',open=o,close=c,
                      ma20=ma,ma60=9,prior_high20=11,prior_low20=8,market_allowed=True,suspended=False,st=False,
                      up_limit=20,down_limit=5,volume=100000,liquidity_confirmed=True,source_grade='OFFLINE_SYNTHETIC',source_hash=digest([d,o,c,ma])) for d,o,c,ma in values]
    freeze(PUBLIC/'PAPER_LAB.json',simulate(sessions,experiment))
    freeze(PUBLIC/'LIFECYCLES.json',dict(cases=checks,real_information_updated=False,
                                       limitation='真实第二观察重新核对保留证据；状态变化用显式模拟，非新公告/用户买卖；模拟持仓不能证明已接入真实账户'))
    assert sha256(BASE_STORE.read_bytes()).hexdigest()==store_hash
    freeze(PUBLIC/'PRESERVATION.json',dict(scope='本批实际读取的原V2 Store与原V3目录证据；不重复全历史审计',
                                         original_store_sha256=store_hash,original_store_changed=False,
                                         source_hashes={s.id:s.sha256 for s in previous.sources},market_api_requests=0,
                                         private_deletions=0,orders=0))
    print(json.dumps(checks,ensure_ascii=False))


if __name__=='__main__':main()
