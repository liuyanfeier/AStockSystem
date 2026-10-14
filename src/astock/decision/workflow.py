"""Compare verified research versions, save append-only review evidence, never order."""
from decimal import Decimal
from pathlib import Path

from astock.company.models import ResearchCatalog
from astock.company.workflow import verify_documents
from astock.decision.models import RunInput
from astock.research.core import day, digest, encoded, instant, read_json, require
from astock.research.journal import append_event
from astock.research.publication import publish_bytes
from astock.data.warehouse_lock import warehouse_connection

STATES = {'CONTINUE_WATCH': '继续观察', 'WAIT_EVIDENCE': '暂停新交易，等待证据',
          'INVALIDATION_REVIEW': '触发投资逻辑失效复核', 'END_WATCH': '研究结束或退出观察队列'}


def verified_catalog(value: dict, documents: Path) -> ResearchCatalog:
    catalog = ResearchCatalog.model_validate(value)
    verify_documents(catalog, documents)
    return catalog


def figures(company):
    return {v.id: v.model_dump(mode='json') for v in company.financials}


def evaluate(criterion, before: dict | None, after: dict | None) -> dict:
    """Numeric research checks; language interpretation stays in explicit human review."""
    base = dict(id=criterion.id, metric_id=criterion.metric_id, reason=criterion.reason,
                previous=before, latest=after, evidence_class='DISCLOSED_METRIC_NOT_PREDICTION')
    if not before or not after or before['value'] is None or after['value'] is None:
        return dict(base, state='UNKNOWN', explanation='缺少可追溯指标，不能认定逻辑成立或失效')
    comparable = (before['unit'], before['accounting_basis']) == (after['unit'], after['accounting_basis'])
    # Flow comparisons require the same fiscal season and one-year interval, or an exact-period correction.
    if before['period_start'] or after['period_start']:
        comparable &= bool(before['period_start'] and after['period_start'])
        comparable &= before['period_start'][5:] == after['period_start'][5:] and before['period_end'][5:] == after['period_end'][5:]
        comparable &= day(after['period_end']).year - day(before['period_end']).year in (0, 1)
    comparable &= day(after['period_end']) >= day(before['period_end'])
    if not comparable:
        return dict(base, state='UNKNOWN', explanation='单位、合并口径或报告期间不可比，需人工复核')
    a, b = Decimal(before['value']), Decimal(after['value'])
    ok = {'NOT_LOWER': b >= a, 'NOT_HIGHER': b <= a, 'POSITIVE': b > 0}[criterion.expectation]
    return dict(base, state='SUPPORTED' if ok else criterion.failure,
                explanation='指标满足研究检查；不证明未来假设或交易盈利' if ok else '指标挑战原研究检查，需核对原表和原因')


