"""Concrete license-false pilot and deterministic raw-only expansion proposals."""
from __future__ import annotations
from pathlib import Path

from astock.phase1 import acquisition, contracts, evidence, legacy, pipeline
from astock.phase1.core import PRODUCTION, Phase1Error, day, digest, file_hash, logical_id, require, strict_json


def propose(root: Path, selection_path: Path, market6_path: Path, baseline: dict, protected_history: dict) -> dict:
    selection = strict_json(selection_path.read_bytes())
    previous = strict_json(market6_path.read_bytes())
    evidence.validate_selection(root, selection, baseline)
    old_market = previous.get('members') or previous.get('requests')
    require(len(selection['members']) == 27 and isinstance(old_market, list) and len(old_market) == 6, 'EXACT_PRESERVED_PILOTS_REQUIRED')
    destination = root / PRODUCTION
    calendar = []
    for original_member in selection['members']:
        m = original_member['request']
        req = contracts.request(root, m['dataset'], m['params'], fields=m['fields'])
        req.update(origin_id=original_member['member_id'], object_id=original_member['object_id'], origin_plan=original_member['origin_plan'],
                   legacy_request_hash=digest(m), legacy_request=m)
        calendar.append(req)
    market = []
    for item in old_market:
        m = item.get('request', item)
        req = contracts.request(root, m['dataset'], m['params'], fields=m.get('fields'))
        req.update(origin_id=m['member_id'])
        market.append(req)
    pilots = []
    for code, exchange, status in [('600519.SH', 'SSE', 'L'), ('000001.SZ', 'SZSE', 'L'), ('T00018.SH', 'SSE', 'D')]:
        pilots.append(contracts.request(root, 'stock_basic', dict(ts_code=code, exchange=exchange, list_status=status)))
    pilots.append(contracts.request(root, 'bak_basic', dict(ts_code='600519.SH', trade_date='20231229')))
    for code in ('600519.SH', '601398.SH'):
        for ds in sorted(contracts.FINANCIAL):
            params = dict(ts_code=code, period='20231231')
            if ds != 'fina_indicator': params.update(report_type='1')
            pilots.append(contracts.request(root, ds, params))
    for src in ('SW2014', 'SW2021'):
        pilots.append(contracts.request(root, 'index_classify', dict(src=src, level='L1')))
    pilots.append(contracts.request(root, 'index_member_all', dict(ts_code='600519.SH', is_new='N')))
    pilots += [contracts.request(root, 'index_basic', dict(ts_code='000300.SH')),
               contracts.request(root, 'index_daily', dict(ts_code='000300.SH', trade_date='20231229'))]
    stages = [dict(name='calendar27', requests=calendar, budget=27, purpose='ONLY_UNTOUCHED_FROZEN_MEMBERS'),
              dict(name='core_domain_pilots', requests=pilots, budget=len(pilots), purpose='SOURCE_PERMISSION_RAW_CONTRACT_AND_CORE_FIELD_PROBE'),
              dict(name='preserved_market6', requests=market, budget=6, purpose='EXACT_OLD_PILOT_RAW_ONLY_NOT_SESSION_OR_IDENTITY_ADMISSION')]
    members = calendar + pilots + market
    plan = acquisition.make_plan(root, destination, members, baseline, protected_history=protected_history)
    cs = contracts.catalog(root)
    for stage in stages:
        stage['checks'] = [dict(dataset=m['dataset'], logical_id=logical_id(m), params=m['params'], fields=m['fields'], contract_hash=m['contract_hash'],
                                cap=cs[m['dataset']]['cap'], date_axis=cs[m['dataset']]['date_axis'], empty_policy='STOP_UNLESS_MATCHED_EVIDENCE',
                                permission='ACCOUNT_PERMISSION_UNVERIFIED', research_usage=False) for m in stage.pop('requests')]
    return dict(protocol='PHASE1_UNIFIED_EXECUTION_APPLICATION_V1', execution_license=False, reviewer=None, approved_at=None,
                implementation_sha=None, delivery_sha=None, independent_review_ref=None, human_license=None,
                root=str(root.resolve()), destination=str(destination.resolve()), pins=acquisition.pins(root),
                legacy_snapshot_hash=digest(baseline), protected_history=protected_history,
                plan=plan, plan_hash=digest(plan), stages=stages, exact_pilot_budget=len(members),
                selection_hash=file_hash(selection_path), preserved_market6_hash=file_hash(market6_path),
                max_attempts=1, spacing_seconds=1.25, retries=0, redirects=0, first_new_error='STOP_ALL_REMAINING_PLAN_CALLS',
                recovery='NEW_MATCHED_APPROVAL_FOR_UNTOUCHED_MEMBERS_AND_EXACT_STOPPED_CONSUMPTION;NEVER_RESET_OR_RESEND',
                derived_failed_calendar=dict(original_status='FAILED', new_validation_only=True, actual_adoption_pending=True, license=False),
                offline_fact_adoption=dict(protocol='PHASE1_FACT_ADMISSION_V1', approved_policy=None, candidate_batch=None, license=False,
                    domains=['listing_episodes', 'security_identifiers', 'security_status', 'industry_membership', 'rule_history', 'market_crosscheck'],
                    raw_interpretation=['EXACT_EXISTING_CAPTURE_WITH_VERSION_EVIDENCE', 'FAILED_CALENDAR_COMPLETE_BODY_ONLY_ORIGINAL_FAILED_UNCHANGED'],
                    vintage_evidence='VERSION_SPECIFIC;CURRENT_DOWNLOAD_ANN_DATE_IS_NOT_VINTAGE_PROOF'),
                original_deployment=dict(SQL_writes=0, strategy='SEPARATE_ADDITIVE_ISOLATED_STORE_ONLY;NO_ORIGINAL_SCHEMA_MIGRATION',
                    backup='MANAGED_EXCLUSIVE_NEW_STORE_BACKUP_AND_READABILITY_CHECK_BEFORE_ADDITIVE_UPGRADE',
                    rollback='TRANSACTION_ROLLBACK_AND_OLD_FACT_HASH_CHECK;NO_SILENT_FILE_RESTORE'),
                full_target=dict(start='2013-01-01', end='2026-09-30', venues=['SSE', 'SZSE', 'BSE'],
                    base_daily_calendar_upper_bound=30126, market_expansion='VERIFIED_CALENDAR_UNION;GLOBAL_CONSUMPTION_EXCLUSION;UNKNOWN_OVERLAPS_HOLD',
                    calendar_2013_SSE='DERIVATIVE_PENDING', calendar_2013_SZSE='CONSUMED_UNKNOWN_HOLD', BSE_holds='UNCHANGED;INCEPTION_AND_MAPPING_EVIDENCE_REQUIRED',
                    financial_requests=None, industry_requests=None, security_requests=None, rule_documents=None,
                    pagination_extra_requests=None, total_budget=None, IO_storage_budget=None, execution_license=False),
                go_no_go=['MATCHED_FINAL_SHA_AND_PINS_AND_HUMAN_LICENSE', 'FULL_PROTECTION_AND_LEGACY_HASH_MATCH',
                          'NO_NEW_FAILED_UNCERTAIN_STRANDED_OR_CONFLICT', 'CIVIL_ROWS_AND_CROSS_WINDOW_CALENDAR_VALID',
                          'CAP_BELOW_LIMIT_IS_RAW_ONLY;UNKNOWN_CAP_REQUIRES_COMPLETENESS_POLICY',
                          'FUTURE_RESEARCH_REQUIRES_APPROVED_EPISODES_SESSION_STATUS_RULE_INDUSTRY_AND_FINANCIAL_VINTAGES'],
                phase1_final_standard='TARGET_COVERAGE_AND_NO_FUTURE_LEAKAGE_AND_SECOND_SOURCE_SAMPLING_AND_REBUILD_INCREMENT_AND_INDEPENDENT_FINAL_REVIEW',
                new_market_API_in_engineering=0, original_SQL_writes_in_engineering=0, research_admitted=False)


