# R2-B time integrity fix: unified engineering review

**Author delivery status: R2_B_TIME_INTEGRITY_FIX_REVIEW_READY.** Independent
repair review and matched execution reapproval are still pending. This report
does not close P1, resume production B or claim R2 FINAL PASS. Real-data admission
remains BLOCKED; Phase1C.2 CLOSED; market/provider requests zero.

## Problem and resulting behavior

The independent review of `63a166b89f44850dd9fa2efa8ab06c0e49a8bfd5` confirmed
one P1 at two entry paths. TIMESTAMPTZ preserves an instant, while its JSON offset
changes with database session timezone. Both resolver hashing and pinned/live
member comparison previously treated equivalent offsets as different content.

One shared resolver-only serializer now converts the seven explicitly enumerated
aware datetime fields with `astimezone(UTC)` to six fractional digits and `Z`.
It preserves null publication and rejects naive clocks; date/native/ID/interval/
scope/ordinal/evidence/approval/status/version and observation order retain their
semantics. Hashing, snapshot payload and pinned/live equality share that rule.
Checksum, canonical membership/payload, missing-member and real tamper checks
remain enforced. A one-microsecond change remains significant.

## Frozen design and explicit version boundary

Authorization/design commit: `bbd032b` (before implementation).
Engineering implementation/test SHA: `20d2c23bea98d091407f973f491cf89082647e20`.
The final materials SHA and actual CI are retained in the ignored final handoff
after committing/pushing this report; source/test/design bytes match that
engineering commit. Original engineering approval remains
`2f2592968a7f8e2500ee5e0bd3772a15a5c621f5`, never relabeled.

New frozen `r2-a-design-v1-addendum-4.md` pins protocol
`R2_RESOLVER_UTC_INSTANT_V2`; file SHA256:
`068054fc25ac0e40eab0e33682f8c5be14debdcf7765e8d842bbb39666dd3e6b`.
Approval and Context each require the explicit protocol and
`time_integrity_addendum_hash`, with no v1-compatible defaults. Schema admission,
case import and Context validation check this pin. Old v1 JSON is preserved and
cannot execute via v2 admission. New metadata fits existing JSON storage:
**SQL001–010 is unchanged**, including all TIMESTAMPTZ columns.

No global receipt serial/digest, raw/frozen identity/context, legacy conversion,
logical hash, DQ policy, NULL/factor/tolerance or provider behavior changed.
Existing tests only receive the required new synthetic approval/Context pins.

## Persistent SQL regressions

33 new tests use temporary synthetic managed storage and fixture-only approvals.
They deploy008–010, import mixed UTC/+08:00 microsecond clocks with null
published_at, register and publish a COMPLETE fixture generation, close the
connection, reopen and validate pinned membership/JSON and select/rebuild across
Asia/Shanghai, UTC, America/New_York and Asia/Kathmandu. Both Asia/Shanghai and UTC
are initial write sessions. Same-context independent generations match logical
hash/schema/units/source/quarantine; repeated registration is stable.

Initial registration rejects stale v1 or changed-instant digests. Persisted/reopened
selection rejects changed instants/native/dataset/event/raw/ordinal/security/
episode/code interval/evidence/approval/status/version/order and missing members,
observations or snapshot. Six material changes independently alter the digest.
All seven explicit clock fields test equivalent offsets, precision and naive
rejection. F1–F3 factor completeness, exact pair attribution, appended successor/
unrelated member stability and checksum/tamper regressions remain enabled.

Focused checks:118 passed before the final clock/digest additions, followed by
33/33 final time-integrity regressions. One final full offline suite: **622 passed,
1 warning,418.71s**. The warning is the retained multithreaded fork regression.
Doctor/contracts passed. Current-credential/pattern and decoded scans passed,
including1118 Parquet paths. Final exact-SHA CI is recorded from actual run/jobs/
logs in the ignored final handoff after push. Documentation changes do not repeat
the completed local suite.

## Actual materials: read-only, not synthetic approval

Managed read-only access to the actual failed isolate confirms identical aware
instants, non-time fields, exact scopes and observation order by immutable ID in
all four timezones. Raw capture checks confirm first_observed_at equals the
earliest retrieved_at in each of the12 exact binding scopes. Canonical payloads
and their digest agree with the original approved payload after v2 serialization.

Old resolver hash:
`5ed2a9d8831ca37efd4f50f754812903b5e52ea54bd34c56c5241ae720c92772`.
Serialization-only candidate:
`408a3a328da5858a2e400c09675bedb2623f8afb6ff00d2a501854608454dbe3`.
Its coincidence with a previous UTC diagnostic is not reapproval or a v1 hash
substitution. The candidate snapshot is ignored private diagnostic material.
No production Approval/Context is authored or registered; failed isolate bytes
remain unchanged. Original3 episodes/3codes/12bindings/192rows and DQ facts
(63 NOT_CERTIFIED,1374 exact out-of-scope,0exceptions/0BSE transitions) remain
limited and unchanged. No historical investigation or request is repeated.

## Reviewer-owned candidate metadata

The private impact manifest retains old case/DQ/resolver/Context/file pins, new
engineering/design/protocol pins and a non-executable Context template with null
reviewer fields. A final new Context hash is deliberately undetermined until
reviewer refs/times and final payloads exist; the model rejects the template.

The existing unified Approval model requires matching review_ref and actual
approval availability. Reviewer must explicitly version episode/code refs and
availability, binding refs/decision/availability and the1374 DQ disposition refs
where required by the new review. Preserve first_observed_at, retrieved_at,
published_at, old approval history and exact factual scope. Do not backdate the
new engineering review or overwrite v1 records. Metadata versioning changes
case/DQ/resolver/Context hashes; the serialization-only candidate above is not
necessarily the final execution hash. Reviewer finalizes all canonical and byte
pins, actual review_ref/approved_at and knowledge_as_of. The author fills none.

## Historical preservation and next boundary

Original DB SHA256 remains
`2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`;
schema001–007/19tables,181raw,252oldcurated/lineage,1102protected files,
frozen identity and133 strict receipts VALID/EXACT with0failures are retained.
The old backup, failed isolate, independent approval files, old26+17 evidence,
blocker ZIP/index and historical reviews remain byte-identical. Baseline2539
private/protected files were pinned before implementation and checked afterwards.
Original migrations/bindings/Contexts/generations/audits written here:0.

Private evidence is newly stored under
`data/private/phase1c1-r2-b-time-integrity-fix/2026-10-03-v2/`, including read-only
proof, candidate diffs/template, full test/scan logs and evidence index. Public
Git contains only source/tests/governance and sanitized summaries. After unified
repair REVIEW and matched reviewer approval, limited B requires a **new** rehearsal
from verified schema007 and revalidated backup/inventory, not reimport into the old
failed isolate. Production publication/two-generation DQ remain NOT_EXECUTED.
