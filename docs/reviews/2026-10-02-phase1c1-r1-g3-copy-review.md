# Phase 1C.1-R1 — Batched G2 remediation and G3 copy candidate

2026-10-02 · **BATCH_REVIEW_READY / ISOLATED_COPY_ACCEPTED**.
Independent batch review pending; original deployment NOT_PERFORMED;
R1 FINAL NOT_PASS; real data gate BLOCKED; R2 LOCKED; Phase1C.2 CLOSED.

## Scope and provenance

The [human batch revision](2026-10-02-phase1c1-r1-batch-authorization.md) authorizes
G2 fixes and G3 backup/copy acceptance before one independent review. It overrides
intermediate pauses only, preserves the retained CHANGES_REQUIRED review, and
expressly prohibits original 007/binding/audit deployment.

Reviewed G2 baseline: `26004ac573d6f66fe14cc63bb87b37543109cf22`.
**Tested implementation SHA: `4da3267667dc238497a555f0e30e931408d3e55e`.**
The final artifact commit contains only this report/manifest and current scope
pointers; final SHA and its exact-SHA CI are supplied in the user handoff and ignored
private handoff. No earlier CI is substituted for that final commit.

G2 closure and 38 additional regression cases are documented in the
[fix evidence](2026-10-02-phase1c1-r1-g2-fix-review.md). Both independent P2 findings
are accepted and corrected; related stale context, cursor lifetime and context-exit
cleanup defects were corrected within the authorized scope. This is author closure
evidence, not an independent PASS.

## Verified backup and isolated acceptance

The original no-WAL database was protected by its stable coordination lock and
opened **read_only=True** only. A read-only native connection excluded native writers
during byte-copy; original connections closed before isolated migration. Backup was
fsynced, checksum-equal and reopened read-only to compare **all 17 original tables**.
A new empty 0600 sibling `.lock` is coordination metadata; the original DB/data were
not written. The persistent inode stays present and ignored.

The working database and all 1,102 protected evidence files were physically copied
into ignored private storage; no hard links or symlinks were used. Original backup
and copied source files are read-only. Catalogs/SQL are copied unchanged. Strict
validation used the isolated root, with no reconstruction or source rewrite.

| Requirement | Recomputed copy result |
|---|---|
| Frozen planned receipts | 133 COMPLETE; 133 distinct request/run/object IDs; attempt sum 133 |
| Per-receipt exact proof before upgrade | 133 VALID, 0 failed; legacy audit explicitly UNREGISTERED |
| All old raw objects | 181 checksum/schema/count/event-bound/complete-sidecar proofs; batch subset exactly 133 |
| Old curated and lineage | 252 physical/schema/count/event-bound/logical-hash proofs and exact lineage/run/raw/receipt joins; generations 0/1 each 126 |
| Frozen identity | `83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c`, unchanged |
| Isolated 007 transaction | UPGRADED; 133 exact bindings and 133 VALID UPGRADE audits |
| After-upgrade strict read-only audit | 133 VALID, 0 failed; EXACT binding; same evidence/receipt digests as preflight |
| Repeated isolated upgrade | ALREADY_VALID; binding/audit rows and timestamps unchanged |
| Original and copied history | All 17 old table digests identical (copy schema_version1–6 retained); all 1,102 protected file sizes/hashes and path sets identical |
| Original deployment | None; versions 1–6 only; neither 007 table present |

The shared validators and actual `audit_slice_batch` entry point were exercised.
Original receipts, attempts, capture commits, terminal/retrieval/availability times,
batch status, previous quarantine/audits, curated bindings and frozen identity stay
unchanged. Existing historical/data-semantic findings remain for R2, without rerun,
new mapping, curation, DQ execution or tolerance changes.

## Private evidence and reproducibility

Ignored local evidence contains the verified backup, independent working copy,
one-off validation script and `acceptance.json` with **133 receipt, 181 raw and 252
curated records**, all-old-table inventories and zero issues. Public artifacts contain
only sanitized aggregates/provenance/digests. Review requires access to private local
evidence for independent recomputation; public counts alone are insufficient.

| Artifact | SHA256 |
|---|---|
| Original DB / verified backup | `924bf429b25c4ac2fafc557bdbc67667b39de902b3175a7d7828461207fd4617` |
| Preserved G0 inventory | `f5c30de4f0e0ccb7f526914f047fcccfe65e52d3100784744039dbc158848e9c` |
| Private acceptance artifact | `50a9bb4d552ac2f705904d48b20d84f2b65835ab371078e047cc310c5e1d84b7` |
| One-off acceptance script | `c4360a71ccb43dab19ef17fe3ff139e0e9145d2b44b12f005b33766fbfbd8bb9` |
| Accepted isolated DB | `656e270cb43c84eaee9959e41f427b5df406cd675d4818fcd203c583229364a6` |

The private script is reproducible using a fresh output directory and the recorded
implementation, frozen original evidence and G0 inventory. It refuses overwrites;
contradictory/missing evidence yields BLOCKED without repair. It is a one-off review
artifact, not new reporting or ingestion infrastructure.

## Author self-check, tests and zero-market evidence

Python 3.12.14 / locked DuckDB 1.5.6: **480 passed, 1 warning in 239.23s**;
focused boundary/fault tests **116 passed, 1 warning in 43.08s**. Python warned about
the intentional cross-thread fork test; all bounded fork/pipe assertions passed.
Offline locked sync, token-NO doctor, contracts v1(12)/v2(9), probe plan, identity
specs and slice plan/specs passed. No dependency, SQL001–007, catalog or old review
was modified. Final current-SHA CI remains a required handoff check.

The acceptance process denied Tushare construction/fetch, httpx request, socket
connect/DNS and settings access during audit. Every spy counter was **0**. Credential
access was confined to optional local decoded scanning before the audit; receipt
proof did not require a token. Existing compressed-Parquet secret regressions and
private decoded credential scan passed. No capture/resume/claim/curation/DQ or
market/API command was invoked. GitHub/CI traffic is repository verification only.

The final acceptance self-check verifies report/manifest against private records,
backup/copy hashes, all original evidence, source tree identity, test logs, secret
exclusions and staged exact paths. Full datasets/private reports/DBs/locks remain
ignored; real `.env`, credentials, `.tools` and `.venv` are excluded from commits.

## Pending deployment and review boundary

This delivery establishes author engineering checks and **isolated-copy acceptance**.
It deliberately does not satisfy the original-deployment step in the retained G3
specification. An independent reviewer must assess this exact batch; no R1 FINAL
PASS is asserted. Original 007/binding/audit deployment needs separate explicit
authorization, fresh preservation/preflight checks and the approved backup/rollback
procedure. The accepted copy is evidence, not a replacement for the original.

No real evidence is unresolved within this copy acceptance (0 issues). Data identity,
coverage/calendar/quarantine/partial-generation follow-ups remain deferred to R2.
Stop for the unified independent review. R2 and Phase1C.2 stay closed.
