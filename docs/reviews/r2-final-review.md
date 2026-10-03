# R2-B limited execution — blocked rehearsal delivery

**Author status: R2_B_BLOCKED_BEFORE_ORIGINAL_DEPLOYMENT.**
R2_FINAL_REVIEW_READY has not been reached. The independently approved package
passed provenance/file/canonical-hash checks, but actual isolated Context
registration failed. No R2 schema, identity, Context, generation or DQ was
deployed to the original warehouse. Historical completeness and real-data
admission remain BLOCKED; Phase1C.2 remains CLOSED.

## Authority and immutable implementation

The user supplied the retained historical review, independent approved package
and limited execution prompt, then explicitly instructed Codex to continue.
See `2026-10-03-r2-b-limited-execution-authorization.md` and the verbatim supplied
`Codex_Phase1C1_R2_B_Approved_Limited_Execution_Prompt.md`.

Approved engineering SHA: `2f2592968a7f8e2500ee5e0bd3772a15a5c621f5`.
Implementation commit: `5108731af43bc0738144b6e835c5b65f5f5fc37f`.
Approved materials SHA: `f2df32b5d722fb3b73bf0e3a9294d5517c6fdfa1`.
Actual execution SHA: `f597671fd553e2240b3793ac342bd3b7201096cc`;
that commit adds only the supplied approval documents and user authorization.
Final delivery SHA is the commit containing this report/index/reproduction;
actual final CI/SHA are recorded in the ignored final handoff after push.
All approved source, schema, tests, policy, AGENTS and prior tracked file bytes
remain unchanged. The new public reproduction is an isolated synthetic review
artifact, not a production implementation change.

Independent ZIP SHA256:
`df956f993912a2c85a4f1608be573aa763e68306ec9405b732387f9f8c61df08`.
Its14 unique members passed CRC and exact equality with the supplied files;
all manifest byte hashes and reviewed implementation hashes match. The original
author approval ZIP remains
`fda8ecf5e945673d34a484b411226740551396408f130c6e61cc6937aee81a17`.
Approved payloads were copied into a new ignored independent-approval directory,
without changing proposals, review packages, references or approval times.

## Fixed approval pins

Actual approval/knowledge time remains `2026-10-03T03:52:23.856708+00:00`.
CURRENT_RECONSTRUCTION / OBSERVED_CAPTURE and fixture_only=false are unchanged.

| Object | Approved canonical hash |
| --- | --- |
| Case-set | `5f263b228917e2076984e8a71bcc9c6c4368ab415fab698e771ced9b0dd2c26c` |
| DQ evidence | `4f7ad76a9d9613cc3b654c08994b583dc952b45c33051bad8539a32a231aaa19` |
| Resolver | `5ed2a9d8831ca37efd4f50f754812903b5e52ea54bd34c56c5241ae720c92772` |
| Actual Context | `0fd34edc7eb0d19c0cf1b9f39de1a6d3aa378da171e9f68f048890de2f2afda2` |

The case-set contains3 episodes,3 codes,12 bindings and192 exact observations.
The evidence has63 uncertified sessions,1374 exact approved out-of-scope
dispositions,0 reference exceptions and0 operational BSE transitions. None of
the old251 drafts,5584 carry scopes or248 pending BSE cases were activated.

## Original preflight, backup and retained history

Managed exclusive ownership was acquired before the original read-only
preflight, consistent backup and isolated rehearsal. No lock was stolen or
replaced; no unmanaged writer was admitted. Original DB had no WAL. Before and
after checks returned the identical SHA256:
`2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`.

Preflight verified133 strict receipts VALID / EXACT, failure0, unchanged evidence
hash;181 raw bytes/schema/manifests;252 old curated/schema/lineage files; original
19 table content hashes and schema001–007;1102 protected files; frozen identity
`83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c`.
The old26 indexed artifacts and17 repair artifacts passed retained byte checks.

Old frozen Context generation1 was independently converted without publication:
126/126 logical hashes and quarantine membership match the original lineage,
with394580 resolved+7666 quarantine=402246 source rows. No old table, timestamp,
attempt, successful fact, output or audit was changed.

The new backup is readable, has the exact original DB hash and identical19-table
content, and is retained read-only at
`data/private/phase1c1-r2-b/2026-10-03-limited-v1/verified-predeployment-backup.duckdb`.
The recovery record explicitly prohibits silent original replacement. No original
rollback was needed because original deployment never started.

## P1 engineering blocker: resolver timestamp representation

