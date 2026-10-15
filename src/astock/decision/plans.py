"""Append-only research plans and explicit reviews in the private working Journal."""
import json
from pathlib import Path

from astock.company.models import ResearchCatalog
from astock.company.workflow import verify_retained_market_anchor
from astock.data.warehouse_lock import warehouse_connection
from astock.decision.daily import DailyObservation, DailyProfile, load_daily_profile
from astock.decision.models import ResearchPlan, ReviewAction, RunInput
from astock.decision.plan_models import PlanInput, PlanRecord
from astock.decision.workflow import verified_catalog
from astock.portfolio import manual
from astock.research.core import digest, instant, read_json, require
from astock.research.journal import JournalEvent, active_events, append_events_in_transaction
from astock.research.store import ResearchStore


def _bootstrap(run: RunInput) -> str:
    return digest(dict(mode=run.mode, plans=[p.model_dump(mode='json') for p in run.plans],
                       review_actions=[a.model_dump(mode='json') for a in run.review_actions],
                       simulation_events=[e.model_dump(mode='json') for e in run.simulation_events]))


def _state(events: list[dict], run: RunInput, baseline_hash: str | None = None,
           previous_hash: str | None = None) -> dict:
    mode = 'USER_MANUAL' if run.mode == 'REAL_EVIDENCE' else 'SIMULATED'
    require(all(e.get('input_mode') in (None, mode) for e in events), 'PLAN_MIXED_MODE')
    seed = _bootstrap(run)
    plans = {p.code: p for p in run.plans}
    reviews = {a.code: (a, None) for a in run.review_actions}
    closed = {a.code for a in run.review_actions if a.action == 'END_WATCH'}
    identifiers = []
    records = sorted([e for e in events if e['kind'] == 'RESEARCH_INPUT'],
                     key=lambda e: (instant(e['recorded_at']), e['event_id']))
    for event in records:
        record = PlanRecord.model_validate(event['research_input'])
        request = record.request
        require(record.bootstrap_hash == seed, 'PLAN_BOOTSTRAP_CHANGED')
        require(baseline_hash is None or record.baseline_hash == baseline_hash, 'PLAN_BASELINE_CHANGED')
        require(previous_hash is None or record.previous_catalog_hash == previous_hash, 'PLAN_CATALOG_BASELINE_CHANGED')
        require(request.expected_plan_hash == digest([seed, identifiers]), 'PLAN_RECORD_CHAIN')
        current = plans.get(request.code)
        target = digest(current.model_dump(mode='json')) if current else None
        require(record.target_plan_hash == target, 'PLAN_TARGET_CHANGED')
        if request.action == 'CREATE':
            require(current is None or request.code in closed, 'PLAN_ALREADY_ACTIVE')
            plans[request.code] = record.plan
            reviews.pop(request.code, None)
            closed.discard(request.code)
        else:
            require(current is not None, 'PLAN_REQUIRED')
            require(request.action == 'END_WATCH' or request.code not in closed, 'PLAN_ALREADY_ENDED')
            reviews[request.code] = record.review, record.reviewed_catalog_hash
            if request.action == 'END_WATCH':
                closed.add(request.code)
        identifiers.append(event['event_id'])
    require(len(plans) <= 20, 'PLAN_CAPACITY')
    return dict(plan_hash=digest([seed, identifiers]), mode=mode, closed=closed,
                plans=plans, reviews=reviews, records=records, bootstrap_hash=seed)


def _context(root: Path, profile_path: Path) -> tuple[DailyProfile, RunInput]:
    return load_daily_profile(root, profile_path, DailyObservation(observed_at=manual.now_utc()))


def _events(store: ResearchStore, as_of: str) -> list[dict]:
    if not store.path.exists():
        return []
    with warehouse_connection(store.path, read_only=True) as db:
        store._check(db)
        return active_events(db, as_of)[1]


def preview_plans(root: Path, profile_path: Path) -> dict:
    profile, run = _context(root, profile_path)
    state = _state(_events(ResearchStore(profile.journal_store), run.observed_at), run)
    old, new = (ResearchCatalog.model_validate(read_json(p)) for p in (profile.previous, profile.latest))
    available = sorted({c.code for c in old.companies} & {f['code'] for f in read_json(profile.baseline_market)['features']})
    return dict(plan_hash=state['plan_hash'], mode=state['mode'], available_codes=available,
                latest_reviewed_codes=sorted(c.code for c in new.companies),
                plans=[dict(code=p.code, ended=p.code in state['closed'], plan=p.model_dump(mode='json'))
                       for p in state['plans'].values()],
                metrics={c.code: [dict(id=f.id, name=f.name) for f in c.financials] for c in old.companies})


