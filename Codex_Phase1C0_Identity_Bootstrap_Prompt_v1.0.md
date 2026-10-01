# Codex Task — Phase 1C.0 Identity Bootstrap + Contract v2 + Curation Governance v1.0

Base: current reviewed `main` after Phase 1B.1.

This task is **Phase 1C.0 only**.

Do NOT begin historical full backfill.  
Do NOT download 2013-present daily history.  
Do NOT implement strategy, signal, backtest, portfolio, broker or order code.

Read first:

- `AGENTS.md`
- `docs/data_contract.md`
- `docs/data_dictionary.md`
- `docs/security_identifier_history.md`
- `docs/reviews/2026-10-01-phase1b-review.md`
- `docs/reviews/2026-10-01-phase1b1-identity-review.md`
- `AStockSystem_Phase1C_Core_Market_Data_Foundation_Design_v1.0.md` if present

## 1. Update phase scope

Update AGENTS.md minimally:

- Phase 1B.1 accepted;
- Phase 1C.0 permits identity bootstrap, contract v2, curation governance and bounded BSE mapping evidence only;
- no Phase 1C.1/1C.2 backfill yet.

Do not rewrite historical review files.

## 2. Preserve contract v1

`config/contracts/v1/` is immutable historical probe configuration.

Do not edit v1 files.

Extend the loader so callers explicitly request a catalog version.

Production code must never silently select “latest”.

Existing Phase 1A/1B tests must continue to load v1 exactly.

## 3. Create contract catalog v2

Create `config/contracts/v2/` for:

- stock_basic
- bse_mapping
- trade_cal
- daily
- daily_basic
- adj_factor
- stk_limit
- stock_st
- suspend_d

### stock_basic v2 required fields

- ts_code
- symbol
- name
- fullname
- market
- exchange
- curr_type
- list_status
- list_date
- delist_date

Do not add current `industry`, `area`, `act_name`, `act_ent_type`, or `is_hs` as historical research fields.

### daily v2

Include Phase 1B fields plus:

- ah_vol
- ah_amount

Document that Tushare currently says these fields start on 2026-07-06 and historical nulls are valid.

### daily_basic v2

Request:

- ts_code
- trade_date
- close
- turnover_rate
- turnover_rate_f
- volume_ratio
- pe
- pe_ttm
- pb
- ps
- ps_ttm
- dv_ratio
- dv_ttm
- total_share
- float_share
- free_share
- total_mv
- circ_mv
- limit_status

### bse_mapping v2

Endpoint `bse_mapping`.

Fields:

- name
- o_code
- n_code
- list_date

Use current official Tushare documentation URL.

Do not infer switch dates from this endpoint.

## 4. Add typed curation specs

Create `config/curation/v1/`.

At minimum specs for:

- daily
- daily_basic
- adj_factor
- stk_limit
- stock_st
- suspend_d

A curation spec must declare:

- source contract catalog/version
- source column
- target column
- logical target type
- nullable policy
- unit
- identity requirement
- research usage class

Do not use PyArrow empty-array inference as the curated schema definition.

Names with provider units should become explicit, e.g.:

- `vol` → `volume_hands`
- `amount` → `amount_cny_thousand`
- `total_share` → `total_share_10k`
- `total_mv` → `total_mv_10k_cny`
- turnover/dividend values should be explicitly `_pct` where applicable.

Do not round values.

## 5. Phase 1C usage classes

Represent/document at least:

- daily: `SIGNAL_ELIGIBLE_NEXT_SESSION`
- daily_basic: `CURRENT_RECONSTRUCTION`
- adj_factor: `AUDIT_RECONSTRUCTION_ONLY`
- stk_limit: `EXECUTION_CONSTRAINT_ONLY`
- suspend_d: `EXECUTION_FACT_ONLY`
- stock_st: `UNIVERSE_RISK_STATE_ONLY`

