-- Phase 1B: preserve both sides of the FK while rebuilding CHECK constraints.
-- Apply after 002. Transactional reruns preserve every existing row, including PROBE.
BEGIN TRANSACTION;
CREATE TEMP TABLE phase1b_runs_copy AS SELECT * FROM ingestion_run;
CREATE TEMP TABLE phase1b_objects_copy AS SELECT * FROM raw_object_manifest;
DROP TABLE raw_object_manifest;
DROP TABLE ingestion_run;
CREATE TABLE ingestion_run (
    run_id UUID PRIMARY KEY,
    source VARCHAR NOT NULL CHECK (source = 'tushare'),
    dataset VARCHAR NOT NULL CHECK (dataset IN ('stock_basic', 'trade_cal', 'daily', 'daily_basic', 'adj_factor', 'stk_limit', 'suspend_d', 'stock_st', 'index_basic', 'index_daily', 'index_classify', 'index_member_all')),
    mode VARCHAR NOT NULL CHECK (mode IN ('PROBE', 'AUDIT', 'SNAPSHOT', 'INCREMENTAL', 'BACKFILL')),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status VARCHAR NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')),
    code_commit VARCHAR NOT NULL CHECK (regexp_full_match(code_commit, '[0-9a-f]{40}')),
    config_hash VARCHAR NOT NULL CHECK (regexp_full_match(config_hash, '[0-9a-f]{64}')),
    provider_client_version VARCHAR NOT NULL CHECK (regexp_full_match(provider_client_version, '[0-9]+\.[0-9]+\.[0-9]+')),
    requested_start DATE,
    requested_end DATE,
    request_count BIGINT NOT NULL DEFAULT 0 CHECK (request_count >= 0),
    row_count BIGINT NOT NULL DEFAULT 0 CHECK (row_count >= 0),
    raw_object_count BIGINT NOT NULL DEFAULT 0 CHECK (raw_object_count >= 0),
    error_category VARCHAR CHECK (error_category IN ('TRANSPORT', 'REDIRECT', 'AUTH', 'PERMISSION', 'PROVIDER', 'INVALID_RESPONSE')),
    error_http_status INTEGER CHECK (error_http_status BETWEEN 100 AND 599),
    error_provider_code BIGINT,
    UNIQUE (run_id, dataset),
    CHECK (finished_at IS NULL OR finished_at >= started_at),
    CHECK ((status = 'RUNNING' AND finished_at IS NULL) OR (status <> 'RUNNING' AND finished_at IS NOT NULL)),
    CHECK (requested_start IS NULL OR requested_end IS NULL OR requested_start <= requested_end),
    CHECK (error_category IS NOT NULL OR (error_http_status IS NULL AND error_provider_code IS NULL))
);

