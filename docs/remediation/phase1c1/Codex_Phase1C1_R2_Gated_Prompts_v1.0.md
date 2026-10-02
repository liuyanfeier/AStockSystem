# Codex prompts — Phase 1C.1-R2（R1通过后逐Gate执行）

v1.0 · 2026-10-02。先把同包 `Phase1C1_R2_Historical_Identity_Coverage_Spec_v1.0.md` 放入项目可读文档目录。现在只生成规格；**全部R2 prompts尚未授权执行**。启动R2-G0需要R1 FINAL REVIEW PASS和用户明确授权；以后每次只复制一个Gate。

每个prompt中的 `[SHA]`、`[approval]` 是必填实际证据，不能把占位符当批准。代码作者只能报告 REVIEW_READY，不能替独立reviewer签字。修订后重审新SHA；测试/CI通过不自动推进。真实数据均留在ignored private目录，公开只交脱敏证据。

## R2-G0 — 证据台账与具体设计

```text
Execute ONLY R2-G0: read-only historical identity/coverage evidence and design.
Prerequisite: independent R1 FINAL REVIEW PASS at [R1 SHA], exact SHA CI PASS,
verified existing 133 receipts, and explicit human authorization for R2-G0.
Read the actual review record. If missing, STOP: R2_LOCKED.
Read R2 spec, R1 spec, AGENTS.md, full Phase1C.1 review and current HEAD diff.

Hard limits for every R2 gate:
- ZERO new market/provider APIs, including metadata/mapping/calendar calls.
- No 133 replay, old probes, capture/resume, stock_basic/bse_mapping recapture.
- Preserve raw, old curated generations 0/1, lineage, frozen request/identity,
  prior audit/reviews and migrations 001-006. New versions/contexts only.
- No Phase1C.2 or full backfill. No strategies/signals/backtests/broker/orders.

Tasks (read-only data; design documentation only):
1. Build private anomaly ledger covering all existing 7666 quarantine rows,
   5008 interval failures (4515 code-start /493 venue-start), 1374 PRE_BSE_LEGACY,
   1284 NO_IDENTIFIER_MAPPING, 2512 ERROR flags and 13244 REVIEW flags. Reconcile
   overlaps/source row counts; do not confuse flags with unique anomalies.
2. Observe BSE native representation by dataset, event date, capture time, raw row
   and known official pair. Keep 6 May pilots and 242 October changes distinct.
   Compare available earlier stock_st old-code evidence, without new API calls.
3. Case dossiers for 000022.SZ, 000043.SZ, 300114.SZ and unknown limit identifiers:
   episodes, listing/termination/restructuring/code reuse, provider evidence and
   missing stock_basic reason. Mark UNKNOWN rather than inventing company links.
4. Inventory 1226 coverage flags, delist boundary cases and 689009.SH/2021-11-12
   NULL pre_close. Identify official/provider sources and exact missing evidence.
   Read-only official announcements/provider documentation are allowed; preserve
   source URL, title, event/publication/retrieval times, summary/hash. No new market
   rows or downloadable security lists/mappings disguised as documentation.
5. Design provider/episode schema, resolver scope and bitemporal knowledge rules;
   exact raw evidence links; new derivation context; append-only audit and complete
   generation publication. Specify approved migration sequence without reusing
   occupied numbers. Do not change old batch identity_snapshot_hash/knowledge time.
6. Classify each proposed decision VERIFIED /EVIDENCE_REQUIRED /CONFLICT /
   OUT_OF_SCOPE and mark exact affected datasets/rows. A proposal is not approval.
   List bounded-vs-full-history limits and venue-calendar certification gaps.

No new aliases/episode records applied; no code model change; no real re-curation.
Write sanitized r2-g0-design-and-evidence.md and focused documentation commit.
Report exact SHA, available/missing evidence, test/CI status, zero market calls.
Result DESIGN_REVIEW_READY. STOP FOR INDEPENDENT REVIEW.
R2-G1 NOT AUTHORIZED. Phase1C.2 CLOSED.
```

