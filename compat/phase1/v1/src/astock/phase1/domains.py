"""Versioned domain facts and historical queries; no guessed identities or PIT."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from astock.phase1.contracts import FINANCIAL, catalog
from astock.phase1.core import day, digest, instant, require, stamp

SHANGHAI = ZoneInfo('Asia/Shanghai')


def conservative_next_session(publication_date: str, calendar_rows: list[dict]) -> datetime:
    require(all(type(r.get('is_open')) is int and r['is_open'] in (0, 1) for r in calendar_rows), 'PUBLICATION_CALENDAR_TYPE')
    next_days = sorted(day(r['cal_date']) for r in calendar_rows if r['is_open'] == 1 and day(r['cal_date']) > day(publication_date))
    require(bool(next_days), 'PUBLICATION_NEXT_SESSION_UNKNOWN')
    first, last = day(publication_date) + timedelta(days=1), next_days[0]
    expected = {first + timedelta(days=i) for i in range((last - first).days + 1)}
    relevant = [day(r['cal_date']) for r in calendar_rows if first <= day(r['cal_date']) <= last]
    require(set(relevant) == expected and len(relevant) == len(expected), 'PUBLICATION_CALENDAR_COVERAGE_UNKNOWN')
    return instant(datetime.combine(next_days[0], time(9, 30), SHANGHAI))


def knowledge(row: dict, source: dict, metadata: dict, *, fixture: bool) -> dict:
    observed = instant(source['retrieved_at'])
    publication_date = row.get('f_ann_date') or row.get('ann_date')
    result = dict(published_at=None, available_at=stamp(observed), retrieved_at=stamp(observed),
                  precision='DATE' if publication_date else 'OBSERVED_MICROSECOND', knowledge_basis='OBSERVED_CAPTURE',
                  source_publication_date=publication_date, vintage_status='UNPROVEN')
    proof = metadata.get('knowledge')
    if proof:
        require(proof.get('vintage_verified') is True and proof.get('evidence_hash')
                and len(proof['evidence_hash']) == 64, 'VERSION_SPECIFIC_VINTAGE_REQUIRED')
        # A production derivation needs a separately reviewed policy; fixture flags
        # are never production publication evidence.
        require(fixture and proof.get('namespace') == 'FIXTURE' or
                not fixture and proof.get('namespace') == 'APPROVED_POLICY'
                and proof.get('approval_ref') and proof.get('policy_hash')
                and source.get('approved_knowledge_policy_hash') == proof['policy_hash']
                and source.get('approval_ref') == proof['approval_ref'], 'PIT_POLICY_NAMESPACE')
        if proof['precision'] == 'DATE':
            require(publication_date is not None, 'PUBLICATION_DATE_MISSING')
            available = conservative_next_session(publication_date, proof['calendar_rows'])
            require(available <= observed, 'PUBLICATION_AVAILABILITY_ORDER')
            result.update(available_at=stamp(available), precision='DATE', knowledge_basis='CONSERVATIVE_NEXT_SESSION')
        else:
            published = instant(proof['published_at'])
            require(publication_date is None or published.astimezone(SHANGHAI).date() == day(publication_date), 'PUBLICATION_DATE_CONFLICT')
            available = instant(proof['available_at'])
            require(published <= available <= observed, 'PUBLICATION_AVAILABILITY_ORDER')
            result.update(published_at=stamp(published), available_at=stamp(available), precision=proof['precision'], knowledge_basis='VERIFIED_SOURCE_VERSION')
        result['vintage_status'] = 'FIXTURE_VERIFIED' if fixture else 'EXTERNAL_POLICY_CANDIDATE'
    return result


def facts(root: Path, member: dict, rows: list[dict], source: dict) -> tuple[list, list]:
    c, ds = catalog(root)[member['dataset']], member['dataset']
    output, findings = [], []
    for ordinal, row in enumerate(rows):
        k = knowledge(row, source, member.get('metadata', {}), fixture=source['fixture_only'])
        payload = dict(row, source_publication_date=k.pop('source_publication_date'), vintage_status=k.pop('vintage_status'))
        entity = row.get('security_id') or row.get('ts_code') or row.get('index_code')
        event = row.get('trade_date') or row.get('cal_date') or row.get('end_date') or row.get('valid_from')
        start, end = row.get('valid_from'), row.get('valid_to')
        eligibility = 'OBSERVED_ONLY'
        series = {f: row.get(f) for f in c['key']}
        if ds in FINANCIAL:
            series = {f: row.get(f) for f in ('ts_code', 'end_date', 'report_type', 'comp_type')}
            eligibility = 'HISTORICAL_VINTAGE_UNPROVEN' if k['knowledge_basis'] == 'OBSERVED_CAPTURE' else 'PIT_CANDIDATE'
            if not (row.get('ann_date') or row.get('f_ann_date')):
                findings.append(dict(reason='FINANCIAL_PUBLICATION_DATE_UNKNOWN', dataset=ds, entity=entity, event_date=event))
        elif ds in ('stock_basic', 'bak_basic'):
            # List/delist dates are source claims; today’s name/status is not a
            # historical episode, and code reuse never generates a security ID.
            eligibility = 'IDENTITY_EVIDENCE_REQUIRED'
            findings.append(dict(reason='IDENTITY_EPISODE_EVIDENCE_REQUIRED', dataset=ds, entity=entity, event_date=event))
        elif ds == 'security_identifiers':
            eligibility = 'FIXTURE_IDENTITY' if source['fixture_only'] else 'BATCH_IDENTITY_CANDIDATE'
            if row['identifier_type'] == 'EXCHANGE_CODE':
                from astock.data.identity import is_normalized_ashare_identifier
                require(is_normalized_ashare_identifier(row['identifier']), 'NORMALIZED_EXCHANGE_IDENTIFIER_REQUIRED')
        elif ds == 'listing_episodes':
            eligibility = 'FIXTURE_EPISODE' if source['fixture_only'] else 'BATCH_EPISODE_CANDIDATE'
            require(day(row['list_date']) <= day(row['valid_from']), 'EPISODE_LISTING_ORDER')
            require(row['last_trading_date'] is None or row['delist_date'] is None or day(row['last_trading_date']) <= day(row['delist_date']), 'DELIST_LAST_TRADE_ORDER')
        elif ds in ('stock_st', 'suspend_d'):
            start = row['trade_date']
            end = (day(start) + timedelta(days=1)).isoformat()
            payload['state_type'] = 'RISK_WARNING' if ds == 'stock_st' else 'SUSPENSION_EVENT'
            payload['state_value'] = row.get('type') if ds == 'stock_st' else row.get('suspend_type')
            payload['interval_basis'] = 'SOURCE_SINGLE_DAY_ONLY_NO_FORWARD_FILL'
            if payload['state_value'] is None:
                findings.append(dict(reason='STATUS_VALUE_UNKNOWN', dataset=ds, entity=entity, event_date=event))
        elif ds == 'index_member_all':
            # Provider removal-day inclusivity/taxonomy lineage is not inferred.
            payload['classification_version'] = member.get('metadata', {}).get('classification_version')
            eligibility = 'INDUSTRY_INTERVAL_POLICY_REQUIRED'
            findings.append(dict(reason='INDUSTRY_VERSION_INTERVAL_EVIDENCE_REQUIRED', dataset=ds, entity=entity, event_date=event))
        elif ds == 'rule_history':
            eligibility = 'FIXTURE_RULE' if source['fixture_only'] else 'RULE_CANDIDATE'
            for f in ('sell_delay_trading_days', 'min_order_qty', 'order_qty_step', 'ipo_no_limit_sessions', 'price_tick', 'price_limit_ratio'):
                require(row[f] is None or row[f] >= 0, 'NEGATIVE_RULE_CONSTRAINT')
        if start is not None:
            require(end is None or day(start) < day(end), 'EMPTY_EFFECTIVE_INTERVAL')
        f = dict(dataset=ds, domain=c['domain'], series_key=digest(dict(dataset=ds, key=series)),
                 entity=entity, event_date=day(event).isoformat() if event else None,
                 valid_from=day(start).isoformat() if start else None, valid_to=day(end).isoformat() if end else None,
                 **k, source_object=source['object_id'], source_row=ordinal, payload=payload, eligibility=eligibility)
        f['fact_hash'] = digest(f)
        output.append(f)
    return output, findings


def known_versions(rows: list[dict], as_of: str) -> tuple[list, list]:
    at, groups = instant(as_of), defaultdict(list)
    for row in rows:
        if row['available_at'] is not None and instant(row['available_at']) <= at:
            groups[row['series_key']].append(row)
    selected, conflicts = [], []
    for candidates in groups.values():
        newest = max(instant(r['available_at']) for r in candidates)
        latest = [r for r in candidates if instant(r['available_at']) == newest]
        payloads = {digest(r['payload']) for r in latest}
        if len(payloads) > 1:
            conflicts.extend(latest)
        else:
            selected.append(sorted(latest, key=lambda r: r['fact_hash'])[0])
    return selected, conflicts


def active(row: dict, event: str) -> bool:
    return (row['valid_from'] is None or day(row['valid_from']) <= day(event)) and (row['valid_to'] is None or day(event) < day(row['valid_to']))


def resolve(rows: list[dict], native: str, event: str, as_of: str, *, exchange=None, source=None) -> dict:
    mappings, conflicts = known_versions([r for r in rows if r['dataset'] == 'security_identifiers'], as_of)
    matches = [r for r in mappings if r['payload']['identifier'] == native and active(r, event)
               and (exchange is None or r['payload']['exchange'] == exchange)
               and (source is None or r['payload']['source'] == source)]
    if any(r['payload']['identifier'] == native and active(r, event) for r in conflicts) or len(matches) > 1:
        return dict(status='CONFLICT', security_id=None, episode_id=None)
    if not matches:
        return dict(status='EVIDENCE_REQUIRED', security_id=None, episode_id=None)
    mapping = matches[0]['payload']
    episodes, episode_conflicts = known_versions([r for r in rows if r['dataset'] == 'listing_episodes'], as_of)
    matching_episodes = [r for r in episodes if r['entity'] == mapping['security_id'] and active(r, event)]
    if len(matching_episodes) > 1 or any(r['entity'] == mapping['security_id'] and active(r, event) for r in episode_conflicts):
        return dict(status='CONFLICT', security_id=None, episode_id=None)
    if not matching_episodes:
        return dict(status='EVIDENCE_REQUIRED', security_id=None, episode_id=None, reason='LISTING_EPISODE_REQUIRED')
    episode = matching_episodes[0]['payload']
    if any(episode[f] != mapping[f] for f in ('security_id', 'episode_id', 'exchange', 'board')):
        return dict(status='CONFLICT', security_id=None, episode_id=None)
    return dict(status='RESOLVED', security_id=matches[0]['payload']['security_id'], episode_id=matches[0]['payload']['episode_id'],
                exchange=matches[0]['payload']['exchange'], board=matches[0]['payload']['board'], fact_hash=matches[0]['fact_hash'])


def historical_snapshot(rows: list[dict], security_id: str, event: str, as_of: str, *, taxonomy=None) -> dict:
    known, conflicts = known_versions(rows, as_of)
    native = {r['payload']['identifier'] for r in known if r['dataset'] == 'security_identifiers'
              and r['payload']['security_id'] == security_id and active(r, event)}
    identities = [resolve(rows, n, event, as_of) for n in native]
    exchanges = {r['exchange'] for r in identities if r['status'] == 'RESOLVED'}
    boards = {r['board'] for r in identities if r['status'] == 'RESOLVED'}
    def belongs(r):
        if r['dataset'] == 'trade_cal':
            return r['payload']['exchange'] in exchanges and r['event_date'] == day(event).isoformat()
        if r['dataset'] == 'rule_history':
            return r['payload']['exchange'] in exchanges and r['payload']['board'] in boards | {'*'}
        if r['entity'] == security_id:
            return True
        if r['entity'] in native:
            identity = resolve(rows, r['entity'], r['event_date'] or event, as_of)
            return identity['status'] == 'RESOLVED' and identity['security_id'] == security_id
        return False
    result = dict(security_id=security_id, event_date=day(event).isoformat(), as_of=stamp(instant(as_of)),
                  query_mode='CURRENT_RECONSTRUCTION' if instant(as_of).astimezone(SHANGHAI).date() > day(event) else 'HISTORICAL_KNOWLEDGE_CUTOFF',
                  research_admitted=False, domains={}, unknowns=[])
    for domain in ('security', 'calendar', 'market', 'status', 'financial', 'industry', 'rule', 'index'):
        chosen = [r for r in known if r['domain'] == domain and belongs(r) and active(r, event)]
        if domain == 'market':
            chosen = [r for r in chosen if r['event_date'] == day(event).isoformat()]
        if domain == 'financial':
            chosen = [r for r in chosen if r['event_date'] is not None and day(r['event_date']) <= day(event)]
        if domain == 'industry':
            chosen = [r for r in chosen if r['dataset'] == 'industry_membership' and
                      (taxonomy is None or r['payload']['classification_version'] == taxonomy)]
            versions = {r['payload']['classification_version'] for r in chosen}
            if taxonomy is None and len(versions) > 1:
                chosen = []
                result['unknowns'].append(dict(domain=domain, reason='TAXONOMY_VERSION_REQUIRED'))
        if domain == 'rule':
            statuses = [r['payload']['state_value'] for r in known if r['dataset'] == 'security_status'
                        and r['entity'] == security_id and r['payload']['state_type'] == 'RISK_WARNING' and active(r, event)]
            if len(set(statuses)) != 1:
                chosen = []
                result['unknowns'].append(dict(domain=domain, reason='RULE_STATUS_SCOPE_UNKNOWN_OR_CONFLICT'))
            else:
                chosen = [r for r in chosen if r['payload']['state'] in ('*', statuses[0])]
                if len(chosen) > 1:
                    chosen = []
                    result['unknowns'].append(dict(domain=domain, reason='RULE_SCOPE_OVERLAP_CONFLICT'))
        overlapping_groups = defaultdict(list)
        if domain in ('status', 'industry'):
            for r in chosen:
                key = r['payload'].get('state_type') if domain == 'status' else (r['payload']['classification_version'], r['payload']['level'])
                overlapping_groups[key].append(r)
            if any(len({r['payload'].get('state_value') if domain == 'status' else r['payload']['industry_code'] for r in group}) > 1 for group in overlapping_groups.values()):
                chosen = []
                result['unknowns'].append(dict(domain=domain, reason='OVERLAPPING_EFFECTIVE_FACTS_CONFLICT'))
        if any(belongs(r) and r['domain'] == domain and active(r, event) for r in conflicts):
            chosen = []
            result['unknowns'].append(dict(domain=domain, reason='SAME_TIME_VERSION_CONFLICT'))
        result['domains'][domain] = chosen
        if not chosen:
            result['unknowns'].append(dict(domain=domain, reason='EVIDENCE_REQUIRED'))
    return result


def adjusted_price(rows: list[dict], native: str, event: str, anchor: str, as_of: str) -> dict:
    require(day(event) <= day(anchor) <= instant(as_of).astimezone(SHANGHAI).date(), 'FUTURE_ADJUSTMENT_ANCHOR')
    known, conflicts = known_versions([r for r in rows if r['entity'] == native], as_of)
    wanted = {day(event).isoformat(), day(anchor).isoformat()}
    require(not any(r['event_date'] in wanted and r['dataset'] in ('daily', 'adj_factor') for r in conflicts), 'ADJUSTMENT_VERSION_CONFLICT')
    prices = [r for r in known if r['dataset'] == 'daily' and r['event_date'] == day(event).isoformat()]
    factors = {r['event_date']: r for r in known if r['dataset'] == 'adj_factor' and r['event_date'] in wanted}
    if len(prices) != 1 or prices[0]['payload']['close'] is None or set(factors) != wanted or any(factors[d]['payload']['adj_factor'] is None for d in wanted):
        return dict(status='EVIDENCE_REQUIRED', value=None, research_admitted=False)
    value = prices[0]['payload']['close'] * factors[day(event).isoformat()]['payload']['adj_factor'] / factors[day(anchor).isoformat()]['payload']['adj_factor']
    return dict(status='VALID_RECONSTRUCTION', value=value, event_date=event, anchor=anchor,
                source_hashes=[prices[0]['fact_hash'], *[r['fact_hash'] for r in factors.values()]], research_admitted=False)


def rule_at(rows: list[dict], exchange: str, board: str, state: str, event: str, as_of: str,
            *, listing_date=None, sessions=None) -> dict:
    known, conflicts = known_versions([r for r in rows if r['dataset'] == 'rule_history'], as_of)
    def matches(r):
        p = r['payload']
        return p['exchange'] == exchange and p['board'] in (board, '*') and p['state'] in (state, '*') and active(r, event)
    candidates = [r for r in known if matches(r)]
    if any(matches(r) for r in conflicts) or len(candidates) > 1:
        return dict(status='CONFLICT', rule=None)
    if not candidates:
        return dict(status='EVIDENCE_REQUIRED', rule=None)
    p = dict(candidates[0]['payload'])
    if p['ipo_no_limit_sessions']:
        if listing_date is None or sessions is None:
            return dict(status='EVIDENCE_REQUIRED', rule=None, reason='IPO_SESSION_AGE_UNKNOWN')
        if not all(isinstance(r, dict) and r.get('exchange') == exchange and type(r.get('is_open')) is int and r['is_open'] in (0, 1) for r in sessions):
            return dict(status='EVIDENCE_REQUIRED', rule=None, reason='IPO_CIVIL_CALENDAR_REQUIRED')
        first, last = day(listing_date), day(event)
        civil = {first + timedelta(days=i) for i in range((last - first).days + 1)}
        covered = [r for r in sessions if first <= day(r['cal_date']) <= last]
        if {day(r['cal_date']) for r in covered} != civil or len(covered) != len(civil):
            return dict(status='EVIDENCE_REQUIRED', rule=None, reason='IPO_SESSION_COVERAGE_UNKNOWN')
        trading = sorted(day(r['cal_date']) for r in covered if r['is_open'] == 1)
        if not trading or trading[0] != day(listing_date) or trading[-1] != day(event):
            return dict(status='EVIDENCE_REQUIRED', rule=None, reason='IPO_SESSION_COVERAGE_UNKNOWN')
        if len(trading) <= p['ipo_no_limit_sessions']:
            p['price_limit_ratio'] = None
            p['price_limit_basis'] = 'IPO_EXEMPTION'
    unknown = [f for f in ('sell_delay_trading_days', 'min_order_qty', 'order_qty_step', 'price_tick') if p[f] is None]
    if p['price_limit_ratio'] is None and p.get('price_limit_basis') != 'IPO_EXEMPTION':
        unknown.append('price_limit_ratio')
    return dict(status='PARTIAL' if unknown else 'KNOWN', rule=p, unknown_fields=unknown, fact_hash=candidates[0]['fact_hash'])


def sellable_on(purchase: str, delay: int | None, sessions: list[str]) -> dict:
    if delay is None:
        return dict(status='EVIDENCE_REQUIRED', date=None)
    require(type(delay) is int and delay >= 0, 'SELL_DELAY_TYPE')
    days = sorted({day(d) for d in sessions if day(d) >= day(purchase)})
    if not days or days[0] != day(purchase) or len(days) <= delay:
        return dict(status='EVIDENCE_REQUIRED', date=None)
    return dict(status='KNOWN_CONSTRAINT_ONLY', date=days[delay].isoformat(), guarantees_fill=False)


def quantity_valid(rule: dict, quantity: int) -> dict:
    low, step = rule.get('min_order_qty'), rule.get('order_qty_step')
    if low is None or step is None:
        return dict(status='EVIDENCE_REQUIRED', valid=None)
    require(type(quantity) is int and quantity >= 0 and step > 0, 'ORDER_QUANTITY_TYPE')
    return dict(status='KNOWN_CONSTRAINT_ONLY', scope='BUY_MINIMUM_AND_INCREMENT_ONLY',
                valid=quantity >= low and (quantity - low) % step == 0,
                sell_odd_lot_policy='EVIDENCE_REQUIRED', guarantees_fill=False)
