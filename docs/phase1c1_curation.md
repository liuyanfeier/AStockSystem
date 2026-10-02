# Bounded slice curation

Phase 1C.1 uses the exact plan in `config/slices/phase1c1.yaml`. Capture requires
`astock data slice capture --live`; `--stop-after 8` intentionally interrupts,
and `--batch <UUID>` resumes only unsent requests. Every request has one attempt.
A crash after registered raw publication reconciles locally; an uncertain HTTP
receipt blocks replay. Failed or capped captures block the batch.

`astock data slice curate --batch <UUID>` operates offline. It freezes the accepted
identity snapshot at the batch knowledge time, selects the latest known version
before applying `[valid_from, valid_to)` intervals, and joins exact provider
identifiers and venue intervals. It never matches names or code suffixes.
Ambiguity, conflicting provider exchange, changed inputs or broken lineage stop
curation. Unknown/native non-normalized identifiers and pre-BSE records remain in
raw and explicit quarantine. Non-STK limit records are outside this A-share scope.
Provider delisting dates remain unclassified metadata; no end date is invented.

Curation v2 preserves v1 and fixes `stk_limit.asset_type` and `exchange` to string,
as documented at https://tushare.pro/document/2?doc_id=183. Scalars are strictly
typed; units and permitted research usage are embedded in Arrow field metadata.
No scale conversion, imputation or precision guessing occurs. Empty partitions
have the same explicit schema as populated partitions.

Outputs are daily_bar, daily_basic_snapshot, adjustment_factor_observed,
suspension_daily and risk_warning_daily, plus price_limit_daily for validation.
Each row retains native `ts_code`, raw object ID, zero-based raw row number and
observed retrieval/availability timestamps. Availability is **OBSERVED_CAPTURE**;
identity and historical valuation snapshots are **CURRENT_RECONSTRUCTION**, not
historical point-in-time knowledge. Observed adjustment factors are audit-only.

Private lineage sidecars, manifests and quarantine details stay under ignored
`data/`. SQL stores governance and hashes, not market rows. `--rebuild` publishes
fresh generation objects from the same immutable raw inputs and verifies logical
hashes against generation zero, including schema, units, usage and row provenance.
Logical hashes exclude new publication time and run IDs; file hashes are separate.
A partial curation publication fails closed and requires investigation rather than
silently reusing an incomplete generation. No automatic HTTP recovery is involved.

## DQ acceptance

`astock data slice dq --batch <UUID>` verifies every raw and curated hash, schema,
identity snapshot, request receipt and row derivation. Cross-table checks use
resolved intersections; missing/provider-only sets are reported separately.
Price tolerance is 0.011 currency units; causal percentage tolerance is 0.011
percentage points. The independent observed-factor return audit allows the
explicit quoted-pre_close rounding allowance `100 * 0.011 / pre_close` additionally.
Thresholds are fixed before live capture and never adjusted to obtain a pass.

Expected coverage uses frozen historical venue start dates, not today's active
stock list. Missing rows require full-day S suspension, a listing boundary or
explicit provider delist metadata review; unexplained gaps are errors. Provider
status-only records, pre-BSE legacy rows and out-of-scope limits remain visible.
Missing early stock_st data cannot prove historical absence of risk warnings.
Open venue intervals after a provider delist date remain REVIEW, not fabricated
closed intervals. Sparse selected boundary cases cannot establish a global last
trading-date convention. Conversion success and DQ acceptance are distinct;
dataset_date_audit reflects the current generation's conservative batch DQ status.

The causal audit chains only adjacent SSE-calendar sessions for each security:
`scale_t = scale_previous * previous_close / pre_close_t`, starting at 1 for each
segment. It checks causal return against pct_chg, and independently checks observed
factor return. Gaps reset segments; this is an audit, not a strategy or qfq series.
The SSE-calendar adjacency basis does not independently certify every BSE session.
Official identity intervals separately verify six pilot changes on 2025-05-06 and
242 remaining changes on 2025-10-09, plus pre-opening exclusions. Incomplete
observed transition pairs stay REVIEW. Errors block acceptance; review items stay
PARTIAL until adjudicated. No DQ finding triggers new provider requests.

## R1-G1 remediation admission boundary

The workflow above describes the historical rehearsal, not permission to execute
it again. Current market request budget is zero. Exact receipt proof and migration
007 bindings now precede resume, CAPTURED promotion, curation and DQ. Local crash
reconciliation additionally requires already published sidecar and capture-contract;
registered raw alone is insufficient. Old real receipts remain unbound until the
approved R1-G3 copy/backup deployment; no real curation or DQ is authorized in G1.

The new token-free `astock data slice audit --batch UUID` performs read-only receipt
verification; `--legacy-preflight` explicitly reports unregistered legacy evidence
without migration or acceptance. G1 uses synthetic fixtures only. Follow the
[R1 specification](remediation/phase1c1/Phase1C1_R1_Engineering_Integrity_Spec_v1.0.md)
and wait for independent review before R1-G2. R2 and Phase1C.2 remain closed.