## R2-G1 — Provider/episode模型与resolver

```text
Execute ONLY R2-G1 under R2 spec and approved G0 design.
Require R1 FINAL REVIEW PASS, independent R2-G0 DESIGN REVIEW PASS at [SHA],
and explicit human authorization for G1. Check actual HEAD and approved scope.
ZERO market APIs; no capture/replay/metadata/calendar refresh. Preserve raw,
old curated/lineage/identity/knowledge times/audits/migrations 001-006. No Phase1C.2.

Implement model and synthetic tests only:
1. Separate official EXCHANGE_CODE intervals from dataset/capture-scoped provider
   native bindings to security/listing episode. Preserve legacy ts_code resolver
   for old frozen contexts. No shared wildcard alias without specific evidence.
2. Provider binding must retain exact native string, event applicability, observed
   capture scope, knowledge availability, binding version, evidence and reviewer
   decision. New knowledge cannot appear in old knowledge_as_of.
3. Resolver accepts provider, dataset, native string, event date, capture context,
   knowledge_as_of; selects uniquely and checks episode/venue/explicit exchange
   and asset semantics. Ambiguity/conflict fails closed, never first-row-wins.
4. Add approved new schema/migration(s), FK/uniqueness/overlap validation and typed
   contracts. Define new quarantine row lineage with raw FK and zero-based row.
   Legacy quarantine lacking row numbers stays legacy; do not guess backfill.
5. No names/suffix/digit inference, no T-prefix normalization, no automatic old/new
   company/successor merging. No pre-BSE provider code creating pre-opening venue.

Test same event at old/new knowledge cutoffs; daily retrospective vs stock_st
event-native; unknown dataset/capture; scoped validity; 6/242 separate dates;
official old/new code invariance; before-venue failure; code reuse/episode conflict;
ambiguous candidates; provider exchange conflict; T600018.SH remains quarantined.
Use synthetic bindings ONLY; do not apply real historical decisions in G1.
Run full offline suite, doctor, contracts/typed specs, secret scan and exact SHA CI.
Write sanitized r2-g1-review.md, focused commit and review handoff with schema,
compatibility, test/CI, limitations and zero-market-call evidence.
STOP: G1 REVIEW_READY. R2-G2 NOT AUTHORIZED. Phase1C.2 CLOSED.
```

## R2-G2 — 逐case证据裁定与追加binding

```text
Execute ONLY R2-G2. Require independent R2-G1 Review PASS [SHA] with exact SHA
CI PASS and explicit human G2 authorization. Read R2 spec, G0 evidence dossiers
and the reviewer-approved list of real cases/bindings. R1 approval still required.
ZERO market APIs; no live probes or new lists/mappings/calendars. Preserve raw,
old generations, old accepted identity/snapshot and audits. Phase1C.2 CLOSED.

1. Apply only case decisions explicitly approved from evidence. New binding and
   episode versions are append-only and scoped to approved dataset, event/capture
   evidence. Store real records privately, publicly only sanitized summary/hash.
   No forced addition of raw rows or full securities lists to Git.
2. BSE: distinguish official 6-pilot May 6 switch and 242 remaining October 9 switch
   from provider retrospective representation. Every endpoint needs its own
   evidence; no daily alias propagation to stock_st or other endpoints.
3. Treat 493 before-venue rows independently of 4515 before-code rows. Pre-opening
   BSE records remain PRE_BSE_LEGACY/OUT_OF_SCOPE unless an independently proven
   other-venue episode is recorded; never admit them as BSE trading history.
4. Investigate 000022.SZ, 000043.SZ, 300114.SZ separately: exact security/episode,
   official events, restructuring/code reuse, provider identity, stock_basic omission.
   No guessed successor/name match. Unknown limit assets need explicit evidence.
5. Any case lacking approval/evidence stays quarantined EVIDENCE_REQUIRED or
   CONFLICT. Newly discovered cases go to reviewer; do not create aliases yourself.
6. Produce a dry-run resolution delta with raw row/binding/evidence provenance,
   no real curated publication. Preserve native identifiers and original times.

Run model/decision validation, negative scope/conflict/knowledge tests, full offline
checks and current SHA CI. Record old snapshot unchanged, new binding snapshot hash,
approved vs unresolved counts and private evidence references. Write sanitized
r2-g2-review.md and focused code/evidence commit through the established workflow.
Missing evidence may produce a bounded partial decision set, never fake mappings
or data PASS. STOP: G2 REVIEW_READY. R2-G3 NOT AUTHORIZED. Phase1C.2 CLOSED.
```

