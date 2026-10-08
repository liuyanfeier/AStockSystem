-- Independent v2 capture only. Reject v1 stores; never migrate original warehouse.
CREATE TABLE backfill_pin (plan_hash VARCHAR PRIMARY KEY, payload VARCHAR NOT NULL);
CREATE TABLE backfill_authorization (plan_hash VARCHAR PRIMARY KEY REFERENCES backfill_pin(plan_hash),
 approval_hash VARCHAR NOT NULL, human_hash VARCHAR NOT NULL, approval VARCHAR NOT NULL, human VARCHAR NOT NULL);
CREATE TABLE backfill_plan_member (plan_hash VARCHAR REFERENCES backfill_pin(plan_hash),
 member_id VARCHAR NOT NULL, payload VARCHAR NOT NULL, PRIMARY KEY(plan_hash,member_id));
CREATE TABLE backfill_member (member_id VARCHAR PRIMARY KEY, object_id UUID UNIQUE NOT NULL,
 created_at VARCHAR NOT NULL, payload VARCHAR NOT NULL, origin_plan VARCHAR NOT NULL REFERENCES backfill_pin(plan_hash));
CREATE TABLE backfill_event (member_id VARCHAR REFERENCES backfill_member(member_id), ordinal INTEGER,
 state VARCHAR CHECK(state IN ('CLAIMED','CALL_ENTERED','COMPLETE','FAILED','UNCERTAIN')),
 recorded_at VARCHAR NOT NULL, payload VARCHAR NOT NULL, PRIMARY KEY(member_id,ordinal));
CREATE TABLE backfill_receipt (member_id VARCHAR PRIMARY KEY REFERENCES backfill_member(member_id),
 object_id UUID UNIQUE NOT NULL, manifest_hash VARCHAR NOT NULL, source_hash VARCHAR NOT NULL,
 completed_at VARCHAR NOT NULL);
