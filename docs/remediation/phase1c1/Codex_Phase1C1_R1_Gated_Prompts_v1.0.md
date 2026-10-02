# Codex prompts — Phase 1C.1-R1（逐Gate执行）

v1.0 · 2026-10-02。先把同包 `Phase1C1_R1_Engineering_Integrity_Spec_v1.0.md` 放入AStockSystem可读文档目录；以下每次只复制一个prompt。规格中的建议名称可在G0固定，硬不变量不可缩减。R1-G0没有批准记录即可进行只读设计；所有后续Gate必须填入真实前Gate批准与SHA，空白/占位符不是授权。

不是“一次完成R1”的总prompt。每Gate后结束当前任务，等待用户在下一条指令明确授权。修订同Gate不能启动下一Gate。不要自动创建新chat或发送消息给其他chat。

## R1-G0 — 只读库存、具体设计与Gate恢复

```text
Implement ONLY Phase1C.1-R1 Gate R1-G0: read-only inventory and detailed design.
Read Phase1C1_R1_Engineering_Integrity_Spec_v1.0.md, AGENTS.md, the full Phase1C.1
review and existing planner/capture/raw/curate/DQ code. The new remediation scope
replaces the old four-commit implementation sequence for this task only.

Historical reviewed SHA: 2aba10fc143a8b1975b00b7a2a965cd1465942a7.
Real batch: 1d34d71f-c711-4893-9729-0b719bbba6dd.
Read actual HEAD and working-tree state; report subsequent changes. Do not reset,
overwrite user changes, or assume unreviewed changes are approved.

Hard limits:
- ZERO new market/provider API requests, including metadata/mappings/calendars.
- Do not rerun 133 requests, old probes, or real capture/resume commands.
- Do not change raw, old curated/lineage, receipts, attempts, identity snapshot,
  old reviews or migrations 001-006. No R2 implementation. Phase1C.2 CLOSED.
- No strategies/signals/backtests/portfolio/broker/orders.

Tasks:
1. Locate local private batch evidence without exposing tokens/raw rows. Read-only
   inventory: request manifest, DB/schema, 133 receipts, raw contracts/sidecars,
  181 old raw objects, 252 old curated objects. Mark unavailable evidence honestly.
2. Explain each validator caller and failure propagation, including resume,
   finalize, COMPLETE branch, CAPTURED promotion, _object_table, curate, DQ.
3. Specify exact receipt invariant and a token-free read-only audit entry point.
   Keep capture code_commit frozen; store verification SHA separately.
4. Determine pinned DuckDB migration capabilities. Propose new 007/next migration:
   FK where practical, strict application validator always; if using binding
   ledger, specify its FK/unique keys, validation-before-insert and legacy handling.
   Do not edit/rebuild live tables during G0.
5. Specify DB-scoped OS process lock, atomic claim/finalize and crash behavior.
6. Specify private-copy migration/rollback and immutable inventory comparisons.
7. Write exact negative/concurrency/migration test plan and future lifecycle
   policy. Register partial publication/quarantine/audit/calendar follow-ups.
8. Produce docs/reviews/YYYY-MM-DD-phase1c1-r1-g0-design.md (sanitized) and a
   focused documentation commit if repository commit/push workflow is available.
   Run applicable offline documentation/plan checks and exact SHA CI when pushed.

No real migration, binding insertion, code implementation or market-data execution.
Report HEAD, artifact SHA, inventory availability, proposed schema, deviations,
test/CI status and ZERO market calls with evidence, not an unsupported assertion.
Result: R1-G0 DESIGN_REVIEW_READY. STOP FOR INDEPENDENT REVIEW.
R1-G1 NOT AUTHORIZED. R2 LOCKED. Phase1C.2 CLOSED.
```

## R1-G1 — Exact receipt invariant与迁移

