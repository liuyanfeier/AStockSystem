# Codex Task --- Phase 1C.1 Bounded Historical Slice Implementation v1.0

Implement Phase 1C.1 only.

Do not start full 2013-present backfill.

Do not implement strategies, signals, backtests, portfolio, broker, or
orders.

## Commit sequence

### Commit 1

Implement:

-   bounded slice configuration
-   planner
-   request manifest
-   run lifecycle
-   resume logic

### Commit 2

Implement:

-   real Tushare capture
-   immutable raw persistence
-   lineage
-   failure artifacts

Use only approved slices.

### Commit 3

Implement:

Raw → validation → identity resolution → curated parquet.

Requirements:

-   use security_identifier_history
-   quarantine unresolved identifiers
-   preserve lineage
-   explicit units

### Commit 4

Implement DQ:

-   schema checks
-   duplicate checks
-   cross-table checks
-   BSE transition checks
-   suspension checks
-   causal adjustment audit
-   rebuild hash verification

## Tests

Add tests for:

-   interruption and resume
-   no duplicate raw objects
-   deterministic rebuild
-   BSE old/new continuity
-   unresolved identifier quarantine
-   empty typed schema
-   lineage reconstruction

## Stop if:

-   identity ambiguity appears
-   provider mapping conflicts appear
-   lineage breaks
-   row cap occurs
-   schema requires guessing

## Final report

Return:

PHASE 1C.1 STATUS

SLICE COVERAGE

RAW OBJECTS

CURATED OBJECTS

IDENTITY RESULTS

QUARANTINE

DQ RESULTS

RESUME TEST

REBUILD HASH TEST

CAUSAL ADJUSTMENT TEST

LIMITATIONS

PHASE 1C.2 RECOMMENDATION

Then stop.
