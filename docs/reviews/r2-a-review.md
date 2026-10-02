# Phase1C.1 R2-A review package

Author handoff: **R2_A_REVIEW_READY**, conditional on the final delivery commit's
verified CI recorded in the handoff. This is not independent engineering approval,
historical case approval, data PASS or R2 FINAL PASS. **R2-B NOT_AUTHORIZED;
real-data gate BLOCKED; Phase1C.2 CLOSED.**

## Authority and exact code

R1 FINAL independent PASS: `cc458ce2e8229dcc914e9a45ae2ac6186f48c45c`,
[baseline CI36986260440](https://github.com/liuyanfeier/AStockSystem/actions/runs/36986260440),
480 passed. The independent report, v1.1 batch prompt and user authorization are
retained in this repository. Design freeze commit: `1f4d983`.
Tested implementation: `39be745e4aa62a7d07102b8d4e82fbbf4e4f30b4`.
The final artifact commit contains this report and its manifest; its own SHA cannot
be embedded in its contents. The author's final handoff records the exact final
SHA/CI, distinct from tested implementation and approved R1 baseline.

## Existing evidence reconciliation

Only existing181 raw and126 generation1 outputs were inspected. One old generation
has402,246 source rows:394,580 resolved +7,666 quarantine, exactly conserved.
Quarantine:5,008 interval failures (4,515 code-start;493 venue-start),1,374
PRE_BSE_LEGACY and1,284 NO_IDENTIFIER_MAPPING. Recomputed old quality flags:
2,512 ERROR +13,244 REVIEW =15,756 unique finding keys, including1,226 coverage
flags. These counts are not independent anomaly totals:1,285 exact source rows
intersect quarantine and ERROR;1,117 candidate-security/day coverage keys intersect
quarantined daily rows. The latter join is diagnostic, not approved identity.
There are1,286 unique ERROR source rows and9,208 diagnostic episode-or-native/date
keys; source-free coverage findings remain source-free.

The BSE matrix contains16,996 exact dataset/event/capture/ordinal observations,
including earlier stock_st captures. Six pilots switch2025-05-06;242 remaining
pairs switch2025-10-09. No mapping list was downloaded again. Retrospective daily,
basic, factor and limit representations are separately scoped from event-native
stock_st/suspend observations. Missing transition sides stay NOT_OBSERVED;
pre-opening rows do not gain an invented venue.

## Candidate cases and authority

Private proposal v2 has346 review items;251 have model-valid inactive drafts.
EVIDENCE_REQUIRED/CONFLICT/OUT_OF_SCOPE dispositions remain separate. Each pins
exact raw rows, capture time/bytes, dataset/event, candidate episode/binding,
evidence, impact and proposal hash. Old resolved rows additionally have explicit
carry-forward proposals:5,584 security scopes/386,309 rows, plus8,271 old resolved
rows incorporated into the251 case scopes. There is no frozen-resolver fallback
in the new model. Counts overlap and must not be summed as unique anomalies.

| Case | Primary documentary fact | Proposed disposition |
|---|---|---|
| 000022.SZ →001872.SZ | [Issuer implementation notice](https://static.cninfo.com.cn/finalpage/2018-12-26/1205690369.PDF):2018-12-26 switch, continuing shares/listed entity | Bounded scoped candidate; independent approval pending |
| 000043.SZ →001914.SZ | [Issuer implementation notice](https://disc.static.szse.cn/download/disc/disk02/finalpage/2019-12-16/a5a3d55e-cc2e-42e6-91c1-ea98235594fb.PDF):2019-12-16 switch and shareholder continuity | Bounded scoped candidate; independent approval pending |
| 300114.SZ →302132.SZ | [Issuer implementation notice](https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF):2025-02-17 switch and continuing shares | Bounded scoped candidate; independent approval pending |
| 689009.SH /2021-11-12 NULL | [SSE listing announcement](https://www.sse.com.cn/disclosure/announcement/listing/c/c_20201027_5242851.shtml):CDR; raw limit labels STK | Asset conflict; NULL explanation/exemption EVIDENCE_REQUIRED; no fill or automatic exclusion |
| Other unknown limit instruments | [Provider field documentation](https://tushare.pro/document/2?doc_id=183) cannot establish exact A-share class | EVIDENCE_REQUIRED; no prefix/name inference |
| Delist/coverage |4,858 metadata flags and10 boundary dossiers retained | Authoritative termination/last-trade and venue sessions still missing |

BSE authority uses the preserved [official mapping evidence](https://www.bse.cn/service/code_mapping.html),
[pilot announcement](https://www.bse.cn/important_news/200025487.html),
[pilot implementation](https://www.bse.cn/important_news/200025603.html) and
[remaining migration notice](https://www.bse.cn/important_news/200026735.html).
New documentary summaries retain actual retrieval/knowledge times; they do not
backdate knowledge to old captures. The three old codes' omission from current
all-status stock_basic remains unexplained; no new provider fetch was used.

## Engineering and frozen policy

Explicit additive008–010 introduce independent episodes/official codes, exact
provider bindings, immutable context/input membership, append-only generation
history, verified publication/quarantine and finding/output/batch quality audits.
Generic migration and old resolver/curation/DQ remain unchanged. Production
admission requires R1 exact133 inputs/126 parent outputs; fixture contexts require
explicit opt-in and cannot enter production APIs. Physical schema constraints are
compared with a reference memory catalog, not accepted by table names alone.

Publication independently reconstructs each expected output. File/lineage/DB
crashes resume after exact checks; corrupted orphans are retained and append
BLOCKED. Promotion validates the complete membership and every source ordinal in
one transaction. DQ and rebuild require explicit COMPLETE IDs. Same-context
rebuild compares logical/schema/units/semantic binding/source and quarantine;
publication UUID/time is excluded. COMPLETE does not imply research admission.

The frozen policy retains price0.011, causal0.011pp and original independent factor
method/tolerance. Coverage observes before disposition; current active lists,
delist+1, NULL fill, relaxed severity/tolerance and cross-venue SSE certification
are prohibited. Exact approved out-of-scope dispositions may remain quarantined
without invented identity. Findings and old-to-new disposition ledgers preserve
unexplained disappeared findings. Application APIs append; SQL constraints do not
claim to prevent arbitrary direct SQL UPDATE.

Design v1 remains byte-identical. Two appended designs separately pin DQ evidence
and source dispositions; all design/policy/schema/source hashes are in the manifest.
Documentation of approved observations is not proof of a complete historical
universe. The private drafts' observation envelopes need independent episode/
universe/calendar decisions before actual admission. No real generation or new
real DQ was run in A; full-history/PIT claims remain unsupported.

## Verification, preservation and reviewer decisions

Local full-suite and diagnostic results are in the manifest/private logs. Synthetic
regressions cover scopes/knowledge/ambiguity, code reuse, BSE venue/native/official
boundaries, NULL/suspension/coverage/calendars, schema transactions, complete/
partial selection, file/lineage/DB/promotion faults, corrupted orphans, two-process
publication, repeat/resume, exact FK/source conservation, append-only audits,
approved out-of-scope decisions and old/new context rebuild. No new dependencies.

Original schema remains001–007/all19 table contents unchanged.181 raw,252 old
curated/lineage,1,102 protected files, frozen identity and133 completion/audit rows
retain their original proofs. Original DB SHA before/after:
`2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`.
Strict read-only audit: VALID/EXACT,checked133,failure0. Source/table/protected
hashes plus provider/http/socket denial counters support zero new market requests.
Decoded Parquet/current-credential and credential-pattern scans passed. Staging
contains no .env, credentials, DB/WAL, datasets, private reports, .tools or .venv.
Legacy SQL/specs/source/reviews remain intact; contract/dictionary only append.

Private evidence is at `data/private/phase1c1-r2-a/`; `evidence-index.json` lists
artifact hashes, candidate set, carry-forward scopes, context draft, execution logs
and final preservation/scan. No full raw rows, datasets or executable real case
payloads are in Git.

The reviewer must separately approve engineering exact SHA, DQ/design/addenda/
context/publication/evidence hashes and an explicit executable approved_case_set.
Candidate engineering validity is not historical authority. Missing universe,
calendar, limit asset, delist and NULL evidence can remain quarantined while
engineering is reviewed. Do not start B until the user explicitly authorizes it.