## R2-G3 — Coverage/delist/NULL/calendar与DQ政策

```text
Execute ONLY R2-G3. Require independent R2-G2 Review PASS [SHA], exact SHA CI
PASS and explicit G3 authorization. Read R2 spec and approved case decisions.
ZERO market APIs; no refresh/capture/replay. Preserve all historical inputs,
generations, identity records, reports and audits. Phase1C.2 CLOSED.

Freeze and implement DQ policy BEFORE looking at new real-generation DQ totals:
1. Coverage by security/listing episode/venue/date/dataset, using historical
   episode evidence. Distinguish identity-induced false gaps from missing bars.
   Separate observation from disposition: an observed bar cannot be hidden by
   date>=provider_delist_date. Current active lists cannot define old universe.
2. Explain gaps only with approved exact evidence: full-day suspension, official
   episode boundary or asset scope. Partial suspension, S/R conflicts, unclassified
   delist dates and insufficient listing evidence remain review/blocking.
   No effective_to=provider_delist_date+1 global rule, no deletion of delisted IDs.
3. Split NULL/reference-missing/numeric mismatch. 689009.SH/2021-11-12 gets only
   reviewed evidence-scoped disposition; if unresolved keep ERROR/BLOCKED.
   Preserve NULL. No fill from daily, zero/default imputation or tolerance change.
4. Split BSE official code transition, provider representation validation and
   security/episode continuity. Same raw native code across switch may be correct
   only under verified retrospective binding. Missing observed side is NOT_OBSERVED.
5. Venue-specific session basis. Existing SSE calendars cannot certify all BSE/
   SZSE sessions. Unknown adjacency is NOT_CERTIFIED; gap/episode reset behavior
   explicit. Keep causal and factor audit methodology and fixed tolerances.
6. Define append-only findings, curation quality and batch acceptance audit;
   local_status independent of batch_gate_status. No UPDATE of old dataset_date_audit.
   Stable keys link old flags to new disposition, with evidence/decision/blocking.

Synthetic tests cover delist metadata+observed bar, termination vs last trading,
survivorship, identity repair effects, suspension conflicts, NULL not-applicable
scope negatives, unknown calendar, official vs provider transitions, future factor
prefix invariance, and batch BLOCKED with local PASS.
Run full offline tests/contracts/specs/doctor/secret scan, current SHA CI.
Write r2-g3-review.md with fixed policy hash and approved exception evidence.
Do not publish/run a new real generation yet. STOP: G3 REVIEW_READY.
R2-G4 NOT AUTHORIZED. Phase1C.2 CLOSED.
```

## R2-G4 — 派生context、完整generation与审计出版

