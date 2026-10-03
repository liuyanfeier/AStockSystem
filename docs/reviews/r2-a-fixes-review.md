# R2-A consolidated F1–F3 repair review

Author status: **R2_A_REVIEW_READY**, pending independent review. The independent
review of `68b62ca6fb65e28b4ea059ca8c197c244b5a2253` was CHANGES_REQUIRED.
This package records author verification; it does not declare independent PASS.
R2-B **NOT_AUTHORIZED**, real-data gate **BLOCKED**, Phase1C.2 **CLOSED**.

## Baselines and approval artifacts

R1 FINAL approved baseline: `cc458ce2e8229dcc914e9a45ae2ac6186f48c45c`.
Repair design frozen before implementation at
`e59d012e65a2d12301dd0ce76ed80bff60df906e`.
Tested implementation: `5108731af43bc0738144b6e835c5b65f5f5fc37f`.
The final delivery SHA is the commit containing this report and
[repair manifest](r2-a-fixes-manifest.json); obtain it with
`git log -1 --format=%H -- docs/reviews/r2-a-fixes-manifest.json`.
Final handoff is withheld until that exact SHA's CI succeeds; its SHA, CI URL,
job result and log checksum are recorded in ignored
`data/private/phase1c1-r2-a-fixes/final-handoff.json` and the delivery reply.

Retained [independent review](2026-10-03-phase1c1-r2-a-independent-review.md),
[original repro](2026-10-03-r2-a-independent-repros.py),
[fix prompt](../remediation/phase1c1/Codex_Phase1C1_R2_A_Consolidated_Fix_Prompt.md)
and [authorization](2026-10-03-r2-a-fixes-authorization.md) are unchanged records.
[Design addendum 3](../remediation/phase1c1/r2-a-design-v1-addendum-3.md) hash:
`8d4e77c29c8a56e70fc3a4cb2ac8746a049c8cfc3a6e7d992defe9af7062f069`.
Old design/addenda/policy hashes retain their bytes; all schema and implementation
hashes are in the manifest. New approvals/contexts must pin
`correction_addendum_hash`. `approved_case_set/hash` remain **null**.

## Defect closure evidence

| Finding | Corrective implementation | Synthetic negative and positive evidence |
|---|---|---|
| F1 / P1 | `reconstruction_dq.py:137,257` validates each daily row against exactly one factor at security/episode/event scope | Empty factor with one daily is BLOCKED at its raw row; NULL/zero/negative/duplicate/wrong event or identity block; isolated and gap-reset valid factors PASS. Nonfinite factors are rejected. No imputation |
| F2 / P2 | `reconstruction_dq.py:141,307` emits each actual abnormal pair; current raw event is primary scope, previous raw event participates in stable key | May 7 causal and factor mismatches are dated May 7: daily May 7 BLOCKED, May 8 PASS. Appending clean May 9 preserves earlier finding keys/date/source/payload |
| F3 / P2 | `reconstruction.py:179,390` plus undeployed SQL009 persist/validate context-specific snapshots | Same synthetic store: old COMPLETE, later approved v2 binding plus episode/code, new COMPLETE; both explicit selections/audits valid, old rebuild logical/schema/source identical. Pinned episode/code/binding/observation, snapshot payload/membership or missing snapshot all reject |

`tests/test_reconstruction_regressions.py` contains 26 new cases. The original
three failures were reproduced before repair with provider/HTTP/socket denial
and zero counters. The repair keeps causal scaling and tolerances unchanged:
price 0.011; causal 0.011 percentage points; factor
`0.011 + 100 * 0.011 / current pre_close`. Old immutable DQ/source code is untouched.
Aggregate pair counts remain separate from source findings and output admission.

## Validation and preservation

Affected tests: **78 passed**, three production-shape cases deferred to the full
suite. Full offline suite: **589 passed, 1 warning, 406.25 seconds**; all production
shape cases pass. The warning is the existing multithreaded fork deprecation.
Doctor, v1/v2 contracts, probe plan, identity specs, slice plan/specs all pass.
CI uses existing locked dependencies and Python 3.12 without a market token.

Separate read-only author preservation check: 19 original table contents,
181 raw captures, 252 old curated/lineage objects, frozen identity, schema001–007,
133 completion bindings and upgrade audits, and all 1,102 protected files unchanged.
Strict receipts: **VALID / EXACT, checked133, failures0**. DB before/after SHA:
`2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`.
Original source facts remain **402,246 = 394,580 resolved + 7,666 quarantine**.
Existing 26 private evidence artifacts, prior public report/manifest and candidate
hashes remain unchanged. Private repairs evidence index is pinned in the manifest.
No original schema deployment, real bindings, real generation or real DQ occurred.

Decoded Parquet/current-credential and credential-pattern scans pass (1,753 paths
in the preservation scan; final public/staged files receive another literal scan).
No `.env`, credential, database/WAL, raw/curated data, `.tools` or `.venv` is staged.
Original offline verification denies provider construction/fetch, HTTP and sockets:
all counters **0**. Regression tests use temporary synthetic stores and deny network.
Private rows, backups, logs and receipts remain ignored.

## Unresolved historical facts and stop

No historical evidence is newly approved. Venue sessions/universe are incomplete;
unknown limit assets, NULL/CDR conflicts, delist semantics, and current stock_basic
old-code omissions still need evidence. Existing scoped candidates, proposal hash
and frozen carry-forward proposals remain inactive. Engineering repair does not
grant historical PIT, full-history admission or market-data permission.

Stop after final exact-SHA CI verification and await one independent R2-A review
of implementation, amended context/DQ policy and the explicit approved case set.
