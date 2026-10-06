# Full backfill runner v1: frozen candidate design

Frozen before implementation in this batch. This independent protocol prepares
future CURRENT_RECONSTRUCTION / OBSERVED_CAPTURE capture, not research admission.
No accepted171 file, bounded133/126 guard, SQL001–010, v2 identity/time/hash/NULL
semantics or fixed FAILED metadata store changes. All production licenses default
false. Full target remains 2013-01-01..2026-09-30 and six market datasets.

## Boundary and authorization

A separate `python -m astock.data.full_backfill_v1` CLI accepts only a complete
exact-member plan. It never delegates to TushareClient._fetch. Pure validation
needs no credential. Production capture requires `--live`, byte-pinned independent
review and separate actual human authorization artifacts, matching implementation
Git SHA, clean checkout, source/design/catalog/DDL pins, plan/member hashes,
fixed store, reviewed budget and time ordering. Fixture namespace accepts only
httpx.MockTransport; production rejects injected transports and fixture artifacts.
Review/human metadata is external evidence, never generated as actual approval.
Production artifacts cannot override default namespace, destination or endpoint.
A future independent approval must explicitly license each metadata logical request
and disclose the old FAILED request; this runner cannot retry that old request.

## Membership, storage and lifecycle

New `sql/offline/full_backfill_v1.sql` lives only in an independent store. Managed
writer ownership, stable process/thread/context locks and transaction helper are
reused unchanged. Reused atomic_new_file provides no-clobber fsync publication;
Clock/pace/strict_json/safe_path are reused from the accepted metadata module.
New store has pinned plan/catalog/code identity, exact request members, events and
receipts. Logical member ID hashes dataset, params, fields and contract bytes;
run labels cannot create a new budget. Production destination is fixed
`data/private/full-backfill-v1`, never original warehouse or old metadata store.
Plan persistence costs zero attempts. Claim and CALL_ENTERED each commit before
transport. Global stop on unresolved claims/terminal failure; max1 attempt/member,
no retries, no resend after FAILED/UNCERTAIN. Reopen validates every completed
member and pins before another request. A persisted call with no complete source
requires external reconciliation, never another send. Full safe body+source may
be locally reconciled without transport; no claim/call timestamp is rewritten.

## Transport and completeness

Pinned HTTPS api.tushare.pro, verify TLS, retries0, trust_env=false,
follow_redirects=false, identity encoding, >=1.25s persisted call-start spacing
across reopen/boot changes. No endpoint URL or unbudgeted generic fetch option.
Validate actual content length/HTTP/envelope, exact fields and finite scalar types,
request date/venue scope, duplicate natural keys, native identifiers retained.
Documented cap equality, unknown cap, unexplained empty or permission/schema
failure stops. Unknown adj_factor cap requires separately reviewed completeness
facts before production. No hidden offset/automatic repartition requests.
Credential echoes (literal/encoded/JSON-decoded) are suppressed before persistence.

## Immutable evidence and failure boundaries

Publish full response.body, http-source.json, typed.parquet, manifest.json and
sidecar.json. Arrow schema/type/source/time/hash and exact UUID binding must match
redecoded body. Explicit COMPLETE receipt and promotion event commit together
only after all five closed files validate. Zero manifests/fake UUID/missing files,
extra artifacts, schema/event/receipt/plan tampering and unsafe links reject.
Local failure after durable body+source can reconcile the same immutable evidence;
registration/promotion failures roll back receipt/event transaction. Failure before
source cannot be assumed received; retain consumed claim as UNCERTAIN. Never
restore or overwrite data to hide failures. Body receipt means observed response,
CALL_ENTERED means local invocation only.

## Offline acceptance and unresolved prerequisites

Closed mock HTTP exercises the actual new capture branch with nonempty rows,
cap/truncation/empty/permission/schema/unknown transport, publication/registration/
promotion faults, process-style close/reopen/resume, licensing/pins/budget and
artifact tampering. Deny real sockets. Reuse accepted30126 membership/scale proof;
this batch does not prove full-history real IO, account permission, historical
coverage, session certification or typed research curation. Raw typed fields are
source-preserving capture only; normalized identity and DQ/Context admission await
actual authoritative fact approval. No original integration/deployment this batch.