def _key(request_id: str, mode: str) -> str:
    return digest(['RESEARCH_PLAN_INPUT_V1', mode, request_id])


def _receipt(event: dict) -> dict:
    record = event['research_input']
    request = record['request']
    return dict(request_id=request['request_id'], receipt_id=event['event_id'], action=request['action'],
                code=request['code'], mode=request['mode'], recorded_at=event['recorded_at'],
                plan_hash=digest(record['plan']) if record['plan'] else record['target_plan_hash'], orders_created=0)


def existing_plan_input(root: Path, profile_path: Path, request_id: str) -> dict | None:
    profile, run = _context(root, profile_path)
    mode = 'USER_MANUAL' if run.mode == 'REAL_EVIDENCE' else 'SIMULATED'
    if not profile.journal_store.exists():
        return None
    with warehouse_connection(profile.journal_store, read_only=True) as db:
        ResearchStore(profile.journal_store)._check(db)
        row = db.execute('SELECT payload FROM research_journal WHERE id=?', [_key(request_id, mode)]).fetchone()
    return _receipt(json.loads(row[0])) if row else None


def record_plan_input(root: Path, profile_path: Path, request: PlanInput) -> dict:
    profile, run = _context(root, profile_path)
    mode = 'USER_MANUAL' if run.mode == 'REAL_EVIDENCE' else 'SIMULATED'
    require(request.mode == mode, 'PLAN_PROFILE_MODE')
    store = ResearchStore(profile.journal_store)
    store.initialize()
    key = _key(request.request_id, mode)
    with warehouse_connection(store.path) as db:
        store._check(db)
        db.execute('BEGIN')
        try:
            prior = db.execute('SELECT payload FROM research_journal WHERE id=?', [key]).fetchone()
            if prior:
                event = JournalEvent.model_validate_json(prior[0])
                require(event.research_input.request == request, 'PLAN_REQUEST_ID_CONFLICT')
                db.execute('COMMIT')
                return _receipt(json.loads(prior[0]))
            recorded = manual.now_utc()
            old = verified_catalog(read_json(profile.previous), profile.documents)
            latest = verified_catalog(read_json(profile.latest), profile.documents)
            require(instant(old.as_of) <= instant(latest.as_of) <= recorded, 'PLAN_EVIDENCE_TIME')
            baseline = read_json(profile.baseline_market)
            owner = next((c.store for c in profile.components if c.bundle == baseline['bundle_id']), profile.store)
            verify_retained_market_anchor(baseline, ResearchStore(owner))
            require(instant(baseline['as_of']) <= recorded, 'PLAN_MARKET_TIME')
            _, active = active_events(db, recorded.isoformat())
            state = _state(active, run, digest(baseline), digest(old.model_dump(mode='json')))
            require(request.expected_plan_hash == state['plan_hash'], 'PLAN_PREVIEW_CHANGED')
            require(all(instant(e['recorded_at']) < recorded for e in state['records']), 'PLAN_CLOCK_NOT_ADVANCING')
            current = state['plans'].get(request.code)
            target = digest(current.model_dump(mode='json')) if current else None
            materialized, review = None, None
            if request.action == 'CREATE':
                require(current is None or request.code in state['closed'], 'PLAN_ALREADY_ACTIVE')
                company = next((c for c in old.companies if c.code == request.code), None)
                require(company is not None and request.code in {f['code'] for f in baseline['features']}, 'PLAN_COMPANY_EVIDENCE_REQUIRED')
                require(all(c.metric_id in {f.id for f in company.financials} for c in request.draft.criteria),
                        'PLAN_METRIC_REQUIRED')
                values = request.draft.model_dump(mode='json')
                materialized = ResearchPlan(**values, code=request.code,
                    created_at=recorded.isoformat(), review_date_basis='USER_CONFIRMED_RESEARCH_DATE',
                    baseline_catalog_hash=digest(old.model_dump(mode='json')), baseline_market_hash=digest(baseline),
                    baseline_market_date=baseline['window_end'], baseline_market_bundle_id=baseline['bundle_id'])
            else:
                require(current is not None, 'PLAN_REQUIRED')
                require(request.action == 'END_WATCH' or request.code not in state['closed'], 'PLAN_ALREADY_ENDED')
                require(current.baseline_catalog_hash == digest(old.model_dump(mode='json')) and
                        current.baseline_market_hash == digest(baseline), 'PLAN_BASELINE_CHANGED')
                hashes = []
                if request.action == 'REVIEW_EVIDENCE':
                    require(request.code in {c.code for c in latest.companies}, 'PLAN_LATEST_REVIEW_REQUIRED')
                    hashes = sorted({s.sha256 for s in latest.sources if s.code == request.code and s.state == 'RETRIEVED'})
                    require(bool(hashes), 'PLAN_REVIEW_SOURCES_REQUIRED')
                review = ReviewAction(code=request.code,
                    action='END_WATCH' if request.action == 'END_WATCH' else 'ACKNOWLEDGE_CHANGED_EVIDENCE',
                    recorded_at=recorded.isoformat(), reason=request.reason, confirmed=True, evidence_hashes=hashes,
                    provenance='USER_MANUAL' if mode == 'USER_MANUAL' else 'OFFLINE_SIMULATION_NOT_USER_ACTION')
            record = PlanRecord(request=request, plan=materialized, review=review, target_plan_hash=target,
                bootstrap_hash=state['bootstrap_hash'], baseline_hash=digest(baseline),
                previous_catalog_hash=digest(old.model_dump(mode='json')),
                reviewed_catalog_hash=digest(latest.model_dump(mode='json')))
            event = JournalEvent(event_id=key, kind='RESEARCH_INPUT', code=request.code,
                event_at=recorded, recorded_at=recorded, input_mode=mode, confirmed=True, research_input=record)
            # Validate the same replay path used by the next report before committing.
            _state([*active, event.model_dump(mode='json')], run, digest(baseline), digest(old.model_dump(mode='json')))
            append_events_in_transaction(db, [event])
            db.execute('COMMIT')
            return _receipt(event.model_dump(mode='json'))
        except Exception:
            db.execute('ROLLBACK')
            raise


