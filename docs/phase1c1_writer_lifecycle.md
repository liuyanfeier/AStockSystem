# Phase 1C.1 writer ownership and lifecycle

2026-10-02 · R1-G2 implementation/policy · G3 isolated-copy batch authorized · R2 locked.

The [human batch revision](reviews/2026-10-02-phase1c1-r1-batch-authorization.md)
authorizes G2 review fixes and isolated-copy G3 acceptance before one final review.
Original 007/binding/audit deployment remains prohibited in this batch.

## Managed handle lifetime and fork addendum

Disk helpers require a `warehouse_connection` handle whose creating guard is still
active in its creating process, thread and context. A path lock alone does not
admit an earlier native connection. `execute`/`executemany` return the scoped handle;
explicit cursors share its lifetime and close before the owner's lock releases.
Root close invalidates all child cursors; cursor close leaves the root valid.
Escaped handles, copied stale contexts, foreign threads and fork children fail
before native execution. Reacquiring the path cannot revive an ended scope.

Only native memory databases without attached disk databases may bypass ownership.
Arbitrary proxies/empty simulated PRAGMA results cannot grant this exception.
Explicit `WarehouseConnectionProxy` fault adapters delegate ownership to their
checked base handle; existing transactional fault tests retain their assertions.
Additional attached disk databases are outside the owner's path and are rejected
by mutation helpers. Native SQL/private internals are trusted application code,
not a security sandbox for hostile SQL or reflection.

A process-wide descriptor registry synchronizes open/register and unregister/close
with fork. Child cleanup closes every inherited lock descriptor, including those
owned/acquiring in another thread/context, without LOCK_UN on the parent's shared
open-file description. The registry is cleanup machinery, not authority to reuse
another thread's guard. A copied ContextVar cannot revive an inactive guard.
An invalid cross-context exit reports `WAREHOUSE_LOCK_CONTEXT` while still closing
the descriptor; token-reset errors cannot skip cleanup and strand ownership.

## One cooperating owner per warehouse

Use `warehouse_connection(resolved_db_path)` before a writer opens DuckDB or reads
its preflight inputs. It owns `fcntl.flock(LOCK_EX)` on the stable sibling
`{database_filename}.lock` through connection close, local file publication and
finalization. The lock file is a persistent regular file; never unlink, replace,
truncate, steal by PID/mtime, or treat existence as ownership. New files use 0600;
symlink/nonregular/multiply linked lock paths are rejected. Resolved directory/file
aliases share the canonical lock. Filesystem hard-link aliases of the database
itself are outside this path-keyed protocol; do not create such aliases.

Default contention returns `WAREHOUSE_BUSY` immediately. Explicit helper waits are
monotonic and limited to 5 seconds. A competitor cannot connect, preflight, construct
a provider, claim, fetch or publish. DuckDB native connection conflicts also fail
closed (`WAREHOUSE_NATIVE_LOCKED_OR_OPEN_FAILED`), covering an uncooperative native
writer. Guard reuse is local to the owning process/thread; fork children close their
inherited guard descriptors without unlocking the parent's open-file description.

The connection owner covers capture, generic/explicit migration, raw and capture
metadata publication, curation, DQ governance writes, identity/bootstrap admission
and the older probe targeting this warehouse. Disk mutation helpers additionally
require an existing exclusive guard; acquiring a lock after an unmanaged connection
was opened is not an accepted usage. Explicit in-memory synthetic/reference databases
have no filesystem guard. Manual SQL/external writers are not an application-level
ownership guarantee: DuckDB native locking and exact proof remain necessary.

Read-only audit takes `LOCK_SH` before its read-only connection and a DuckDB BEGIN
snapshot. Multiple cooperating readers can share; readers and writers exclude each
other. No shared-to-exclusive upgrade exists. Source DB/data remain read-only;
coordination may create the empty stable lock file once. It is ignored runtime
state, not a completion record. Persisting future DB audit history needs an exclusive
owner from the outset.

## Durable claim and exact finalization

