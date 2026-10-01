# Security Identifier History

Phase 1B.1 finalizes minimum offline identity governance in migration
`004_security_identifier_history.sql` and `astock.data.identity`. No real mappings
or security IDs are seeded. An official code pair evidences an identifier
transition; allocating an internal ID requires separate security review.

| Field | Meaning |
|---|---|
| security_id | Independently allocated stable security identity; code reuse does not imply equality |
| source | Explicit identifier authority/provider |
| identifier_type | Namespace, e.g. `provider_code` or `exchange_symbol` |
| identifier | Exact native value; no stripping, prefix removal or guessed conversion |
| exchange | Explicit exchange scope |
| valid_from | Inclusive exchange-local effective date supported by evidence |
| valid_to | Exclusive effective end; null means no known end |
| published_at | Aware publication timestamp; null when exact time is unknown |
| available_at | Aware knowledge time; currently OBSERVED_CAPTURE only |
| retrieved_at | Exact aware system observation time |
| evidence_source | Required document URL/object reference; verify provenance before admission |

Dates use `[valid_from, valid_to)`; timestamps persist as UTC `TIMESTAMPTZ`.
Unknown effective dates stay quarantined outside the eligible mapping table.
Date-only publication evidence retains its precision/date in the referenced local
report: leave `published_at` null, never invent midnight publication.
`available_at >= retrieved_at` and, when known, `available_at >= published_at`.
Official switch dates do not establish historical knowledge eligibility. Public
knowledge reconstruction requires a reviewed extension with evidence basis and
precision; this audit cannot make historical backtests eligible.

## Versions, ambiguity and resolution

Logical lineage: `(source, identifier_type, identifier, exchange, valid_from)`.
Append corrections at the same immutable effective-start anchor and a later
`available_at`; the primary key adds that knowledge timestamp. Select the latest
known version **before** testing effective dates. The resolver takes `event_date`
and timezone-aware `as_of`, matches namespaces exactly, and returns an ID or
`None`; it never falls back to current names/codes or suffix heuristics.

`IdentityHistory` checks every knowledge boundary. Overlapping effective intervals
within an exact identifier scope, including redundant overlaps, fail closed.
Code reuse may resolve to different IDs in disjoint intervals. Same-time duplicate
versions fail; input order never selects a winner. `IdentityHistory.append`
validates stored histories and inserts transactionally; failure rolls back.
Mapping admission currently assumes a single writer owning the connection; concurrent
mapping admission requires a reviewed serialization mechanism before use.
DuckDB CHECKs enforce row constraints only: direct SQL bypasses cross-row audits
and must not be used for mapping admission. General retractions or effective-start
anchor changes require further design, not silent edits. Evidence presence alone
does not authenticate its content. No foreign key to a name/code-based master
snapshot implies security equivalence; stable IDs need independently reviewed allocation.

## Raw versus normalized validation

`is_native_identifier` requires nonblank text and preserves exact spelling.
`is_normalized_ashare_identifier` separately requires six digits and SH/SZ/BJ.
Raw captures retain native identifiers even when normalization needs review.
Probe audits expose `invalid_source_identifier_count` separately from
`non_normalized_identifier_count`/`identity_status`. The legacy
`invalid_identity_count` remains a normalization count for compatibility.
Source DQ may pass while identity is REVIEW_REQUIRED; the aggregate probe gate
still remains PARTIAL. Previous captures/reports are not rewritten.

BSE pairs and switch dates require the official table/notices, distinguishing
six-stock pilot from remaining-stock transition. Preserve all-status universes;
current delisted names/codes alone cannot resolve historical joins. See the bounded
[Phase 1B.1 review](reviews/2026-10-01-phase1b1-identity-review.md).
