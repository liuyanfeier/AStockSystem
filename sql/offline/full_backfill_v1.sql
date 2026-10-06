-- Independent capture store only. Never migrate original warehouse.
CREATE TABLE backfill_pin (id INTEGER PRIMARY KEY CHECK(id=1), payload VARCHAR NOT NULL);
CREATE TABLE backfill_member (member_id VARCHAR PRIMARY KEY, object_id UUID UNIQUE NOT NULL,
 created_at VARCHAR NOT NULL, payload VARCHAR NOT NULL);
CREATE TABLE backfill_event (member_id VARCHAR REFERENCES backfill_member(member_id), ordinal INTEGER,
 state VARCHAR CHECK(state IN ('CLAIMED','CALL_ENTERED','COMPLETE','FAILED','UNCERTAIN')),
 recorded_at VARCHAR NOT NULL, payload VARCHAR NOT NULL, PRIMARY KEY(member_id,ordinal));
CREATE TABLE backfill_receipt (member_id VARCHAR PRIMARY KEY REFERENCES backfill_member(member_id),
 object_id UUID UNIQUE NOT NULL, manifest_hash VARCHAR NOT NULL, source_hash VARCHAR NOT NULL,
 completed_at VARCHAR NOT NULL);
