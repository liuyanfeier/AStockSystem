# Import atomicity and finite45 preview authorization

The user supplied the retained Import Atomicity and Finite45 Preview Prompt on
2026-10-04 and requested implementation if reasonable. The prompt matches the
independently reproduced P1 and authorizes one continuous repair/test/preview batch.
Clean starting SHA: `fd1d1b5638a0194ae30adcc59f06fc1ab4a25f62`.

Implement only the core importer transaction and persistent-order compatibility
fix, necessary regressions, a new unapproved finite45 version and fresh fixture-only
126-output transformation. Preserve v2 semantics, all existing SQL/contracts/DQ,
old approvals, original data and both failed stores. New source pins must identify
the changed implementation; old approvals do not authorize it for production.

Provider/document requests and original writes: zero. No calendar retry/reset,
133 replay, production identity/session approval, or Phase1C.2 work. Complete full
offline tests, preservation/secret/package checks, commit/push and exact-SHA CI;
deliver once as `IMPORT_ATOMICITY_AND_FINITE45_PREVIEW_REVIEW_READY`, then stop for
independent review. The calendar capture license remains pinned to its old SHA.
