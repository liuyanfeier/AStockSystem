-- Explicit owner supplies transaction/approval; never run on original during R2-A.
CREATE TABLE listing_episode (
    episode_id UUID PRIMARY KEY,
    security_id VARCHAR NOT NULL,
    venue VARCHAR NOT NULL CHECK (venue IN ('SSE','SZSE','BSE','OTHER')),
    asset_type VARCHAR NOT NULL CHECK (asset_type IN ('STK','CDR','BOND','OTHER','UNKNOWN')),
    valid_from DATE NOT NULL,
    valid_to DATE CHECK (valid_to IS NULL OR valid_to>valid_from),
    last_trading_date DATE,
    provider_delist_date DATE,
    published_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL CHECK (available_at>=retrieved_at),
    evidence_ids JSON NOT NULL,
    approval_ref VARCHAR NOT NULL,
    CHECK (published_at IS NULL OR available_at>=published_at)
);
CREATE TABLE official_exchange_code (
    code_id UUID PRIMARY KEY,
    episode_id UUID NOT NULL REFERENCES listing_episode(episode_id),
    identifier_type VARCHAR NOT NULL CHECK (identifier_type='EXCHANGE_CODE'),
    identifier VARCHAR NOT NULL CHECK (regexp_full_match(identifier,'[0-9]{6}\.(SH|SZ|BJ)')),
    valid_from DATE NOT NULL,
    valid_to DATE CHECK (valid_to IS NULL OR valid_to>valid_from),
    available_at TIMESTAMPTZ NOT NULL,
    evidence_ids JSON NOT NULL,
    approval_ref VARCHAR NOT NULL
);
CREATE TABLE provider_native_binding (
    binding_id UUID PRIMARY KEY,
    binding_version INTEGER NOT NULL CHECK (binding_version>=1),
    provider VARCHAR NOT NULL CHECK (provider='tushare'),
    dataset VARCHAR NOT NULL CHECK (dataset IN ('daily','daily_basic','adj_factor','stk_limit','stock_st','suspend_d')),
    native_identifier VARCHAR NOT NULL CHECK (length(trim(native_identifier))>0),
    episode_id UUID NOT NULL REFERENCES listing_episode(episode_id),
    representation_kind VARCHAR NOT NULL CHECK (representation_kind IN ('EVENT_NATIVE','RETROSPECTIVE','UNKNOWN')),
    first_observed_at TIMESTAMPTZ NOT NULL,
    decision_at TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    evidence_ids JSON NOT NULL,
    decision_status VARCHAR NOT NULL CHECK (decision_status IN ('PROPOSED','APPROVED','EVIDENCE_REQUIRED','CONFLICT','OUT_OF_SCOPE')),
    approval_ref VARCHAR,
    supersedes_binding_id UUID REFERENCES provider_native_binding(binding_id),
    knowledge_basis VARCHAR NOT NULL CHECK (knowledge_basis='CURRENT_RECONSTRUCTION'),
    CHECK (first_observed_at<=decision_at AND decision_at<=available_at),
    CHECK (decision_status<>'APPROVED' OR (approval_ref IS NOT NULL AND representation_kind<>'UNKNOWN'))
);
CREATE TABLE provider_binding_observation (
    binding_id UUID NOT NULL REFERENCES provider_native_binding(binding_id),
    raw_object_id UUID NOT NULL REFERENCES raw_object_manifest(object_id),
    raw_row_number BIGINT NOT NULL CHECK (raw_row_number>=0),
    event_date DATE NOT NULL,
    PRIMARY KEY (binding_id,raw_object_id,raw_row_number,event_date)
);
