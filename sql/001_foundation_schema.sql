-- Phase 0 only. No real securities, trading rules or hypotheses are seeded.
-- Knowledge timestamps use TIMESTAMPTZ; effective date intervals are [from, to).
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS security_master (
    security_id VARCHAR NOT NULL,
    ts_code VARCHAR,
    symbol VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    exchange VARCHAR NOT NULL,
    board VARCHAR NOT NULL,
    list_date DATE NOT NULL,
    delist_date DATE,
    security_type VARCHAR NOT NULL,
    source VARCHAR NOT NULL CHECK (length(trim(source)) > 0),
    valid_from DATE NOT NULL,
    valid_to DATE,
    published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (security_id, source, valid_from, available_at),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (delist_date IS NULL OR delist_date >= list_date),
    CHECK (published_at IS NULL OR available_at >= published_at)
);

CREATE TABLE IF NOT EXISTS trade_calendar (
    exchange VARCHAR NOT NULL,
    calendar_date DATE NOT NULL,
    is_open BOOLEAN NOT NULL,
    previous_open_date DATE,
    source VARCHAR NOT NULL CHECK (length(trim(source)) > 0),
    published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (exchange, calendar_date, source, available_at),
    CHECK (previous_open_date IS NULL OR previous_open_date < calendar_date),
    CHECK (published_at IS NULL OR available_at >= published_at)
);

CREATE TABLE IF NOT EXISTS market_rule_history (
    rule_id VARCHAR NOT NULL,
    exchange VARCHAR NOT NULL,
    board VARCHAR NOT NULL,
    security_status VARCHAR NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    price_limit_rule VARCHAR NOT NULL,
    price_limit_fraction DECIMAL(9, 6),
    settlement_t_plus_n INTEGER,
    lot_size INTEGER,
    lot_size_rule VARCHAR,
    special_ipo_rule VARCHAR,
    notes VARCHAR,
    source VARCHAR NOT NULL CHECK (length(trim(source)) > 0),
    published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (rule_id, source, available_at),
    CHECK (effective_to IS NULL OR effective_to > effective_from),
    CHECK (price_limit_fraction IS NULL OR price_limit_fraction BETWEEN 0 AND 1),
    CHECK (settlement_t_plus_n IS NULL OR settlement_t_plus_n >= 0),
    CHECK (lot_size IS NULL OR lot_size > 0),
    CHECK (published_at IS NULL OR available_at >= published_at)
);

CREATE TABLE IF NOT EXISTS data_quality_log (
    run_id VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    check_name VARCHAR NOT NULL,
    severity VARCHAR NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'ERROR')),
    passed BOOLEAN NOT NULL,
    observed VARCHAR,
    expected VARCHAR,
    details VARCHAR,
    PRIMARY KEY (run_id, dataset, check_name, checked_at)
);

CREATE TABLE IF NOT EXISTS research_hypothesis (
    hypothesis_id VARCHAR NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    question VARCHAR NOT NULL,
    economic_rationale VARCHAR NOT NULL,
    data_required VARCHAR NOT NULL,
    parameter_family VARCHAR,
    research_start DATE,
    research_end DATE,
    validation_start DATE,
    validation_end DATE,
    oos_start DATE,
    oos_end DATE,
    result VARCHAR,
    decision VARCHAR,
    notes VARCHAR,
    PRIMARY KEY (hypothesis_id, revision),
    CHECK (recorded_at >= created_at),
    CHECK (
        (research_start IS NULL AND research_end IS NULL) OR
        (research_start IS NOT NULL AND research_end IS NOT NULL AND research_start <= research_end)
    ),
    CHECK (
        (validation_start IS NULL AND validation_end IS NULL) OR
        (validation_start IS NOT NULL AND validation_end IS NOT NULL AND validation_start <= validation_end)
    ),
    CHECK (
        (oos_start IS NULL AND oos_end IS NULL) OR
        (oos_start IS NOT NULL AND oos_end IS NOT NULL AND oos_start <= oos_end)
    ),
    CHECK (research_end IS NULL OR validation_start IS NULL OR research_end < validation_start),
    CHECK (validation_end IS NULL OR oos_start IS NULL OR validation_end < oos_start),
    CHECK (research_end IS NULL OR oos_start IS NULL OR research_end < oos_start)
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    migration_id VARCHAR NOT NULL UNIQUE,
    description VARCHAR NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_version (version, migration_id, description)
VALUES (1, '001_foundation_schema', 'Phase 0 foundation and governance')
ON CONFLICT DO NOTHING;

COMMIT;