def compare(run: RunInput, previous: ResearchCatalog, latest: ResearchCatalog, market: dict,
            memberships: list[dict] | None = None, baseline_market: dict | None = None) -> dict:
    cutoff = instant(run.observed_at)
    require(instant(previous.as_of) <= instant(latest.as_of) <= cutoff, 'DECISION_RESEARCH_TIME')
    require(instant(market['as_of']) <= cutoff and day(market['window_end']) <= day(run.required_market_date), 'DECISION_MARKET_TIME')
    old, new = {c.code: c for c in previous.companies}, {c.code: c for c in latest.companies}
    sources = {s.id: s.model_dump(mode='json') for s in latest.sources}
    old_sources = {s.id: s.model_dump(mode='json') for s in previous.sources}
    prices = {f['code']: f for f in market['features']}
    eligible=None
    if 'parameters' in market:
        from astock.features.market import ObservationParameters
        from astock.screening.candidates import screen
        from astock.research.core import market_day
        qualified,_=screen(market['features'],ObservationParameters.model_validate(market['parameters']),
                           market_day(instant(market['as_of'])),limit=False)
        eligible={f['code'] for f in qualified}
    industries = {r['code']:r['industry_code'] for r in memberships or []}
    stale = market['window_end'] != run.required_market_date
    events = {(e.code, e.criterion_id): e for e in run.simulation_events}
    actions = {a.code: a for a in run.review_actions}
    cards = []
    baseline_market=baseline_market or market
    for plan in run.plans:
        require(plan.baseline_catalog_hash == digest(previous.model_dump(mode='json')), 'DECISION_BASELINE_CHANGED')
        require(plan.code in old and plan.code in new and plan.code in prices, 'DECISION_COMPANY_MISSING')
        require(instant(previous.as_of) <= instant(plan.created_at), 'DECISION_PLAN_BEFORE_RESEARCH')
        require(plan.baseline_market_hash==digest(baseline_market) and plan.baseline_market_date==baseline_market['window_end'] and
                plan.baseline_market_bundle_id==baseline_market['bundle_id'], 'DECISION_BASELINE_MARKET_CHANGED')
        require(instant(baseline_market['as_of'])<=instant(plan.created_at),'DECISION_PLAN_BEFORE_MARKET')
        a, b = old[plan.code], new[plan.code]
        af, bf = figures(a), figures(b)
        require(all(c.metric_id in af for c in plan.criteria), 'DECISION_BASELINE_METRIC_UNKNOWN')
        checks = [evaluate(c, af.get(c.metric_id), bf.get(c.metric_id)) for c in plan.criteria]
        for check in checks:
            overlay = events.get((plan.code, check['id']))
            if overlay:
                check.update(state=overlay.state, explanation=overlay.explanation,
                             evidence_class='OFFLINE_SIMULATION_NOT_DISCLOSURE', simulation_event=overlay.model_dump(mode='json'))
        changes = []
        for key in sorted(af.keys() | bf.keys()):
            if af.get(key) != bf.get(key):
                changes.append(dict(type='FINANCIAL', key=key, previous=af.get(key), latest=bf.get(key)))
        for section in ('profile', 'events', 'support', 'counter', 'unknowns'):
            old_rows = {r.id: r.model_dump(mode='json') for r in getattr(a, section)}
            new_rows = {r.id: r.model_dump(mode='json') for r in getattr(b, section)}
            for key in sorted(old_rows.keys() | new_rows.keys()):
                if old_rows.get(key) != new_rows.get(key):
                    changes.append(dict(type=section.upper(), key=key, previous=old_rows.get(key), latest=new_rows.get(key)))
        company_source_ids = {s.id for s in latest.sources if s.code == plan.code} | {s.id for s in previous.sources if s.code == plan.code}
        for key in sorted(company_source_ids):
            if old_sources.get(key) != sources.get(key):
                changes.append(dict(type='SOURCE_VERSION', key=key, previous=old_sources.get(key), latest=sources.get(key)))
        states = {c['state'] for c in checks}
        state = 'INVALIDATION_REVIEW' if 'INVALIDATION_REVIEW' in states else 'WAIT_EVIDENCE' if states & {'UNKNOWN', 'CHALLENGED'} else 'CONTINUE_WATCH'
        if plan.unresolved_material_risk and state == 'CONTINUE_WATCH':
            state = 'WAIT_EVIDENCE'
        action=actions.get(plan.code)
        if action and action.action=='ACKNOWLEDGE_CHANGED_EVIDENCE':
            required={sources[s]['sha256'] for s in company_source_ids if s in sources and sources[s]['state']=='RETRIEVED'}
            require(set(action.evidence_hashes)==required,'DECISION_ACKNOWLEDGEMENT_SOURCE_BINDING')
            require(instant(action.recorded_at)>=instant(latest.as_of),'DECISION_ACK_BEFORE_RESEARCH')
        elif any(c['type'] in ('EVENTS','COUNTER','PROFILE') for c in changes) and state=='CONTINUE_WATCH':
            state='WAIT_EVIDENCE'
        if action and action.action=='END_WATCH':
            state = 'END_WATCH'
        due = instant(plan.review_due) <= cutoff
        price = prices[plan.code]
        no_trade = [*plan.no_trade_reasons, '风险预算、仓位及退出参数未经用户批准']
        if plan.unresolved_material_risk:
            no_trade.append(plan.unresolved_material_risk)
        if stale or price.get('last_date') != run.required_market_date:
            no_trade.append('行情未覆盖要求的完整交易日，需更新报价与交易状态')
        if new[plan.code].unknowns:
            no_trade.append('有限公告检查未穷尽；估值/竞争等未核实项不能视为已解决')
        if state != 'CONTINUE_WATCH':
            no_trade.append(STATES[state])
        refs = [sources[s] for s in sorted(company_source_ids) if s in sources]
        cards.append(dict(code=plan.code, name=price['name'], industry_code=industries.get(plan.code), state=state, state_text=STATES[state],
                          hypothesis_state='INVALIDATION_REVIEW' if 'INVALIDATION_REVIEW' in states else 'CHALLENGED' if 'CHALLENGED' in states else 'UNKNOWN' if 'UNKNOWN' in states else 'SUPPORTED_BY_CURRENT_CHECKS',
                          plan=plan.model_dump(mode='json'), previous_research=a.model_dump(mode='json'), latest_research=b.model_dump(mode='json'),
                          previous_catalog_hash=digest(previous.model_dump(mode='json')), latest_catalog_hash=digest(latest.model_dump(mode='json')),
                          checks=checks, evidence_changes=changes, sources=refs,
                          previous_sources=[s.model_dump(mode='json') for s in previous.sources if s.code == plan.code], price=price,
                          technical_eligible=plan.code in eligible if eligible is not None else None,
                          no_new_disclosures=not changes, evidence_refresh_due=due, review_overdue=due,
                          evidence_age=[dict(id=s['id'], report_published_on=s['published_on'], available_at=s['available_at']) for s in refs],
                          manual_action=actions[plan.code].model_dump(mode='json') if plan.code in actions else None,
                          priority='优先复核' if due or state == 'INVALIDATION_REVIEW' else '补证据' if state == 'WAIT_EVIDENCE' else '按计划跟踪',
                          next_actions=plan.observable_checks, no_trade_reasons=no_trade, trade_eligible=False,
                          risk_budget=None, position_limit=None, order=None))
    return dict(protocol='DECISION_LOOP_REPORT_V0', mode=run.mode, as_of=run.observed_at,
                bundle_id=market['bundle_id'], window_end=market['window_end'], required_market_date=run.required_market_date,
                market_snapshot_hash=digest(market), previous_catalog_hash=digest(previous.model_dump(mode='json')),
                latest_catalog_hash=digest(latest.model_dump(mode='json')), run_input_hash=digest(run.model_dump(mode='json')),
                market=market['radar']['market'], market_fresh=not stale, cards=cards,
                limitation='继续观察不代表可入场；研究指标检查不等于全部假设已证实；未检索新公告不等于没有新公告；逻辑失效复核不产生卖单')


