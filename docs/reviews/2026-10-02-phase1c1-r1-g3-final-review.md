# Phase 1C.1-R1-G3 — Original deployment and final review package

2026-10-02 · **R1 FINAL_REVIEW_READY / ORIGINAL_DEPLOYMENT_ACCEPTED**.
Author execution/self-check complete; independent **R1 FINAL REVIEW pending**.
Real-data gate BLOCKED; R2 LOCKED; Phase1C.2 CLOSED. No author-issued FINAL PASS.

## Approval, execution and delivery provenance

The [deployment authorization](2026-10-02-phase1c1-r1-g3-deployment-authorization.md)
records the user's explicit approval of the G2 fixes and G3 copy acceptance at
**`ac622718d978b85f90680694ec1cc8e0a3bd8b1a`**. Independent copy PASS is human-relayed;
the full independent report/reviewer identity was not supplied. This does not
constitute independent approval of this subsequent original deployment.

**Approved baseline SHA = execution implementation SHA =
`ac622718d978b85f90680694ec1cc8e0a3bd8b1a`.** Before deployment, HEAD matched exactly;
source, tests, SQL, catalogs/configuration, dependencies and CI were unchanged.
Only the new authorization and current scope documentation were uncommitted.
The upgrade's verification_code_commit records that execution SHA; historical
capture commits/timestamps remain unchanged. The earlier implementation
`4da3267667dc238497a555f0e30e931408d3e55e` and copy review are preserved.

The **final delivery SHA** is the commit containing this report and manifest.
Its exact SHA, successful CI run URL and result are supplied in the final user
handoff and ignored `handoff.json`; a self-referential SHA is not embedded in its
own commit. Final handoff is withheld until that exact commit's CI succeeds.

## Original preflight and approved deployment

The original stable exclusive coordination guard was held continuously across
backup, preflight, migration, repeat validation and read-only acceptance. Managed
connections were opened after the guard; native read-only ownership excluded
external native writers during backup, and the native writer excluded other native
process connections at deployment. Conflict/WAL/changed evidence would fail closed.
There was no conflict, WAL or evidence discrepancy.

Schema001–006 and every old table/file matched the independently accepted copy.
The previous backup was rechecked; a new fsynced backup was checksum-equal,
made read-only and reopened to compare all 17 historical tables. Fresh original
strict legacy preflight checked each receipt plus all raw/curated/lineage evidence.
Its private evidence checkpoint was saved **before** opening the original writer.

The unchanged `apply_receipt_integrity_upgrade` entry point committed **007 DDL,
133 completion bindings, 133 VALID UPGRADE audits and version7 in one transaction**.
It reruns strict validation before DDL/DML and publishes version7 last. No receipt,
attempt, status, success fact, timestamp, quarantine or previous curated binding
was rewritten. No other table was added. Success required no rollback or restore;
the approved transaction rollback path remains covered by the existing fault tests.

## Original offline acceptance

| Requirement | Recomputed original result |
|---|---|
| Exact completion | 133/133 COMPLETE; distinct request/run/object IDs each 133; attempt sum 133; batch raw 133 |
| Raw preservation/validation | All 181 physical checksum/schema/count/event-bound/complete-sidecar proofs valid |
| Curated and lineage | All 252 physical/schema/count/event-bound/logical-hash and exact receipt/raw/run lineage checks valid; generations0/1 each126 |
| Receipt proof | Pre/post receipt, evidence, contract and plan hashes unchanged for all133 |
| Original history | 17 old table row counts/digests identical, including schema_version rows1–6; only version7 and two approved tables/records added |
| Protected files/identity | Exact path sets, sizes and hashes of all1,102 unchanged; frozen identity unchanged |
| New records | 133 completion bindings and 133 VALID UPGRADE audits; execution verification SHA ac622718… |
| Repeat upgrade | ALREADY_VALID; complete binding/audit rows and timestamps unchanged |
| Actual read-only audit | VALID / EXACT; checked133, failure0; same aggregate evidence hash as preflight/copy |
| Audit write exclusion | DB byte hash equal immediately before/after read-only audit and subsequent read-only acceptance; no WAL |