Do NOT mark historical PE/PB/PS/dividend-yield fields as strict PIT alpha-ready.

## 6. Migration 005 — governance only

Create a new migration. Do not rewrite 001–004.

It may rebuild lineage CHECK constraints safely if required to admit `bse_mapping`, but must preserve every existing Phase 1B row/manifests.

Add governance tables:

### security_venue_history

Fields must support:

- security_id
- venue
- effective_from
- effective_to
- provider_list_date
- provider_delist_date
- source
- available_at
- retrieved_at
- evidence_source

Use half-open effective intervals where end is known.

### curation_run

At least:

- curation_run_id
- dataset
- partition_key
- started_at
- finished_at
- status
- code_commit
- config_hash
- input_manifest_hash
- identity_snapshot_hash
- row_count
- resolved_count
- quarantined_count

### curated_object_manifest

At least:

- object_id
- curation_run_id
- relative_path
- sha256
- schema_hash
- row_count
- min_event_date
- max_event_date

### identity_quarantine

At least:

- quarantine_id
- dataset
- provider_identifier
- event_date
- reason
- raw_object_id
- curation_run_id
- first_seen_at

Reasons must support:

- NO_IDENTIFIER_MAPPING
- AMBIGUOUS_IDENTIFIER
- NON_NORMALIZED_IDENTIFIER
- OUTSIDE_IDENTIFIER_INTERVAL
- PRE_BSE_LEGACY
- ASSET_OUT_OF_SCOPE

### dataset_date_audit

At least:

- dataset
- trade_date
- curation_run_id
- provider_rows
- resolved_rows
- quarantined_rows
- duplicate_count
- cap_hit
- status
- safe structured details

No market row table is required yet.

## 7. Deterministic security_id allocator

Implement a small, explicit allocator.

Use a fixed UUID5 namespace committed in code/config.

Seed material:

`exchange | identity_anchor_identifier | provider_list_date`

Rules:

### SSE/SZSE
- normalized native code
- unique listing episode
- no overlap/conflict
- anchor = provider code

### BSE with official old/new mapping
- anchor = official OLD code
- old and new identifiers share one security_id

### Unresolved/non-normalized
- quarantine
- no guessed security_id

Names must never determine equality.

Once a real security_id has been admitted locally, future provider metadata changes must not silently recompute it.

Add tests for deterministic rebuild and code reuse.

## 8. BSE public-authority audit

Phase 1C.0 may make only a bounded identity-related live request:

- one Tushare `bse_mapping` capture.

It may also fetch public BSE evidence without any credential:

- https://www.bse.cn/service/code_mapping.html
- https://www.bse.cn/important_news/200025487.html
- https://www.bse.cn/important_news/200025603.html
- https://www.bse.cn/important_news/200026735.html
- https://www.bse.cn/company/introduce.html

Do not use search-engine snippets as final mapping data if the official page itself is fetchable.

Keep official-page raw evidence local/ignored if stored.

Compare every Tushare old/new pair against the official BSE table.

If pair sets differ:

`Phase 1C.0 = PARTIAL/BLOCKED`

Do not “fix” mismatches.

## 9. BSE switch dates

Use authoritative rules:

- six pilot companies: 2025-05-06
- remaining mapped stock population: 2025-10-09

Resolve the pilot set from official evidence.

Never infer pilot membership or mappings from code suffix/last digits.

## 10. BSE venue boundary

Record:

`BSE venue trading start = 2021-11-15`

For a BSE listing whose provider list_date is earlier:

- preserve provider_list_date;
- set BSE venue effective_from to 2021-11-15.

For listing after BSE opening:

- venue effective_from = provider list_date.

This is a research venue boundary, not a rewrite of regulatory continuous-listing tenure.

Any historical `.BJ` fact before 2021-11-15 must be capable of classification as `PRE_BSE_LEGACY`.

## 11. Bootstrap from existing Phase 1B stock_basic raw