```text
Execute ONLY R2-G4. Require independent R2-G3 Review PASS [SHA] with exact SHA
CI PASS and explicit G4 authorization. Read approved R2 context/publication design.
ZERO market APIs. Preserve raw, old curated 0/1, lineage, snapshot, batch knowledge,
audit records and migrations 001-006. No real new generation in G4. Phase1C.2 CLOSED.

1. Add explicit derivation_context linking parent batch/generation, exact immutable
   raw set, old snapshot, new approved binding/episode snapshots, spec/DQ hashes,
   new knowledge cutoff, tested code SHA and approval refs. Never edit frozen batch.
2. Preserve legacy same-context rebuild against old logical hashes. New identity
   context has a new derivation, not a legacy --rebuild with mismatch check disabled.
   Same-context rebuild MUST still produce identical logical hashes.
3. Complete generation manifest expects 126 noncalendar outputs from 133 verified
   raw requests. Unique context/generation/request keys; per-object verified
   registration; no promotion until the full expected set and row lineage pass.
   DQ selects explicit complete generation, never max(generation) over partials.
4. Safe resumable publication after file/sidecar/DB/promotion failure. Validate
   orphans by exact context and checksums; never trust existing file alone; no double
   binding or deletion/overwrite of old generations. Use R1 DB process lock.
5. New quarantine schema/raw FK/zero-based row lineage. Source rows classified
   exactly once; resolved+quarantine preserves all rows, including out-of-scope.
6. Add append-only versioned DQ/curation acceptance audits and stable finding ledger.
   Keep original dataset_date_audit untouched. Generation COMPLETE is publication,
   not research admission or independent Review approval.
7. Outputs preserve native identifiers, raw timestamps, typed units/empty schema and
   CURRENT_RECONSTRUCTION/OBSERVED_CAPTURE basis. Identity availability separately
   tracks new knowledge. Never label these outputs historical PIT.

Test crash at kth file, lineage, DB insert, promotion; repeat/resume; concurrent writers;
unknown context; partial not selected; legacy rebuild; new context deterministic
rebuild; exact raw row conservation; quarantine FK; old audit bytes unchanged.
Synthetic data ONLY. Run full offline checks/secret regression/current SHA CI.
Write r2-g4-review.md with migration/protocol/invariants and focused commit.
STOP: G4 REVIEW_READY. R2-G5 NOT AUTHORIZED. Phase1C.2 CLOSED.
```

## R2-G5 — 现有raw离线新派生、rebuild和DQ

```text
Execute ONLY R2-G5 under R2 spec. Require independent R2-G4 Review PASS [SHA],
exact SHA CI PASS, reviewed R2-G2 bindings/R2-G3 policy and explicit G5 authorization.
Original batch=1d34d71f-c711-4893-9729-0b719bbba6dd.
ZERO market APIs; no capture/resume/replay/refresh. No new source market data.
Preserve 181 old raw, old 252 curated, lineage, identity snapshot, old reviews/audits.
Phase1C.2 CLOSED. No strategies/backtests/broker.

1. Preflight with R1 strict validator: 133 exact receipts and unchanged frozen plan.
   If private evidence absent/corrupt, report BLOCKED, do not fetch/reconstruct facts.
2. Record tested implementation SHA, new knowledge cutoff, approved binding/spec/DQ
   hashes. Back up DB; rehearse new additive migrations on private copy first.
   Create new derivation_context without editing old batch frozen identity/time.
3. Publish full new generation from existing raw only; 126 expected outputs and
  402246 source rows accounted for exactly once, resolved+quarantined. If source
   inventory differs, investigate rather than force counts. Retain NULL/native values.
4. Run DQ on explicit complete new generation. Produce private per-finding ledger:
   all old 2512 errors/13244 reviews/7666 quarantine dispositions, overlap counts,
   new findings, remaining blocking cases, evidence refs. Keep UNKNOWN/CONFLICT blocking.
   Report coverage 1226 baseline -> new categories and separate 5,008 interval causes.
5. Rebuild same NEW context independently into a second fresh generation; require
  126/126 logical hash equality and full schema/source lineage. New versus old hash differences
   require approved semantic delta explanation; do not demand old/new equality.
   Old context still reproducible. Do not delete originals for rebuild tests.
6. Report new causal pair coverage by certified venue session vs provisional/unknown,
   fixed tolerances, counts and gaps. No “zero errors” from skipped uncertified tests.
7. Prove 181 raw and old 252 curated unchanged, old identity hash unchanged, attempt sum
   unchanged, new provider fetch count = 0 via denied transport/spy and inventory evidence.
   Run full offline tests, doctor/contracts/specs, decoded secret scans and CI.

Write sanitized r2-g5-offline-validation.md and focused evidence commit; separate
tested code SHA from artifact SHA, current SHA CI URL/status. Private detailed data
stays ignored. If DB absent/evidence insufficient, report the actual limits; do not
infer PASS from synthetic fixtures or public baseline totals.
Report publication status, engineering verification, evidence completeness and
bounded data gate separately. Author result=REVIEW_READY, not self-approval.
STOP. R2-G6 NOT AUTHORIZED. Phase1C.2 CLOSED regardless of DQ outcome.
```