```text
Execute ONLY R1-G1 under Phase1C1_R1_Engineering_Integrity_Spec_v1.0.md.
Required human authorization: R1-G0 DESIGN REVIEW PASS for exact SHA [fill SHA]
and explicit instruction to execute R1-G1. Verify the actual approval record and
current HEAD. If absent, do not implement; report the missing gate.

ZERO new market APIs. Do not rerun capture/resume or 133 requests. Preserve raw,
old curated/lineage, old identity, receipts/attempts/timestamps, migrations 001-006,
old reviews. No R2. Phase1C.2 CLOSED. No trading/research features.

Implement the approved G0 design:
1. Shared strict slice receipt validator proving exactly one manifest/run AND
   exact object_id, run_id, dataset, typed request params, frozen contract/plan,
   file checksum/schema/count, safe paths, sidecar and capture-contract identity.
2. verify_batch must fail on empty requested run set or any zero-object run.
   Preserve generic valid multi-part behavior; enforce exactly-one in slice
   validator. A valid zero-row Parquet is not a zero-object run.
3. Integrate validation at resume skip, COMPLETE branch, local reconciliation,
   finalize, CAPTURED promotion, curate, DQ and _object_table. Reject before HTTP.
   A bad COMPLETE must not allow pending requests to proceed.
4. Add approved 007/next migration with practical FK/binding integrity; never
   rewrite 006 or silently repair historical receipts. Report DB-vs-application
   guarantees. Fresh, 006 upgrade, repeated migration, invalid legacy and rollback
   tests must prove preservation. Use synthetic/private isolated copies only.
5. Add token-free offline audit entry point that never constructs provider client,
   claims requests, relabels old batch or recreates missing manifests/sidecars.
6. Structure failures with stable reason codes. Operation blocked evidence must
   preserve original contradictory receipt rather than reset/retry it.

Required tests: fake UUID/no manifest; foreign run object; wrong dataset/params;
receipt object mismatch; wrong contract; 0/2 slice objects; empty run IDs; missing run;
valid empty table; valid exact completion; bad file/schema/count/sidecar/metadata;
unsafe paths; JSON order equivalent vs typed difference; bad COMPLETE+pending.
Application legacy tests remain necessary even if new DB FK rejects bad inserts.
All provider fetch spies must show ZERO for rejected paths.

Run full offline pytest, doctor, contracts v1/v2, slice plan/specs and secret scan
regressions. Do not require real credentials or data in CI. Do not migrate the
original real DB during this gate; G3 performs approved deployment/validation.
Write sanitized docs/reviews/YYYY-MM-DD-phase1c1-r1-g1-review.md, focused commit,
push only through the established workflow, and verify CI for EXACT current SHA.
No prior SHA CI substitution. If inaccessible, report CI_UNVERIFIED.

Report code/schema diff, invariants, test totals, CI URL/status, unresolved issues,
no market call evidence and current SHA. Mark REVIEW_READY, never self-PASS.
STOP. R1-G2 NOT AUTHORIZED. R2 LOCKED. Phase1C.2 CLOSED.
```

## R1-G2 — 进程锁、原子claim与生命周期政策

```text
Execute ONLY R1-G2. Read R1 spec and approved G0/G1 design.
Require independent R1-G1 Review PASS for [exact SHA] with exact SHA CI PASS and
explicit human authorization for R1-G2; verify current HEAD. Otherwise stop.
Market API budget ZERO, including metadata/calendars. No real capture/resume, 133
replay, identity/coverage edits, raw/old curated rewrite, history/migration 001-006 edit.
No R2. Phase1C.2 CLOSED. No strategy/backtest/broker work.

Implement:
1. OS advisory exclusive lock keyed by resolved warehouse DB path. Stable inode,
   no exists/PID/mtime-based acquisition or lockfile unlink races. Acquire before
   writer connection, preflight and mutation; release on exception/exit/OS death.
   Cover migration, capture, curation, DQ writes, identity/bootstrap writes targeting
   this DB. Define consistent-snapshot read-only audit behavior.
2. Second writer fails BUSY/LOCKED or waits bounded time, consumes no attempt and
   makes no fetch. DB native-lock failure also fails closed.
3. Atomic transaction for PENDING->IN_FLIGHT, attempt=1 and ingestion request_count.
   Validate update count. No fetch before successful commit. Finalization is
   conditional/idempotent only for exact same completion.
4. Fault handling: committed uncertain claim never retried; manifest-after-crash
   reconciles only exact local evidence; orphan/duplicate/incomplete local evidence
   blocks. Test these using synthetic clients/data, not existing live batch.
5. Document historical RUNNING/started_at as pre-created governance. Preserve
   historical timestamps/status. Design future PLANNED->RUNNING or create-at-claim
   with separate timing semantics, without building Phase1C.2 executor.
6. Record R2 requirements for partial generations, quarantine FK/row number and
   append-only local/batch audit; full-scale readiness stays unproved.

Run meaningful real subprocess lock tests with temporary synthetic DB: concurrent
claim, publisher exclusion, exception/kill release, path aliases, no double binding.
Test claim transaction rollback and finalize crash windows with fetch count=0/1
as expected; never connect to provider. Retain G1 negatives and full offline suite,
doctor, contracts v1/v2, plan/specs, credential scan. Current SHA CI must pass.

Write focused code/policy commit and sanitized r1-g2-review artifact. Report exact
SHA, CI URL, concurrency/fault evidence, history preservation and zero market calls.
Mark REVIEW_READY and STOP. R1-G3 NOT AUTHORIZED. R2 LOCKED. Phase1C.2 CLOSED.
```