def expand_market(root: Path, destination: Path, baseline: dict, *, start: str, end: str, budget: int) -> dict:
    """Offline deterministic proposal only; missing civil coverage stops expansion."""
    require(type(budget) is int and budget > 0, 'EXPLICIT_EXPANSION_CAP_REQUIRED')
    require(day(start) <= day(end), 'EXPANSION_WINDOW')
    with acquisition.store(root, destination, fixture=destination.resolve() != (root / PRODUCTION).resolve(), read_only=True) as db:
        pipeline.inputs(root, destination, db)
        pipeline.verify_generation_inputs(root, destination, db)
        rows = pipeline.fact_rows(db)
        local = acquisition.local_consumption(db)
    calendars = [r for r in rows if r['dataset'] == 'trade_cal' and day(start) <= day(r['event_date']) <= day(end)]
    require(calendars, 'CALENDAR_REQUIRED_FOR_EXPANSION')
    from datetime import timedelta
    expected = {day(start) + timedelta(days=i) for i in range((day(end) - day(start)).days + 1)}
    require(all({day(r['event_date']) for r in calendars if r['payload']['exchange'] == venue} == expected
                for venue in ('SSE', 'SZSE')), 'EXPLICIT_VENUE_CIVIL_COVERAGE_REQUIRED')
    requests, held = [], []
    sessions = sorted({r['event_date'] for r in calendars if r['payload']['is_open'] == 1})
    for date in sessions:
        for dataset in sorted(contracts.MARKET):
            request = contracts.request(root, dataset, dict(trade_date=day(date).strftime('%Y%m%d')))
            try:
                legacy.check_unconsumed(request, baseline)
                require(not any(logical_id(request) == r['logical_id'] for r in local), 'CONSUMED_NEW_REQUEST')
            except Phase1Error as error:
                require(str(error) in ('ALREADY_CONSUMED_GLOBAL_REQUEST', 'OVERLAPPING_HISTORICAL_SCOPE_HOLD', 'CONSUMED_NEW_REQUEST'), 'UNEXPECTED_EXPANSION_HOLD')
                held.append(dict(logical_id=logical_id(request), dataset=dataset, date=date, action='REUSE_OR_HOLD_NEVER_RESEND'))
                continue
            requests.append(request)
    require(len(requests) <= budget, 'EXPANSION_EXCEEDS_EXPLICIT_CAP')
    return dict(execution_license=False, reviewer=None, approved_at=None, requests=requests, held=held,
                request_count=len(requests), expansion_hash=digest(requests), BSE_inception_scope_certified=False,
                research_admitted=False, root=str(root.resolve()), legacy_hash=digest(baseline))
