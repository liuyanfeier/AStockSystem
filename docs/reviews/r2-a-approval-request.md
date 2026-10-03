# R2-A consolidated historical approval request

**Author status: APPROVAL_PACKAGE_READY. Historical approval remains pending.**
This single application covers case decisions, the inactive identity payload,
DQ evidence and Context v3. It does not authorize R2-B or activate any record.
Real-data gate remains BLOCKED; Phase1C.2 remains CLOSED.

## Approved engineering and materials scope

Independent engineering PASS is retained verbatim in
`2026-10-03_Phase1C1_R2_A_Fixes_Independent_Review.md` and
`Phase1C1_R2_A_Engineering_Approval_Manifest.json`.
Approved reviewed SHA: `2f2592968a7f8e2500ee5e0bd3772a15a5c621f5`;
implementation commit: `5108731af43bc0738144b6e835c5b65f5f5fc37f`.
The materials SHA is the Git commit containing this report/index; its actual SHA
and final CI evidence are recorded separately in the private final handoff.
Every pre-existing tracked file at the reviewed SHA is unchanged, including
AGENTS, source, tests, SQL and policy. Only sanitized application documents are
added. The approval manifest's engineering hashes match local files.

## Finite identity application

Three cases propose issuer-documented SZSE listing dates and explicit later
code transitions. These dates are primary-document facts; **the decision to
admit the bounded identity scopes remains the reviewer's judgment**.

| Case | Proposed listing start | Official new code starts | Exact parent-batch rows |
| --- | --- | --- | ---: |
| 000022 → 001872 | 1993-05-05 | 2018-12-26 | 72 |
| 000043 → 001914 | 1994-09-28 | 2019-12-16 | 72 |
| 300114 → 302132 | 2010-08-27 | 2025-02-17 | 48 |

