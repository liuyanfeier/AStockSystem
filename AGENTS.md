# Repository Guidelines

## Scope & Structure

AStockSystem is a macOS A-share research project. R1 FINAL independently passed at `cc458ce2e8229dcc914e9a45ae2ac6186f48c45c`. The user authorized R2-A under `docs/remediation/phase1c1/Codex_Phase1C1_R2_Batched_Prompts_v1.1.md`; see `docs/reviews/2026-10-02-phase1c1-r2-a-authorization.md`. Freeze concrete design before implementing provider/episode resolution, DQ policy, context/publication/quarantine/audits and synthetic regressions. A replaces intermediate G0/G1/G3/G4 pauses and permits G2 proposals only. Original warehouse, raw, old252 curated/lineage, frozen identity/receipts/audits, SQL001–007 and old specifications/reviews remain immutable; no real new bindings/episodes or generations take effect. Use scoped managed connections per `docs/phase1c1_writer_lifecycle.md`. Missing evidence is EVIDENCE_REQUIRED, conflict is CONFLICT; never infer aliases, merge company successors, rewrite native identifiers or relax NULL/tolerances. Zero market/provider requests, including metadata/mapping/calendar; no capture/resume/replay. Read-only official/provider documentation is allowed. Complete all A work with focused commits, one final full offline verification/secret scan and final exact-SHA CI, then stop as R2_A_REVIEW_READY for independent policy/context/approved_case_set review. R2-B NOT_AUTHORIZED, real-data gate BLOCKED, Phase1C.2 CLOSED; no backfill, strategies, signals, backtests, portfolio, broker or orders.

Current repair batch: F1–F3 from the retained 2026-10-03 independent review and consolidated fix prompt; see `docs/reviews/2026-10-03-r2-a-fixes-authorization.md` and frozen design addendum 3. Complete together with synthetic regressions, offline preservation/secret checks and final exact-SHA CI; retain previous review packages. No original deployment or real R2 approvals.

Latest authorized batch supersedes that historical repair scope: R2-B time-integrity P1 engineering fix per `docs/reviews/2026-10-03-r2-b-time-integrity-fix-authorization.md` and new frozen addendum 4. Repair both resolver digest and pinned-member time comparison, require explicit v2 protocol/design pins, run managed synthetic SQL/reopen/rebuild/tamper regressions and actual-material read-only checks. Preserve all v1 approvals and failed isolation; no original writes or author production approval. Deliver once as R2_B_TIME_INTEGRITY_FIX_REVIEW_READY with final exact-SHA CI; real B execution awaits matched reviewer reapproval. Zero market requests; Phase1C.2 CLOSED.

Matched-v2 execution authorization now supersedes that waiting boundary: see `docs/reviews/2026-10-03-r2-b-matched-v2-resume-authorization.md` and the verbatim matched-v2 resume prompt. Independent repair PASS and actual approval pin reviewed/Context SHA 0251e485396fb9e1a4214f71a298ad2777ebde90. After verified007 backup and fresh full isolated rehearsal, deploy approved008–010/import/register on original, publish two explicit COMPLETE generations, exact-evidence DQ and four-timezone same-Context rebuild; preserve original19 tables,1102 files, all old approvals/failed isolates/reviews. No source/schema/policy/test/design changes or author approval. Finish full offline checks and final exact-SHA CI, deliver once as R2_FINAL_REVIEW_READY, then stop. Zero market requests; real-data gate BLOCKED, Phase1C.2 CLOSED.

Use `src/astock/` for Python, `tests/` for pytest, `config/` for versioned configuration, `sql/` for schema, `docs/` for contracts and governance, and `skills/` for workflows. Local data belongs in `data/{raw,curated,warehouse}/`; generated outputs belong in `reports/`.

## Development & Style

Use Python 3.12 and project-local uv. From the repository root, `export PATH="$PWD/scripts:$PATH"`, then `uv sync --locked`, `uv run pytest`, `uv run astock doctor`, and `uv run astock data contracts`. The wrapper keeps tool storage local. Use four-space indentation, type hints, `snake_case` functions/modules, and `PascalCase` classes. No formatter/linter is configured. Explain necessary new dependencies before adding them.

## Data Integrity

Never use future information. Model time-sensitive data point-in-time; distinguish `period_end`, `published_at`, `available_at` and effective intervals. Do not silently apply today's knowledge historically. Retain delisted securities and historical ST/risk-warning, suspension, board/listing and industry membership. Identify every source; keep raw data append-only/immutable where practical. Derived features must be reproducible from stored sources. Follow `docs/data_contract.md`.

## Execution & Research

Future execution/backtests must model applicable T+1, suspensions, board/ST rule changes, IPO exceptions, lots/order constraints, costs, slippage and overnight gaps. Never assume limit-up buys or limit-down sells are executable. Historical rules need effective dates.

