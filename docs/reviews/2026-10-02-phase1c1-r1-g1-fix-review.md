# Phase 1C.1-R1-G1 — Independent review corrections

2026-10-02 · **REVIEW_READY** · G2 NOT AUTHORIZED · R2 LOCKED · Phase1C.2 CLOSED.

## Review and scope

The [independent review](2026-10-02-phase1c1-r1-g1-independent-review.md) inspected
`86d3b94fc50f93e52768016b85e83a0c42f70a69` and returned CHANGES_REQUIRED for P1
pending-with-capture-evidence and P2 incomplete schema verification. Both findings
are accepted. This is a focused G1 correction, not an independent approval.
The supplied review is retained byte-for-byte; the previous G0/G1 reports remain
historical records. Its two findings qualify the previous G1 guarantee statements.

## P1: reject contradictory PENDING before execution

The shared batch preflight now checks each PENDING receipt: attempts=0,
object_id/failure_code absent; one pre-created RUNNING ingestion run with no finish
or errors; request_count/raw_object_count/row_count=0; no raw manifest for that run;
no accepted binding referring to that request, ordinal or run. The legacy
pre-created started_at remains valid and is not treated as a consumed attempt.

Any contradiction returns `PENDING_EXECUTION_CONFLICT` before upgrade DDL or
registration, resume queueing, provider construction, claim or fetch. Direct claim
also rechecks this unexecuted condition before writing. Existing contradictory
rows, raw, metadata and bindings are preserved. Capture can append only a safe
private operation-block artifact. No counter/receipt reset is a repair path.
IN_FLIGHT exact local recovery and uncertain/failed capture blocking remain intact.
The claim's existing split writes are unchanged: atomic claim and process locking
still require separately authorized G2 work.

## P2: verify structure, including empty and repeat upgrades

`receipt_schema.py` supplies shared read-only acceptance for normal admission,
completion registration and explicit/repeat upgrade. It verifies the exact 007
migration ID and persistent main-table identities, rejecting temporary shadows,
views, duplicate names in other schemas/databases and alternate current schemas.
It compares ordered columns, engine types, nullability/defaults, PK/UNIQUE/FK/CHECK
constraints and referenced parent catalog/schema/table identity.

The reference is built once in an isolated memory database from this checkout's
versioned 001–007 SQL. The pinned DuckDB engine produces both catalog structures;
generated constraint names/OIDs/declaration ordering are excluded, composite key
ordering is preserved, and CHECK expressions use parser-normalized catalog values.
No SQL source-text comparison or source-warehouse write is involved. Whitespace
and named-constraint variations have a positive normalization regression.

An incompatible structure returns `BINDING_SCHEMA_REQUIRED`; incompatible upgrade
name counts retain `UPGRADE_SCHEMA_CONFLICT`. No automatic schema repair occurs.
Within the explicit transaction, the structure is checked immediately after DDL
and before version 7 publication. A repeat checks the published schema even with
zero batches. Existing all-or-nothing rollback coverage remains in place.

## Changed files

- `src/astock/data/receipt_integrity.py`: shared PENDING proof and batch admission.
- `src/astock/data/receipt_schema.py`: normalized catalog schema acceptance.
- `src/astock/data/receipt_migration.py`: repeat, draft and registration checks.
- `src/astock/data/slice_plan.py`: unexecuted proof before direct claim.
- `tests/test_receipt_review_fixes.py`: review fault reproductions and rollback.
- `docs/data_contract.md`, `README.md`: corrected guarantees and current review gate.
- This addendum and the supplied independent review under `docs/reviews/`.

No dependency, migration001–007, config/catalog, identity mapping or earlier review
was changed. No G2 concurrency infrastructure was implemented.

## Validation

29 new regressions
cover legacy006 upgrade rejection, independent run/counter/raw/binding conflicts,
zero provider/claim/fetch calls, unchanged old rows/files, wrong migration ID,
same-name dummy tables, required column/type/nullability and PK/UNIQUE/FK/CHECK
loss, shadow tables, all 133 completed/bound requests with an invalid audit table,
normalized valid repeat and rejected deployment DDL with full rollback.

Full local suite: **382 passed in 202.85s** (Python 3.12.14; locked DuckDB 1.5.6).
All tests use the existing autouse socket/network denial.

Offline doctor (token configured NO), contracts v1/v2, probe plan, identity specs,
slice plan and slice specs pass. Locked offline dependency synchronization passes.
CI for the containing commit is checked after push; its exact SHA, run URL and
final outcome are recorded in the user handoff and ignored private handoff artifact.
The old commit's green CI is not evidence for this correction.

## Preservation and staging audit

The original DB remains byte-identical to G0:
`924bf429b25c4ac2fafc557bdbc67667b39de902b3175a7d7828461207fd4617`.
All 1,102 protected file sizes/hashes match, with zero differences. The original
inventory artifact hash remains
`f5c30de4f0e0ccb7f526914f047fcccfe65e52d3100784744039dbc158848e9c`.
This preserves original 006, 133 COMPLETE/133 consumed attempts, 181 raw, 252 previous
curated objects and frozen identity. It does not grant G3 strict acceptance.

Pre-staging audit scans only the nine explicit changed files for the configured
token and credential patterns. It excludes .env/database/raw/curated/warehouse/
private reports/.tools/.venv; checks immutable SQL/catalog/config/review artifacts
and the protected inventory; then stages exact paths and checks that snapshot again.
No real market request, capture/resume, curation/DQ or warehouse migration occurs.

## Next gate

Stop for an independent review of the new exact SHA. G2 needs REVIEW PASS and new
explicit authorization; real 007 deployment and 133 strict acceptance remain G3.
R1 FINAL remains NOT_READY; R2 LOCKED; real data gate BLOCKED; Phase1C.2 CLOSED.
There are no new scope questions; reviewer approval is the outstanding gate.