Actual isolated migrations008–010 returned UPGRADED; exact repeat returned
ALREADY_VALID without changing table content. Import committed exactly3 episodes,
3 codes,12 bindings and192 observation rows. All old isolated table contents
(schema_version001–007 subset) and1102 copied protected files remain identical.

`import_approved_cases` then returned a different resolver digest after its
database reload. `register_context` rejected the original approved Context with
**`ValueError: Resolver snapshot changed`**. Isolated Context/generation counts
are both0, and no generation files/publication/DQ were created.

| Readback | Resolver hash | Changed time representations |
| --- | --- | ---: |
| Original approved payload | `5ed2a9d8831ca37efd4f50f754812903b5e52ea54bd34c56c5241ae720c92772` | 0 |
| Actual Asia/Shanghai database session | `df9325a0875c6e64c7354762be1b716dcae91e96522795b7c9d210227eeaa222` | 33 |
| Isolated UTC session diagnostic | `408a3a328da5858a2e400c09675bedb2623f8afb6ff00d2a501854608454dbe3` | 12 |

Model comparisons confirm identical aware time instants and all semantic fields,
members and observation order. In the default session, retrieved/available times
on episodes, code availability and binding decision/availability change their JSON
offset representation. In UTC,12 binding first_observed_at representations change.
The approved payload contains both UTC and+08:00 representations; selecting one
session timezone cannot preserve that mixed representation after TIMESTAMPTZ
storage. UTC was tested only in the isolated session, without changing any
approved file or original connection.

The reviewed `ProviderResolver.snapshot_hash` at
`src/astock/data/provider_identity.py:186` and `resolver_payload` at
`src/astock/data/reconstruction.py:172` hash model JSON with its timezone spelling.
`load_resolver` returns database-normalized time representations. Instant equality
therefore does not guarantee digest equality across this storage boundary.
The registration guard correctly refuses admission; it was not disabled.

Reproduce the same issue with only synthetic PROPOSED metadata and an in-memory
database, without real approvals, market rows or API access:

```sh
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen python docs/reviews/r2-b-resolver-timezone-repro.py
```

Both Asia/Shanghai and UTC preserve semantic models but change the digest. This
reproduction passed. Existing tests passed as well; this report does not claim
that their coverage establishes actual approved database-roundtrip stability.

## Required engineering review and unfinished execution

The supplied prompt says: “预演失败就提交具体阻断结果，不猜测补 identity” and
“若获批实现或政策需要变更，保留结果，集中交付审查，不自行扩展批准”。
This batch therefore retains the actual failure and stops original deployment.
It does not edit reviewed code, synthesize a new approval, substitute a readback
hash, re-time decisions or relabel a different Context as the approved one.

Recommended follow-up for independent engineering review: establish one canonical
time-instant serialization shared by resolver hashing and snapshot payloads, with
equivalent-offset / mixed-offset / SQL roundtrip regressions in both timezones.
Preserve original source and legacy frozen-context semantics. Review the exact
corrective implementation and have the reviewer fix matching final resolver,
Context and implementation/approval hashes before another deployment attempt.
The current UTC diagnostic digest is not a newly approved replacement.

Pending: successful isolated Context registration; original008–010 deployment and
approved import; two independent COMPLETE generations; exact-evidence real DQ;
126/126 same-context logical/schema/units/source comparison; new actual
finding/source-disposition ledger. No new findings were fabricated, and all15756
old finding keys/severities remain in the unchanged legacy ledger. The expected
192 resolved+402054 quarantine result remains an approved expectation, not a
newly executed generation. Certified/provisional/unknown new causal pair counts
are NOT_EXECUTED; no empty result is called a data PASS.

## Validation and delivery

One local full suite:589 passed,1 warning,395.83s. Offline doctor and contracts
passed. Current credential, decoded-Parquet and credential-pattern scans passed
across original/protected and isolated/new private evidence. Execution transport
guards recorded0 provider construction/fetch/HTTP/socket calls; original inventory
and tables are unchanged. No new market/mapping/calendar requests were made.

Public delivery contains supplied approval/authorization documents, this report,
sanitized count/hash index and synthetic reproduction. Private root is
`data/private/phase1c1-r2-b/2026-10-03-limited-v1/`; index
`r2-final-manifest.json` pins preflight/recovery/backup, actual readbacks, approved
payload, full old-context verification, final preservation and tests. The small
private review ZIP excludes databases and full raw/curated capture files.
Final exact-SHA CI and clean Git evidence are recorded in private final-handoff
after the actual materials commit. **No R2 FINAL PASS or completed R2-B delivery
is claimed.**
