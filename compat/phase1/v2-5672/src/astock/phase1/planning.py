"""Finite candidate quantities and explicit unresolved expansion dependencies."""
from datetime import date


def full_target():
    start,end=date(2013,1,1),date(2026,9,30)
    civil=(end-start).days+1
    quarters=[f'{y}Q{q}' for y in range(2013,2027) for q in range(1,5) if (y,q)<=(2026,3)]
    return dict(protocol='PHASE1_FULL_COVERAGE_CANDIDATE_V2',start=str(start),end=str(end),execution_license=False,
        civil_days=civil,calendar=dict(venue_year_upper=3*14,venue_year_basis='3 venues ×14 calendar years; BSE inception/holds require evidence',current_untouched27=27,reuse_failed_SSE2013='SEPARATE_DERIVATIVE_ADOPTION_REQUIRED',consumed_unknown='HOLD_NEVER_RESEND'),
        market=dict(interfaces=6,civil_day_request_upper=civil*6,actual_requests=None,formula='6 × verified trading-date union minus reusable/consumed members; uncertain overlaps HOLD',unknowns=['civil venue coverage','historical universe','permissions','cap/pagination','empty policy']),
        security=dict(current_status_venue_partition_candidates=9,formula='3 venue partitions × L/D/P; source support/overlap must be tested',historical_archive_first_year=2016,archive_trading_dates=None,episodes_bindings_documents=None,missing_2013_2015='SOURCE_GAP_NOT_INFERRED'),
        financial=dict(report_quarters=len(quarters),quarters=quarters,predecessor_quarters=['2012Q4'],ordinary_interfaces=4,
            nominal_report_probes_per_security=4*(len(quarters)+1),total_requests=None,
            formula='4 × approved security/report-period units; split announcements/revisions and pagination only as approved members',
            unknowns=['historical listing universe','required earlier predecessor reports','company/report types','account permissions','vintage archives','revision completeness','unknown caps','announcement windows']),
        industry=dict(classification_version_level_candidates=6,formula='SW2014/SW2021 × L1/L2/L3 candidates; pilot retains two L1 calls',membership_requests=None,unknowns=['version activation','member universe','exit inclusivity','early history','source caps']),
        rules=dict(documents=None,formula='official version × venue/board/status/IPO effective scope',unknowns=['historical versions','deferred clauses','lots/sell odd-lot','session/listing age']),
        reference=dict(pilot_requests=2,full_index_daily_request_upper=civil,actual_requests=None,scope='minimal original-roadmap reference, no index research expansion'),
        IO=dict(calendar_row_upper=civil*3,market_row_formula='sum(active evidenced universe per verified session) × applicable endpoints',raw_bytes=None,normalized_bytes=None,storage_budget=None,
            history_scan_seconds_observed=53.95,protect_every_call=True),
        total_budget=None,go_no_go='pilot source evidence then matched finite expansion; no total license from upper bounds')