## R1-G3 — 真实证据离线验收与R1最终包

```text
Execute ONLY R1-G3: final offline validation of EXISTING Phase1C.1 evidence.
Require independent R1-G2 Review PASS [exact SHA], exact SHA CI PASS and explicit
authorization for G3. Read R1 spec and preceding approvals. No R2 execution.

Market API budget ZERO. Do NOT invoke real capture/resume or replan/recreate batch.
No edits to frozen request/capture provenance, raw, old curated, old identity/history.
No re-fetch on missing evidence. Phase1C.2 CLOSED.
Batch=1d34d71f-c711-4893-9729-0b719bbba6dd.
Expected original identity hash=
83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c.

1. Record actual implementation SHA and frozen evidence inventory. Back up real
   DB safely, verify backup, and use isolated copy for strict preflight/migration.
   Apply reviewed additive migration/binding/audit to original DB only if all
   preflight checks pass and authorized G0 scheme allows it. Never repair receipt
   fields, attempts, old timestamps, or raw/sidecars to force acceptance.
2. Offline audit 133/133 COMPLETE exact receipts against frozen manifest; 133
   distinct request/run/object; attempt sum 133; batch raw objects 133. Validate 181 old
   raw checksums/schema/count/metadata. Prove old 252 curated and lineage/bindings
   unchanged and old identity snapshot unchanged. Counts mismatching: investigate,
   report BLOCKED; do not mutate to desired numbers.
3. Verify offline audit has no client construction/transport access. Use denied
   provider transport or spy, in addition to pre/post attempt/request/raw inventory.
   Counter stability alone is not proof of zero HTTP.
4. Run full offline suite/doctor/contracts/plan/specs, private decoded credential
   scan and exact SHA CI. Store per receipt evidence privately under ignored data.
5. Produce sanitized docs/reviews/YYYY-MM-DD-phase1c1-r1-g3-review.md: baseline SHA,
   tested code SHA, schema/migration, result counts, immutable inventory digest,
   test/CI, zero API evidence, limits, and retained data BLOCKED/Phase1C.2 CLOSED.
   If reporting doc is a later SHA, distinguish tested SHA from final artifact SHA.
   Push focused evidence commit through existing workflow and verify its CI.

If local real DB/raw absent or any check fails: result REAL_VALIDATION_BLOCKED.
Do not fabricate 133/133 from public report; do not claim R1 FINAL PASS.
If all checks pass: result R1 FINAL_REVIEW_READY. Author cannot self-approve.
Return exact SHA(s), CI URL/status, evidence location, remaining future requirements.
STOP for independent R1 FINAL REVIEW. R2 NOT AUTHORIZED until that review PASS
and a new explicit R2-G0 authorization. Phase1C.2 stays CLOSED regardless.
```

## 独立Review prompt（每Gate复用）

```text
Review ONLY AStockSystem Phase1C.1-R1 [GATE] at exact SHA [SHA], against R1 spec,
approved preceding gate and its focused diff. Read code, migration, tests and actual
CI for this SHA. Do not implement remediation or invoke provider/live commands.
Zero new market calls. Do not begin R2 or Phase1C.2.

Check exact receipt joins and all callers; generic-vs-slice cardinality; empty
verification; schema migration/rollback; history immutability; claim/lock/fault
behavior; actual transport evidence. For G3 validate private 133/181/252 evidence
when accessible. If inaccessible, distinguish code review from unverifiable real
claims; no R1 FINAL PASS without the required real evidence.
Return PASS / CHANGES_REQUIRED / BLOCKED for this exact gate/SHA, with actionable
findings and test/CI limitations. Separate historical fact from public report and
locally recomputed fact. Explicitly state next gate has NOT been executed.
For G3 only, issue R1 FINAL REVIEW PASS if all mandatory evidence meets spec.
Do not auto-execute or auto-authorize R2. Phase1C.2 remains CLOSED.
```

批准记录最少字段：Gate、exact SHA、CI URL/result、reviewer与日期、verdict、blocking findings、获准下一Gate。缺某项应明确缺口；R1-G3真实验证缺口是硬阻断。任何追加代码修正使原exact SHA批准失效，须重新Review新SHA。