def persist(report: dict, store, output: Path) -> str:
    """Dedicated private loop store reuses the five-table schema and ordinary REVIEW events."""
    store.initialize()
    attach_prior_observations(report,store)
    key = store.save_report(report)
    output.mkdir(parents=True, exist_ok=True)
    publish_bytes(output / f'{key}.json', encoded(report) + b'\n')
    for card in report['cards']:
        baseline = dict(protocol='DECISION_INITIAL_PLAN_V0', mode=report['mode'], as_of=card['plan']['created_at'],
                        bundle_id=card['plan']['baseline_market_bundle_id'], window_end=card['plan']['baseline_market_date'], plan=card['plan'],
                        previous_research=card['previous_research'], sources=card['previous_sources'],
                        catalog_hash=card['previous_catalog_hash'])
        baseline_id = store.save_report(baseline)
        initial = dict(event_id=digest([baseline_id, card['code'], 'PLAN']), kind='PLAN', code=card['code'],
                       event_at=card['plan']['created_at'], recorded_at=card['plan']['created_at'],
                       research_report_id=baseline_id, thesis=card['plan']['thesis'],
                       invalidation='；'.join(card['plan']['invalidation_conditions']),
                       exit_conditions='研究复核条件；不产生订单', review_due=card['plan']['review_due'],
                       confirmed=False, notes='程序提出的研究计划；非过去用户真实判断；' + report['mode'])
        initial_path = output/f"{initial['event_id']}.event.json"
        publish_bytes(initial_path, encoded(initial))
        append_event(store, initial_path)
        event = dict(event_id=digest([key, card['code'], 'REVIEW']), kind='REVIEW', code=card['code'],
                     event_at=report['as_of'], recorded_at=report['as_of'], research_report_id=key,
                     thesis=card['plan']['thesis'], invalidation='；'.join(card['plan']['invalidation_conditions']),
                     exit_conditions=card['state_text'], review_due=card['plan']['review_due'], confirmed=False,
                     notes='程序研究复核；非用户实际动作；' + report['mode'])
        path = output / f"{event['event_id']}.event.json"
        publish_bytes(path, encoded(event))
        append_event(store, path)
        if card['manual_action']:
            action=card['manual_action']
            exit_event=dict(event_id=digest([key,card['code'],action['action']]), kind='EXIT' if action['action']=='END_WATCH' else 'REVIEW', code=card['code'],
                            event_at=action['recorded_at'], recorded_at=action['recorded_at'], research_report_id=key,
                            confirmed=action['provenance']=='USER_MANUAL', notes=action['provenance']+'；'+action['action']+'；研究动作，不代表实际卖出；'+action['reason'])
            exit_path=output/f"{exit_event['event_id']}.event.json"
            publish_bytes(exit_path,encoded(exit_event));append_event(store,exit_path)
    return key


