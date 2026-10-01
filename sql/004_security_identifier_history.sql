-- Phase 1B.1 governance only. No real/guessed identity mappings are seeded.
-- Cross-row overlap checks and knowledge selection live in astock.data.identity.
BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS security_identifier_history (
    security_id VARCHAR NOT NULL CHECK (length(trim(security_id)) > 0),
    source VARCHAR NOT NULL CHECK (length(trim(source)) > 0),
    identifier_type VARCHAR NOT NULL CHECK (length(trim(identifier_type)) > 0),
    identifier VARCHAR NOT NULL CHECK (length(trim(identifier)) > 0),
    exchange VARCHAR NOT NULL CHECK (length(trim(exchange)) > 0),
    valid_from DATE NOT NULL,
    valid_to DATE,
    published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    evidence_source VARCHAR NOT NULL CHECK (length(trim(evidence_source)) > 0),
    PRIMARY KEY (source, identifier_type, identifier, exchange, valid_from, available_at),
    CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (published_at IS NULL OR available_at >= published_at),
    -- Only OBSERVED_CAPTURE knowledge is supported in this minimum model.
    CHECK (available_at >= retrieved_at)
);
INSERT INTO schema_version (version, migration_id, description)
VALUES (4, '004_security_identifier_history', 'Phase 1B.1 source-scoped identity governance')
ON CONFLICT DO NOTHING;
COMMIT;