Version strategy parameters in configuration, never here. Register hypotheses and changes before experiments; evaluate strategy modules separately. Do not optimize against final out-of-sample data or adopt strategies merely because results look good. Preserve historical reports; append corrections with provenance.

## Tests & Contributions

Name tests `test_*.py`. Test trading rules, time availability, historical rules and explicit data-quality assumptions when implemented. Run the full suite and doctor before review. Use imperative, focused commit subjects, e.g. `chore: establish astock phase-0 foundation`. PRs explain purpose, validation, linked issues, deviations and configuration/migration impacts; include screenshots for UI changes.

## Secrets

Keep `.env` local. Never send token through chat; live requests require `--live` and exact pinned HTTPS. Never commit or print secrets in logs/reports, request brokerage passwords, or introduce broker credentials in this phase. Commit placeholders only. Public Git must exclude raw datasets, private reports, balances, holdings and personal execution history; use ignored `private/` or `data/private/`. Lightweight sanitized review evidence belongs in `docs/reviews/`.

## Current Admission Batch A

The latest user authorization supersedes the prior completed R2 execution scopes: see `docs/reviews/phase1c1-admission-a/2026-10-03/authorization.md` and retained prompts in `docs/remediation/phase1c1/admission-a/`. Complete Admission A investigation, finite evidence proposals, minimum new-version offline capabilities, synthetic regressions and approval package together. Original schema 001–010 and every existing warehouse table, raw/curated/private evidence file and review remain immutable. Zero market/provider requests; official document lookup only. Preserve existing approved192 bindings; never manufacture reviewer metadata or production approval. Separate incremental case delta from merged resolver snapshot. Keep legacy bounded133/126 guards unchanged. Use managed read-only original connections and isolated synthetic stores. Final full offline checks, secret scan and exact-SHA CI; stop ADMISSION_A_REVIEW_READY. Admission B NOT_AUTHORIZED; Phase1C.2 CLOSED.

## Current Admission A Evidence Closure

User authorized the retained 2026-10-04 evidence-closure prompt after agreeing with independent F1/F2 findings; see `docs/reviews/phase1c1-admission-a-evidence/2026-10-04/authorization.md`. Correct materials in new versions, reuse accepted offline engineering and exact source ledgers, investigate shared official documentary evidence and prepare finite unapproved case/DQ/Context plus exact seven-SZSE metadata proposals. Freeze any minimal new offline design first; no live transport integration or execution license. Preserve all old private/public evidence, 34 original tables/schema001–010, approved192 observations and bounded133/126 guards. Zero market/provider requests; managed original read-only, permitted official documentation HTTP separately counted. No author production approvals. Full offline verification/secret scan/final exact-SHA CI, then stop ADMISSION_A_EVIDENCE_REVIEW_READY. Batch B NOT_AUTHORIZED; Phase1C.2 CLOSED.

## Current Combined Remediation and Candidate B Rehearsal

Latest human authorization supersedes the evidence-closure pause only within `docs/reviews/phase1c1-combined-remediation-b-rehearsal/2026-10-04/authorization.md` and retained combined prompt. Freeze a separate dedicated exact-seven metadata live design, implement and mock-test it without live calls; append D1 source correction and finite EVENT_NATIVE proposals. Evidence-supported nonempty candidates may enter a fresh managed isolated B snapshot under CANDIDATE_REHEARSAL_ONLY and fixture_only=true. Preserve old192 approvals and original133/126 scope; production approvals remain null/false. Original34 tables/schema001–010 and all historical files/guard/fake interfaces immutable; managed original read-only, no real API/capture/replay, no original deployment. One final offline/secret/exact-SHA CI delivery, stop COMBINED_REMEDIATION_B_REHEARSAL_REVIEW_READY. Formal B and real seven calls require subsequent matched independent approval and human authorization; Phase1C.2 CLOSED.

## Current Admission B Limited15 Execution

Latest human authorization supersedes the combined-rehearsal waiting boundary only within `docs/reviews/phase1c1-admission-b/2026-10-04-limited15/authorization.md` and the retained limited15 prompt. Use the supplied actual independent approval bytes, approved implementation SHA45554a142a8e8d3e1b6cb0147db537bc88d1b55e and Context470017335c3e7fd9f69480b35e2ac3012ceea2892a3f94706fdfcfb5af262475; no author re-signing or payload changes. After managed exclusive current backup and fresh matched production-shaped isolated rehearsal, append only3 daily bindings/15 single-day official codes/15 exact observations,0 episodes; register exact fixture_only=false Context and produce two126 COMPLETE generations/DQ/rebuild/four-timezone acceptance. Preserve all old34-table rowsets, old192 approvals,133 receipts/181raw/252curated/frozen identity and historical files/Contexts/generations. No repeated migration, allow_fixture, source/test/schema/policy/config/dependency/frozen-design changes or silent restore. Zero market/provider/metadata/calendar/mapping requests; no capture/resume/replay. Real metadata license remainsfalse. Final offline/decoded-secret/exact-SHA CI delivery once as ADMISSION_B_LIMITED15_FINAL_REVIEW_READY; stop for independent final Review. Global data admission BLOCKED; Phase1C.2 CLOSED.

