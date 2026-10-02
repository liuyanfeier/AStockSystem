-- Append-only through the owner API, not an arbitrary-SQL immutability claim.
CREATE TABLE reconstruction_quality_audit (
    audit_id UUID PRIMARY KEY,
    context_id UUID NOT NULL,
    generation_id UUID NOT NULL,
    policy_hash VARCHAR NOT NULL,
    implementation_sha VARCHAR NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    finding_set_hash VARCHAR NOT NULL,
    local_status VARCHAR NOT NULL CHECK (local_status IN ('PASS','PARTIAL','BLOCKED')),
    batch_gate_status VARCHAR NOT NULL CHECK (batch_gate_status IN ('PASS','PARTIAL','BLOCKED')),
    supersedes_audit_id UUID REFERENCES reconstruction_quality_audit(audit_id),
    detail JSON NOT NULL,
    FOREIGN KEY(context_id,generation_id) REFERENCES derivation_generation(context_id,generation_id)
);
CREATE TABLE reconstruction_finding_observation (
    observation_id UUID PRIMARY KEY,
    audit_id UUID NOT NULL REFERENCES reconstruction_quality_audit(audit_id),
    finding_key VARCHAR NOT NULL,
    raw_object_id UUID REFERENCES raw_object_manifest(object_id),
    raw_row_number BIGINT CHECK (raw_row_number>=0),
    episode_id UUID REFERENCES listing_episode(episode_id),
    payload JSON NOT NULL,
    UNIQUE(audit_id,finding_key),
    CHECK ((raw_object_id IS NULL AND raw_row_number IS NULL) OR
           (raw_object_id IS NOT NULL AND raw_row_number IS NOT NULL)),
    CHECK (raw_object_id IS NOT NULL OR episode_id IS NOT NULL)
);
CREATE TABLE reconstruction_output_quality (
    audit_id UUID NOT NULL REFERENCES reconstruction_quality_audit(audit_id),
    generation_id UUID NOT NULL,
    request_id VARCHAR NOT NULL,
    local_status VARCHAR NOT NULL CHECK (local_status IN ('PASS','PARTIAL','BLOCKED')),
    finding_set_hash VARCHAR NOT NULL,
    PRIMARY KEY(audit_id,request_id),
    FOREIGN KEY(generation_id,request_id) REFERENCES derivation_output(generation_id,request_id)
);