Prefer the existing local Phase 1B stock_basic captures.

Do NOT rerun the full 47-request Phase 1B probe.

Build a private bootstrap audit:

- normalized SSE/SZSE unique episodes
- BSE rows
- duplicated/reused code candidates
- missing list_date
- non-normalized identifiers
- code overlap conflicts
- quarantine count

`T600018.SH` must remain quarantined/unresolved.

Do not map it to the current 600018 security.

If existing raw data is absent locally, STOP and report that instead of silently replacing the evidence with a fresh snapshot.

## 12. Populate identity governance locally

After all validation:

- allocate stable security_ids for unambiguous listing episodes;
- populate `security_identifier_history`;
- populate `security_venue_history`;
- keep ambiguous records in quarantine.

For BSE old/new identifiers:
- effective intervals use official switch dates;
- knowledge availability remains OBSERVED_CAPTURE/current retrieval semantics.

Do not pretend these mappings were captured historically.

No names/current industry should be backdated as historical PIT.

## 13. Identity snapshot hash

Implement a deterministic `identity_snapshot_hash` over the reviewed current reconstruction:

- sorted security_identifier_history effective rows
- sorted security_venue_history rows
- quarantine classification/version

This hash will be an input to future curation runs.

## 14. Curated governance utilities

Implement only governance/helpers needed for later Phase 1C.1:

- deterministic curation config hash
- deterministic input-manifest hash
- safe path validation for future curated files
- immutable/no-clobber publication helper may reuse Phase 1B atomic writer logic

Do NOT actually curate 2013-present data.

## 15. Synthetic tests

Add tests for:

- v1 remains unchanged/loadable;
- v2 explicit catalog selection;
- no implicit latest version;
- curation spec type stability for empty inputs;
- deterministic UUID5 security_id;
- names do not change identity;
- code reuse with disjoint listing episodes does not merge;
- ambiguous overlap quarantines;
- T-like non-normalized provider id is retainable but unresolved;
- BSE old/new same security_id;
- pilot switch exact 2025-05-06;
- remaining switch exact 2025-10-09;
- BSE venue boundary 2021-11-15;
- pre-BSE `.BJ` can be classified PRE_BSE_LEGACY;
- migration 005 preserves Phase 1B lineage;
- identity snapshot hash deterministic;
- no real token in CI.

GitHub CI remains fully offline/synthetic.

## 16. Review artifact

Create:

`docs/reviews/YYYY-MM-DD-phase1c0-review.md`

Include only sanitized aggregate evidence:

- base/implementation commit
- contract v2 list
- Tushare bse_mapping count
- official BSE mapping count
- exact pair mismatch count
- pilot pair count
- security_id allocated count
- identifier-history row count
- venue-history row count
- quarantine count by reason
- code-reuse/overlap candidate count
- explicit T600018 status
- local tests
- CI
- confirmation no historical backfill started

Do not publish full provider stock list.

A small public BSE pair sample is acceptable only if sourced from the public official BSE table.

## 17. Stop conditions

BLOCK/PARTIAL if:

- existing Phase 1B raw missing;
- official BSE table cannot be reliably read;
- Tushare vs official BSE mapping has unexplained differences;
- security_id allocation has ambiguous overlaps;
- migration loses existing lineage;
- T600018 is silently normalized;
- any full historical backfill starts.

## 18. Final report

Return:

```text
PHASE 1C.0 STATUS
PASS / PARTIAL / BLOCKED

BASE + COMMIT
...

CONTRACT V2
...

BSE MAPPING AUDIT
...

SECURITY ID BOOTSTRAP
...

VENUE HISTORY
...

QUARANTINE
...

GOVERNANCE SCHEMA
...

TESTS
...

GITHUB CI
...

WHAT I DID NOT DO
...

PHASE 1C.1 RECOMMENDATION
...
```

Then STOP.

Do not begin Phase 1C.1 or full historical backfill.
