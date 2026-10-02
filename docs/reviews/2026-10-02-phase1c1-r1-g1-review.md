# Phase 1C.1-R1-G1 — Exact receipt integrity

2026-10-02 · **REVIEW_READY** · R1-G2 NOT AUTHORIZED · R2 LOCKED · Phase1C.2 CLOSED.

## Authorization and scope

Start HEAD/origin/main: `a69cba7bcd722de461eee695469b99e7ea21fe43`; clean working tree.
The user relayed G0 REVIEW PASS and authorized continuation with “REVIEW 没问题，继续吧”,
referring to this immediately preceding exact-SHA handoff. G0 CI succeeded at
[run 36959757828](https://github.com/liuyanfeier/AStockSystem/actions/runs/36959757828).
The independent reviewer's name/full review text was not supplied; this records
human-relayed approval, not an author-generated approval. No blocking findings were
reported. Authorized next Gate was G1 only.

Implementation follows the [approved G0 design](2026-10-02-phase1c1-r1-g0-design.md),
[R1 specification](../remediation/phase1c1/Phase1C1_R1_Engineering_Integrity_Spec_v1.0.md)
and [G1 prompt](../remediation/phase1c1/Codex_Phase1C1_R1_Gated_Prompts_v1.0.md).
No market APIs, real capture/resume, real curation/DQ, real upgrade or receipt
backfill was executed. All new schema/behavior testing uses isolated synthetic
storage. No dependencies, identity mappings, DQ thresholds or calendars changed.

## Changes and guarantees

| Files | Result |
|---|---|
| `raw_validation.py`, `raw_writer.py` | Generic verification rejects empty/missing/zero-object/duplicate runs; validates every registered part and the exact sidecar set; preserves valid multipart behavior |
| `receipt_integrity.py`, `slice_errors.py` | Shared structured exact proof, frozen plan/batch/run provenance, safe reasons, binding verification and read-only batch audit |
| `receipt_migration.py`, `sql/007_slice_receipt_integrity.sql` | Explicit transaction-owned additive ledger/history upgrade; no edits to 001–006 or on-open legacy backfill |
| `slice_plan.py`, `slice_capture.py` | Proof before resume/client/skip/reconciliation/promotion; conditional transactional finalization; invalid historical facts preserved |
| `slice_curate.py`, `slice_dq.py` | Shared full-batch proof before publication or governance writes; `_object_table` consumes exact proof |
| `cli/main.py` | `astock data slice audit --batch UUID [--legacy-preflight]`, no Settings/token/client/claim/migration prerequisites |
| Three new test modules; two revised slice test modules | Meaningful negative, migration, audit and finalization regressions; old fake-COMPLETE acceptance replaced with rejection |
| AGENTS/README, contract/dictionary/curation addenda | Current Gate, deployment limits, schema semantics and audit usage |

A COMPLETE now requires one exact raw object for its run and receipt UUID, matching
frozen request ID/ordinal/dataset/typed params/contract, compatible successful run
and one consumed attempt. Physical hash/schema/count/event bounds, endpoint policy,
exact sidecar fields/object set and capture-contract identity must all agree.
Candidate recovery requires IN_FLIGHT plus a compatible RUNNING run and already
published complete local metadata; registered raw alone cannot be promoted.

JSON key order is irrelevant for semantic comparison; duplicate/unknown keys,
coercible wrong types and null-versus-missing differences are rejected. Timestamp
instants are compared explicitly and proof digests normalize DB timestamps to UTC;
changing a connection timezone does not change identity. Raw and metadata paths
reject traversal, external locations and every symlink component.

All COMPLETE proofs are checked before any pending work/client creation. Finalize
re-reads within its transaction, checks both conditional update counts, proves the
new COMPLETE and inserts its binding/audit atomically. Repeating the identical
accepted completion preserves finished_at and the sole binding; different inputs
are rejected. Missing sidecars/contracts are never recreated during recovery.
Active synthetic capture publishes metadata and scans for secrets before finalizing.

Bad historical COMPLETE or uncertain resume blocks the operation without rewriting
receipt/run/batch facts. New safe operation-block artifacts are append-only in
ignored private storage. Original006 reason enums remain unchanged; novel active
failure details are private, with compatible legacy LINEAGE categorization.

## Schema guarantees and explicit legacy handling

007 adds `slice_receipt_completion_binding` and `slice_receipt_validation_audit`.
Composite request references, parent run/object FKs and unique accepted bindings
supply existence/uniqueness guarantees. Application validation supplies coherent
request/run/object relationships and actual file truth. A synthetic test proves
independent valid FKs alone can still represent an incoherent request reference;
shared proof rejects it. Append-only policy is enforced by application paths,
not a claim that arbitrary manual SQL updates are impossible.

The generic migration helper remains 001–006. The explicit upgrade validates old
COMPLETE evidence before DDL, then creates schema, registers exact bindings and
history, rechecks them and inserts schema_version7 last, all in one transaction.
A repeat verifies rather than repairing; incompatible partial schema blocks.
Normal admission requires both new tables, the exact 007 version record and a freshly
matching binding. The upgrade's internal pre-publication checks do not grant normal
admission before schema publication. Fresh batch initialization can explicitly
install empty 007 before creating a batch; existing-batch capture never upgrades it.

**The original real warehouse still has 006 and no new bindings.** This Gate provides
upgrade code/tests, not real deployment. R1-G3 must use approved backup/copy preflight
before any original schema/binding/audit insertion.

`audit` opens the existing warehouse read-only inside a consistent transaction;
missing evidence never creates a DB. Default requires bindings. Explicit
`--legacy-preflight` can report `LEGACY_PREFLIGHT_EVIDENCE_VALID` with
`binding=UNREGISTERED`, which grants neither normal admission nor review PASS.
The command prints sanitized aggregate reasons/counts and never relabels the batch,
repairs evidence or persists source DB records. Verification SHA/time are separate
from frozen capture commit/availability/knowledge time; dirty implementation is
rejected for truthful verification-SHA provenance.

## Validation and preservation

Final local suite: **353 passed in 100.94s** (Python 3.12.14, locked DuckDB 1.5.6).
Baseline 269 plus 84 new cases; earlier suites/probes are not substituted for this
final run. Doctor, contracts v1 (12) / v2 (9), slice plan (133), probe plan, curation
v1/v2 specifications passed offline. Existing compressed/decoded secret-scan
regressions passed. No numerical coverage target is asserted.

Covered cases include fake UUID/no manifest, foreign-run objects, receipt UUID
mismatch, dataset/params/contract/run/time/count mismatch, zero/two objects, generic
multipart, valid empty object, damaged/missing files/schema/count/event bounds,
sidecar/capture metadata corruption and extra/duplicate members, directory/file/
metadata symlinks, unsafe paths, typed JSON/duplicate keys, missing/duplicate/changed
frozen requests, missing/altered/unpublished bindings, and bad COMPLETE plus pending.
Rejected capture paths assert no constructor/fetch and no attempt changes.
A promotion test rejects corrupt proof even when counts are 133/133/133.

Fresh 006→007, populated upgrade, repeat, invalid legacy, schema conflict and injected
DDL/registration/history/version failures passed. The second-DDL fault occurs after
the first table is actually created within the transaction; rollback removes it.
Every old table/file remains unchanged across upgrade or failure except the approved
new schema_version row on successful upgrade. Finalization faults at each write
roll back both receipt/run changes and binding/history. Repeated completion is
idempotent. CLI tests deny Settings/client/fetch/claim/migrate/upgrade and verify
source DB bytes/files unchanged for normal and legacy audit.

Separately, hash comparison to private G0 inventory confirms the actual original
DB and all 1,102 inventoried old raw/curated/lineage/private batch files unchanged.
Original DB SHA256 remains
`924bf429b25c4ac2fafc557bdbc67667b39de902b3175a7d7828461207fd4617`;
identity inventory is preserved by unchanged DB bytes. All 001–006, configuration/
catalogs and historical reviews were compared byte-for-byte with approved HEAD.
This is preservation evidence, **not G3 strict real 133/181/252 acceptance**.

Market/provider calls this Gate: **0**. Test fixtures deny socket access; permitted
transport tests use httpx MockTransport and synthetic clients. Successful offline
audit and rejected-path tests also deny/count provider construction/fetch and
credential/claim/migration paths. Only offline plan/specs/doctor/tests ran on this
checkout. No real audit/capture/resume/curation/DQ CLI was invoked. GitHub push/CI
communication is separate from market transport. Doctor prints token presence
only; no secret value enters logs or this artifact.

## Review handoff and remaining work

Pre-staging audit uses explicit approved paths, checks the actual local secret
without printing it, and excludes .env, raw/curated/warehouse, private reports,
.tools/.venv and runtime files. The focused delivery SHA and its exact-SHA CI URL/
result are supplied in final handoff; they cannot be self-inserted into this same
commit. Prior G0 CI is authorization evidence, not current implementation CI.

No G0 design invariant was reduced. Pinned DuckDB's UPDATE RETURNING on an FK
parent failed in synthetic validation; conditional UPDATE uses its affected-row
Count result instead, still requiring exactly one row and preserving atomicity.
No parent-table rebuild or weakened FK was introduced.

Remaining mandatory work: G2 OS DB lock/process tests and atomic claim (the old
split claim is intentionally still open); G3 original evidence acceptance and
approved deployment; independent R1 final review before R2. Historical identity/
coverage, partial generations, quarantine row FKs, append-only DQ/calendar policy
remain R2 work. No full-scale readiness or real-data PASS is claimed.

**R1-G1 REVIEW_READY. Stop for independent exact-SHA review. R1-G2 NOT AUTHORIZED;
R2 LOCKED; Phase1C.1 real-data gate BLOCKED; Phase1C.2 CLOSED.**
