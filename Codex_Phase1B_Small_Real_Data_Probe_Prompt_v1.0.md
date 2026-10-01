# Codex Task — Phase 1B Small Real-Data Probe v1.0

Base the work on the current reviewed `main`.

Phase 1A is approved. This task is **Phase 1B only**.

Read first:

- `AGENTS.md`
- `docs/data_contract.md`
- `docs/data_dictionary.md`
- `docs/reviews/2026-10-01-phase1a-review.md`
- `docs/reviews/2026-10-01-phase1a-transport-audit.md`
- `docs/security_identifier_history.md`
- `AStockSystem_Phase1B_Small_Real_Data_Probe_Design_v1.0.md` if present

Do not begin Phase 1C.
Do not perform historical full backfill.
Do not implement strategies, signals, backtests, broker APIs or orders.

## 0. Credential rule

A real Tushare token may be used in Phase 1B, but ONLY from local secret configuration.

Never ask the user to paste the token into Codex/chat.

If `TUSHARE_TOKEN` is not locally configured, stop before any live request and tell the user:

`Configure TUSHARE_TOKEN locally in .env outside the chat/model input, then rerun.`

Never echo, log, serialize, commit, or include the token in an exception or public artifact.

## 1. Pre-live security fixes

Before any real-token request:

### Exact endpoint pinning

Production Tushare transport may send credentials only to:

`https://api.tushare.pro`

Reject:

- any other hostname;
- explicit non-443 port;
- HTTP;
- userinfo;
- query;
- fragment;
- alternate path except empty `/`;
- every 3xx redirect.

Use:

- TLS verification enabled;
- `follow_redirects=False`;
- `trust_env=False`.

Do not disable TLS or fall back to HTTP under any failure.

Keep documentation URLs separate from credential-bearing provider endpoint validation.

### `PROBE` mode

Do not rewrite migration 002.

Create migration 003 that makes `PROBE` a valid `ingestion_run.mode`.

If DuckDB requires transactional table recreation to change an existing CHECK constraint:
- preserve existing rows;
- preserve FK integrity;
- test migration from a populated synthetic pre-003 database;
- make rerunning migration controlled/idempotent.

Do not assume the local database is empty.

### Error category

Add `PERMISSION` to safe provider/run error categories.

Official Tushare REST documentation states provider code `2002` represents a permission problem.

Keep observed invalid-token code handling separate:
- `40101` may be classified AUTH based on Phase 1A observation;
- document that this is observed, not an official code contract.

### `stk_limit`

Update the contract to request:

- trade_date
- ts_code
- pre_close
- up_limit
- down_limit
- asset_type
- exchange

Update contract tests.

## 2. Real provider client

Create a small dedicated client, e.g.:

`src/astock/data/tushare_client.py`

Do not use the Tushare SDK for the credential-bearing request path.

Responsibilities only:

- exact pinned HTTPS POST;
- typed provider envelope validation;
- safe error classification;
- return fields/items in a typed structure.

Do not write DB/files from the transport class.

Token must use `SecretStr` or equivalent.

Successful envelope requires:

- HTTP 200
- provider code 0
- `data` object
- unique string `fields`
- `items` list
- every item width equals field count

Never log raw response bodies/messages on errors.

Store only safe categories and numeric HTTP/provider codes.

## 3. Live-call pacing and retries

Phase 1B must remain single-threaded.

Enforce at least 1.25 seconds between live requests.

Retry at most one time after the first attempt for transient:

- ConnectError
- ConnectTimeout
- ReadTimeout
- HTTP 5xx

Do not retry:

- AUTH
- PERMISSION
- redirects
- invalid schema
- contract violations

A retry must still obey pacing.

## 4. Probe plan

Create a versioned probe plan, preferably:

`config/probes/phase1b.yaml`

Only these endpoints:

- trade_cal
- stock_basic
- daily
- daily_basic
- adj_factor
- stk_limit
- stock_st
- suspend_d

### Fixed historical anchors

- `2015-07-08` — suspension-stress audit anchor
- `2019-06-25` — Tushare `stk_limit` documented sample anchor
- `2020-08-24` — ChiNext trading-rule transition anchor
- `2025-08-13` — Tushare `stock_st` documented sample anchor

### Recent anchor

Use `trade_cal` to resolve the latest open SSE trading date in:

`2026-09-01 .. 2026-09-30`

Do not assume the resulting date before querying the calendar.

Persist the resolved date only in local run metadata and sanitized review summary.

## 5. Handshake

The FIRST real-token request must be a small `trade_cal` request.

If authentication fails:
- record only safe category/code;
- stop all further live requests;
- Phase 1B is BLOCKED.

If TLS/redirect/endpoint validation fails:
- stop;
- never attempt HTTP fallback.

## 6. `stock_basic` probe

Fetch explicit partitions:

- exchange: SSE, SZSE, BSE
- list_status: L, D, P, G, UN

Do not rely on provider default `L`.

Request exact contract fields.

If any response row count equals documented `max_rows`:
- mark `POTENTIAL_TRUNCATION`;
- do not silently accept completeness.

Commit only aggregate counts/statuses, not the full security list.

## 7. Cross-sectional date probes

For each of the five resolved anchor dates, fetch by `trade_date`:

- daily
- daily_basic
- adj_factor
- stk_limit
- stock_st
- suspend_d

Do not loop over securities.

Every request must specify fields explicitly from the versioned contract.

If an endpoint returns provider code 2002:
- classify PERMISSION;
- preserve already successful audit captures;
- final Phase 1B cannot PASS.

## 8. Raw writer

Implement a reusable but small append-only raw writer.

Layout:

`data/raw/tushare/<dataset>/run_id=<uuid>/part-NNN.parquet`

