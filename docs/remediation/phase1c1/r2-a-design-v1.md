# R2-A concrete design v1

Frozen before implementation, 2026-10-02. Scope: bounded reconstruction from the
existing 133 requests. Authority is the retained v1.1 batch prompt and R1 FINAL
PASS at cc458ce2e8229dcc914e9a45ae2ac6186f48c45c. All real writes/publication belong
to separately authorized R2-B. This design and its byte hash remain immutable;
necessary design changes receive explicit append-only addenda/new versions.

## Schema and identity

Explicit additive migration **008_r2_provider_identity** introduces immutable
`listing_episode`, `official_exchange_code`, `provider_native_binding`, and exact
`provider_binding_observation` rows. Episode includes stable security, venue,
asset, half-open event interval and actual evidence/knowledge availability. Official
code intervals are independent of provider representation. A binding records one
provider/dataset/native string, episode, version, representation kind, evidence,
first observation/availability/decision times, approval reference and optional
superseded binding. Applicability is an explicit set of `(raw_object_id,
zero-based raw_row_number,event_date)` observations with raw FK; there is no
wildcard dataset/capture/event interval. Approved imports require a reviewed
case-set hash; proposals never become active automatically.

The resolver accepts provider, dataset, exact native, event, raw object/row and
knowledge cutoff. Only APPROVED knowledge-visible versions participate; exact
observation scope precedes episode/venue/asset checks. Conflicting candidates fail
closed even if stable security IDs agree. Official code at event is returned
separately; native value is retained. No suffix/digits/names/successor inference,
T-prefix rewrite, pre-opening BSE admission or legacy resolver mutation. Versioned
snapshot validation rejects overlap and forked supersession. New knowledge never
appears at the old frozen batch cutoff.

## DQ policy v1

Versioned `config/dq/r2-v1.json` fixes rule semantics and price/causal/factor
tolerances before new real DQ. Coverage key is security/episode/venue/event/dataset;
observation precedes disposition. Historical episodes define expected membership;
current active lists and unclassified delist metadata cannot erase bars. Proven
termination outside episode, full-day S, partial S, S/R conflict and metadata
boundaries are distinct. Unknown calendar/episode and in-scope unexplained gaps
remain blocking. Null reference, numeric mismatch and evidence-scoped
NOT_APPLICABLE are separate; no fill/default/tolerance tuning. An exception needs
approved case/evidence and exact dataset/episode/date/field scope.

BSE checks independently cover official 6-pilot/242-remaining code intervals,
native representation and security/episode continuity. Same native across an
official switch requires scoped retrospective evidence; missing sides are
NOT_OBSERVED. Venue-session evidence is keyed by venue/episode/day; existing SSE
windows certify SSE only. Non-SSE SSE-basis diagnostics remain provisional;
unknown adjacency resets segments and is NOT_CERTIFIED. Keep forward close/
pre_close causal scaling and factor audit unchanged. Report certified, provisional
and excluded pairs separately. Local quality and batch gate are independent.

## Context, publication and row conservation

Migration **009_r2_derivation_publication** introduces immutable derivation context,
expected raw/request inputs, generation header, append-only state events, verified
output registration, raw-FK row quarantine and complete-generation manifest.
Context pins parent batch/generation, all133 raw inputs,126 market outputs, frozen
identity/plan, provider/episode/official snapshots, curation specs, DQ policy,
knowledge cutoff, tested SHA and independent approval hashes. Production admission
checks the full frozen plan via R1; small synthetic plans require an explicit
fixture-only flag and cannot be admitted as production.

PLANNED→BUILDING→COMPLETE or BLOCKED are derived from ordered events. Per expected
request, deterministically compute new typed output and exact quarantine row set;
stage no-clobber Parquet and lineage under a new context/generation/request path,
then atomically register after physical/schema/logical/lineage checks. Orphans are
reconciled only by independently rebuilding and matching complete expected bytes/
lineage; mismatches remain BLOCKED, never overwritten/deleted. Unique keys, managed
writer ownership and one transaction prevent duplicate registration. Complete
promotion revalidates all126 outputs, immutable inputs and exact source row sets;
no max-generation selection, partial promotion or inferred file success. DQ must
select an explicit COMPLETE context/generation. COMPLETE is not data admission.

Each input row occurs exactly once in resolved or quarantine, with raw FK and
zero-based ordinal. NULL/native/retrieval times are preserved. Typed metadata is
CURRENT_RECONSTRUCTION/OBSERVED_CAPTURE; identity availability is separate. Logical
hash includes schema/units/native/source/semantic binding; generation UUID/time
is excluded. Same-context independent generations must agree. Legacy conversion,
frozen resolver, logical mismatch enforcement and old specs stay unchanged.

## Findings and migration boundaries

Migration **010_r2_append_only_quality** adds finding observations plus per-output
and batch quality audits. Stable finding keys use rule and exact raw row or episode
scope. Audit rows pin context/generation/policy/implementation/time/finding-set
hash, local status, batch gate and supersedes reference. Reruns append; no UPDATE
to old audits, batch state or new historical events. Application APIs enforce
append-only semantics; FK/CHECK/UNIQUE do not prevent arbitrary direct SQL UPDATE
and are not claimed as such. New migrations are explicit, never on-open.

## Evidence and verification

Private ledger separately reconstructs flags, unique source rows and episode/date
keys, with diagnostic intersections; candidate joins do not resolve rows. BSE
matrix is dataset/event/capture scoped and retains earlier stock_st observations.
Every proposed case pins exact raw row set, evidence, episode/binding draft,
knowledge times, impact and proposal hash. Missing evidence remains REQUIRED,
conflicts remain CONFLICT and out-of-scope rows remain traceable quarantine.

Test negative scopes/knowledge/episode ambiguity, official/native transitions,
asset/venue/NULL/coverage/calendar, complete/partial selection, crash boundaries,
orphan corruption, concurrent/resumed publication, row/FK conservation, audit
append-only behavior and old/new rebuilds. No original migration or real derivation
in A. Retain baseline DB hash/all19 tables and all1,102 protected files; deny
provider/network/settings in real audit and keep counters. Final full tests,
offline diagnostics, decoded secret scan and exact-SHA CI precede R2-A Review.
