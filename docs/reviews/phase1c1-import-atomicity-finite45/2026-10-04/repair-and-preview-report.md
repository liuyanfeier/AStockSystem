# Import Atomicity and Finite45 Preview — Author Report

2026-10-05. Status: `IMPORT_ATOMICITY_AND_FINITE45_PREVIEW_REVIEW_READY`.
Author engineering self-check and the isolated candidate transformation passed.
Independent review and finite45 production approval remain pending. Limited15's
previous acceptance remains valid; global DQ/calendar BLOCKED, Phase1C.2 CLOSED.

## P1 repair and compatibility

The core importer now rejects observation lists incompatible with persistent SQL
UUID/ordinal/date order before INSERT. It does not sort signed payloads or change
v2 semantics. Complete old-plus-delta resolver validation precedes writing; INSERT,
SQL readback, canonical membership and hash comparison run in one managed
transaction. Only verified readback can COMMIT. Both direct and delta imports use
this protection; exact repeats retain approval/raw validation and ALREADY_VALID.

Runtime repair/preview execution SHA:
`e43b521b7b276661b12684378fdbfbe73e8a949f`.
The final delivery also includes two existing synthetic fixture builders explicitly
ordered before synthetic approval, preserving their facts and business assertions.
Of167 prior accepted pins,4 changed:2 production modules and2 existing test files;
163 remain unchanged. One new test module adds17 cases. SQL001–010, v2 clocks/order/
membership, original contracts/DQ/tolerances and metadata transport/guard are unchanged.
The final implementation manifest and handoff record the exact final SHA and pins;
old approvals are never authority for deploying this repair or new facts.

## Tests and actual-material controls

Six pre-fix regression failures reproduced both direct/delta defects. After repair,
52 targeted tests passed: reversed valid observations cannot reach INSERT; injected
post-INSERT hash mismatch/readback exceptions roll back all four identity rowsets,
including new episodes/codes; close/reopen and subsequent valid import succeed.
UUID integer/ordinal/date ordering matches DuckDB, including UUID sign boundaries.
Four-zone imports/readback/repeats preserve offsets-as-instants, microseconds/nulls
and old metadata. Conflict/partial/approval/raw-ordinal/FK controls remain effective.

The first full run found5 old unsigned-fixture order failures (748 passed); their
creation was corrected before approval hashing, with no signed material change.
The affected existing tests then passed67/67. Final full suite: **753 passed,
1 warning in437.18s** (existing fork deprecation warning). Seven locked offline
commands passed. Production read-only compatibility verified existing192+15,
15 bindings/207 observations, both pinned Contexts and strict133 VALID/EXACT with
0 failures. No production reimport was performed.

## Actual finite45 preview

A new unapproved v6 changes only the nine observation-list orders. Old/new ordered
hashes are retained; all observation sets, identifiers/dates/ordinals/row hashes,
first-observed instants and factual fields are identical. The original v5 and old
failed isolate remain untouched. Fixture approvals have current real timestamps,
explicit CANDIDATE_REHEARSAL_ONLY namespace and no production authority.

A fresh managed copied store imported9 bindings/45 observations (0 episodes/codes),
verified complete merged SQL hash and old metadata, reopened and repeated
ALREADY_VALID. One fixture Context was registered. Actual126 conversions produced
physical Parquet outputs, lineage and402,246 complete row dispositions:

| Check | Actual result |
|---|---:|
| Source denominator |402,246; exact old member hash; added/removed0|
| Resolved / quarantine |252 /401,994|
| Preserved old output rows |207; full value/identity/NULL hashes identical|
| New supported rows |45; exact9-binding membership|
| Excluded candidates |42 endpoint aliases and15 daily mirrors|
| Retained raw NULLs |dv_ratio3, dv_ttm3, pre_close3|
| New COMPLETE generations / DQ audits |0 /0|

Remaining quarantine facts/reasons are identical. The status is
`CANDIDATE_TRANSFORMATION_VERIFIED`;252 is verified converted output rows here,
separately from252 identity observations. No finding closure is claimed without an
actual audit. Production remains207 resolved/402,039 quarantine,63 uncertified
sessions and402,147 findings, including15 factor/30 cross-endpoint gaps.

## Preservation, calendar and handoff

136,599 historical files, the previous review package and every indexed old failed
isolate file retained their bytes. Original warehouse hash stays
`27aabd6143d977decefefb8eb1f1b2b9e66ee29c14045d9df284871bcecf065f`;
original Context47001733… and2 Contexts/4 generations/4 audits remain intact.
Fixed metadata and old failed isolate hashes stay91a2c5d2… andec32a433… respectively.
Provider/document requests, original writes,133 replay and support messages:0.

Calendar remains first-member FAILED/1 consumed attempt/6 unattempted/0 responses
or civil rows. Remote delivery/account permission are UNKNOWN. The old true capture
license remains pinned to fd1d1b5; no reset, resend, new store or re-signed license.
A private one-page future evidence proposal is non-executing.

Decoded credentials, explicit staging exclusions and final ZIP/reference checks
are recorded privately. Code/tests/design/authorization and this aggregate report
are committed; raw/DB/candidate approvals/outputs/ZIP remain ignored. Final handoff
links the exact final-SHA CI, actual logs, implementation manifest, rollback proof,
row-set differences, preservation, calendar proposal and primary review package.
Stop for independent combined Review; no original deployment or Phase1C.2 work.
