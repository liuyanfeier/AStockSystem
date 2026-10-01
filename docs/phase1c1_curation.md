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