One `PROBE` ingestion_run per dataset.

Multiple requests for one dataset use successive parts in the same run.

Requirements:

- write temporary file;
- close/flush;
- compute SHA-256 of exact Parquet bytes;
- atomic rename;
- then record manifest metadata;
- never overwrite an existing part;
- failures keep already completed immutable parts for audit.

Add a sanitized local `manifest.json` sidecar if useful.

No token may appear in it.

Do not commit raw files.

## 9. No production curated tables

Do NOT create production:

- daily_bar
- daily_basic market table
- adj_factor market table
- price_limit_daily
- risk_warning_daily
- suspension_daily

Do not persist a curated warehouse yet.

Audit/normalization previews may occur in memory only.

This is deliberate: Phase 1B observes real provider behavior before Phase 1C freezes curated schemas.

## 10. Logical content fingerprint

For audit only, implement a deterministic logical fingerprint:

- provider values/nulls preserved;
- canonical column order;
- rows sorted by contract natural key;
- deterministic JSONL-like canonical encoding;
- SHA-256.

Do not confuse this with raw Parquet byte SHA.

Do not add it to permanent DB schema unless a separate design justification is reviewed.

## 11. Repeat-consistency probe

Repeat exactly:

- endpoint: daily
- trade_date: 20190625

Compare two independent captures:

- fields
- row count
- natural-key set
- logical content SHA-256

Expected logical content should match.

If not:
- keep both captures;
- report differences;
- Phase 1B is PARTIAL, not silently normalized.

## 12. Data-quality audit

Create deterministic audit code for probe captures.

At minimum report:

### Provider/contract
- requested vs observed fields
- rows
- documented cap
- exact-cap warning
- natural-key duplicates
- null counts

### daily
- OHLC consistency
- positive prices
- nonnegative volume/amount
- `close - pre_close` vs `change`
- `100 * change / pre_close` vs `pct_chg`
with documented rounding tolerances

### daily_basic ↔ daily
- intersection count
- only_daily
- only_daily_basic
- close mismatch count

### stk_limit ↔ daily
For `asset_type == STK`:
- intersection
- pre_close mismatch count
- breakdown by exchange

### adj_factor ↔ daily
- intersection
- only_daily
- only_adj
- null/nonpositive factor count

### stock_st
- duplicates
- type/type_name summary
- codes unresolved against all-status stock_basic universe

Do NOT infer ST from security name.

### suspend_d
- S/R counts
- null/non-null suspend_timing counts
- for S records with null timing, compare whether daily row exists
- treat exceptions as audit findings, not automatic data deletion

### BSE
- aggregate observed code/suffix patterns only
- do not create historical mappings

## 13. Availability semantics

For Phase 1B historical captures:

- `retrieved_at` = actual capture time
- availability basis = `OBSERVED_CAPTURE`
- `available_at` = retrieved_at

Document explicitly:

This means the system observed the historical record now.
It does NOT mean the record/version was historically available on its event date.

No Phase 1B data is eligible for strategy backtests.

## 14. CLI

Implement an explicit controlled interface, e.g.:

- `astock data probe plan`
- `astock data probe run --live`
- `astock data probe status`

Rules:

- plan/status are offline by default;
- no live network without explicit `--live`;
- no `sync-all`;
- no full backfill command.

## 15. Secret scan

After live probe, scan exact generated probe artifacts for the exact token byte/string.

Return only PASS/FAIL.

Never output the secret.

If FAIL:
- do not commit review artifacts;
- Phase 1B BLOCKED.

Also audit Git staging before every commit.

## 16. Public review artifacts

Create:

- `docs/reviews/YYYY-MM-DD-phase1b-review.md`
- `docs/reviews/YYYY-MM-DD-phase1b-observed-schema.json`

They may include only sanitized aggregate evidence:

- commit SHA
- run IDs
- datasets
- request counts
- row counts
- observed field names/types
- null/duplicate counts
- cap warnings
- cross-table mismatch counts
- logical fingerprint
- DQ status
- permission status

Do NOT include:
- token
- raw provider body
- full stock list
- full market rows
- raw Parquet
- account/personal data

## 17. CI

GitHub CI remains fully synthetic/offline.

Never put the real token in GitHub Actions.

Add tests for:

- exact endpoint pinning;
- other HTTPS host rejection;
- non-443 rejection;
- redirects;
- token redaction;
- provider code 2002 → PERMISSION;
- 40101 → observed AUTH classification;
- response schema validation;
- PROBE migration preserving synthetic pre-003 rows;
- atomic raw writer behavior with synthetic data;
- no overwrite;
- logical fingerprint determinism under row reordering;
- DQ audit logic;
- CLI requires `--live`;
- all Phase 0/1A tests remain green.

## 18. Stop conditions

Immediately BLOCK real probing if:

- token missing;
- endpoint is not exact pinned HTTPS;
- TLS fails;
- redirect occurs;
- authentication fails;
- secret scan fails.

Permission failure can allow other safe probes to complete for evidence, but final status cannot PASS.

## 19. Required completion report

Return exactly:

```text
PHASE 1B STATUS
PASS / PARTIAL / BLOCKED

BASE + IMPLEMENTATION COMMITS
...

LIVE HTTPS / AUTH
...

PERMISSIONS
...

PROBE PLAN + RESOLVED DATES
...

RAW / LINEAGE RESULTS
...

DATA QUALITY
...

REPEAT CONSISTENCY
...

SECRET AUDIT
...

LOCAL TESTS
...

GITHUB CI
...

PUBLIC REVIEW ARTIFACTS
...

OPEN QUESTIONS
...

WHAT I DID NOT DO
...
```

After push, verify GitHub Actions on the exact implementation/review commit.

Then STOP.

Do not begin Phase 1C.