Claim owns one transaction: reread/validate unexecuted PENDING; conditionally set
IN_FLIGHT/attempts=1; conditionally set the corresponding RUNNING run's
request_count=1; verify both affected-row counts; COMMIT. Fetch can follow only a
successful return. DuckDB 1.5.6's UPDATE count result is used for the referenced run;
RETURNING on that parent triggers its FK update limitation. No table/FK is rebuilt.
An exception, zero affected count or death before commit leaves both facts unchanged.

A committed claim is a consumed reservation, not proof a provider received HTTP.
Unknown outcome stops; it cannot become retryable PENDING. Finalization rechecks
exact local evidence inside its conditional transaction, commits completion/binding/
audit together, and repeats only for the same freshly proven completion. Old terminal
times are preserved on repeat. No second accepted binding is manufactured.

## Crash boundaries

| Boundary | Later permitted behavior |
|---|---|
| Before claim COMMIT | Both receipt and request counter remain unexecuted; a later valid claim is possible |
| After claim COMMIT, transport uncertain | Block; preserve attempt/count; no resend |
| Published file without raw registration | ORPHAN_LOCAL_EVIDENCE; preserve bytes; no guessed registration/overwrite |
| Registered raw without complete sidecar/contract | Block; do not reconstruct missing metadata |
| Exact registered raw plus complete metadata | Validate and reconcile locally, without fetching that request |
| Extra part/temp/unknown file in a slice run directory | Block as orphan/ambiguous evidence, including otherwise valid COMPLETE/candidate |
| Before finalize COMMIT | Whole transaction rolls back; exact candidate remains recoverable locally |
| After finalize COMMIT | One valid completion/binding/history row; exact repeat changes no terminal facts |

A slice directory has exactly its `part-000.parquet`, `manifest.json` and
`capture-contract.json`; a PENDING run cannot contain local capture evidence.
This slice rule does not reduce generic multipart raw support. Process death releases
OS ownership; it does not grant repair/retry authority. Rejected operation diagnostics
append privately and never rewrite contradictory historical receipts/runs.

## Historical and future timing semantics

Preserve historical `RUNNING` and `started_at`: these were pre-created governance
records, not exact HTTP starts. Current claim changes reservation counters only;
no historical timestamp/status cleanup or schema reinterpretation occurs.

Before any future Phase 1C.2 executor, choose a separately reviewed PLANNED→RUNNING
model or create-at-claim model. Separate created_at (governance), claimed_at (durable
reservation), http_attempt_started_at (observed local call entry) and finished_at
(terminal outcome). A call-entry marker is not remote receipt evidence. Keep provider
retrieved_at/available_at and verification times separate. This policy creates no
new executor, lifecycle migration or real backfill.

## Registered R2 follow-ups — not implemented here

- A generation/context manifest must declare all expected members (currently 126
  market partitions, excluding seven calendars), frozen inputs and publication
  state. Partial generations must not be selected as complete through max(generation).
  Design interrupted-generation recovery and atomic complete-generation admission;
  never guess membership from existing object counts.
- Quarantine must reference the real raw object and curation run, and record the
  known source row ordinal with an explicit indexing convention. Do not guess legacy
  row numbers or silently retrofit missing FK provenance.
- Append local object/dataset/date quality history with code/config/input/time
  provenance, separate from the batch gate. Preserve earlier findings instead of
  overwriting them; separately record any later batch verdict.
- Dataset-scoped historical identifier bindings, delisted episodes, NULL/coverage
  semantics and independent SSE/SZSE/BSE calendar certification remain R2 concerns.
  Serial ownership does not resolve these data semantics.

Locks protect bounded cooperating publication, not an entire multi-object generation
transaction. Existing per-object curation/DQ publication remains subject to the
registered follow-ups. Full-scale readiness, R1 FINAL PASS and the real data gate
are not established by these synthetic tests. G3 requires independent G2 REVIEW PASS
and fresh human authorization. Phase 1C.2 stays closed.
