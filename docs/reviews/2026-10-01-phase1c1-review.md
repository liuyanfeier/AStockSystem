# Phase 1C.1 Bounded Historical Slice Review

## PHASE 1C.1 STATUS

**Implementation and bounded recovery/rebuild verified; real data gate BLOCKED.**
The existing historical data gate is not upgraded. Curated outputs are review
artifacts, not accepted research inputs. No Phase 1C.2 or full backfill began.

Base: `c54b85a4cd88abbb9dd6d99553c0dff62cf5977f`.
Four planned implementation commits:

1. `83519c9016a9a54eeebe8c626398d32fe32ca919` — fixed planner and durable receipts.
2. `6a986451bba00fe5f2387ebc2ba4325ded7b818e` — capture and immutable recovery.
3. `fd638572b598e6734e06da7bf630ddc4b8198c23` — identity, typed curation and quarantine.
4. `c3161b2651839f2b34e5d46cdf162f3b4ce6d1e0` — DQ and causal/rebuild audits.

Actual capture, curation and rebuild code commit: `c3161b2651839f2b34e5d46cdf162f3b4ce6d1e0`.
A subsequent minimal fix, `96e8b7612d9ef647857af5f54f8faea080788dfe`, extends
credential scanning to decoded typed Parquet with dates/timestamps and compressed
text. Its regression test passes; it changes no identity, outputs or thresholds.
This review document is a subsequent documentation commit; obtain its exact SHA
from Git. No dependencies were added. Earlier contracts/specs and migrations
001–005, accepted identity tables and historical review files remain unchanged.

## SLICE COVERAGE

The user approved 21 sessions, including 2025-04-30. The frozen plan adds seven
small SSE-calendar checks: **133 logical requests / 133 HTTP attempts**, one per
request, including six market datasets per session. No stock_basic/bse_mapping
recapture or full 47-request probe occurred.

| Slice | Sessions | Captures | Resolved daily rows | Quarantined daily rows | Unexplained coverage flags |
| --- | --- | ---: | ---: | ---: | ---: |
| baseline_2013 | 2013-01-04, 2013-01-07, 2013-01-08 | 19/19 | 7,186 | 9 | 57 |
| chinext_boundary | 2020-08-21, 2020-08-24, 2020-08-25 | 19/19 | 11,806 | 257 | 45 |
| bse_opening | 2021-11-12, 2021-11-15, 2021-11-16 | 19/19 | 13,594 | 436 | 152 |
| bse_pilot_switch | 2025-04-30, 2025-05-06, 2025-05-07 | 19/19 | 15,404 | 730 | 730 |
| bse_remaining_switch | 2025-09-30, 2025-10-09, 2025-10-10 | 19/19 | 16,023 | 241 | 242 |
| after_hours_fields | 2026-07-03, 2026-07-06, 2026-07-07 | 19/19 | 16,550 | 0 | 0 |
| latest_sample | 2026-09-28, 2026-09-29, 2026-09-30 | 19/19 | 16,677 | 0 | 0 |

Resolved samples include SSE/SZSE/BSE rows, 3,864 risk-warning rows, 619 suspension
rows, and 10 selected provider-delisting-date boundary cases. The current
stock_basic market metadata identifies 8,732 selected bar rows as STAR members;
this is CURRENT_RECONSTRUCTION, not proof of historical board membership.
After-hours fields are null on 2026-07-03, then have non-null volume/amount in
4,478 rows on July 6 and 5,194 on July 7. Coverage is observed, not assumed universal.

## RAW OBJECTS / CURATED OBJECTS

133 new immutable raw objects, complete receipts, contract/version metadata,
request parameters, retrieval timestamps, row/schema/content hashes and sidecars.
All 48 earlier raw objects remain intact: **181 raw objects total**; all hashes pass.

