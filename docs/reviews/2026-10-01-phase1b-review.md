# Phase 1B Review — 2026-10-01

## Status and commits

Phase 1B: **PARTIAL**, pending reviewer approval. Base: `46402ebb789da2e0ee884992cfed84337a30072b`.
Exact implementation: `3f91ecd8e17c24efeb7186be124ff8b385902f70`. Batch: `a3771e7b-3b2c-4fa0-a730-4e296a5268ac`.

## Scope and live transport

Dedicated REST client pins https://api.tushare.pro, TLS verification enabled,
redirects forbidden, environment proxies disabled. Single thread, at least 1.25s
between attempts, at most two attempts for connect/read timeout/connect error/5xx.
TLS errors are not retried. SDK is not used. No HTTP fallback. First request is
SSE trade_cal for 2026-09-01 through 2026-09-30; missing token blocks before storage.
AUTH classification for 40101 is observed Phase 1A behavior; permission 2002 is
[officially documented](https://tushare.pro/document/1?doc_id=40). Real transport
success is measured by successful captures, not inferred from empty-token probes.

Resolved recent date: 2026-09-30. Historical anchors:
2015-07-08, 2019-06-25, 2020-08-24, 2025-08-13. Plan is capped at 47 logical
requests; retries can raise attempts to 94. No per-security loop or full backfill.

## Raw / lineage and permissions

| Dataset | Run status | Attempts | Rows | Objects |
|---|---|---:|---:|---:|
| adj_factor | SUCCEEDED | 5 | 21848 | 5 |
| daily | SUCCEEDED | 6 | 23779 | 6 |
| daily_basic | SUCCEEDED | 5 | 19989 | 5 |
| stk_limit | SUCCEEDED | 5 | 21562 | 5 |
| stock_basic | SUCCEEDED | 15 | 5919 | 15 |
| stock_st | SUCCEEDED | 5 | 782 | 5 |
| suspend_d | SUCCEEDED | 5 | 1444 | 5 |
| trade_cal | SUCCEEDED | 1 | 30 | 1 |

Unlisted endpoints were not reached. Failed-run safe error categories/codes are in
the adjacent aggregate JSON; no response body/message is published.
Migration 003 preserves populated 002 runs and FK-linked manifests, adding PROBE
and PERMISSION. Repeated migration is tested. Migrations 001/002 stay unchanged.
Raw byte hash means exact Parquet bytes, not HTTP response bytes. Atomic no-clobber
publication uses a POSIX hard link of a closed, fsynced temp file; unlike os.rename,
it cannot overwrite a concurrently created destination. Manifest insert follows
publication; completed orphan files survive DB failure for audit, never count as
registered objects. Sidecars record OBSERVED_CAPTURE and available_at=retrieved_at.

Lineage count reconciliation: True.
Parquet checksum/schema/row counts and sidecar reconstruction: True.

## DQ and repeat consistency

Adjacent JSON contains requested/observed fields and types, per-capture null and
duplicate counts, documented caps/distance, exact-cap errors, OHLC/positive-price/
volume/amount checks, daily change and percentage errors, cross-table comparisons,
ST type labels and unresolved-code counts, suspension full-day candidates, BSE
pattern aggregates, and deterministic logical hashes. Price/change tolerance is
0.011 currency units; percentage tolerance is 0.011 percentage points. These cover
reported rounding only; mismatches are retained, not corrected. Missing price rows
are not imputed; cap hits, identity ambiguity, unexplained mismatches or permissions
prevent PASS. Provider values/nulls remain local; full stock lists/market rows are
never in review artifacts. Logical hashes canonicalize column order, natural-key
order and duplicate-key row tie-breakers; preserve value/null distinctions.

Repeat daily/20190625: {'fields_match': True, 'logical_hash_match': True, 'natural_keys_match': True, 'row_count_match': True}.
These captures reflect current observation of history, not event-day knowledge;
no Phase 1B data is eligible for historical strategy backtests.

## Secret / privacy audit

SECRET_SCAN: PASS for exact local token bytes in this batch's raw files, decoded
Parquet values, sidecars, local aggregate summary and review drafts. Token is only
read from local SecretStr settings; no secret printed, logged, serialized in metadata
or copied into Git. Local raw, default warehouse and private paths remain ignored.
No account, broker, balance, holding or personal execution data is used. Git staging
and exact-token scan must pass before review commit; CI gets no real token.

## Validation and CI

Local full-suite results and exact-commit GitHub CI evidence are appended after
verification. CI is synthetic, socket-blocked and offline after locked dependency
installation. Real probe is explicitly --live and never runs in GitHub Actions.

## Open questions / next gate

Review any aggregate DQ/permission/schema/coverage discrepancies before Phase 1C.
Unknown historical identity coverage and BSE code/calendar issues are not guessed.
HTTPS success, if observed, still does not establish an official support guarantee.
No production curated schema, history-wide backfill, strategy, backtest, broker,
orders or Phase 1C work. Stop after sanitized evidence push and exact-commit CI.

## Observed findings and acceptance evidence — 2026-10-01

**Final Phase 1B status: PARTIAL.** Real HTTPS authentication and permissions passed
for all eight endpoints. All 47 logical requests succeeded with 47 total attempts
(no retries). Recent completed session resolved from actual SSE calendar: **2026-09-30**.
The batch saved **47 raw objects / 95,353 rows**, including the independent repeated
daily/20190625 capture. All eight runs completed SUCCEEDED; this does not override
the overall DQ gate. Local raw reconstruction and lineage reconciliation passed.
No documented row cap was reached; no natural-key duplicates or scope/date mismatch
was detected. Repeated fields, row count, key set and logical fingerprint all match.

Two unresolved identity findings prevent PASS:

1. SSE/D stock_basic: **1** code fails the expected six-digit/suffix format.
   It remains in raw; no guessed rewrite, filtering or mapping was applied.
2. stock_st/2025-08-13: **2** codes are unresolved against the complete 15-partition
   stock_basic capture. Dedicated source/identity audit is required, including
   historical code changes. This is not proof that today's codes identify the past.

Observed current BSE stock_basic: **357** records in aggregate 6digits.BJ pattern,
no unexpected pattern. This observation is not a historical BSE mapping rule.
One observed stock_basic market label is null; it is reported, not filled.
Historical daily versus daily_basic/stk_limit coverage also differs: only_daily
counts for 2015/2019/2020 are 22/37/87 against daily_basic and 23/38/88 against
stk_limit's STK subset. These are aggregate coverage observations, not automatic
proof of missing provider rows. They require asset/history coverage review.
Intersections have zero close or pre_close mismatches. Factors are positive where
observed; only_adj counts remain reported and are not treated as traded bars.
Full-day-style suspension candidates have zero daily-row exceptions in the sample.

Local checks: **210 passed** on Python 3.12.14; astock doctor, data contracts, probe
plan and offline status all passed. CI remains socket-blocked/synthetic; real local
.env is excluded and never uploaded. Implementation commit
`3f91ecd8e17c24efeb7186be124ff8b385902f70` passed
[Actions run 36822189067](https://github.com/liuyanfeier/AStockSystem/actions/runs/36822189067)
(Success, 21s), verified through the GitHub Actions UI with exact SHA.

Public files: this review and `2026-10-01-phase1b-observed-schema.json` only.
The implementation commit contains the two supplied specifications, plan, new
migration/client/writer/audits/CLI, synthetic tests and scope/contract documentation;
`git diff 46402ebb789da2e0ee884992cfed84337a30072b..HEAD --name-only` gives the exact
file inventory. Migrations 001/002 and locked dependencies remain unchanged.
Original supplied design Markdown hard-break spaces were preserved; implementation
and review files passed whitespace checks separately.

Secret scans passed before implementation staging and across generated raw bytes,
decoded Parquet, sidecars, private aggregate summary and public review drafts.
No runtime logs were generated. Raw, warehouse, .env and private paths are ignored;
only source/specs/tests/docs were staged. Review commit requires one more exact-token
index audit and its exact-SHA CI is checked before final handoff. No additional
live request is planned. Stop at PARTIAL for reviewer remediation; no Phase 1C.
