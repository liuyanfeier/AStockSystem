-- Explicit R2 schema owner only; no automatic deployment.
CREATE TABLE derivation_context (
    context_id UUID PRIMARY KEY,
    context_hash VARCHAR NOT NULL UNIQUE,
    payload JSON NOT NULL,
    fixture_only BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE derivation_input (
    context_id UUID NOT NULL REFERENCES derivation_context(context_id),
    request_id VARCHAR NOT NULL,
    raw_object_id UUID NOT NULL REFERENCES raw_object_manifest(object_id),
    dataset VARCHAR NOT NULL,
    raw_hash VARCHAR NOT NULL,
    raw_schema_hash VARCHAR NOT NULL,
    row_count BIGINT NOT NULL CHECK (row_count>=0),
    is_output BOOLEAN NOT NULL,
    PRIMARY KEY(context_id,request_id),
    UNIQUE(context_id,raw_object_id)
);
CREATE TABLE derivation_resolver_snapshot (
    context_id UUID PRIMARY KEY REFERENCES derivation_context(context_id),
    resolver_hash VARCHAR NOT NULL,
    payload JSON NOT NULL
);
CREATE TABLE derivation_generation (
    generation_id UUID PRIMARY KEY,
    context_id UUID NOT NULL REFERENCES derivation_context(context_id),
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(context_id,generation_id)
);
CREATE TABLE derivation_generation_event (
    generation_id UUID NOT NULL REFERENCES derivation_generation(generation_id),
    sequence INTEGER NOT NULL CHECK (sequence>=0),
    state VARCHAR NOT NULL CHECK (state IN ('PLANNED','BUILDING','COMPLETE','BLOCKED')),
    occurred_at TIMESTAMPTZ NOT NULL,
    detail JSON NOT NULL,
    PRIMARY KEY(generation_id,sequence)
);
CREATE TABLE derivation_output (
    context_id UUID NOT NULL,
    generation_id UUID NOT NULL,
    request_id VARCHAR NOT NULL,
    relative_path VARCHAR NOT NULL UNIQUE,
    file_hash VARCHAR NOT NULL,
    logical_hash VARCHAR NOT NULL,
    lineage_hash VARCHAR NOT NULL,
    schema_hash VARCHAR NOT NULL,
    resolved_count BIGINT NOT NULL CHECK (resolved_count>=0),
    quarantine_count BIGINT NOT NULL CHECK (quarantine_count>=0),
    registered_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY(generation_id,request_id),
    FOREIGN KEY(context_id,generation_id) REFERENCES derivation_generation(context_id,generation_id),
    FOREIGN KEY(context_id,request_id) REFERENCES derivation_input(context_id,request_id)
);
CREATE TABLE derivation_row_quarantine (
    generation_id UUID NOT NULL,
    request_id VARCHAR NOT NULL,
    raw_object_id UUID NOT NULL REFERENCES raw_object_manifest(object_id),
    raw_row_number BIGINT NOT NULL CHECK (raw_row_number>=0),
    event_date DATE NOT NULL,
    provider_identifier VARCHAR,
    reason VARCHAR NOT NULL,
    PRIMARY KEY(generation_id,raw_object_id,raw_row_number),
    FOREIGN KEY(generation_id,request_id) REFERENCES derivation_output(generation_id,request_id)
);
CREATE TABLE derivation_complete_manifest (
    generation_id UUID PRIMARY KEY REFERENCES derivation_generation(generation_id),
    manifest JSON NOT NULL,
    manifest_hash VARCHAR NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL
);
