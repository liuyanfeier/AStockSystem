# Phase 1C.1-R1-G0 — Inventory and engineering integrity design

2026-10-02 · **DESIGN_REVIEW_READY** · Documentation only; implementation has not started.

## Scope, provenance and approval boundary

Reviewed baseline and inventory code SHA: `2aba10fc143a8b1975b00b7a2a965cd1465942a7`.
Initial HEAD equalled origin/main and this baseline; the working tree was clean.
Batch: `1d34d71f-c711-4893-9729-0b719bbba6dd`.
Read the full referenced ChatGPT review (conversation `6abbb168-b6a4-83ec-b871-fd5816dcdf21`, review message `304fa8d7-a502-4097-9ef7-8504a4373ecf`), existing source and migrations.

The supplied [R1 specification](../remediation/phase1c1/Phase1C1_R1_Engineering_Integrity_Spec_v1.0.md) and [gated prompts](../remediation/phase1c1/Codex_Phase1C1_R1_Gated_Prompts_v1.0.md) control this remediation. The ZIP SHA256 is `44f05987c30e920985154cc87cf27c44878c5bf9e09390ef1eaa25a43e34644c`; all five supplied documents are retained byte-for-byte under `docs/remediation/phase1c1/`, without replacing earlier specifications. Their status statements describe the supplied plan, not an approval record.

This task replaces the old four-commit implementation sequence with one delivery per Gate. The prior sequence did not wait for independent review after each implementation step; this remediation restores that boundary. G0 permits inventory and design without prior approval. **G1 requires independent G0 DESIGN REVIEW PASS for the exact delivery SHA and explicit next-Gate authorization. R2 is LOCKED until R1 FINAL REVIEW PASS and explicit R2-G0 authorization. Phase 1C.2 is CLOSED.** No approval is asserted here.

No source, tests, dependency lock, configuration, SQL migration, old review, raw, old curated/lineage, receipt, attempt, identity or existing private evidence was edited. New private G0 inventory/probe records and this documentation are the only additions. No capture/resume, probe, curation, DQ execution or real migration was invoked.

## Read-only local inventory

The actual database was opened read-only inside a consistent transaction. Parquet checks read metadata/schema and hashes, not public market rows. Original files and database bytes were hashed before and after inventory. Detailed records remain ignored under `data/private/phase1c1-r1-g0/`; only aggregates appear here.

| Evidence | Locally observed availability / result |
|---|---|
| Frozen request manifest | Present; matches the approved plan; 133 requests |
| Warehouse | Present; DuckDB 1.5.6; schema versions 1–6; no WAL observed |
| Receipts | 133 COMPLETE; 133 distinct request IDs, run IDs and object IDs; attempt sum 133 |
| Preliminary receipt/raw joins | 0 object/run/dataset/parameter inconsistencies |
| Raw | 181 objects: 133 in this batch and 48 earlier; 181 checksum/schema/count matches |
| Sidecars and capture contracts | Raw sidecars present; all 133 slice capture contracts present and inventoried |
| Curated | 252 objects: generation 0 and 1 each 126; 252 checksum/schema/count matches; lineage files present |
| Governance | 142 ingestion runs, 253 curation runs, 252 dataset-date audits, 15,340 quarantine records |
| Identity / venue | 6,159 identifier-history and 5,911 venue-history records; snapshot unchanged |
| Preservation | Existing file inventory and database bytes unchanged |

Frozen capture SHA: `c3161b2651839f2b34e5d46cdf162f3b4ce6d1e0`.
Frozen plan hash: `99975249e0b33fe21b99f295a950be8fd94accf89a2444fb5f535b6ee9cd7451`.
Frozen knowledge time: `2026-10-01T19:24:48.248531+08:00`; stored batch status remains CURATED, which does not establish data acceptance.
Identity snapshot: `83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c`.

The private inventory artifact itself has SHA256 `f5c30de4f0e0ccb7f526914f047fcccfe65e52d3100784744039dbc158848e9c`; one-off inventory and synthetic capability/negative-probe scripts are retained alongside it for local reproduction. They are not product code or committed runtime infrastructure.

Inventory digests (SHA256):

| Subject | Digest |
|---|---|
| Original database bytes | `924bf429b25c4ac2fafc557bdbc67667b39de902b3175a7d7828461207fd4617` |
| Frozen request-manifest file | `885bd8d770ad8ad1d87b43ecd2f662430e19f0246af76dd6ce34b0a0d16098c5` |
| Existing immutable file inventory | `ee1be295431a28248cbfd7ee1d20fd1f384d90f0289bf1374da675ccf3024f55` |
| Governance table inventory | `f1d9cdd099b5b11d5f8617df3fc23bf4aaab1d9fd76e21bd7057af2aa97d8410` |

