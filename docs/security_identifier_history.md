# Security Identifier History — Design Note

Phase 1A proposal only. No mapping table or historical mappings are created.

A provider code is a source identifier, not a permanent internal security identity.
Names change and may be reused. Allocate stable `security_id` independently; retain
source-scoped identifier versions instead of joining historical facts by current name/code.

| Proposed field | Meaning |
|---|---|
| security_id | Stable internal identity, independent of vendor representation |
| source | Identifier authority/provider |
| identifier_type | Explicit type, e.g. provider code or exchange symbol |
| identifier | Exact source value; preserve formatting |
| exchange | Exchange scope; do not infer it from today's code alone |
| valid_from | Inclusive effective date supported by source evidence |
| valid_to | Exclusive effective end; null means no known end |

Add `published_at`, evidence-supported `available_at`, exact `retrieved_at` and
source-document/object references before implementing the table. Corrections append
knowledge versions; never rewrite old knowledge. Effective intervals alone cannot
support point-in-time identity resolution. Audit overlapping mappings, code reuse,
unmapped facts and source conflicts; quarantine ambiguity rather than guessing.

BSE historical code changes need a dedicated authoritative-source audit before full
backfill. Neither provider suffix patterns nor today's listings prove historical
mappings. Phase 1A supplies no conversion formula, guessed pairs or inferred dates.
Future review must also resolve exchange-calendar coverage and treatment of taxonomy
versions before cross-dataset joins are considered complete.
