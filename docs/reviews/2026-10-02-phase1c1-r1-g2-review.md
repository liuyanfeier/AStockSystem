# Phase 1C.1-R1-G2 — Writer ownership and atomic claim

2026-10-02 · REVIEW_READY · G3 NOT AUTHORIZED · R2 LOCKED · Phase1C.2 CLOSED.

## Approval and implementation boundary

Clean start HEAD/origin/main: `1a769b7acd0ed5c0bd41b2cc232571584be9babe`.
The user responded to that exact-SHA G1 handoff with “OK 没问题了，继续开始 G2 吧”.
This records human-relayed G1 REVIEW PASS and explicit G2 execution authorization.
The final reviewer's name/full text was not supplied; no author-generated independent
PASS is asserted. The earlier CHANGES_REQUIRED document and G1 addendum remain intact.
G1 exact-SHA [CI run 36967316797](https://github.com/liuyanfeier/AStockSystem/actions/runs/36967316797)
passed 382 tests in 490.05s, doctor/token-NO/contracts/plans/specs all passed.

Implementation follows the approved [G0 design](2026-10-02-phase1c1-r1-g0-design.md)
and [G2 prompt](../remediation/phase1c1/Codex_Phase1C1_R1_Gated_Prompts_v1.0.md).
No real market API, capture/resume, migration, curation or DQ command was run.
All disk execution/fault tests target temporary synthetic roots. No SQL migration,
configuration/catalog, dependency, historical review or identity mapping changed.

## Changes

| Area | Concrete result |
|---|---|
| `warehouse_lock.py` | Resolved-path OS advisory exclusive/shared guards; stable regular `.lock` inode; lock-before-connect; bounded contention; safe native failure; owner reuse and fork handling |
| `raw_writer.py`, `receipt_migration.py`, `identity.py` | Disk helpers require an already-held exclusive owner before preflight, writes or publication; explicit memory fixtures remain supported |
| `slice_plan.py` | Conditional receipt/ingestion reservation in one transaction with both affected-row checks; COMMIT before fetch |
| `slice_capture.py`, `receipt_integrity.py` | Owner through capture/finalize/failure publication; shared snapshot audit; orphan/extra slice directory evidence blocks |
| `slice_curate.py`, `slice_dq.py`, `bootstrap.py`, `probe.py` | Every warehouse writer connects/preflights under the same guard; the older probe constructs its client and publishes its report while owned |
| Two new test modules plus spawned worker helper | Real process contention, exception/kill/fork/native-lock behavior, committed-claim visibility and crash recovery/rollback |
| Seven prior regression modules | Only disk fixture/native connection usage adapted to the guarded production API; prior assertions retained |
| AGENTS/README/contract and [lifecycle policy](../phase1c1_writer_lifecycle.md) | Current authorization/gate, ownership coverage, preserved timing semantics and registered R2 follow-ups |

### Lock guarantees and limits

`fcntl.flock` on macOS/Linux owns the canonical database's persistent sibling lock.
Default contention is `WAREHOUSE_BUSY`; explicit helper waits are monotonic and
bounded to 5s. No unlink/PID/mtime lock acquisition or takeover exists. New lock files
use 0600; symlink/nonregular/multiply linked lock paths are rejected. Directory/file
symlink aliases share the resolved path. Helpers reuse the owner in the same process
and thread. A fork child closes inherited descriptors without unlocking the parent,
then acquires independently. Exception, connection close, exit and OS death release
ownership; the lock inode stays present.

Ownership precedes writer connection and preflight, spans local file publication,
completion transaction and connection close, and covers migration, raw, capture,
curation/DQ, identity/bootstrap and the earlier probe. Unmanaged disk helpers reject
late acquisition. Read-only audit holds shared ownership and BEGIN snapshot;
shared-to-exclusive upgrade is forbidden. An initially absent coordination lock may
be created, but source DB/data are not written. Native DuckDB connection errors fail
closed with a safe code, even for a synthetic uncooperative native writer.

This protects cooperating local application processes. Manual SQL, database hard-link
aliases, network filesystem behavior and full-scale concurrency are not certified.
Serial publication does not make a 126-object generation transaction atomic; R2
partial-generation/quarantine/append-only audit requirements are documented only.

### Claim and fault behavior

Claim rechecks PENDING/unexecuted facts inside BEGIN, conditionally sets IN_FLIGHT/
attempt=1, conditionally updates the exact run's request_count=1, checks both counts and
commits. Referenced-parent UPDATE uses DuckDB's count result; its RETURNING form
triggers the pinned 1.5.6 FK update limitation. No FK/table workaround or rebuild occurs.
The capture client observes both committed facts from a second connection at synthetic
fetch entry. A claim error/zero count/death before commit leaves both old facts intact.

Committed uncertain claims remain consumed and blocked, including a crash before a
synthetic fetch begins. No reset/refetch is introduced. Finalization retains the G1
conditional transaction/idempotence proof. Process death before commit leaves an
exact IN_FLIGHT candidate, no binding/history; after commit leaves one valid binding/
history. Repeating the same freshly proven completion preserves terminal timestamps.

Slice run directories reject unregistered raw, extra part/temp/unknown files and
incomplete metadata. An exact registered raw plus complete sidecar/contract can be
reconciled locally. Orphans stay as evidence; missing metadata is never recreated.
Generic multipart raw behavior remains valid. Operation-block diagnostics append
privately under the same owner and preserve contradictory history.

## Verification and process evidence

**60 new process/claim/fault regressions passed in 29.94s.**
**Full local suite: 442 passed in 229.86s (Python 3.12.14; locked DuckDB 1.5.6).**

Required process cases include a real capture owner paused at fetch; claim/capture/
publisher/curation competitors BUSY with construction/fetch/claim/preflight counters=0;
a separate owner paused inside actual immutable raw publication; all eight writer
entrypoints blocked before mutation; aliases, bounded wait, compatible shared readers,
audit-before-connect, unsafe paths, native conflict, exception release while still
alive, kill release and fork noninheritance. Lock inode remains unchanged.

Fault cases include claim's first/second zero update, second-write error and precommit
failure; process death between updates/before/after commit; raw-file-before-registration,
registered-raw-before-metadata, exact-metadata-before-finalization; and deaths after
finalize run/receipt/binding/audit writes plus before/after COMMIT. The expected fetch
count is 0 on rejected/recovery paths and 1 for the single successful synthetic owner.

Existing credential/compressed-secret regressions and denied-network fixtures remain
in the full suite. Spawned workers independently deny socket network calls, use
synthetic clients/settings, and install construction/fetch/preflight spies for rejected
paths. No existing real evidence is fed to a capture client. Locked offline sync,
no-token doctor, contracts v1/v2, probe plan, identity specs, slice plan/specs are checked.
New exact-SHA CI is verified after push; final URL/SHA/log counts are recorded in the
user handoff and ignored private handoff. Prior G1 CI is not substituted.

## Original history and staging audit

Original DB SHA256 remains
`924bf429b25c4ac2fafc557bdbc67667b39de902b3175a7d7828461207fd4617`.
All 1,102 G0 protected file sizes/hashes remain identical; inventory artifact SHA256
remains `f5c30de4f0e0ccb7f526914f047fcccfe65e52d3100784744039dbc158848e9c`.
No lock file was created for the real warehouse. Original 006, 133 COMPLETE/133 attempts,
181 raw, 252 previous curated objects, frozen identity and timestamps are preserved by
byte/logical baseline preservation, not claimed to have passed G3 strict acceptance.

Before staging, audit the explicit code/test/doc paths for the configured credential
and credential patterns; exclude real .env, DB/WAL/lock, raw/curated/warehouse/private
reports, .tools and .venv. Check immutable SQL 001–007/config/old reviews and the private
inventory. Stage exact paths only and check the staged snapshot again. Final Git
status, exact commit SHA and current-SHA CI are supplied in the handoff.

## Unresolved items and next gate

No new scope question is outstanding. Data semantics, partial-generation readiness,
quarantine FK/row provenance and append-only quality history remain registered R2
work. Historical RUNNING/started_at remain pre-created governance; future created_at,
claimed_at, http_attempt_started_at and terminal timing require separate reviewed
lifecycle design before any Phase1C.2 executor. No lifecycle schema cleanup is performed.

Delivery is G2 REVIEW_READY, not self-PASS. Stop for independent review of the new SHA.
G3 requires that PASS and fresh human authorization; original 007 deployment/133 strict
acceptance remain G3. R1 FINAL NOT_READY, R2 LOCKED, real data gate BLOCKED,
Phase1C.2 CLOSED. No further Gate runs automatically.
