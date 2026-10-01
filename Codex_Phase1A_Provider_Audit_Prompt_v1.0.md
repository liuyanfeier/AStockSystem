# Codex Task — Phase 1A Provider / Transport / Contract Audit v1.0

Use the current approved AStockSystem main branch.

This task is **Phase 1A only**.

Do not use a real Tushare token.
Do not download real market data.
Do not begin historical backfill.
Do not implement strategy, signals, backtests, broker integration, or live orders.

## Goal

Establish the provider-security gate, dataset contracts, lineage schema, and synthetic-test foundation required before any real Tushare credential is used.

## 1. Read first

Read and follow:

- AGENTS.md
- docs/data_contract.md
- docs/data_dictionary.md
- docs/phase0_report.md
- docs/reviews/README.md
- AStockSystem_Phase1_Data_Foundation_Design_v1.0.md if present in the repository

Do not silently change previously approved semantics.

## 2. Transport security audit — NO REAL TOKEN

Current public Tushare materials have a transport inconsistency:
- official HTTP documentation shows `http://api.tushare.pro`;
- public Python SDK source has historically used an HTTP endpoint;
- `https://api.tushare.pro` appears TLS-reachable.

Create `docs/reviews/YYYY-MM-DD-phase1a-transport-audit.md`.

Audit, without a real credential:

1. Inspect the current Tushare Python package/source if you install it for inspection.
2. Record the actual base endpoint used by the inspected version.
3. Perform only credential-free or deliberately invalid-token probes.
4. Check whether `https://api.tushare.pro`:
   - validates TLS normally;
   - accepts the REST-shaped request;
   - returns structured Tushare-style errors;
   - redirects anywhere.
5. Never send a real token.
6. Never fall back to HTTP.
7. Any future provider client must fail closed if the configured URL is not HTTPS or redirects/downgrades to HTTP.

Do not claim HTTPS is officially supported unless authoritative evidence says so.
Distinguish:
- observed technical behavior;
- official documentation;
- inference.

If HTTPS cannot be safely validated, mark Phase 1A BLOCKED and stop before real-data implementation.

## 3. Do not add real Tushare ingestion yet

You may create:
- interfaces;
- Pydantic contracts;
- mocked/fake provider transport;
- sanitized request/response structures.

You may NOT:
- call Tushare with a real token;
- create a real `.env`;
- write real market rows;
- backfill data.

## 4. Add lineage/governance schema

Create a new migration, do not rewrite migration history casually.

Add at minimum:

### ingestion_run

Fields should cover:
- run_id
- source
- dataset
- mode
- started_at
- finished_at
- status
- code_commit
- config_hash
- provider_client_version
- requested_start
- requested_end
- request_count
- row_count
- raw_object_count
- sanitized error metadata

### raw_object_manifest

Fields should cover:
- object_id
- run_id
- dataset
- relative_path
- sha256
- retrieved_at
- row_count
- schema_hash
- min_event_date
- max_event_date
- sanitized request params

No token or secret may be representable in normal logs/manifests.

Update schema versioning and tests.

## 5. Dataset contract model

Implement a small typed DatasetContract model.

Do not create a generic plugin framework.

The contract needs at least:

- dataset
- provider
- endpoint
- required_fields
- natural_key
- max_rows
- timezone
- units
- availability_policy
- revision_policy
- fetch_partition
- quality_checks

Create versioned YAML contracts for the initial Tier-A datasets:

- stock_basic
- trade_cal
- daily
- daily_basic
- adj_factor
- stk_limit
- suspend_d
- stock_st
- index_basic
- index_daily
- index_classify
- index_member_all

Do not fetch them.

For documented facts such as row limits/update schedules, cite the source URL in the contract metadata or adjacent documentation.

Do not invent an undocumented limit.

## 6. Availability semantics

Extend documentation/types so future records can represent:

- event date/time
- published_at
- available_at
- retrieved_at
- availability_basis
- time_precision

Use explicit availability-basis values such as:

- MARKET_CLOSE_RECONSTRUCTED
- PROVIDER_DOCUMENTED_SCHEDULE
- SOURCE_PUBLICATION
- CONSERVATIVE_NEXT_SESSION
- OBSERVED_CAPTURE
- EXECUTION_FACT
- UNKNOWN

Do not assign actual production availability timestamps yet.

## 7. Privacy boundary for the public repository

The GitHub repository is public.

Update ignore/documentation so future personal/private data cannot be committed accidentally.

At minimum ignore:

- `data/private/**`
- `private/**`

Document that the public repository must never contain:

- provider tokens;
- broker credentials;
- account balances;
- holdings;
- personal execution history;
- private reports;
- raw provider datasets.

Do not create personal-data files.

## 8. Raw data policy

Document the future raw layout, but do not create real raw data:

```text
data/raw/<provider>/<dataset>/run_id=<id>/
    part-000.parquet
    manifest.json
```

Requirements:
- append-only;
- source-shaped;
- checksum;
- exact retrieved_at;
- sanitized request parameters;
- no token;
- raw market data remains ignored by Git.

## 9. Security identifier design note

Create a design note for `security_identifier_history`.

Do not fully implement historical mappings yet.

Explicitly flag:
- provider code is not permanent internal identity;
- names change;
- BSE historical code changes require a dedicated audit before full backfill.

Propose fields:
- security_id
- source
- identifier_type
- identifier
- exchange
- valid_from
- valid_to

Do not guess historical BSE mappings.

## 10. Synthetic tests

All CI tests must remain network-free unless a narrowly isolated transport-security test is explicitly marked non-CI.

Add tests for:

- dataset contract validation;
- no plaintext HTTP provider URL accepted by future transport config;
- redirect/downgrade rejection in mocked transport;
- secret redaction from request/manifests/errors;
- ingestion_run constraints;
- raw manifest checksum/metadata constraints;
- availability-basis enum validation;
- no real token needed;
- existing Phase 0 tests remain green.

Do not put real provider responses in fixtures.

## 11. CLI

Only add diagnostic/audit commands if useful.

Acceptable examples:

```bash
astock data contracts
astock data doctor
```

They must be offline by default.

Do not add `sync`, `backfill`, or real ingestion commands yet.

## 12. Review artifact

Create:

`docs/reviews/YYYY-MM-DD-phase1a-review.md`

It must state:

- exact commit base;
- files changed;
- transport findings;
- what is official vs observed;
- schema changes;
- contract list;
- test results;
- CI result after push;
- privacy/secret audit;
- unresolved questions;
- explicit confirmation that no real token/data was used.

## 13. Validation

Before completion:

- run full pytest;
- run astock doctor;
- run any new offline data-contract diagnostics;
- inspect git diff;
- inspect staging for secrets;
- push;
- verify GitHub Actions succeeds.

Then stop.

## 14. Required final answer

Return:

```text
PHASE 1A STATUS
PASS / PARTIAL / BLOCKED

TRANSPORT FINDINGS
...

SCHEMA CHANGES
...

DATASET CONTRACTS
...

TESTS
...

CI
...

SECRET / PRIVACY AUDIT
...

OPEN QUESTIONS
...

EXACT COMMIT SHA
...

WHAT I DID NOT DO
...
```

Do not begin Phase 1B.