Whole DB bytes changed as expected during deployment. Preservation is established
by old table content and protected file digests, not equality of pre/post DB hashes.
This acceptance proves exact completion/lineage integrity; historical data-semantic,
identity-coverage, calendar, quarantine and partial-generation findings remain R2
work and do not become approved research inputs.

## Private evidence and public manifest

Ignored `data/private/phase1c1-r1-g3-original/2026-10-02-deployment/` contains the new
readable backup, one-off deployment script, preflight checkpoint, final acceptance
(133 receipt/181 raw/252 curated results), execution/test logs, offline checks and
final self-check/handoff. Database and market rows are not committed. The script
uses the unchanged reviewed upgrade and validators; old copy-validation helpers
were reused for inventories and data checks. It is a one-off execution artifact,
not a new repository implementation or reporting system. It refuses existing
output destinations and preserves failure evidence; it never overwrites the DB.

The [sanitized manifest](2026-10-02-phase1c1-r1-g3-final-manifest.json) carries
aggregate results and hashes. Private local evidence is required for independent
recomputation; public counts alone are insufficient.

| Artifact | SHA256 |
|---|---|
| Pre-deployment original / new verified backup | `924bf429b25c4ac2fafc557bdbc67667b39de902b3175a7d7828461207fd4617` |
| Post-deployment original / before-and-after audit | `2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba` |
| Frozen identity | `83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c` |
| Preserved G0 inventory | `f5c30de4f0e0ccb7f526914f047fcccfe65e52d3100784744039dbc158848e9c` |
| Private preflight | `dc5655f5a1295b36a344e04c4826767c4a4b43872e3fdd6ef3631f2ebf2af972` |
| Private acceptance | `eee0f5ca6462ecfcc6a93422c7ef18eb7a23a3a183fa57a8121b0bfd7ef92083` |
| One-off deployment script | `af9d6dfc5496c8d7957d2c964f865bc8723450c0587cf6f8da057fab78091468` |

## Engineering checks, secrets and zero market requests

Local Python3.12.14 / locked DuckDB1.5.6: **480 passed, 1 warning in244.63s**.
The warning is the intentional cross-thread fork regression; bounded assertions
passed. Locked offline dependency sync, doctor (tokenNO), contracts v1(12)/v2(9),
probe plan, identity specs, slice plan(133) and slice specs(6) passed. No dependency
or implementation/schema/configuration change was made.

Approved baseline [CI36980388069](https://github.com/liuyanfeier/AStockSystem/actions/runs/36980388069)
was independently fetched: success, 480 passed/4 fork warnings in589.49s. This is
baseline evidence only; final delivery requires the final exact-SHA CI separately.

Deployment/acceptance denied Tushare construction/fetch, httpx requests, socket
connect/DNS and settings access during audit; every entry counter was **0**.
Optional local credential access was only for decoded artifact scanning, before
audit denial. Raw/curated/backup/DB and generated review artifacts passed the
existing credential scan. No capture/resume/replay/metadata fetch/curation/DQ command
was used. GitHub verification is repository traffic, not market-data traffic.

Final self-check compares private/public proofs, original old tables, protected
files, immutable historical Git files and source-tree identity; it verifies all test
logs, credential exclusions and the exact staged documentation paths. Real `.env`,
tokens, databases/WAL/locks, raw/curated/warehouse/private data, `.tools` and `.venv`
remain excluded. Old specifications, migrations and review/approval history remain.

## Handoff boundary

Author engineering checks, previously approved isolated acceptance, and original
deployment/acceptance are distinct evidence. **Original deployment is complete**;
no original deployment task remains in this authorization. Independent R1 FINAL
REVIEW is the remaining approval. No unresolved G3 evidence discrepancy was found.
Do not issue R1 FINAL PASS, begin R2, open Phase1C.2 or rerun market requests.
