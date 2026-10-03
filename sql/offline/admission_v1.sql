-- SYNTHETIC ONLY; not a warehouse migration, no schema_version write.
CREATE TABLE offline_plan (
    plan_id VARCHAR PRIMARY KEY, created_at TIMESTAMPTZ NOT NULL,
    execution_license BOOLEAN NOT NULL CHECK (execution_license=false)
);
CREATE TABLE offline_attempt_event (
    plan_id VARCHAR REFERENCES offline_plan(plan_id),
    ordinal INTEGER NOT NULL, state VARCHAR NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL, payload JSON NOT NULL,
    PRIMARY KEY(plan_id,ordinal),
    CHECK(state IN ('RUNNING','CALL_ENTERED','UNCERTAIN','COMPLETE'))
);
CREATE TABLE offline_raw_manifest (
    plan_id VARCHAR PRIMARY KEY REFERENCES offline_plan(plan_id),
    object_id UUID UNIQUE NOT NULL, relative_path VARCHAR NOT NULL,
    bytes_sha256 VARCHAR NOT NULL, retrieved_at TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL, verified_at TIMESTAMPTZ NOT NULL,
    CHECK(available_at>=retrieved_at AND verified_at>=available_at)
);
CREATE TABLE offline_generation (
    manifest_hash VARCHAR PRIMARY KEY, member_count BIGINT NOT NULL CHECK(member_count>0),
    execution_license BOOLEAN NOT NULL CHECK(execution_license=false),
    complete_hash VARCHAR
);
CREATE TABLE offline_member (
    manifest_hash VARCHAR REFERENCES offline_generation(manifest_hash),
    member_id VARCHAR NOT NULL, dataset VARCHAR NOT NULL, event_date DATE NOT NULL,
    source_hash VARCHAR NOT NULL, source_rows BIGINT NOT NULL, row_hash VARCHAR NOT NULL,
    PRIMARY KEY(manifest_hash,member_id)
);
CREATE TABLE offline_output (
    manifest_hash VARCHAR NOT NULL, member_id VARCHAR NOT NULL,
    bytes_sha256 VARCHAR NOT NULL, sidecar_sha256 VARCHAR NOT NULL,
    PRIMARY KEY(manifest_hash,member_id),
    FOREIGN KEY(manifest_hash,member_id) REFERENCES offline_member(manifest_hash,member_id)
);