**These are G0 inventory observations, not R1-G3 exact-receipt acceptance.** No complete new strict validator exists yet. Counts and physical checks alone cannot prove all sidecar, contract, interval or semantic relationships. The real-data gate remains BLOCKED.

## Findings confirmed against the baseline

Temporary synthetic databases/files reproduced five failures: empty `verify_batch` returns True; a nonexistent run returns True; a fake COMPLETE is skipped by resume; `_object_table` accepts a receipt object UUID different from the one registered for its run; failure of claim's second update leaves IN_FLIGHT/attempt=1 while ingestion request_count=0.

These demonstrate validation/transaction defects, not corruption of the inventoried real batch. No double market request has been demonstrated. Existing conditional updates and native DuckDB locking provide some protection, but do not establish the required process-lock protocol or atomic claim guarantee. Finalization also recreates missing metadata and updates terminal timestamps without an exact idempotence check. A contradictory historical COMPLETE must be retained as evidence, never converted into a retryable request.

## Exact proof and caller behavior — proposed G1

Use one shared `validate_slice_receipt` proof implementation and a batch wrapper. Return structured verdict, stable reason codes, identifiers, expected/observed cardinalities and an evidence digest. No broad exception handler may convert failure into success. Keep detailed diagnostics private; public outputs contain reason/count summaries without exception bodies or rows.

Proof requirements:

1. Read the immutable private request manifest and approved plan/catalog; verify frozen hashes, budget, order, ordinal, request ID, dataset, slice, catalog and contract. A full batch has exactly the frozen 133 requests; IDs, runs and objects are distinct. Do not change the existing request-ID digest algorithm.
2. For COMPLETE, require attempt=1, exactly one compatible ingestion run (source `tushare`, dataset, AUDIT mode, SUCCEEDED, request_count=1, raw_object_count=1 and matching row_count). Capture commit/config hash and requested bounds match frozen inputs. Validate terminal/retrieval time consistency without treating the pre-created started_at as an HTTP timestamp.
3. Require exactly one raw manifest for the run and **manifest.object_id == receipt.object_id**, with the same run, dataset and typed params. Recompute file SHA256, schema hash, row count and event bounds; validate the original endpoint's fields and empty-table policy. Do not change identity/DQ tolerances. One valid zero-row object differs from zero objects.
4. Require exact raw path shape under `data/raw/tushare/{dataset}/run_id={run_id}/`; reject absolute/escaping paths, traversal and every symlink component. Apply the same checks to sidecar, capture-contract and frozen-manifest paths. Reject missing or malformed evidence; never recreate it in audit/recovery.
5. Sidecar top-level run/dataset and the complete object set must equal registered manifests, without duplicates or extra objects. Compare every existing object field: UUID, path, checksum, schema, count, retrieval/availability/basis, event bounds and params. `available_at` remains the recorded OBSERVED_CAPTURE time, not the new verification time. Capture-contract must match its exact eight-field object/plan/contract representation. No `any(...)` shortcut.
6. JSON parsing rejects duplicate keys and unknown fields. Validate the existing RequestParams wire types before model coercion: canonical ISO date strings or explicit null, exchange string or null; do not equate strings with numbers/bools, missing keys with null, or permissively coerced dates. Key order alone is immaterial. Compare timestamp instants using explicit timezone-aware parsing while preserving original serialized evidence.
7. Normal admission additionally requires the unique accepted binding below; validate it against freshly checked evidence. Store verification SHA/time separately, never rewrite capture commit, retrieved_at, available_at or knowledge_as_of.

Generic `verify_batch` rejects empty requested runs, unknown runs, zero-manifest runs and any damaged evidence. Preserve legitimate multi-part raw runs; slice proof imposes exactly one object. Batch proof additionally rejects duplicate or omitted requests/runs/ordinals.

| Caller | Required proof and failure propagation |
|---|---|
| resume pending selection | Validate every COMPLETE before returning any pending work; bad COMPLETE blocks the whole operation |
| capture preflight / COMPLETE branch | Shared proof before client construction/fetch or any claim; no repair/reset/retry on rejection |
| local reconciliation | Explicit candidate mode only; exact registered local evidence; no transport or metadata reconstruction |
| finalize_receipt | Candidate proof, transactional re-read and conditional completion, COMPLETE proof, binding insert; all-or-nothing |
| CAPTURED promotion | Entire frozen request set and every exact bound COMPLETE; counts alone insufficient |
| `_object_table` | Consume validated proof/object or invoke shared validation; cannot independently accept a different UUID |
| curate / DQ preflight | Same full-batch proof before publication or audit writes; failure propagates as operation BLOCKED |
| offline audit | Read-only proof, nonzero on failure; no provider client, Settings/token prerequisite, claims or old-state updates |

