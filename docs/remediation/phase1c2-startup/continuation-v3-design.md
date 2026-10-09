# Frozen continuation v3 design

Frozen before implementation on 2026-10-08. Protocol `CAPTURE_CONTINUATION_V3`.
This is an additive candidate-store protocol, not a production deployment or license.
The v2.1 module, design, catalog, DDL, contracts and six historical tables remain
unchanged. New code pins those original bytes and its own source/design/DDL/diagnostic
module. No new dependency. One canonical production destination remains
`data/private/full-backfill-v1` beneath the reviewer-pinned absolute repository root.

## Historical proof and additive upgrade

Before copying, use the managed shared original lock, byte hash/no-WAL check and
complete ordered six-table rowsets; audit original plans/licenses with v2.1 pins.
The candidate copy retains all UUIDs,origin plans/descriptors,licenses,events and
timestamps. A managed exclusive candidate upgrade validates legacy provenance,
freezes six-table content and legacy evidence-file hashes, then appends four tables:
baseline,authorization,attempt and event/receipt (event and receipt are separate,
five tables total). No UPDATE/DELETE of historical tables or event rows.
Baseline binds the copied original DB hash, canonical production path, exact legacy
DDL/pins and complete six-table content hash. Runtime validates old rowsets and files
against this independently approved baseline; it never interprets old origins using
new pins. Existing COMPLETE objects retain the old physical validator semantics.

Upgrade is transactional and idempotent only with the exact baseline; unexpected
schema/WAL/file differences fail closed. Rollback preserves six original rowsets.
This batch's upgrade entry accepts only an explicitly isolated copy. A production
upgrade requires a separately reviewed future deployment entry and human approval;
no copy can become an alternate production ledger.

## Exact append-only continuation authorization

The application binds baseline/store consumption digest, old origin plan and licenses,
terminal member states, exact unconsumed descriptors/order/membership hash, their
original object UUIDs, all pins, budget,1 attempt/member,1.25-second pacing and
explicit dependency sets. Both old FAILED/UNKNOWN calendars are excluded by the
shared endpoint/dataset/params logical key, irrespective of fields/contract/name.
The independent review additionally binds implementation SHA, canonical production
destination and exact actual-human evidence bytes. Human license binds review hash,
evidence and actual time. Placeholder/fixture/proposed/absent evidence cannot license
production. Repository HEAD/clean root and historical consumption are checked at
execution, not inferred from the old snapshot. All applications delivered now have
execution_license=false,review=null,approved_at=null.

No call may alter origin registration or reuse its old execution license. New attempt
binding records original UUID/origin and new authorization/review/human hashes. Managed
exclusive ownership spans validation and each call. Authorization registration and
CLAIMED/attempt budget consumption occur atomically; CALL_ENTERED commits before HTTP.
Global old/new consumption includes CLAIMED, even if process death precedes send.
No automatic resend/reconcile-to-new-call. A newly stranded/FAILED/UNCERTAIN attempt
stops all later sends; only the exact terminal state set present in the reviewed
baseline is isolated. New authorization cannot extend that isolation set.
All new event ordinals/times/transitions and budgets are revalidated on reopen.

## Response, certification and diagnostics

Closed tests require exact httpx.MockTransport and synthetic token. The future
production transport is fixed HTTPS,verify=true,trust_env=false,retries/redirect0.
This delivery does not expose a production-send entry. Safe observations contain only
fixed error classes/stages,header-received flag,actual body byte count/EOF,UTC times,
approved endpoint host,DIRECT route and TLS verification. Never serialize exception
repr,str,headers,request,token,environment values,proxy userinfo or certificate contents.

Response retention,contract validity,window completeness and research admission are
distinct. Reuse the exact v2.1 decoder/key/NULL/cap/calendar/cross-window checks.
Known-cap valid nonempty and complete civil calendars may produce COMPLETE; leading
predecessor remains uncertified. Unknown-cap market rows produce RAW_RETAINED with
complete physical five-file closure and a RAW_UNCERTIFIED receipt, never COMPLETE
or research Context. Unexplained empty,cap/truncation,HTTP/contract/unsafe failures
stop and preserve safe received originals; no fabricated typed data.
Source,typed,manifest,sidecar and raw bytes are reread in the receipt transaction;
mutation rolls back receipt/success event. Reopen reruns byte/row/schema/provenance
validation without another HTTP. All research_admitted flags are false.

## Verification and retained boundaries

Test license/root/pin/member/dependency rejection; cross-version consumed keys;
atomic claim/attempt binding; managed concurrent claims/process death; new unknown
stops all later calls; old origin/time preservation; five-file mutation rollback;
safe diagnostics/exception leakage; NULL/unknown cap/previous semantics and reopen.
Real-copy upgrade verifies old six full rowsets and files; copy tests have no data
network. Original34/metadata4 tables and all protected files/171pins stay immutable.
No133 replay,finite45 import,Context/DQ registration or production upgrade.
New document4 and DNS/TCP/TLS permissions are separate durable ledgers, not runtime
data licenses. Deliver exact28 and raw-only market6 unapproved applications plus
blocking matrix,actual evidence,tests,preservation,secrets and exact-SHA CI, then stop.

## Pre-implementation clarification for future production entry points

Frozen before adding these entry points: the same reviewed core also exposes a
future production upgrade/capture entry, so exact28 can be reviewed against a concrete
runtime rather than a missing follow-up implementation. This supersedes only the
earlier sentence requiring a separately implemented deployment entry. It does not
authorize invoking production entries in this batch. Upgrade requires --live-equivalent
explicit intent, matched external Review/actual-human bytes, clean exact-SHA root,
canonical fixed destination, current original DB hash and freshly validated legacy
history/consumption. It adds schema/baseline atomically, validates before commit and
rolls back on failure. Every future new send rechecks HEAD/clean root, approvals,
protected baseline/consumption and uses only the fixed verified no-retry transport.
Archived license audits may ignore a later documentation HEAD but never old source
pins. The isolated entry accepts only exact MockTransport/synthetic credentials;
production rejects injected transports or cloned destinations. No production entry
is invoked here; actual deployment and28 calls remain independently unapproved.

Before the final implementation freeze, additionally pin the immutable private
protected-history manifest in the baseline. Production upgrade and each new send
verify its bytes,all historical file hashes and171pins,while holding managed shared
original warehouse/metadata locks. Live capture DB bytes are excluded after additive
upgrade; its frozen six rowsets/legacy source files are checked instead. Fixture-only
baselines may omit that manifest; production may not. The reviewed app binds its
reference through baseline_hash. This check grants no new write or network scope.
