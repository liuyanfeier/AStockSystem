# Identity import atomicity and finite45 preview

2026-10-04. Frozen before the authorized P1 implementation; independent review
pending. The retained prompt permits importer repair and candidate-only preview.

## Compatible order without a protocol change

V2 canonical serialization continues to preserve observation order. SQL readback
uses `ORDER BY ALL` on `(raw_object_id, raw_row_number, event_date)`. Validate
incoming bindings against canonical UUID numeric order, integer ordinal and date
before any INSERT. Reject incompatible order explicitly; do not sort signed
payloads or change the resolver, Context, timestamp or schema protocol. Synthetic
DuckDB checks must prove that UUID comparison agrees with this ordering.

## One verified transaction

The core `import_approved_cases` validates exact approval and raw scope, then
constructs the complete old-plus-new resolver before writing. INSERT all new
identity records, read the complete SQL resolver and compare its canonical payload
and v2 digest inside the existing managed transaction. Return the verified digest
only after COMMIT. Readback, comparison or insertion failure rolls back episodes,
codes, bindings and observations together. `import_delta` delegates first import
verification to this protected core; its exact-repeat/raw checks remain unchanged.

## Candidate scope and preserved history

Create a new unapproved finite45 version with explicitly SQL-compatible order.
Record ordered hashes and unchanged observation sets/facts. Use a fresh managed
fixture-only copy of the read-only original, preserving old207 output facts. Run
126 conversions with physical outputs, lineage and complete row dispositions;
verify actual differences, NULLs and unchanged source402246. Do not run or claim
new COMPLETE generations or DQ audits. Proposals retain null reviewer metadata and
false production license; fixture metadata is separately named and timed.

Original warehouse, metadata FAILED store, previous failed isolate, accepted
payloads and frozen designs remain byte-identical. API and original-write budgets
are zero. Calendar BLOCKED, finite45 production approval pending, Phase1C.2 CLOSED.
