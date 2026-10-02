-- Explicit upgrade owner supplies the transaction and schema_version insertion.
-- Never automatically apply this to a historical warehouse on connection open.
CREATE TABLE slice_receipt_completion_binding (
    batch_id UUID NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 0 AND 132),
    request_id VARCHAR NOT NULL,
    run_id UUID NOT NULL UNIQUE REFERENCES ingestion_run(run_id),
    object_id UUID NOT NULL UNIQUE REFERENCES raw_object_manifest(object_id),
    plan_hash VARCHAR NOT NULL CHECK (regexp_full_match(plan_hash,'[0-9a-f]{64}')),
    contract_hash VARCHAR NOT NULL CHECK (regexp_full_match(contract_hash,'[0-9a-f]{64}')),
    receipt_hash VARCHAR NOT NULL CHECK (regexp_full_match(receipt_hash,'[0-9a-f]{64}')),
    evidence_hash VARCHAR NOT NULL CHECK (regexp_full_match(evidence_hash,'[0-9a-f]{64}')),
    validator_version VARCHAR NOT NULL CHECK (validator_version='R1_EXACT_RECEIPT_V1'),
    verification_code_commit VARCHAR NOT NULL CHECK (regexp_full_match(verification_code_commit,'[0-9a-f]{40}')),
    validated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (batch_id,ordinal),
    FOREIGN KEY (batch_id,ordinal) REFERENCES slice_request(batch_id,ordinal),
    FOREIGN KEY (batch_id,request_id) REFERENCES slice_request(batch_id,request_id)
);
CREATE TABLE slice_receipt_validation_audit (
    audit_id UUID PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES slice_batch(batch_id),
    ordinal INTEGER CHECK (ordinal BETWEEN 0 AND 132),
    purpose VARCHAR NOT NULL CHECK (purpose IN ('LEGACY_PREFLIGHT','UPGRADE','VERIFY','FINALIZE','OPERATION_BLOCK')),
    verdict VARCHAR NOT NULL CHECK (verdict IN ('VALID','BLOCKED')),
    reason_code VARCHAR NOT NULL CHECK (length(reason_code)>0),
    validator_version VARCHAR NOT NULL CHECK (validator_version='R1_EXACT_RECEIPT_V1'),
    verification_code_commit VARCHAR NOT NULL CHECK (regexp_full_match(verification_code_commit,'[0-9a-f]{40}')),
    validated_at TIMESTAMPTZ NOT NULL,
    evidence_hash VARCHAR CHECK (regexp_full_match(evidence_hash,'[0-9a-f]{64}')),
    checked_count INTEGER NOT NULL CHECK (checked_count>=0)
);
