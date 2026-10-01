# Foundation Data Dictionary

Phase 0: six foundation tables; Phase 1A: two additional governance tables.
Phase 1B.1 adds only `security_identifier_history` governance (migration 004,
after 003); no real identity mappings are seeded.
No market-data tables or trading rules are seeded. Apply migrations 001 through 004
in order; schema versions 1–4. Phase 1B raw captures are stored separately.
Dates use exchange-local calendars; timestamps
are `TIMESTAMPTZ`. Effective date intervals are [from, to). Nullable fields mean
unknown/not applicable, never zero. Source must be nonempty. See the data contract
for availability evidence, null distinctions and revision handling.

## Shared source and knowledge fields

In `security_master`, `trade_calendar`, and `market_rule_history`:

| Column | Type / null | Meaning |
|---|---|---|
| source | VARCHAR / required | Provider or primary-document identity; provenance resolution required before ingestion |
| published_at | TIMESTAMPTZ / nullable | Version publication time; NULL if unknown |
| available_at | TIMESTAMPTZ / required | Evidence-supported earliest eligible time under declared research mode |

SQL rejects availability before a known publication. New knowledge versions are
appended; old versions stay intact. Cross-source reconciliation is not implemented.

## security_master

Primary key: `(security_id, source, valid_from, available_at)`.
Business identity: stable `security_id`; codes/names may change or be reused.

| Column | Type / null | Meaning |
|---|---|---|
| security_id | VARCHAR / required | Stable internal security identity |
| ts_code | VARCHAR / nullable | Vendor code, absent for sources without this code |
| symbol | VARCHAR / required | Exchange symbol, not globally unique |
| name | VARCHAR / required | Name in this effective version |
| exchange | VARCHAR / required | Explicit exchange identifier |
| board | VARCHAR / required | Board in this effective version |
| list_date | DATE / required | Listing date known in this version |
| delist_date | DATE / nullable | Delisting date if known; cannot precede listing |
| security_type | VARCHAR / required | Instrument type |
| valid_from | DATE / required | Effective start of identity snapshot |
| valid_to | DATE / nullable | Exclusive end, strictly after start |

Retain delisted records. ST, suspension and industry histories need separate
Phase 1 datasets. Overlap/revision selection requires application-level checks.

## trade_calendar

Primary key: `(exchange, calendar_date, source, available_at)`.
Business key: exchange and calendar date, versioned by source/knowledge time.

| Column | Type / null | Meaning |
|---|---|---|
| exchange | VARCHAR / required | Calendar exchange |
| calendar_date | DATE / required | Local calendar date |
| is_open | BOOLEAN / required | Trading-day status in this published version |
| previous_open_date | DATE / nullable | Prior open date, strictly earlier if supplied |

History must include published calendar corrections, not just today's calendar.
Unknown previous-open dates remain NULL; SQL does not verify the referenced day.

## market_rule_history

Primary key: `(rule_id, source, available_at)`.
`rule_id` identifies a rule version's logical lineage within its source. Distinct
effective regimes receive distinct IDs; corrections append knowledge versions.

| Column | Type / null | Meaning |
|---|---|---|
| rule_id | VARCHAR / required | Source-scoped logical rule identity |
| exchange, board | VARCHAR / required | Applicable market and board |
| security_status | VARCHAR / required | Applicable status, explicitly specified; no implicit wildcard |
| effective_from | DATE / required | Effective start |
| effective_to | DATE / nullable | Exclusive effective end, strictly after start |
| price_limit_rule | VARCHAR / required | Rule description including applicability; not executable code |
| price_limit_fraction | DECIMAL(9,6) / nullable | Fraction 0–1; NULL is not unlimited trading |
| sell_delay_trading_days | INTEGER / nullable | Minimum subsequent trading days before a purchased position becomes eligible for sale; purchase day is day 0; NULL means unknown |
| lot_size | INTEGER / nullable | Positive share count where one scalar suffices |
| lot_size_rule | VARCHAR / nullable | Minimum/increment/sell-odd-lot exceptions |
| special_ipo_rule | VARCHAR / nullable | IPO/new-listing exceptions, including duration |
| notes | VARCHAR / nullable | Additional scope and official-document references |

This field describes resale eligibility only, not cash clearing, settlement,
cash withdrawal or other execution constraints. Count subsequent open dates in
the applicable exchange calendar; weekends/holidays do not increment the delay.
Zero means no trading-day delay from this restriction alone. There is no default;
NULL must not be treated as zero. Cash settlement is not currently needed and has
no column; if introduced, it needs a separate field with its own calendar/unit.

No current rules are seeded. Complex limits, resale exceptions and lot rules require
structured contracts before an execution engine can consume them. No default
matching priority is implied; overlapping/conflicting applicability must be audited.

