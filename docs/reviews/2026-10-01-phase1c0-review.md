# Phase 1C.0 Identity Bootstrap Review

## Scope and commits

Status: **PASS for Phase 1C.0 only**; Phase 1C.1 requires reviewer approval.
This does not upgrade the overall historical market-data gate from PARTIAL.
Base: `904066a9683c98f83b621767222bf167773a865a`.
Implementation and actual runtime code commit:
`2b36145ea0c783cd11fe738c318aa6b2b6e9d670`.
This summary is a subsequent documentation commit; obtain its exact SHA from Git.

Phase 1B/1B.1 reports, contract v1 and migrations 001–004 remain byte-identical.
The existing all-status stock_basic capture (15 objects, 5,919 rows) was reused.
No replacement stock_basic snapshot or full 47-request probe was requested.

## Contract and curation governance

Catalog v2 contains stock_basic, bse_mapping, trade_cal, daily, daily_basic,
adj_factor, stk_limit, stock_st and suspend_d. Callers explicitly select v1/v2.
Six typed curation specs declare null policies, explicit provider units, identity
requirements and restricted research usage. Empty schemas contain concrete Arrow
types; no market curation runner or market row table was added.

Historical PE/PB/PS/dividend values remain CURRENT_RECONSTRUCTION. After-hours
daily fields allow historical nulls before the documented 2026-07-06 start.

## BSE public-authority audit

Exactly **one HTTP attempt / one raw capture**, with no retry:

| Check | Result |
| --- | ---: |
| Tushare bse_mapping pairs | 248 |
| Direct official BSE table pairs | 248 |
| Exact pair-set symmetric difference | 0 |
| Duplicate / invalid / ambiguous pairs | 0 / 0 / 0 |
| Official pilot pairs | 6 |
| Remaining mapped pairs | 242 |

The complete official table was read directly through the browser after ordinary
HTTP access was denied. All 248 exact pairs were extracted; a local transcription
checksum matched the browser extract. The official pilot attachment was downloaded
and parsed; its exact six pairs were checked against the complete table. No search
snippets, code suffix inference or corrected provider mappings were used.

Sources:

- [Official old/new mapping table](https://www.bse.cn/service/code_mapping.html).
- [Official six-stock pilot list and attachment](https://www.bse.cn/important_news/200025487.html).
- [Pilot effective switch: 2025-05-06](https://www.bse.cn/important_news/200025603.html).
- [Remaining effective switch: 2025-10-09](https://www.bse.cn/important_news/200026735.html).
- [Exchange introduction: BSE opens 2021-11-15](https://www.bse.cn/company/introduce.html).
- [Tushare bse_mapping documented fields and cap](https://tushare.pro/document/2?doc_id=375).

Reviewed official pair-extract SHA-256:
`fcc71eb2b094fceca235f67cd6a01f86464aee7e90529da34f059f69b04f68d9`.
Complete pairs, raw captures, attachment and private audits remain local/ignored.

Small official examples: `835305.BJ → 920305.BJ` and
`839680.BJ → 920680.BJ`, both effective 2025-10-09. Their 2025-08-13 ST identifiers
now resolve against the admitted current reconstruction to the same respective
security IDs as their new codes. No historically captured knowledge is claimed.

## Identity and venue admission

| Item | Count |
| --- | ---: |
| Provider stock_basic rows audited | 5,919 |
| Stable security_ids admitted | 5,911 |
| security_identifier_history rows | 6,159 |
| security_venue_history rows | 5,911 |
| Quarantine: MISSING_LIST_DATE | 7 |
| Quarantine: NON_NORMALIZED_IDENTIFIER | 1 |
| Duplicate-code / overlapping-pair candidates | 0 / 0 |

`T600018.SH` remains quarantined/unresolved without an allocated ID. It is never
normalized or merged into current `600018.SH`. Missing listing dates are retained
without guessed dates or IDs; these are excluded from admitted research identities.
Names play no role in UUID5 allocation. The fixed namespace and original provider
listing date preserve deterministic, episode-specific identity.

Mapped BSE old/new aliases share IDs with exact half-open switch boundaries.
Venue effective_from is `max(provider_list_date, 2021-11-15)`; earlier provider
listing tenure is preserved. Pre-opening .BJ facts can be PRE_BSE_LEGACY.
Availability is current OBSERVED_CAPTURE, not reconstructed historical knowledge.

Provider delist_date is retained separately; no invented +1-day or trading-day
exclusive end is applied. **Delisted-universe boundary interpretation needs
review before Phase 1C.1 data admission.** Unknown effective_to remains null.

## Governance, reproducibility and preservation

Migration 005 adds security_venue_history, curation_run,
curated_object_manifest, identity_quarantine and dataset_date_audit. It extends
lineage for bse_mapping without losing any of the original 8 runs / 47 manifests.
After the identity capture: 9 ingestion runs / 48 raw manifests, 1 bootstrap
curation_run, 0 curated_object_manifest and 0 dataset_date_audit rows.
All original and new raw hashes verify.

CURRENT_RECONSTRUCTION identity snapshot SHA-256:
`83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c`.
Input-manifest SHA-256:
`8e819df9d3930c65b174c0b0a8b9a7d1439d7b73a5c59bb251ffc1a35aa71e39`.
Contract/curation configuration SHA-256:
`d7c0dde0d25744fdf3558bbe5857aa902f3fba8889e6dbdd9c25445ae9a1ee82`.

Rebuilding with reversed input order and a new observation time reproduced the
identity hash. Offline rerun reused the original admission: no extra mapping
request, IDs, governance rows or quarantines. Changed admitted inputs/metadata
stop for review; they cannot silently recompute persisted security IDs.

## Tests, CI and staging audit

Local full suite: **250 passed**, Python 3.12.14, locked dependencies.
Doctor, both catalog versions, typed specs and offline probe plan pass.
Synthetic tests cover UUID determinism, name independence, distinct code-reuse
episodes, overlap quarantine, exact BSE transitions, current observation/as-of
resolution, venue boundary, non-normalized retention, deterministic hashes,
no-clobber paths, safe audit details and durable single-attempt capture budget.
Tests prohibit Python network access and use no real credentials or raw captures.

GitHub CI implementation run: **SUCCESS**, 250 tests passed on Linux/Python 3.12.3;
[run 36848898171](https://github.com/liuyanfeier/AStockSystem/actions/runs/36848898171),
exact implementation commit `2b36145ea0c783cd11fe738c318aa6b2b6e9d670`,
23s total / foundation 21s. Remote v2/specs steps passed as part of the same job.
CI uses Python 3.12, locked dependencies, synthetic pytest and offline diagnostics,
including v2/specs; it does not require TUSHARE_TOKEN or call market APIs.

Explicit-path staging and exact-token scans passed. Real .env, credentials,
DuckDB/database files, raw/curated/warehouse data, private evidence/reports,
.tools and .venv remain excluded. Required hidden project files remain tracked.

## Stop and next review

No Phase 1C.1/1C.2 slices, historical backfill, 2013-present download, market row
tables, strategies, signals, backtests, portfolio, broker or order code were begun.
Recommend reviewer approval of Phase 1C.0, followed by clarification of delist
boundaries and the bounded Phase 1C.1 plan. Stop here until approval.
