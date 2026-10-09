-- Additive isolated-copy protocol. All six v2.1 historical tables stay immutable.
CREATE TABLE continuation_baseline (baseline_hash VARCHAR PRIMARY KEY, payload VARCHAR NOT NULL);
CREATE TABLE continuation_authorization (authorization_id VARCHAR PRIMARY KEY,
 application VARCHAR NOT NULL, review VARCHAR NOT NULL, human VARCHAR NOT NULL,
 registered_at VARCHAR NOT NULL);
CREATE TABLE continuation_attempt (member_id VARCHAR PRIMARY KEY REFERENCES backfill_member(member_id),
 object_id UUID UNIQUE NOT NULL, origin_plan VARCHAR NOT NULL,
 authorization_id VARCHAR NOT NULL REFERENCES continuation_authorization(authorization_id),
 claimed_at VARCHAR NOT NULL);
CREATE TABLE continuation_event (member_id VARCHAR REFERENCES continuation_attempt(member_id),
 ordinal INTEGER NOT NULL, state VARCHAR NOT NULL CHECK(state IN
 ('CLAIMED','CALL_ENTERED','COMPLETE','RAW_RETAINED','FAILED','UNCERTAIN')),
 recorded_at VARCHAR NOT NULL,payload VARCHAR NOT NULL,PRIMARY KEY(member_id,ordinal));
CREATE TABLE continuation_receipt (member_id VARCHAR PRIMARY KEY REFERENCES continuation_attempt(member_id),
 manifest_hash VARCHAR NOT NULL,source_hash VARCHAR NOT NULL,completed_at VARCHAR NOT NULL,
 completeness VARCHAR NOT NULL CHECK(completeness IN ('CONTRACT_AND_WINDOW','RAW_UNCERTIFIED')));