def attach_prior_observations(report: dict, store) -> None:
    """Resolve the last known program observation, never a future or unrelated-plan record."""
    import json
    with warehouse_connection(store.path,read_only=True) as db:
        store._check(db)
        candidates=[(key,json.loads(body)) for key,body in db.execute('SELECT id,snapshot FROM research_report').fetchall()]
    for card in report['cards']:
        matching=[]
        for key,old in candidates:
            if old.get('protocol')!='DECISION_LOOP_REPORT_V0' or old.get('mode')!=report['mode'] or instant(old['as_of'])>=instant(report['as_of']):continue
            for prior in old['cards']:
                if prior['code']==card['code'] and prior['plan']==card['plan']:
                    matching.append((instant(old['as_of']),key,old,prior))
        if not matching:
            card['previous_observation']=None;card['changes_since_prior']=[];continue
        latest_time=max(r[0] for r in matching)
        newest=[r for r in matching if r[0]==latest_time]
        require(len(newest)==1,'DECISION_AMBIGUOUS_PRIOR_OBSERVATION')
        _,key,old,prior=newest[0]
        prior_price={k:prior['price'].get(k) for k in ('last_date','close','return_20','above_ma60')}
        current_price={k:card['price'].get(k) for k in prior_price}
        changes=[]
        if prior['state']!=card['state']:changes.append(dict(type='RESEARCH_STATE',previous=prior['state'],latest=card['state']))
        if prior_price!=current_price:changes.append(dict(type='PRICE_OBSERVATION',previous=prior_price,latest=current_price))
        if prior.get('technical_eligible')!=card.get('technical_eligible'):
            changes.append(dict(type='TECHNICAL_QUALIFICATION',previous=prior.get('technical_eligible'),latest=card.get('technical_eligible')))
        prior_checks={c['id']:c for c in prior['checks']}
        for check in card['checks']:
            before=prior_checks.get(check['id'])
            if before!=check:changes.append(dict(type='CRITERION',id=check['id'],previous=before,latest=check))
        card['previous_observation']=dict(report_id=key,as_of=old['as_of'],catalog_hash=old['latest_catalog_hash'],
                                          state=prior['state'],price=prior_price,
                                          personal_action_included=bool(prior.get('manual_action') and prior['manual_action']['provenance']=='USER_MANUAL'))
        card['changes_since_prior']=changes
