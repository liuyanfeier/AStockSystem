# R2-A design v1 addendum 3

2026-10-03, frozen before implementing F1–F3 from the independent review of
68b62ca6fb65e28b4ea059ca8c197c244b5a2253. Existing design, policy, addenda and
historical artifacts retain their bytes. No original database changes are authorized.

## Daily factor completeness and pair attribution

Each resolved daily source row independently requires exactly one finite positive
factor at the same security, listing episode and event. Missing, invalid or ambiguous
factors emit blocking findings on that daily raw row, including isolated bars,
segment starts and gap resets. Factor rows retain their own validation findings.
No factor is filled, fetched or borrowed across episodes/dates.

Certified adjacent pairs retain the existing forward close/pre_close chain and
factor formulas: price tolerance 0.011, causal 0.011 percentage points, factor
0.011 + 100 * 0.011 / current pre_close. Each abnormal pair emits a finding at
its current event/source row, with previous event/source and episode in the stable
key and payload. Aggregates remain separate. Appending a clean bar cannot move
an earlier finding or block the clean day's output. Unknown adjacency resets.

## Context-specific resolver membership

Undeployed migration 009 adds `derivation_resolver_snapshot`, one immutable row
per context, containing its resolver hash and canonical full resolver payload
(episodes, official codes, bindings including exact observations). Registration
atomically stores the snapshot with context and inputs after matching the context
resolver hash against the reviewed store. Context hash already pins that resolver
hash; approval additionally pins this addendum byte hash.

Every subsequent conversion, publication, selection, DQ and rebuild reconstructs
the resolver from this stored membership, verifies the hash against the context,
and compares every pinned member and its observations with its live source record.
Missing or altered members, malformed payloads or changed membership fail closed.
Additional legitimate records/version successors are ignored by old contexts;
new contexts explicitly freeze new membership and their own knowledge cutoff.
There is no latest-snapshot fallback for a registered context. An unregistered
context may only be validated against the full current store for registration.

Only synthetic stores receive schema 008–010 and test approvals. Real case-set
approval remains null. R2-B NOT_AUTHORIZED, real-data gate BLOCKED, Phase1C.2 CLOSED.
