# Phase1 Integrated Data Foundation — Design v1

## Boundaries and entry point

Add `astock.phase1` and `config/phase1/` with a separate isolated-store DDL. Invoke through `python -m astock.phase1`; do not edit frozen capture/metadata/133 engines or their catalogs. Production destination is proposed only. Original stores remain managed read-only. No new dependency is needed.

## Acquisition and recovery

Contracts bind wire fields, precise parameter semantics, types, units, natural keys, nullable fields, row caps and empty-result evidence. Two explicit provider envelope profiles preserve every byte; optional detail/count/has_more have typed diagnostic meaning, not row-count/coverage authority. Unknown business fields stop. Calendar completeness uses every civil date and internal pretrade links; leading predecessor remains separately unknown.

Consumption identities use source/dataset/semantic params, independent of fields/contract/run/root. Import old133/metadata/capture/v3 durable facts into a frozen read-only snapshot; consumed keys never become retryable, uncertain overlapping windows HOLD. Each batch binds root/destination, current global consumption, pins, members/order/budget and predecessor stop. Claims and CALL_ENTERED commit before HTTP. First new error stops the batch; explicit matched recovery can execute only untouched members, retaining every failed claim. Production and fixture licenses cannot interchange.

Publish raw/source/typed/manifest/sidecar, then validate their physical bytes inside the completion transaction. Missing/orphan objects and interrupted claims never become success. Logs preserve primary business errors and disclose secondary output failures. Successful capture, scope completeness and research eligibility are separate facts. Offline validation of an old complete failed body creates a new derivative record with new validation time and old hashes; it changes no old request, event or receipt.

## Domain and point-in-time model

Keep versioned immutable source records plus source/object/generation lineage. Domain adapters produce executable security/episode, calendar, market, status, financial, industry, rule and index-reference records. Securities require explicit evidenced IDs, not names/code suffixes. Effective intervals are half-open; knowledge versions are selected before interval filtering. Ambiguous concurrent facts quarantine rather than choose.

Distinguish report/event date, source publication precision, availability, retrieval/recording and effective intervals. Current financial downloads default to observation availability and cannot be backdated by ann_date; historical publication mode requires version-specific vintage evidence. Date-only publication uses an explicit reviewed conservative next-session policy, never invented intraday precision. Query revisions by as-of knowledge, retain delistings/industry exits and taxonomy versions. Adjustment anchors must be known at query time. Rules select exchange/board/status/listing-age and source/effective scope, with NULL/overlap explicitly unknown/conflict.

## Quality, rebuild and integrity

Separate transport/contract/identity/session/vintage/industry/rule/coverage reasons, retaining old402060 findings. Deterministic rebuild and append-only increment use fixed source manifests and logical hashes; no physical-DB-hash equality requirement across environments. Consumers see queryable fixture evidence and explicit unknowns, never implicit production admission.

Retain full content-hash protection at batch start/end and before every production call until an equivalent cheaper protocol is proved. Measure its cost on a controlled finite fixture; do not optimize based on mtime/size alone. Readback/tamper checks, managed exclusive writer ownership and durable orphan-stop behavior remain mandatory. This intentionally retains potentially expensive safety scanning while other modules advance.

## Concrete adapter and admission choices

The 23 core contracts include three current master statuses, `bak_basic` archival claims, four ordinary per-security financial APIs, SW classification/members, index reference, six evidenced fact domains and the six market APIs. `fina_indicator` window dates select report periods; the other financial windows select announcements. Unknown caps stay unknown. `index_basic.base_point` is numeric in the new contract, following the official output table; frozen catalogs are unchanged.

Listing episodes and identifier intervals are separate. Resolution requires a compatible episode; native strings survive normalization failures. An approved legacy adapter reconstructs the original resolver with all exact source observations, without generating wider aliases. SQL history views expose the unified immutable facts. Status events alone are single-day evidence. Rule queries require explicit status/board/listing/session evidence; buy quantity constraints do not certify odd-lot sells or fills.

Offline fact packages bind real document receipts and a canonical batch digest. Production adoption requires actual matched independent policy and human license bytes at a clean reviewed SHA; fixtures require synthetic namespaces. Publication backdating additionally requires the approved version-specific knowledge policy bound into the source record. Reopen validates its evidence rather than trusting a policy hash claim. No production policy is authored in this batch.

An approved raw interpretation can reference an existing captured financial/market/industry record or the exact complete failed calendar. It compares every response value, request scope and physical source/body hash before deriving new facts. It sends no API, creates no capture receipt and changes no old status. Rebuilds also revalidate the original raw reference, policy and document evidence. This supplies the production route for independently evidenced historical vintages rather than treating fixture backdating as authority. As-of results label later-knowledge/event-date reconstruction explicitly; the demo also exercises two same-day market/financial queries, with closing prices unavailable before their fixture publication cutoff.

Rebuild stores retain source descriptors and verify original bytes when queried, including after rebuild. Generation, normalized facts, quality and lineage commit together with physical reread. Increment retains earlier sources and rows and appends corrections as knowledge versions. The exact pilot is one ordered bounded capture plan; all phases within it advance only while its required checks succeed. Full-target expansion is an offline license-false proposal from civil-validated calendars, excluding consumed scopes; budget and missing venue evidence stop it.

## Acceptance and review

Exercise nonempty datasets through the public CLI, stopped original-store copy27 mock, real365-row offline adaptation, business/logging/crash/root/approval/budget/clock mutations, financial/industry/rule/PIT boundaries, deterministic rebuild and idempotent increment. Run affected tests during development, one final full suite/doctor/contracts and final exact-SHA CI. Deliver one matrix, report, private index and phased license=false application; current sources/permissions/history coverage remain external gates.
