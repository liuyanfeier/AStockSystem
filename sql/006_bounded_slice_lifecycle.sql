-- Phase 1C.1 append-only governance. No changes to earlier migrations.
BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS slice_batch (
    batch_id UUID PRIMARY KEY,
    phase VARCHAR NOT NULL CHECK (phase='1C.1'),
    plan_hash VARCHAR NOT NULL CHECK (regexp_full_match(plan_hash,'[0-9a-f]{64}')),
    identity_snapshot_hash VARCHAR NOT NULL CHECK (regexp_full_match(identity_snapshot_hash,'[0-9a-f]{64}')),
    code_commit VARCHAR NOT NULL CHECK (regexp_full_match(code_commit,'[0-9a-f]{40}')),
    knowledge_as_of TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status VARCHAR NOT NULL CHECK (status IN ('PLANNED','RUNNING','INTERRUPTED','CAPTURED','BLOCKED','CURATED','REVIEWED')),
    request_budget INTEGER NOT NULL CHECK (request_budget BETWEEN 1 AND 133),
    CHECK (finished_at IS NULL OR finished_at>=started_at)
);
CREATE TABLE IF NOT EXISTS slice_request (
    batch_id UUID NOT NULL REFERENCES slice_batch(batch_id),
    ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 132),
    request_id VARCHAR NOT NULL,
    slice_name VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL CHECK (dataset IN ('trade_cal','daily','daily_basic','adj_factor','stk_limit','stock_st','suspend_d')),
    contract_catalog VARCHAR NOT NULL CHECK (contract_catalog='v2'),
    contract_hash VARCHAR NOT NULL CHECK (regexp_full_match(contract_hash,'[0-9a-f]{64}')),
    request_params JSON NOT NULL,
    run_id UUID NOT NULL UNIQUE REFERENCES ingestion_run(run_id),
    status VARCHAR NOT NULL CHECK (status IN ('PENDING','IN_FLIGHT','COMPLETE','FAILED','UNCERTAIN')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 1),
    object_id UUID UNIQUE,
    failure_code VARCHAR CHECK (failure_code IN ('TRANSPORT','REDIRECT','AUTH','PERMISSION','PROVIDER','INVALID_RESPONSE','ROW_CAP','SCHEMA','LINEAGE','UNCERTAIN_CAPTURE','CALENDAR')),
    PRIMARY KEY (batch_id,ordinal),
    UNIQUE (batch_id,request_id),
    CHECK (json_type(request_params)='OBJECT'),
    CHECK (list_has_all(['trade_date','start_date','end_date','exchange'],json_keys(request_params))),
    CHECK ((status='PENDING' AND attempts=0 AND object_id IS NULL) OR status<>'PENDING'),
    CHECK (status<>'COMPLETE' OR (attempts=1 AND object_id IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS slice_curated_binding (
    batch_id UUID NOT NULL REFERENCES slice_batch(batch_id),
    request_id VARCHAR NOT NULL,
    generation INTEGER NOT NULL CHECK (generation>=0),
    raw_object_id UUID NOT NULL REFERENCES raw_object_manifest(object_id),
    curated_object_id UUID NOT NULL UNIQUE REFERENCES curated_object_manifest(object_id),
    logical_hash VARCHAR NOT NULL CHECK (regexp_full_match(logical_hash,'[0-9a-f]{64}')),
    output_name VARCHAR NOT NULL,
    PRIMARY KEY (batch_id,request_id,generation)
);
INSERT INTO schema_version(version,migration_id,description)
VALUES (6,'006_bounded_slice_lifecycle','Bounded historical slices, recovery and logical lineage')
ON CONFLICT DO NOTHING;
COMMIT;