Proposed `astock data slice audit --batch UUID` reads a consistent snapshot and requires bindings. A deliberately separate `--legacy-preflight` checks old unbound evidence for approved upgrade preparation, returning `LEGACY_PREFLIGHT_EVIDENCE_VALID` and `binding=UNREGISTERED`; it does **not** grant normal admission or final Gate PASS. No automatic legacy fallback. A new immutable private audit artifact may be appended; writing DB audit history requires explicit writer mode and the exclusive lock. Default audit never migrates or writes source DB/files.

Candidate-finalize mode is internal, never an acceptance bypass: IN_FLIGHT, attempt=1, RUNNING ingestion and null receipt object; exactly one fully registered local object with already published sidecar/contract. Active synthetic capture publishes complete metadata before finalization. Re-read under transaction; conditional updates must each affect exactly one row. Then run COMPLETE proof and insert binding before COMMIT. Repeated finalization accepts only the identical already-proven binding and changes no terminal time. Missing metadata, orphan files or competing objects block.

## Additive schema and legacy upgrade design

The next unused migration is **007**; proposed name `007_slice_receipt_integrity.sql`. No file is created in G0. Pinned DuckDB 1.5.6 synthetic probes showed `ALTER TABLE ... ADD FOREIGN KEY` and `ADD UNIQUE` unsupported. CREATE TABLE foreign keys, composite references to existing unique keys, uniqueness rejection and transactional DDL rollback worked. A ledger prototype referenced migration006 request keys and completed a synthetic receipt in one transaction. These are capability probes, not production migration tests.

Proposed new tables (all required fields NOT NULL unless stated):

| Table / columns | Keys and semantics |
|---|---|
| `slice_receipt_completion_binding`: batch_id UUID, ordinal INTEGER, request_id VARCHAR, run_id UUID, object_id UUID | PK(batch_id,ordinal); FK(batch_id,ordinal)→slice_request; FK(batch_id,request_id)→slice_request; UNIQUE run_id + FK→ingestion_run; UNIQUE object_id + FK→raw_object_manifest |
| Binding proof fields: plan_hash, contract_hash, receipt_hash, evidence_hash VARCHAR; validator_version VARCHAR; verification_code_commit VARCHAR; validated_at TIMESTAMPTZ | SHA256 checks; version `R1_EXACT_RECEIPT_V1`; 40-hex verification commit. Evidence digest includes checked manifest, file, sidecar and capture-contract digests; receipt digest covers frozen capture facts, not future curation status |
| `slice_receipt_validation_audit`: audit_id UUID, batch_id UUID, ordinal INTEGER nullable, purpose, verdict, reason_code, validator_version, verification_code_commit, validated_at, evidence_hash nullable, checked_count INTEGER | PK audit_id; FK batch_id→slice_batch; purpose CHECK in LEGACY_PREFLIGHT/UPGRADE/VERIFY/FINALIZE/OPERATION_BLOCK; verdict CHECK in VALID/BLOCKED; checked_count>=0; append-only attempts distinct from accepted completion. Ordinal nullable for batch failures; detailed bad IDs/errors remain private, not FK-constrained to fabricated objects |

FKs guarantee existence and uniqueness only. Independent request/run/object references do **not** guarantee they belong to the same receipt; strict application proof supplies that relationship, actual file truth and typed identity. Append-only behavior is enforced by supported application paths and preservation tests; these constraints alone cannot prohibit arbitrary manual UPDATE/DELETE. Every later admission rechecks exact proof/binding. Do not claim FK solves the whole problem.

No old-table rebuild or edit to migrations001–006. Upgrade is an explicit `apply_receipt_integrity_upgrade` operation, not a silent side effect of opening the real database. One transaction owns 007 DDL, validated legacy bindings, validation history and insertion of schema_version7 **last**. Migration DDL must compose with that owner without nested BEGIN. Pre-existing COMPLETE rows receive bindings only after strict legacy preflight; invalid historical evidence aborts without editing it. Fresh empty databases have no fabricated completion bindings. Repeated upgrade verifies existing schema/bindings rather than silently swallowing conflicts.

G1 uses synthetic/isolated databases only. It implements and tests this operation but cannot upgrade the original warehouse. G3 applies it only after approved-copy verification. Until then unbound real legacy receipts remain unaccepted by normal new operations. This is a deliberate fail-closed transition.