## data_quality_log

Primary key: `(run_id, dataset, check_name, checked_at)`; append-only run events.

| Column | Type / null | Meaning |
|---|---|---|
| run_id | VARCHAR / required | Audit run identity |
| dataset | VARCHAR / required | Checked dataset |
| checked_at | TIMESTAMPTZ / required | Check time |
| check_name | VARCHAR / required | Check identifier |
| severity | VARCHAR / required | INFO, WARNING or ERROR |
| passed | BOOLEAN / required | Check outcome |
| observed, expected | VARCHAR / nullable | Sanitized values/conditions; units follow the checked dataset |
| details | VARCHAR / nullable | Sanitized context, never tokens or credentials |

No audit runner or pass/fail policy is implemented yet.

## research_hypothesis

Primary key: `(hypothesis_id, revision)`; append revisions, never erase earlier
questions/results. The initial revision precedes experiments; subsequent revisions
may attach results without changing the original registration.

| Column | Type / null | Meaning |
|---|---|---|
| hypothesis_id | VARCHAR / required | Research lineage ID |
| revision | INTEGER / required | Positive revision, defaults to 1 |
| created_at | TIMESTAMPTZ / required | Original hypothesis creation |
| recorded_at | TIMESTAMPTZ / required | Revision recording, defaults to current time; not before creation |
| question | VARCHAR / required | Testable question |
| economic_rationale | VARCHAR / required | Economic/behavioral rationale |
| data_required | VARCHAR / required | Datasets and availability needs |
| parameter_family | VARCHAR / nullable | Planned parameter ranges; unset before design |
| research_start, research_end | DATE / nullable | Inclusive research period |
| validation_start, validation_end | DATE / nullable | Inclusive validation period |
| oos_start, oos_end | DATE / nullable | Inclusive final out-of-sample period |
| result, decision, notes | VARCHAR / nullable | Results, reviewed decision and supporting context |

Period pairs must both be NULL or both set in ascending order. Set periods must
not overlap and must follow research → validation → OOS order. NULL pairs mean
not designed; they do not authorize running an experiment. SQL cannot enforce
pre-registration or prevent OOS tuning; the review workflow must do so.

## schema_version

Primary key: `version`; unique `migration_id`.

| Column | Type / null | Meaning |
|---|---|---|
| version | INTEGER / required | Positive schema version |
| migration_id | VARCHAR / required | Migration identity |
| description | VARCHAR / required | Migration purpose |
| applied_at | TIMESTAMPTZ / required | Application time, defaults to current time |

The SQL transaction creates missing tables and inserts version 1 once. Re-running
against the same schema is idempotent and preserves rows. `IF NOT EXISTS` does
not verify or repair incompatible preexisting tables; this is not a migration
engine or a schema-drift detector.

## ingestion_run (Phase 1A)

Primary key: UUID `run_id`; unique `(run_id, dataset)` supports manifest linkage.
No runs are seeded. BACKFILL is a reserved metadata mode, not an implemented operation.

| Column | Type / null | Meaning |
|---|---|---|
| run_id | UUID / required | Capture run identity |
| source, dataset | VARCHAR / required | tushare; one of twelve contracted datasets |
| mode | VARCHAR / required | AUDIT, SNAPSHOT, INCREMENTAL or BACKFILL |
| started_at, finished_at | TIMESTAMPTZ / finish nullable | Exact run times; finish cannot precede start |
| status | VARCHAR / required | RUNNING requires no finish; SUCCEEDED/FAILED/CANCELLED require finish |
| code_commit | VARCHAR / required | Full lowercase 40-character Git SHA |
| config_hash | VARCHAR / required | Lowercase 64-character SHA-256; canonical encoding to be designed |
| provider_client_version | VARCHAR / required | Numeric major.minor.patch of actual client; SDK audit version is separate |
| requested_start, requested_end | DATE / nullable | Requested inclusive event-date range; ordered when both known |
| request_count, row_count, raw_object_count | BIGINT / required | Nonnegative totals, default zero; future writer must reconcile with manifests |
| error_category | VARCHAR / nullable | TRANSPORT, REDIRECT, AUTH, PROVIDER or INVALID_RESPONSE |
| error_http_status | INTEGER / nullable | Numeric 100–599 only |
| error_provider_code | BIGINT / nullable | Provider's numeric code; error numbers require a category |

No free-text error/message/body or credential field is provided.

## raw_object_manifest (Phase 1A)

Primary key: UUID `object_id`; unique `relative_path`; foreign key `(run_id, dataset)`
references ingestion_run. Metadata schema only: no objects are produced.

