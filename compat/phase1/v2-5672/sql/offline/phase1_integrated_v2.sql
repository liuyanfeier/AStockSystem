CREATE TABLE p1_meta (key VARCHAR PRIMARY KEY, payload VARCHAR NOT NULL);
CREATE TABLE p1_plan (plan_hash VARCHAR PRIMARY KEY, payload VARCHAR NOT NULL);
CREATE TABLE p1_attempt (
    logical_id VARCHAR PRIMARY KEY, batch_hash VARCHAR NOT NULL,
    request VARCHAR NOT NULL, origin_id VARCHAR NOT NULL, object_id VARCHAR NOT NULL UNIQUE,
    claimed_at TIMESTAMPTZ NOT NULL, authorization_hash VARCHAR
);
CREATE TABLE p1_event (
    logical_id VARCHAR NOT NULL REFERENCES p1_attempt(logical_id), ordinal INTEGER NOT NULL,
    state VARCHAR NOT NULL CHECK (state IN ('CLAIMED','CALL_ENTERED','COMPLETE','RAW_RETAINED','FAILED','UNCERTAIN')),
    recorded_at TIMESTAMPTZ NOT NULL, payload VARCHAR NOT NULL,
    PRIMARY KEY (logical_id,ordinal)
);
CREATE TABLE p1_receipt (
    logical_id VARCHAR PRIMARY KEY REFERENCES p1_attempt(logical_id), object_id VARCHAR NOT NULL UNIQUE,
    manifest_hash VARCHAR NOT NULL, source_hash VARCHAR NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL, completeness VARCHAR NOT NULL
);
CREATE TABLE p1_fact (
    fact_hash VARCHAR PRIMARY KEY, dataset VARCHAR NOT NULL, domain VARCHAR NOT NULL,
    series_key VARCHAR NOT NULL, entity VARCHAR, event_date DATE,
    valid_from DATE, valid_to DATE, published_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ, retrieved_at TIMESTAMPTZ NOT NULL,
    precision VARCHAR NOT NULL, knowledge_basis VARCHAR NOT NULL,
    source_object VARCHAR NOT NULL, source_row INTEGER NOT NULL,
    payload VARCHAR NOT NULL, eligibility VARCHAR NOT NULL,
    CHECK(valid_to IS NULL OR valid_from IS NULL OR valid_to>valid_from),
    CHECK(available_at IS NULL OR published_at IS NULL OR available_at>=published_at)
);
CREATE TABLE p1_generation (
    generation_hash VARCHAR PRIMARY KEY, input_manifest VARCHAR NOT NULL,
    logical_content_hash VARCHAR NOT NULL, namespace VARCHAR NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE p1_lineage (
    generation_hash VARCHAR NOT NULL REFERENCES p1_generation(generation_hash),
    fact_hash VARCHAR NOT NULL REFERENCES p1_fact(fact_hash),
    PRIMARY KEY(generation_hash,fact_hash)
);
CREATE TABLE p1_quality (
    finding_hash VARCHAR PRIMARY KEY, dataset VARCHAR NOT NULL,
    entity VARCHAR, event_date DATE, reason VARCHAR NOT NULL,
    source_object VARCHAR NOT NULL, payload VARCHAR NOT NULL
);
CREATE TABLE p1_derivative_validation (
    validation_hash VARCHAR PRIMARY KEY, original_request_id VARCHAR NOT NULL,
    original_state VARCHAR NOT NULL, body_hash VARCHAR NOT NULL,
    source_hash VARCHAR NOT NULL, contract_hash VARCHAR NOT NULL,
    validated_at TIMESTAMPTZ NOT NULL, evidence VARCHAR NOT NULL,
    production_adopted BOOLEAN NOT NULL DEFAULT FALSE CHECK(NOT production_adopted)
);
CREATE VIEW p1_security_identifier_history AS SELECT
    json_extract_string(payload,'$.security_id') AS security_id,
    json_extract_string(payload,'$.episode_id') AS episode_id,
    json_extract_string(payload,'$.source') AS source,
    json_extract_string(payload,'$.identifier_type') AS identifier_type,
    json_extract_string(payload,'$.identifier') AS identifier,
    json_extract_string(payload,'$.exchange') AS exchange,
    valid_from,valid_to,published_at,available_at,retrieved_at,
    json_extract_string(payload,'$.evidence_source') AS evidence_source,
    fact_hash,source_object,source_row
    FROM p1_fact WHERE dataset='security_identifiers';
CREATE VIEW p1_listing_episode_history AS SELECT * FROM p1_fact WHERE dataset='listing_episodes';
CREATE VIEW p1_financial_vintage_history AS SELECT * FROM p1_fact WHERE domain='financial';
CREATE VIEW p1_industry_membership_history AS SELECT * FROM p1_fact WHERE dataset='industry_membership';
CREATE VIEW p1_market_rule_history AS SELECT * FROM p1_fact WHERE dataset='rule_history';

CREATE TABLE p1_authorization (authorization_hash VARCHAR PRIMARY KEY, plan_hash VARCHAR UNIQUE NOT NULL, payload VARCHAR NOT NULL);