## Database-scoped locking and fault behavior — proposed G2

Use `fcntl.flock` on macOS/Linux keyed by canonical resolved warehouse path. Stable sibling `{db_filename}.lock`: O_CREAT/O_RDWR/O_NOFOLLOW, regular file, never unlink on release. Reject unsafe lock paths; aliases of the same allowed resolved database share one lock. Do not acquire/steal by existence, PID or mtime. The OS releases the lock on descriptor closure, exception or process death.

Acquire exclusive lock **before writer connection, frozen-input preflight and mutation**; hold through local file publication and DB finalization. Default contention returns BUSY/LOCKED immediately; optional wait is monotonic and bounded (maximum 5 seconds). Second writer consumes no attempt and constructs no provider client. DuckDB native-lock failure also fails closed. Inner helpers receive the existing guard/transaction context, avoiding nested lock acquisition. Only explicit synthetic `:memory:` fixtures may bypass filesystem locks.

Cover capture, migration, RawWriter, curation/DQ writes, bootstrap/admission/IdentityHistory.append, and the older probe when targeting this warehouse. Read-only audit takes shared lock before opening DB, then BEGIN for a consistent snapshot. It never upgrades a shared lock midway; explicit audit persistence takes exclusive lock from the start. This protocol covers cooperating application writers; manual external writers remain subject to DuckDB locking and proof revalidation.

Atomic claim: conditional PENDING→IN_FLIGHT/attempt=1 and ingestion request_count=1 in one transaction; validate both update cardinalities; COMMIT before any fetch. On second-write failure all claim state rolls back. A committed claim with uncertain transport history is never retried.

| Crash window | Permitted later action |
|---|---|
| Before committed claim | Still pending; no attempt consumed |
| After claim, network outcome unknown | UNCERTAIN/blocked operation evidence; no resend |
| File exists without DB registration | Orphan diagnostic; no guessed registration or overwrite |
| Manifest registered, sidecar/contract absent | Block; do not reconstruct missing proof |
| Exact object + all metadata, before COMPLETE | Only validated local reconciliation; no fetch |
| Finalization transaction interrupted | Rollback or exact committed binding; validate before idempotent return |
| Existing contradictory COMPLETE | Preserve receipt and terminal facts; append failure evidence; pending work blocked |

G1 establishes conditional transactional finalization; G2 adds process guards and real subprocess/fault tests. Neither Gate runs the existing real capture/resume path.

## Approved-copy deployment and rollback — proposed G3

1. Under approved exclusive lock, close application DB connections. Unexpected WAL, native lock or unknown external writer blocks backup; no guessed checkpoint/unsafe file copy.
2. Byte-copy the closed warehouse to ignored private storage, flush/fsync and verify checksum equality; retain original backup. Record frozen table-row digests plus every old raw, curated, lineage, metadata and private batch file hash. Raw files are shared read-only by the isolated DB copy.
3. On an isolated working copy, strictly preflight all 133 receipts, all 181 raw and 252 curated/lineage objects, frozen request/identity and prior governance. Any mismatch stops with diagnostics; no repairs to achieve expected counts.
4. Apply the additive upgrade/bindings/audit on that copy in one transaction. Re-run strict acceptance and compare every old table's logical digest and old file digest. Preserve schema_version 1–6; only version7/new tables may be added. Successful migration naturally changes whole DB bytes; logical old-row/file preservation is the invariant.
5. Only with explicit G3 authorization, approved G0 design and passing copy checks, repeat original preflight under exclusive lock and deploy the same transaction to original DB. Failure rolls back and verifies old state/no half schema_version. Do not restore or modify raw/curated.
6. If rollback preservation cannot be established, stop CLOSED with the verified backup retained. A restoration step requires the approved rollback procedure: all DB connections closed, stable exclusive lock held, original damaged DB retained privately, verified backup restored atomically and checks repeated. No improvised recovery or silent data loss.

G0 performed no backup deployment, live migration or binding/audit insertion. Review must approve this procedure before G1 implementation; original deployment remains G3-only.

## Required synthetic test plan

All new tests use temporary databases/files, no real credentials; deny provider transport and inspect construction/fetch counters. Keep all existing regressions. Application legacy tests remain necessary even where new FK prevents new invalid inserts.