126 typed output objects per generation: daily_bar, daily_basic_snapshot,
adjustment_factor_observed, suspension_daily, risk_warning_daily, plus
price_limit_daily for checks. Each generation processes **402,246 source rows**:
**394,580 resolved / 7,666 quarantined**. Two generations retain 252 objects.
Schemas, units, null policies, observed availability, native identifiers and
zero-based source row lineage survive empty partitions and reconstruction.
Curation v2 corrects asset_type/exchange to string while preserving v1, matching
[Tushare stk_limit documentation](https://tushare.pro/document/2?doc_id=183).

## IDENTITY RESULTS / QUARANTINE

Frozen identity snapshot remains:
`83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c`.
Exact source identifiers are joined at the frozen knowledge time against
half-open identifier and venue intervals. No identity or interval was rewritten.

| Reason | Rows per generation |
| --- | ---: |
| NO_IDENTIFIER_MAPPING | 1,284 |
| OUTSIDE_IDENTIFIER_INTERVAL | 5,008 |
| PRE_BSE_LEGACY | 1,374 |

Historical captures contain provider-native new BSE codes before their official
exchange-code intervals. Local diagnostic evidence accounts for 4,515 interval
failures as before-code-start cases and 493 as before admitted venue start. These
are diagnostic candidates only, not resolved IDs or invented provider aliases.
The three daily identifiers absent from the registry are `000022.SZ`, `000043.SZ`
and `300114.SZ` (15 rows); no guessed successor mapping was created.
The remaining unknown limit-table identifiers stay quarantined, without assuming
asset class from digits. Existing T600018.SH/bootstrap quarantine remains intact.

Official exchange evidence is preserved from Phase 1C.0:
[complete mapping](https://www.bse.cn/service/code_mapping.html),
[six pilots](https://www.bse.cn/important_news/200025487.html),
[2025-05-06 effective switch](https://www.bse.cn/important_news/200025603.html),
[2025-10-09 remaining switch](https://www.bse.cn/important_news/200026735.html),
[BSE opening](https://www.bse.cn/company/introduce.html).
It establishes exchange transitions, not provider retrospective identifier semantics.
Synthetic continuity passes; real continuity cannot be demonstrated for any of the
6 pilot or 242 remaining pairs because the historical native-code intervals fail.
These cases remain REVIEW/unresolved; no mappings are inferred from code suffixes.

## DQ RESULTS

**2,512 error flags**, comprising:

- 1,285 unresolved traded identity rows (1,270 interval failures + 15 absent IDs).
- 1,226 unexplained daily coverage flags.
- 1 stk_limit pre_close comparison flag: `689009.SH`, 2021-11-12, limit pre_close null.

Flags may overlap; this is not a count of unique securities or anomalies. No
numeric non-null price pair exceeds tolerance. Duplicate/schema/lineage findings,
daily vs daily_basic close discrepancies and causal/factor discrepancies are zero.
Raw row caps were not reached. All 126 current dataset_date_audit entries are
BLOCKED. Conversion status CURATED does not mean data acceptance.

13,244 REVIEW flags include quarantine, missing/provider-only limit rows,
non-observed BSE transition pairs, one suspension/resumption same-date case,
listing boundaries and retained delisting metadata. Provider delist_date remains
unclassified; effective_to stays null. Sparse samples do not establish its global
last-trading-date convention. Errors and review items are not relaxed into PASS.

## RESUME TEST / REBUILD HASH TEST

The real batch intentionally interrupted after 8 complete captures, then resumed
125 unsent requests. Exactly 133 distinct request runs and raw objects; no replay.
Synthetic tests also cover crash reconciliation and refusal to replay uncertain
receipts. Failed/corrupt receipts block recovery.

All 126 generation-zero Parquet outputs were removed after verified recoverable
backup. Offline rebuild read immutable raw, published generation one and matched
**126/126 logical hashes**. Historical generation-zero files were subsequently
restored byte-for-byte to preserve prior manifests. No raw object was deleted,
rewritten or fetched. Every regenerated row's typed schema and source lineage
were verified. Logical hash collection SHA-256:
`a88e3998781fc7ec05c8a38e4267f128ee95cc5d834113a08d1b5a3355933f8a`.

## CAUSAL ADJUSTMENT TEST

64,678 adjacent-session pairs: **0 causal errors / 0 factor errors / 0 missing
factor pairs**. Maximum differences: 0.005048 percentage points causal and
0.018831 percentage points factor return. The fixed tolerances are 0.011 price
units, 0.011 causal percentage points, and factor percentage tolerance
`0.011 + 100 * 0.011 / pre_close` for quoted-reference-price rounding.
26,740 sparse gap resets prevent chaining across distant slices.

The forward scale uses prior close/current pre_close only; observed factors are
an independent audit. Synthetic future ex-right/factor changes leave earlier
price prefixes unchanged. No latest-factor qfq anchoring or strategy exists.

## TESTS / CI / SECRET AND STAGING AUDIT

Final local suite: **269 passed**, Python 3.12.14, locked dependencies. Doctor and
corrected typed specs pass. Tests reject network access and use synthetic data.
The actual runtime implementation's GitHub CI passed **268 tests**, including all
offline plan/spec steps, on [run 36856448365](https://github.com/liuyanfeier/AStockSystem/actions/runs/36856448365).
Final documentation/fix HEAD CI is verified after push and reported in the handoff.
CI uses Python 3.12, locked dependencies, token-free synthetic pytest and doctor;
no market API calls or credentials are required.

Decoded Parquet/file/schema credential scan: PASS across old/new raw, both curated
generations and private evidence/backups. Explicit-path staging scan: PASS.
Real .env, tokens, DuckDB/database files, raw/curated/warehouse data, private reports,
.tools and .venv remain excluded; .gitignore, .env.example and .python-version
remain tracked. Public evidence contains aggregates and a few anomaly codes only,
with no full raw rows or stock lists.

## LIMITATIONS / PHASE 1C.2 RECOMMENDATION

**Do not begin Phase 1C.2.** Request review of bounded Phase 1C.1 remediation first:
separate provider-native retrospective identifiers from authoritative exchange-code
intervals, investigate the three unregistered historical identifiers and remaining
coverage gaps, review the null reference price and delist/listing boundaries.
Current identity/valuation reconstruction and observed capture availability are
not strict historical PIT. The SSE calendar basis does not independently certify
BSE-specific sessions. No new requests, inferred mapping, broad data admission,
strategies, signals, backtests, portfolios, brokers or orders are authorized by
this report. Stop here for reviewer direction.

Private evidence: ignored `data/private/phase1c1/1d34d71f-c711-4893-9729-0b719bbba6dd/`
(request manifest, capture contracts, curation summaries, DQ reports, quarantine
inspection/interval diagnostics, additional-cases-v2, rebuild receipt, final audit).
