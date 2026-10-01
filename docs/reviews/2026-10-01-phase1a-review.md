# Phase 1A Review — 2026-10-01

## Scope and base

Exact base commit: `975bacd9c6fe8e61e13b0e453be2cd076ed19998` (approved Phase 0).
User-authorized scope: Codex_Phase1A_Provider_Audit_Prompt_v1.0.md only.
The supplied prompt is committed for reproducible review. Original planning files,
migration 001, Phase 0 report and locked dependencies remain unchanged.

## Changed files

- `.github/workflows/ci.yml`
- `.gitignore`
- `AGENTS.md`
- `Codex_Phase1A_Provider_Audit_Prompt_v1.0.md`
- `README.md`
- `config/contracts/v1/adj_factor.yaml`
- `config/contracts/v1/daily.yaml`
- `config/contracts/v1/daily_basic.yaml`
- `config/contracts/v1/index_basic.yaml`
- `config/contracts/v1/index_classify.yaml`
- `config/contracts/v1/index_daily.yaml`
- `config/contracts/v1/index_member_all.yaml`
- `config/contracts/v1/stk_limit.yaml`
- `config/contracts/v1/stock_basic.yaml`
- `config/contracts/v1/stock_st.yaml`
- `config/contracts/v1/suspend_d.yaml`
- `config/contracts/v1/trade_cal.yaml`
- `docs/data_contract.md`
- `docs/data_dictionary.md`
- `docs/reviews/2026-10-01-phase1a-review.md`
- `docs/reviews/2026-10-01-phase1a-transport-audit.md`
- `docs/security_identifier_history.md`
- `sql/002_provider_lineage.sql`
- `src/astock/cli/main.py`
- `src/astock/data/audit.py`
- `src/astock/data/availability.py`
- `src/astock/data/contracts.py`
- `tests/conftest.py`
- `tests/test_availability.py`
- `tests/test_cli.py`
- `tests/test_data_contracts.py`
- `tests/test_lineage_schema.py`
- `tests/test_provider_audit.py`

## Transport findings

Technical HTTPS gate passed with normal certificate verification, no redirects,
and structured 40101 authentication errors using empty/deliberately-invalid tokens.
Responses contained no market data. Initial transient connection failures and exact
probe times are recorded in [transport audit](2026-10-01-phase1a-transport-audit.md).

Official API manual describes HTTP; inspected Tushare 1.4.29 wheel defaults to
`http://api.waditu.com/dataapi`. Observed HTTPS reachability is not an official
support declaration or successful real authentication. SDK was statically inspected,
not installed/imported. Repository transport is mock-only and rejects HTTP/all 3xx.

## Schema and contracts

Migration 002 adds ingestion_run and raw_object_manifest, schema version 2, UUID/FK
lineage, ordered times, nonnegative counts, SHA-256 format and run-bound raw paths.
Error metadata is category/numbers only; JSON parameters use a typed allowlist,
rejecting unknown/nested keys, duplicate keys and invalid scalar/date values.
No migration runner, disk DB, market table, ingestion run or raw object is created.

Twelve v1.0 YAML contracts: stock_basic, trade_cal, daily, daily_basic, adj_factor,
stk_limit, suspend_d, stock_st, index_basic, index_daily, index_classify,
index_member_all. Each cites official documentation checked on 2026-10-01.
Undocumented caps remain null for trade_cal, adj_factor, index_daily, index_classify.
Schedules are descriptive, required columns do not imply nonnull cells, and all
availability policies remain UNKNOWN_UNTIL_EVIDENCE. Partitions/checks are proposals.

RecordTimes adds event, publication, availability, exact retrieval, seven evidence
bases and explicit precision; UNKNOWN cannot invent availability. The identifier
history design note flags code/name changes and a separate BSE historical audit.
No actual availability timestamps or identifier mappings are assigned.

## Local validation

- `scripts/uv run --offline --frozen pytest`: **158 passed**, Python 3.12.14.
- `scripts/uv run --offline --frozen astock doctor`: **PASS**, token configured NO.
- `scripts/uv run --offline --frozen astock data contracts`: **PASS (12)**.
- `git diff --check`: passed; migration 001 unchanged.
- Tests globally block Python socket/DNS connections; fixtures are synthetic only.
- CI retains locked installs, Python 3.12, empty TUSHARE_TOKEN and offline tests/doctor;
  adds the offline contract diagnostic. Live HTTPS audit is not a CI test.

## CI after push

Initial local snapshot: remote CI awaits implementation push. Completion requires
an appended CI result identifying the tested implementation SHA and Actions run.
Public GitHub API was rate-limited; the authenticated Actions browser page is
available and showed the approved Phase 0 run succeeded. No token was extracted.

## Secret / privacy audit

Before staging: no real `.env`, credential, database, raw/curated/warehouse dataset,
private/personal data, .tools or .venv is included. Existing hidden project files
remain tracked, with empty .env.example placeholder. New private/ and data/private/
ignore rules were added; current raw/data/report exclusions remain in force.

Requests/manifests/errors are tested with synthetic secret markers. Only structured
safe values survive serialization. No provider token, broker credential, balance,
holding, personal execution or private report was used. Manual HTTPS probes used
only empty/invalid token values and returned data=null. Scratch audit output remains
ignored; no provider response fixture is committed. Explicit staging and index audit
are required before each commit; post-staging results are appended with CI evidence.

## Open questions and deferred implementation

- Obtain authoritative HTTPS support evidence and separately approve real-credential
  client design/entitlement checks before Phase 1B.
- Confirm unknown caps, coverage/truncation handling, null-key normalization and
  full historical listing/membership selection before complete-universe ingestion.
- Audit BSE identifier changes/calendar coverage; verify provider taxonomy-version
  provenance instead of inferring mappings from current codes.
- Design canonical config/schema hashing, actual byte-checksum verification, atomic
  append-only writes, retry/idempotency and aggregate-count reconciliation later.
- Availability evidence/precision and revision policy still need endpoint-specific
  audit before promotion into research/decision records.

## Explicit exclusions

No real token or `.env`; no market download/backfill, strategies/signals/backtests,
broker integration/orders, personal data, reporting infrastructure or Phase 1B.
Stop after commit, push and verified CI; wait for reviewer approval.