## Current Import Atomicity and Finite45 Preview

The latest human authorization supersedes prior fixed-source restrictions only for
the retained importer P1 repair and candidate preview; see
`docs/reviews/phase1c1-import-atomicity-finite45/2026-10-04/authorization.md` and
`docs/remediation/phase1c1/import-atomicity-finite45/design.md`. Validate persistent
observation order without sorting signed payloads, and verify the complete merged
resolver before the core import transaction commits. Cover direct/delta rollback,
reopen, idempotence, real approved material read-only compatibility and four zones.
New finite45 proposals may reorder only their unapproved observation lists with
explicit old/new hashes and identical facts; preview once on a fresh managed
fixture copy with126 outputs and full row-set evidence. Original DB, fixed metadata
FAILED store and prior failed isolate remain immutable. All provider/document
requests and original writes are zero; no capture/resume/reset or133 replay.
Preserve old v2/time/schema/DQ/identity semantics. Commit focused source/tests/docs,
verify full offline tests, preservation/secrets and final exact-SHA CI, then stop
`IMPORT_ATOMICITY_AND_FINITE45_PREVIEW_REVIEW_READY`. Limited15 remains accepted;
finite45 production approval pending, global DQ/calendar BLOCKED, Phase1C.2 CLOSED.

## Current Finite45 Formal Execution and Engineering Closure

The 2026-10-05 human authorization supersedes only the finite45 production-approval
waiting boundary; see `docs/reviews/phase1c1-finite45-formal-execution/2026-10-05/authorization.md`
and retained formal-execution Prompt. Approved/runtime/Context implementation 546b57b
and 171 source pins stay unchanged. Apply the actual independent 9 binding / 45 observation
approval only after verified backup and fresh formal fixture_only=false isolation;
0 episodes/codes/migrations, two 126 COMPLETE generations and approved append-only DQ.
Retain old 34 table rowsets/Contexts/outputs/approvals, fixed failed metadata and prior
isolates; only the authorized original DB hash/additive records and new outputs may
change. No source/test/SQL/config/dependency/design changes, provider/document calls,
capture/resume/replay/reset/license replacement or author independent PASS. Reuse
approved 753 / 119 tests, complete real application/offline/secret/preservation checks,
commit aggregate documentation and verify final exact-SHA CI. Stop
`FINITE45_FORMAL_EXECUTION_AND_PHASE1C1_ENGINEERING_CLOSURE_REVIEW_READY`
for independent final execution review; global DQ/calendar BLOCKED, Phase1C.2 CLOSED.

## Current Evidence and Phase1C2 Launch Preparation

Latest human authorization supersedes the completed finite45 stop only for the
retained evidence-and-launch-preparation Prompt and 2026-10-05 authorization.
Finite45 and Phase1C.1 engineering remain independently CLOSED; do not repeat them.
Preserve accepted171 pins, original34 table rowsets/schema001–010, all raw/curated,
old approvals/reviews and fixed FAILED metadata bytes. New separate runner/design,
CLI/schema/tests and exact unapproved evidence/full-plan/first-batch applications
are permitted. Freeze design before source implementation. Original managed
read-only, data API0, original writes0; no133 replay or old metadata retry/reset.
Direct official/provider DOCUMENT HTTP budget24 includes failures and redirects;
retain body/location/version/time and exact member scopes. Production candidate
review metadata null, execution license false; no author approval. Reuse accepted
30126 synthetic proofs; test the new closed-mock runner path, full offline suite,
decoded/encoded secrets and preservation, commit/push and exact-SHA CI. Deliver once
EVIDENCE_AND_PHASE1C2_LAUNCH_PREPARATION_REVIEW_READY and stop for independent Review.
Global admission BLOCKED pending external evidence; Phase1C.2 CLOSED.

## Current Runner Repair and Acquisition Readiness

The 2026-10-06 human authorization supersedes only the previous preparation stop;
see `docs/reviews/phase1c1-runner-repair-readiness/2026-10-06/authorization.md` and
retained repair Prompt. Complete F1–F4 and append-only v2 multi-plan synthetic
integration, plus exact29 candidate/7 HOLD calendar proposals with pending rules.
Freeze v2 design first, preserve v1 stores/design/DDL and all historical evidence.
API/document HTTP/original writes/replays/rebuilds/reset/retry all0. Managed original
read-only; no production approvals or license, no Phase1C.2. Full offline tests,
preservation/secrets and exact-SHA CI, then stop
RUNNER_INTEGRITY_REPAIR_AND_CALENDAR_ACQUISITION_READINESS_REVIEW_READY.
