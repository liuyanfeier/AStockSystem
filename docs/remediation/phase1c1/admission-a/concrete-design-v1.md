# Admission A Concrete Design v1

Frozen before implementation. Baseline 45e474ef3e6f49b56ea3b1b6f9c4fa7177470f45; R2 UTC instant v2 semantics remain unchanged. This is an author proposal, not policy approval or execution license.

## Investigation and immutable scope

Take a managed read-only inventory of all 34 current tables, current database bytes and all existing data/reports/private files, excluding this new run and lock files. Stream canonical rows in SQL `ORDER BY ALL` and hash newline-separated `receipt_integrity.serial` JSON. Verify strict 133 exact receipts and old181 raw/252 curated using existing validation. After investigation and testing compare the same inventory. Never migrate or write the original.

One ledger entry per (raw UUID, zero-based ordinal) covers 402246 source rows. Retain old resolution, legacy quarantine/finding/case/carry memberships and approved bindings as independent tags; do not add overlapping populations. Candidate groups share a rule, never a wildcard mapping. Material indexes point to immutable large local ledgers with byte hashes. Existing candidate models remain unapproved; unknown episodes, code reuse, provider delisting semantics and NULL exceptions remain EVIDENCE_REQUIRED. Evidence for code changes alone does not prove every endpoint representation.

Separate existing192 approvals, incremental unapproved delta and merged candidate snapshot. Approval references, reviewed SHA and approved_at for NEW proposals are null. Existing approval instants are preserved. Final independent review must approve all hashes and metadata; the author cannot fill them. Session matrix expands from the current 63 checks to venue/event/previous-day pairs. Existing SSE captures prove SSE only. Missing15 bars are searched in the existing raw universe and distinguished from unresolved aliases.

## Offline lifecycle v2

A separate synthetic-only schema contains plans, append-only claim/call/result events and validated raw manifests. Creating PLANNED work makes no HTTP attempt. A claim durably commits RUNNING before transport; local call-entry is committed before invoking the injected fake transport. Neither marker proves a remote receipt. Unknown/crashed attempts require human reconciliation and cannot be automatically resent. Terminal completion requires exact registered immutable bytes, nonempty manifest identity and checksum; it never accepts a random object UUID. Preserve plan/claim/call/finish/retrieval/availability/verification instants separately. Idempotent completion preserves all first times. No live-client entry point or original migration is introduced.

## Full-scale offline membership v1

A separate dataset-year manifest has execution_license=false. Stress universe is every civil date 2013-01-01 through 2026-09-30 times six datasets: a conservative synthetic upper bound, not certified sessions or request approval. Persist exact member IDs in an isolated managed store. Publish immutable typed Parquet and a sidecar, then register. Only exact complete manifest membership promotes; selection refuses partial generations. Recovery verifies files/sidecars/schema/content and detects orphan/tamper/extra/unknown members; replay must be idempotent across dataset-years. Representative nonempty rows verify content and source-row conservation. Empty partitions only exercise membership and recovery. Inject file, sidecar, registration and promotion faults. Report actual runtime, memory, disk and count; real-history throughput remains NOT_PROVEN.

## Incremental import v1

A new wrapper validates the exact approved DELTA and existing-plus-delta resolver before delegating new insertions to the reviewed import. Old approved members need no new review or retiming. A complete canonical identical repeat returns ALREADY_VALID; any partially installed delta or changed member fails. New bindings may reference existing episodes. Temporary managed SQL tests prove durable close/reopen/idempotence and original metadata retention. This capability is tested with synthetic approvals only; no original invocation.

## Proposals and stopping rule

Reuse current DQ policy and fixed tolerances. No new real audit/generation or policy deployment. Package identity groups, finite scope ledgers, DQ/session/reference proposals, candidate bounded133/126 context, capability matrix, nonexecutable full-backfill budget and separate evidence-acquisition budget. Account permissions and actual full-range calendar counts remain UNKNOWN unless already evidenced. Provider caps and field semantics may use read-only documentation. Current observed captures are CURRENT_RECONSTRUCTION/OBSERVED_CAPTURE, never HISTORICAL_PIT.

Run targeted regressions during work; one final full suite, doctor, contracts, decoded secret/exclusion checks and final exact-SHA CI. Author status ADMISSION_A_REVIEW_READY; engineering self-check, evidence completeness and data admission are separate. Batch B NOT_AUTHORIZED and Phase1C.2 CLOSED even if all engineering tests pass.
