# R2 reconstruction operation contract

R2-A authors engineering and proposals only. R2-B requires explicit user
authorization after independent approval of exact source SHA, design/addendum,
DQ policy, DQ evidence and executable case-set digests. Approval records are
trusted inputs from that operational review; strings/hashes are not signatures.
Do not generate an `Approval` from an author's candidate package.

## Explicit schema and cases

Use a reviewed `warehouse_connection` with exclusive ownership, verified backup
and R1 strict preflight; `apply_reconstruction_schema` transactionally adds008–010.
No generic migration/on-open upgrade exists. Physical columns/constraints and
versions are checked against the checkout's reference memory catalog. Repeat
returns ALREADY_VALID. Import only the exact approved payload with
`import_approved_cases`; it verifies every raw row/native/dataset/event and actual
knowledge time before inserting, then validates the combined resolver snapshot.
Episodes, official codes and bindings remain independent. Synthetic approval
records in tests authorize temporary test roots only.

## Context and publication

Create `Context` with immutable133 raw inputs/126 expected outputs, parent batch
and generation, frozen identity/plan, resolver/spec/policy/design/addenda/evidence
hashes, approved implementation SHA and real review references. Registration
revalidates R1 receipts and the parent126 membership. Contexts marked fixture-only
require explicit `allow_fixture=True` at every operation and cannot be admitted
through production entry points. An operator must separately verify checkout SHA
and approval provenance before production use.

Select explicit context/generation IDs. `start_generation`, `publish_output` and
`complete_generation` append history and never use a latest-generation query.
Files and lineage publish with no-clobber semantics. A crash before registration
may leave orphans: resume independently reconstructs and compares exact bytes and
lineage before admission. Corruption is retained and appends BLOCKED; interrupted
transactions roll back registrations and preserve files for verification. A
promotion transaction rechecks full output membership, inputs, schema, hashes,
lineage and each source ordinal. Recovery never overwrites/deletes original files.
A COMPLETE manifest proves publication, not data PASS. Verification errors after
COMPLETE retain that historical publication event and refuse DQ/rebuild admission.

## Offline DQ and rebuild

`audit_complete_generation` requires explicit COMPLETE membership and approved
canonical DQ evidence. Session records, exceptions and BSE cases cannot change
without a changed reviewed context. Findings, per-output quality and batch audits
append atomically; reruns preserve old observations and reference superseded audits.
Missing evidence remains blocking even when another output has local PASS.
`disposition_ledger` retains every old finding, including findings no longer emitted;
disappearance alone never resolves a finding. A trusted reviewer must approve
historical-universe completeness separately from observation-bounded draft episodes.

`compare_generations` requires two independently verified COMPLETE generations of
the same context. It compares logical schema/units/semantic binding/raw source and
quarantine; generation ID/publication time are excluded. Old conversion, frozen
resolver, specifications and legacy mismatch checks remain intact. New code does
not accept full-history coverage or historical-PIT claims.

Explicit approved source dispositions in DQ evidence keep an out-of-scope raw row
quarantined while retaining the exact case/review/evidence decision in its finding.
This does not create an identity or silently discard the source.