CREATE TABLE raw_object_manifest (
    object_id UUID PRIMARY KEY,
    run_id UUID NOT NULL,
    dataset VARCHAR NOT NULL,
    relative_path VARCHAR NOT NULL UNIQUE,
    sha256 VARCHAR NOT NULL CHECK (regexp_full_match(sha256, '[0-9a-f]{64}')),
    retrieved_at TIMESTAMPTZ NOT NULL,
    row_count BIGINT NOT NULL CHECK (row_count >= 0),
    schema_hash VARCHAR NOT NULL CHECK (regexp_full_match(schema_hash, '[0-9a-f]{64}')),
    min_event_date DATE,
    max_event_date DATE,
    request_params JSON NOT NULL,
    FOREIGN KEY (run_id, dataset) REFERENCES ingestion_run (run_id, dataset),
    CHECK (regexp_full_match(relative_path,
        'data/raw/tushare/' || dataset || '/run_id=' || CAST(run_id AS VARCHAR) || '/part-[0-9]{3}\.parquet')),
    CHECK ((min_event_date IS NULL AND max_event_date IS NULL) OR
           (min_event_date IS NOT NULL AND max_event_date IS NOT NULL AND min_event_date <= max_event_date)),
    CHECK (json_type(request_params) = 'OBJECT'),
    CHECK (len(json_keys(request_params)) = len(list_distinct(json_keys(request_params)))),
    CHECK (NOT list_contains(json_keys(request_params), 'market') OR
           regexp_full_match(json_extract_string(request_params, '$.market'), 'MSCI|CSI|SSE|SZSE|CICC|SW|OTH')),
    CHECK (NOT list_contains(json_keys(request_params), 'market') OR json_type(request_params, '$.market') = 'VARCHAR'),
    CHECK (list_has_all(['ts_code', 'trade_date', 'start_date', 'end_date', 'exchange',
                        'market', 'list_status', 'src', 'level', 'is_new', 'l1_code', 'l2_code', 'l3_code'], json_keys(request_params))),
    CHECK (NOT list_contains(json_keys(request_params), 'ts_code') OR
           regexp_full_match(json_extract_string(request_params, '$.ts_code'), '[0-9]{6}\.(SH|SZ|BJ|SI|CSI|WI)')),
    CHECK (NOT list_contains(json_keys(request_params), 'trade_date') OR
           regexp_full_match(json_extract_string(request_params, '$.trade_date'), '[0-9]{4}-[0-9]{2}-[0-9]{2}')),
    CHECK (NOT list_contains(json_keys(request_params), 'start_date') OR
           regexp_full_match(json_extract_string(request_params, '$.start_date'), '[0-9]{4}-[0-9]{2}-[0-9]{2}')),
    CHECK (NOT list_contains(json_keys(request_params), 'end_date') OR
           regexp_full_match(json_extract_string(request_params, '$.end_date'), '[0-9]{4}-[0-9]{2}-[0-9]{2}')),
    CHECK (NOT list_contains(json_keys(request_params), 'exchange') OR
           regexp_full_match(json_extract_string(request_params, '$.exchange'), 'SSE|SZSE|BSE')),
    CHECK (NOT list_contains(json_keys(request_params), 'list_status') OR
           regexp_full_match(json_extract_string(request_params, '$.list_status'), 'L|D|P|G|UN')),
    CHECK (NOT list_contains(json_keys(request_params), 'src') OR
           regexp_full_match(json_extract_string(request_params, '$.src'), 'SW2014|SW2021')),
    CHECK (NOT list_contains(json_keys(request_params), 'level') OR
           regexp_full_match(json_extract_string(request_params, '$.level'), 'L1|L2|L3')),
    CHECK (NOT list_contains(json_keys(request_params), 'is_new') OR
           regexp_full_match(json_extract_string(request_params, '$.is_new'), 'Y|N')),
    CHECK (NOT list_contains(json_keys(request_params), 'l1_code') OR
           regexp_full_match(json_extract_string(request_params, '$.l1_code'), '[0-9]{6}\.SI')),
    CHECK (NOT list_contains(json_keys(request_params), 'l2_code') OR
           regexp_full_match(json_extract_string(request_params, '$.l2_code'), '[0-9]{6}\.SI')),
    CHECK (NOT list_contains(json_keys(request_params), 'l3_code') OR
           regexp_full_match(json_extract_string(request_params, '$.l3_code'), '[0-9]{6}\.SI')),
    CHECK (NOT list_contains(json_keys(request_params), 'ts_code') OR json_type(request_params, '$.ts_code') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'trade_date') OR json_type(request_params, '$.trade_date') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'start_date') OR json_type(request_params, '$.start_date') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'end_date') OR json_type(request_params, '$.end_date') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'exchange') OR json_type(request_params, '$.exchange') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'list_status') OR json_type(request_params, '$.list_status') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'src') OR json_type(request_params, '$.src') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'level') OR json_type(request_params, '$.level') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'is_new') OR json_type(request_params, '$.is_new') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'l1_code') OR json_type(request_params, '$.l1_code') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'l2_code') OR json_type(request_params, '$.l2_code') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'l3_code') OR json_type(request_params, '$.l3_code') = 'VARCHAR'),
    CHECK (NOT list_contains(json_keys(request_params), 'trade_date') OR try_cast(json_extract_string(request_params, '$.trade_date') AS DATE) IS NOT NULL),
    CHECK (NOT list_contains(json_keys(request_params), 'start_date') OR try_cast(json_extract_string(request_params, '$.start_date') AS DATE) IS NOT NULL),
    CHECK (NOT list_contains(json_keys(request_params), 'end_date') OR try_cast(json_extract_string(request_params, '$.end_date') AS DATE) IS NOT NULL),
    CHECK (NOT list_has_all(json_keys(request_params), ['start_date', 'end_date']) OR
           try_cast(json_extract_string(request_params, '$.start_date') AS DATE) <= try_cast(json_extract_string(request_params, '$.end_date') AS DATE))
);
INSERT INTO ingestion_run SELECT * FROM phase1b_runs_copy;
INSERT INTO raw_object_manifest SELECT * FROM phase1b_objects_copy;
DROP TABLE phase1b_objects_copy;
DROP TABLE phase1b_runs_copy;
INSERT INTO schema_version (version, migration_id, description)
VALUES (3, '003_probe_mode', 'Phase 1B probe mode and permission errors')
ON CONFLICT DO NOTHING;
COMMIT;