| Group / cases | Required outcome |
|---|---|
| Fake UUID / zero manifest; foreign-run object; same-run receipt UUID mismatch | BLOCKED; fetch=0; original receipt unchanged |
| Wrong dataset / typed params / frozen contract/catalog/hash | Separate stable failure codes; no claim/fetch |
| Zero/two slice objects; empty runs; missing run; duplicate run | Reject; generic valid multipart remains valid |
| Valid zero-row object; valid exact COMPLETE and binding | Endpoint policy honored; offline audit and skip valid; fetch=0 |
| Missing/modified Parquet; wrong checksum/schema/count/event range | BLOCKED; no publication/repair |
| Missing/wrong/extra/duplicate sidecar objects or capture metadata | Reject exact set/fields; no metadata recreation |
| File/parent/sidecar/contract symlink; traversal/external path | Reject before acceptance |
| JSON key reorder vs duplicate/unknown keys, coercible wrong type, null/missing | Only semantic key reorder accepted |
| Missing/duplicate request, changed ordinal/plan; bad COMPLETE plus pending | Whole preflight rejected; pending fetch=0; never enter provider client |
| Altered or missing binding; repeated finalization with different/same object | Reject mismatch; exact repeat preserves finished_at and one binding |
| Fresh DB, 006 upgrade, repeat, invalid legacy, DDL/mid-binding failure | All keys/rollback correct; old rows/files unchanged; schema_version7 only after success |
| Claim second-write failure / pre-commit crash | PENDING/attempt0/request_count0; fetch=0 |
| Two real subprocess writers: claim and publication | One owner; other BUSY; no duplicate attempt/object/binding |
| Exception/kill release, path aliases, persistent lock file | OS release; no double held lock or inode replacement |
| Post-claim / orphan / incomplete metadata / exact pre-finalize crash | Expected blocked/reconcile path; no resend; fetch=0 or1 only as the synthetic stage warrants |
| Read-only audit with Settings/client/transport denied | Works without token; no claim/migration/source DB writes |

G1 adds exact-proof/migration negatives; G2 adds subprocess and crash tests; G3 validates existing private evidence. Do not mark this plan as already passing.

## Lifecycle policy and registered R2 follow-ups

Preserve old RUNNING/started_at: pre-created governance, not precise HTTP start. Future executor must separate created_at (governance), claimed_at (committed claim), http_attempt_started_at (observed call-entry marker, not proof of remote receipt) and finished_at (terminal outcome). Design PLANNED→RUNNING or create-at-claim before Phase1C.2; no such executor is built here.

Register without implementation: explicit generation/context expected 126-member manifest and complete publication; interrupted-generation recovery; quarantine object FK and source row number without guessing legacy rows; append-only local quality history distinct from batch gate; dataset-scoped historical provider bindings vs venue/identifier intervals; evidence-backed delisted episodes; NULL semantics/coverage policies; independent SSE/SZSE/BSE calendar certification. Existing SSE-basis factor/causal checks are provisional for BSE sessions. Current reconstruction knowledge cannot be silently used as historical availability. See [R2 specification](../remediation/phase1c1/Phase1C1_R2_Historical_Identity_Coverage_Spec_v1.0.md); R2 remains unexecuted.

## Verification, limits and handoff

Local Python 3.12.14 / DuckDB 1.5.6: **269 pytest tests passed in 18.77s**; doctor, contracts v1 (12) / v2 (9), slice plan (133) and curation specs (6) passed offline. Baseline capability/negative probes are separate private diagnostics, not new implementation tests. No dependency was added. Doctor can read the local .env and reported token presence only; no credential value was printed. The designed audit/inventory do not require or read token. CI has an empty token and no .env.

Inventory execution denied Tushare client construction/fetch, httpx requests and socket network access; all spy counters were 0. Full pytest uses its existing network-blocking fixtures. No market-data execution command was called. Original DB/file hashes stayed unchanged. Git push and GitHub CI communication are repository services, not market calls.

Delivery is documentation-only: this design, five byte-identical supplied documents, current scope pointers in AGENTS/README. A focused commit and its exact-SHA CI are required; the delivery SHA/CI URL are supplied in final handoff and are not self-inserted into this file. Prior green CI is not a substitute. Public staged content is audited for credentials and forbidden runtime/data paths; per-object inventories stay ignored.

Open approval decisions: accept the additive ledger + explicit legacy-preflight/upgrade boundary, transaction owner and copy/rollback protocol; approve the strict evidence schema and lock coverage. No missing local inventory was found. Runtime defects remain open for G1/G2 and historical semantics for R2. **R1-G0 DESIGN_REVIEW_READY; R1-G1 NOT AUTHORIZED; R2 LOCKED; real-data gate BLOCKED; Phase1C.2 CLOSED. STOP for independent review of the exact delivery commit.**