## R2-G6 — 最终交付与独立Review

```text
Execute ONLY R2-G6 final documentation/handoff. Require independent R2-G5 Review
at [SHA] and explicit G6 authorization. If G5 has blocking implementation failures,
correct G5 under its own gate and re-review; do not hide them in a final report.
Evidence/data BLOCKED may be an honest G5 outcome, not permission to claim data PASS.
ZERO market APIs. No new recapture, re-curation experiments or policy/model changes.
Preserve all data/history. Phase1C.2 CLOSED.

Create docs/reviews/YYYY-MM-DD-phase1c1-r2-final-review.md with:
- All R1/R2 gate SHAs, CI URLs, status and independent review evidence.
- Old/new context identity, knowledge cutoff, input/spec/policy/evidence hashes.
- BSE official vs provider semantics, 6/242 cases, pre-BSE/venue exclusions.
- Three historical codes, unknown limit assets, coverage/delist/NULL case dispositions.
- Baseline-to-new flags/source rows/unique anomalies and every remaining blocker.
- Complete publication and same context 126/126 rebuild evidence; old 181 raw/252 curated
  preservation; source conservation; zero API evidence; session/PIT limitations.
- Separate Engineering/Model REVIEW_READY, Evidence completeness, and Bounded
  data admission PASS/PARTIAL/BLOCKED. PASS only if the R2 spec actually permits it.
- Future Phase1C.2 prerequisites, but no Phase1C.2 implementation or execution prompt.

Update only current remediation status docs/AGENTS pointers, leaving historical
reviews untouched. All future instructions must retain Phase1C.2 CLOSED and human
gate approval. Run applicable checks and exact artifact SHA CI, report SHA and URL.
STOP for independent R2 FINAL REVIEW. No automatic Phase1C.2 authorization.
```

## 独立Review prompt（每Gate复用）

```text
Review ONLY Phase1C.1-R2 [GATE] at exact SHA [SHA], against R2 spec, preceding
approvals and approved case/policy/context hashes. Read source/tests/migrations,
sanitized evidence and exact SHA CI. Private raw decisions must be supported by
available source evidence; report what cannot independently be verified.
Do not implement changes, fetch market data or begin Phase1C.2.

Check dataset/capture/event/knowledge scopes, official/provider code separation,
episodes/venue boundaries, no guessed aliases, no old snapshot mutation, PIT labels,
NULL/no imputation, fixed tolerances, coverage/calendar evidence, local/batch audits,
append-only history, complete generation selection, recovery/source conservation,
same context rebuild and zero API proof. Confirm old finding to new disposition
accounting, including newly introduced findings and unresolved review severity.
Test green alone is not evidence of historical identity truth.

Return exact gate PASS /CHANGES_REQUIRED /BLOCKED with actionable findings.
For final G6, report separately Engineering/Model, Evidence completeness, Bounded
data admission. Unresolved required evidence means data BLOCKED, even if code PASS.
No historical PIT/full-history claim. Phase1C.2 remains CLOSED in every verdict.
Do not automatically execute or authorize another gate.
```

## Gate批准记录格式

```text
gate_id:
reviewed_exact_sha:
tested_implementation_sha: (如与文档SHA不同)
ci_url_and_result:
reviewer_and_review_date:
verdict: PASS | CHANGES_REQUIRED | BLOCKED
approved_binding_case_ids_and_hash: (G2及以后)
approved_policy_and_context_hashes: (适用时)
remaining_blockers:
explicit_next_gate_authorization: (由用户提供，不能由Codex自填)
phase1c2_authorization: CLOSED
```

该记录是留痕格式，不是自行批准工具。证据与独立Review可以从当前会话明确指令读取；不要求用户重复审批已批准的同一动作。每个新Gate仍必须获得明确授权。