| Column | Type / null | Meaning |
|---|---|---|
| object_id, run_id | UUID / required | Object identity and parent run |
| dataset | VARCHAR / required | Must match parent run's dataset |
| relative_path | VARCHAR / required | `data/raw/tushare/<dataset>/run_id=<uuid>/part-NNN.parquet`; no traversal |
| sha256, schema_hash | VARCHAR / required | Lowercase SHA-256 digests, 64 hex characters |
| retrieved_at | TIMESTAMPTZ / required | Exact actual retrieval time, independent of availability |
| row_count | BIGINT / required | Nonnegative object row count |
| min_event_date, max_event_date | DATE / nullable | Both absent or both present and ordered |
| request_params | JSON / required | Allowlisted, scalar-string public parameters; no duplicate keys or secrets |

Allowlisted keys: ts_code, trade_date, start_date, end_date, exchange, market,
list_status, src, level, is_new and l1_code/l2_code/l3_code. Types and patterns
are checked in SQL and `RequestParams`; absent keys are omitted rather than null.
No arbitrary parameter metadata, headers or response strings are accepted.
Checksum format is validated; verifying bytes and aggregate consistency is deferred.
Do not silently broaden the allowlist to support a future endpoint.

## RecordTimes (type only)

`event_date` (DATE) or `event_at` (aware timestamp) is required. `retrieved_at` is an
aware timestamp; `published_at` and `available_at` may be absent in raw staging.
`availability_basis` is the seven-value enum in the data contract; UNKNOWN prohibits
inventing available_at. `time_precision` records DATE/MINUTE/SECOND/MICROSECOND/UNKNOWN.
These fields are not new market tables. Migration 001 and its sell-delay semantics
remain unchanged. Migration 002 is repeatable, not a schema-drift repair engine.

## Phase 1B migration 003 addendum

Apply 003 after 001/002. It adds PROBE to ingestion_run.mode and PERMISSION to
error_category; no columns or market tables are added. Both tables are rebuilt
transactionally with parent/child rows preserved. Standalone reruns preserve all
rows; the small migration helper skips recorded versions. Original migrations stay
unchanged. Counts include actual request attempts (including retries); object/row
counts include only successfully registered immutable parts. Failed probes retain
completed objects and safe error numbers, never response msg. Default ignored
DuckDB holds governance only; observations are not promoted into Phase 0 identity,
calendar or rule tables. Sidecar metadata records exact current retrieval/availability
and OBSERVED_CAPTURE, not historical market knowledge.

## security_identifier_history (Phase 1B.1)

Migration 004 adds identity governance only. Its eleven columns, types and knowledge
semantics are defined in [Security Identifier History](security_identifier_history.md).
`valid_from/valid_to` are DATE; publication/availability/retrieval use TIMESTAMPTZ;
other fields use required nonblank VARCHAR. Only `valid_to` and `published_at` are
nullable. The source-scoped lineage plus `available_at` is the primary key.
No real mappings are seeded; code reuse must not collapse distinct securities.
Apply through `astock.data.raw_writer.migrate`, which skips recorded migrations.
Cross-row conflicts require `IdentityHistory.append`; SQL checks alone are insufficient.

## Phase 1C.0 governance addendum

Migration `005_identity_bootstrap_governance.sql` preserves existing lineage and
admits the bounded `bse_mapping` audit dataset. It adds:

| Table | Meaning / key fields |
| --- | --- |
| security_venue_history | Stable security_id + venue + half-open effective interval; original provider_list_date/provider_delist_date retained separately; observation availability/retrieval and evidence_source |
| curation_run | UUID, dataset/partition, start/finish/status, exact code_commit, config/input-manifest/identity-snapshot SHA-256, provider/resolved/quarantined counts |
| curated_object_manifest | UUID, parent run UUID, relative immutable path, content/schema hashes, row count and event bounds |
| identity_quarantine | Native identifier retained verbatim, optional event date, reason, registered raw_object_id, parent run UUID and first_seen_at |
| dataset_date_audit | Dataset/date/run, provider/resolved/quarantined/duplicate counts, cap_hit, status and allowlisted integer-count JSON details |

Quarantine supports NO_IDENTIFIER_MAPPING, AMBIGUOUS_IDENTIFIER,
NON_NORMALIZED_IDENTIFIER, OUTSIDE_IDENTIFIER_INTERVAL, PRE_BSE_LEGACY,
ASSET_OUT_OF_SCOPE, MISSING_LIST_DATE and IDENTITY_METADATA_REVIEW.
Application admission validates cross-row identity conflicts and raw provenance;
SQL CHECK constraints alone do not prove temporal identity consistency.

Typed specs in `config/curation/v1/` define future column names and units:
`volume_hands`, `amount_cny_thousand`, `total_share_10k`,
`total_mv_10k_cny`, plus explicit turnover/dividend `_pct` values.
Numeric values remain unrounded; nullable values are preserved. These specs are
schema definitions, not populated market-data tables.
