# R2 design v1 addendum 4: resolver time integrity v2

2026-10-03. Frozen before implementing the independently confirmed P1 at
63a166b89f44850dd9fa2efa8ab06c0e49a8bfd5. This author design is review pending;
historical designs, v1 approvals, receipts and failed rehearsal remain immutable.

## Resolver serialization protocol

`R2_RESOLVER_UTC_INSTANT_V2` canonicalizes only these aware datetime fields:
episode `published_at`, `retrieved_at`, `available_at`; official code
`available_at`; binding `first_observed_at`, `decision_at`, `available_at`.
Convert with `astimezone(UTC)`, encode ISO8601 with exactly six fractional digits
and `Z`, reject naive values, preserve null. Do not reinterpret local clocks,
truncate precision or convert dates. Native values, IDs, intervals, source
ordinals, evidence/approval references, versions/status and observation order
retain their semantics. Members remain sorted by immutable ID.

One shared canonical member/payload implementation supplies resolver digests,
persisted snapshot JSON and pinned/live member equality. Stored snapshot checksum,
canonical payload/membership, model digest and every pinned live member must agree;
missing/tampered records fail closed. Equivalent offsets alone are ignored.
Unrelated/superseding later members cannot change an old Context's frozen set.

## Explicit approval and Context version boundary

Approval and Context each require `resolver_protocol` fixed to the v2 constant
and `time_integrity_addendum_hash` pinning this file. No defaults accept v1.
Their agreement and the file hash are checked at schema admission and Context
validation. These fields live in existing JSON payloads; SQL008–010 stays unchanged.
Context hash changes with these pins, resolver digest and new reviewed SHA.
Old v1 Approval/Context bytes remain historical evidence, cannot execute through
v2 admission, and are not migrated or relabeled automatically. R1 frozen identity,
receipt serial/digest, raw serialization, legacy conversion/logical hashes and
DQ policy are outside this protocol.

## Verification and reapproval

Use managed synthetic persistent SQL stores for 008–010/import/register/close/
reopen/select/rebuild across Asia/Shanghai, UTC, America/New_York and Asia/Kathmandu.
Mixed offsets, microseconds and null publication must survive; one microsecond
and material/member/snapshot changes must fail. Retain F1–F3 regressions.
Actual approved payload/readback comparisons are strictly read-only, separate
from synthetic approvals/publication. No real v2 Context is registered here.

Reviewer must issue matching new implementation/protocol/design/resolver/Context
pins. Case and DQ facts remain limited to the prior approved scope. Existing import
checks also require shared review references and availability at/after approval;
the reviewer must explicitly version those metadata if reapproval needs it,
preserving first observation and historical evidence instants. Candidate hashes
are diagnostics, never production approval. No author approval time/ref is filled.
Original warehouse deployment remains blocked until unified engineering review
and matched reviewer approval; Phase1C.2 CLOSED, market requests zero.