For 000022, issuer basic information and share-class sections establish the
listing date; the code-change notice describes listed-entity continuity and
investor processing. [Issuer information](https://static.cninfo.com.cn/finalpage/2019-11-01/1207055051.PDF),
[code-change notice](https://static.cninfo.com.cn/finalpage/2018-12-26/1205690369.PDF).
For 000043, note III of the issuer's financial statements establishes its
initial ordinary-share listing; the transition announcement states the new
code's effective date. [Issuer financial statements](https://static.cninfo.com.cn/finalpage/2022-08-27/1214420211.PDF),
[transition notice](https://disc.static.szse.cn/download/disc/disk02/finalpage/2019-12-16/a5a3d55e-cc2e-42e6-91c1-ea98235594fb.PDF).
For 300114, the IPO announcement supplies the listing date; subsequent issuer
disclosure identifies the A-share instrument and the new-code notice describes
continuity of the listed issuer. This does not merge the acquired subsidiary's
identity into the listed security. [IPO notice](https://disc.static.szse.cn/disc/disk01/finalpage/2010-08-26/0d5a2794-89fc-4d16-9a69-8b3372d778ad.PDF),
[share-class disclosure](https://static.cninfo.com.cn/finalpage/2011-08-24/59867420.PDF),
[new-code notice](https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF).

The candidate has **3 episodes, 3 codes and 12 PROPOSED bindings**, all
EVENT_NATIVE, covering exactly 192 existing resolved rows across daily,
daily_basic, adj_factor and stk_limit. No quarantined row is automatically
rescued. Binding membership fixes raw UUID, zero-based ordinal and event date;
the requests also retain dataset, capture hash and retrieval time. Pre-switch
observations are excluded because the old-code interval's earliest start is
not independently established. Null episode/code end means an unasserted end,
not certification of indefinite future listing. No observation envelope is
used as an episode boundary, no native identifier is rewritten, and no
provider-wide alias is proposed. Exact candidate source keys and dataset /
episode / event keys have no duplicates. Publication dates retain date-only
precision; author retrieval time is current knowledge, not historical PIT.

## Complete retained and unresolved scope

All **346 old case items, 251 inactive drafts and 5,584 carry-forward security
scopes** remain intact. The application contains individual requests and exact
member hashes, plus original artifact pointers. Every one of **402,246** parent
source rows has a new proposed disposition: 192 finite binding requests and
**402,054 retained-quarantine requests**. The latter includes **394,388** old
resolved rows and all **7,666** old quarantine rows. Old success/resolution facts
are not altered; the new resolver has no implicit fallback. The 5,584 carry
scopes cover 386,309 rows; the remaining case-specific old resolved rows are
handled in the same complete ledger. All **15,756** original findings are
retained with their original keys and explicit pending disposition requests.

Case observations referencing prior Phase1B captures are validated against
the existing raw store and distinguished from the 133 parent inputs. They are
supporting evidence, not newly added Context inputs. The impact companion
records per-case duplicate risks, native observation groups, original draft
pointers and parent/supplementary scope. Unproved listing/termination bounds,
delist semantics, unknown assets and incomplete coverage remain
EVIDENCE_REQUIRED; evidence contradictions remain CONFLICT.

## DQ evidence application

The canonical envelope has exactly four keys:

| Section | Application | Limit |
| --- | --- | --- |
| sessions | 63 SZSE episode/event records referencing retained SSE previous-session observations | All uncertified; SSE cannot certify SZSE or BSE |
| reference_exceptions | Empty | No NULL or factor imputation; no inferred exception |
| bse_transitions | Empty operational subset; 248 separate exact decision requests retained in the companion | BSE episode continuity/bounds are unproved; no dangling episode FK |
| source_dispositions | 1,374 exact pre-BSE source-row requests | PROPOSED_OUT_OF_SCOPE, actual approval reference null |

The BSE companion separates cached official old/new pairs and switch dates,
provider-native observations, episode continuity and session certification.
It preserves the six-stock 2025-05-06 pilot versus remaining-stock 2025-10-09
transition; missing observed sides remain NOT_OBSERVED. Official pair facts do
not establish an entire episode. No new mapping/list was downloaded. The
reviewer must either retain these unresolved companion requests or establish
supported episodes and then finalize matching operational transition evidence;
the empty operational subset is not BSE approval or a transition PASS.

The exchange identifies 689009 as a depositary receipt. That fact alone neither
explains an exact NULL reference-price observation nor authorizes
NOT_APPLICABLE. The existing CDR/provider-STK/NULL conflict remains recorded.
[SSE listing notice](https://www.sse.com.cn/disclosure/announcement/listing/c/c_20201027_5242851.shtml).

Policy is unchanged: price tolerance 0.011, causal tolerance 0.011 percentage
points, independent factor tolerance `0.011 + 100 * 0.011 / pre_close`.
Canonical `evidence_hash()` and file-byte SHA256 are both indexed. Reviewer
adjustments require new final hashes. Approval of an envelope retaining unknown
or NOT_CERTIFIED evidence permits that declared audit basis, not certification.
Proposed dispositions cannot be passed directly to the real audit; final
decisions/statuses/references must be supplied first.

## Context v3 and decisions requested together

The old Context v2 remains unchanged. V3 contains the full current Context and
Approval field sets, exact parent batch/generation, frozen identity hash and
full plan hash, 133 distinct request/raw inputs, 126 market outputs and
402,246 source rows. It pins candidate resolver membership and current
spec/policy/design/addenda 1–3 hashes, including correction_addendum_hash.
`implementation_sha` is the approved reviewed SHA, distinct from the materials
SHA and its implementation commit. `fixture_only=false`,
CURRENT_RECONSTRUCTION and OBSERVED_CAPTURE are explicit.

The resolver payload is inactive. Actual review reference, approved_at,
knowledge_as_of, final case/resolver/evidence/context hashes and binding
decision/availability times remain pending. V3 is **not an executable Context**.
The index distinguishes candidate hashes from null final hashes. The model's
own serialization is used for snapshot hash round-trips, preserving timezone
representation; an earlier preparation-only mismatch is retained privately
as rejected evidence and was corrected without changing engineering code.

Please decide this package as one batch and produce mutually consistent
`case-decisions.json`, `approved-case-set.json`, `approved-dq-evidence.json`,
`approved-context.json` and `approval-manifest.json`, with actual decisions,
references and times. A finite approval is permitted; unresolved scopes stay
isolated and the external real-data gate remains BLOCKED. R2-B still requires
separate user authorization.

## Preparation checks and private delivery

Author checks passed for source references, model intervals/conflicts,
inactive membership, duplicate scope, canonical-hash round-trips, all source
dispositions/findings and Context/input structure. Full read-only preservation
passed: original DB before/after
`2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`,
schema001–007, 19 original tables, 133/133 VALID / EXACT receipts (failure0),
181 raw, 252 old curated/lineage, frozen identity and 1,102 protected files
unchanged. The old 26 indexed artifacts and 17 indexed repair artifacts are
preserved. Credential, decoded-Parquet and credential-pattern scans passed.
Market/provider/transport calls and original writes were zero; no real new
binding, migration, generation, publication or DQ was run.

Source/schema/policy did not change, so local checks were preparation-specific;
the existing CI executes the full suite, locked Python3.12 dependencies and
offline doctor for the final materials SHA. Actual CI result is in the final
handoff, not a fabricated pre-commit SHA in this report.

Ignored private root: `data/private/phase1c1-r2-a-approval/`. Required files are
`case-decision-requests.json`, `case-set-proposal.json`,
`dq-evidence-proposal.json`, `context-proposal-v3.json` and
`approval-package-manifest.json`; additional full disposition, impact,
documentary and validation files are indexed. A private ZIP contains the
application and referenced retained case/mapping evidence for transfer to
the reviewer; it contains no database, full raw capture files or credentials.
See `r2-a-approval-package-index.json` for exact paths, byte hashes, candidate
canonical hashes, counts and preserved dependency indexes. Only this sanitized
report/index, authorization, supplied prompt and independent engineering
approval documents enter Git. **No author claim of historical approval or
R2 FINAL PASS is made.**
