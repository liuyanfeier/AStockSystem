# Foundation Data Dictionary

Phase 0 only: six tables, no real market data or trading rules. Schema source:
`sql/001_foundation_schema.sql`. Dates use exchange-local calendars; timestamps
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
| settlement_t_plus_n | INTEGER / nullable | Nonnegative settlement/resale restriction descriptor; full applicability in notes |
| lot_size | INTEGER / nullable | Positive share count where one scalar suffices |
| lot_size_rule | VARCHAR / nullable | Minimum/increment/sell-odd-lot exceptions |
| special_ipo_rule | VARCHAR / nullable | IPO/new-listing exceptions, including duration |
| notes | VARCHAR / nullable | Additional scope and official-document references |

No current rules are seeded. Complex limits, T+N exceptions and lot rules require
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