def resolve_plan_run(store: ResearchStore, run: RunInput, previous: ResearchCatalog,
                     latest: ResearchCatalog, baseline: dict) -> tuple[RunInput, list[dict]]:
    state = _state(_events(store, run.observed_at), run, digest(baseline), digest(previous.model_dump(mode='json')))
    latest_hash = digest(latest.model_dump(mode='json'))
    reviews = [review.model_dump(mode='json') for review, catalog_hash in state['reviews'].values()
               if review.action == 'END_WATCH' or catalog_hash is None or catalog_hash == latest_hash]
    original = {p.code: p for p in run.plans}
    events = [e.model_dump(mode='json') for e in run.simulation_events if e.code in original and
              state['plans'][e.code] == original[e.code]]
    effective = RunInput.model_validate({**run.model_dump(mode='json'),
        'plans': [p.model_dump(mode='json') for p in state['plans'].values()],
        'review_actions': reviews, 'simulation_events': events})
    return effective, state['records']


def retained_catalog(previous: ResearchCatalog, latest: ResearchCatalog, codes: set[str]) -> tuple[ResearchCatalog, set[str]]:
    """Keep original source times for objects absent from the limited latest review."""
    missing = codes - {c.code for c in latest.companies}
    if not missing:
        return latest, set()
    require(missing <= {c.code for c in previous.companies}, 'PLAN_COMPANY_EVIDENCE_REQUIRED')
    sources = {s.id: s for s in latest.sources}
    for source in previous.sources:
        if source.code in missing:
            require(source.id not in sources or sources[source.id] == source, 'PLAN_SOURCE_VERSION_CONFLICT')
            sources[source.id] = source
    return ResearchCatalog.model_validate({**latest.model_dump(mode='json'),
        'companies': [c.model_dump(mode='json') for c in [*latest.companies,
                       *[c for c in previous.companies if c.code in missing]]],
        'sources': [s.model_dump(mode='json') for s in sources.values()]}), missing
