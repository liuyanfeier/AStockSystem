# Full backfill capture v2.1 — frozen destination repair design

Frozen before implementation on 2026-10-06. Retain v1 DDL/design/stores unchanged.
No original warehouse migration or live authorization is part of this batch.

## Contract and physical completion

Catalog permits only suspend_d.suspend_timing as a nullable natural-key component,
with the exact accepted contract bytes and note as authority. NULL stays NULL;
required keys, empty strings and duplicate full tuples fail. No price/DQ change.
Use the same reconcile validator for reopened COMPLETE and tentative COMPLETE,
inside the receipt/event transaction after both fault callbacks, before commit.
Re-read all five files and source/body/time/UUID/member/plan/approval/event bindings
and exact deterministic typed bytes. Failure rolls back receipt/event only; durable
claim/call and damaged source evidence stay, no overwrite or second HTTP.

## Append-only registry, single global ledger

Protocol FULL_BACKFILL_CAPTURE_V2 uses a new independent DDL at the same fixed
production destination. Existing v1 stores are rejected read-only, never upgraded.
Backfill_pin stores immutable canonical plans keyed by canonical hash; separate
append-only authorization rows bind exact review/human bytes and hashes. A plan
membership table preserves exact descriptors and budget. Global members have one
origin plan, UUID and payload. A global consumption key hashes endpoint,dataset,params;
it excludes fields, contract version, evidence, plan/budget/namespace/run names.
Any descriptor difference on an existing logical member rejects, even if COMPLETE.
An identical cross-plan COMPLETE may reuse only after original plan/license and
five-file/receipt/event verification. Noncomplete overlap rejects; FAILED/UNCERTAIN
or unreconciled claim anywhere stops new sends. No new run/store reset in production.
Per-plan budget counts claims originating there; total claims remain auditable.
Managed exclusive ownership serializes register/claim; registries/old completions
are validated before new register/send. Old captures validate with their origin
provenance, never current-plan licensing. Changed archived plan or license hashes,
extra members, orphans and unknown schema fail closed.

## Calendar completeness and approvals

Rules are proposed evidence, not calendar certification or documented cap/account
support. Exact civil-date coverage, unique venue/date, valid native dates and 0/1
is_open; pretrade_date must precede cal_date and equal the last earlier open day
where observable. Leading unknown predecessor stays explicit; first request's
external predecessor is uncertified, and previous-lookback requests are linked.
29 candidates are SSE15/SZSE14; SZSE2013 and BSE6 remain HOLD, outside executable
membership. Empty/cap/truncation/wrong dates/venues/previous relations stop.

## Three hash domains

Finalize descriptors first. Runtime membership hashes exact requests in their
execution order; approval descriptor-set hash canonicalizes complete descriptors
by member_id (duplicate rejects), so reorder is stable but any field delta changes
it. File byte SHA256 is separate. Proposal validator checks exact runtime/descriptor
correspondence, budgets, candidate/HOLD partition and final index references.
Review/human production approval stays absent; all proposals execution_license=false.

## Final approval descriptor binding

Before implementing the final descriptor pin, freeze a separate finalized descriptor
file: its complete semantic descriptor-set checksum and file SHA256 both enter the
runtime plan's approval_descriptors reference. Exact requests match that file in
execution order. Review and human artifacts thereby pin the descriptor reference
through the immutable plan hash. No application/plan reference cycle; descriptor
file first, plan second, application/index/manifest last. FIXTURE adhoc plans may
explicitly use null; real PRODUCTION authorization requires this reference.

## V2.1 destination binding addendum

Frozen before implementation on 2026-10-08 after author packaging checks. The
review artifact must pin the canonical absolute production destination; its human
approval hash binds that field. `--root` cannot relocate consumption by cloning a
clean reviewed checkout: the reused review no longer matches the calculated
canonical destination. Fixture reviews explicitly carry null instead. Protocol
FULL_BACKFILL_CAPTURE_V2_1 rejects v1/v2 stores/approvals; no existing production
backfill store exists and no migration is authorized. Retain the 17e263a package,
full v2 source/design/DDL and all fixture databases as superseded author evidence.
