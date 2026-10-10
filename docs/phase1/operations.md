# Phase1 V2 Consolidated Operations

Use the existing locked Python3.12 environment. Current runtime is PHASE1_INTEGRATED_V2; original source engines and contracts v1 stay frozen. See [V2 design](design-v2.md), [matrix](acceptance-matrix-v2.md) and [consolidated report](../reviews/phase1-consolidated-fix/report.md).

## Latest controlled RAW49 closure and whole task

See [controlled report](../reviews/phase1-raw49-controlled/report.md) and
[whole task](full-historical-delivery-task-v1.md). Actual controller closed as
BOUNDED_CAPTURE_FINISHED_WITH_HOLDS; 49 new attempts, COMPLETE=26, FAILED=2, RAW_RETAINED=21,
0 unattempted. Parent/child policy approval was actual reviewed
derivation, not author independent signing; all chains and old consumption retained.
Do not run the controller again, clear its session or activate remaining members.
Runtime source/23pins stayed66b1; documents are now separate delivery HEAD. Audit
is read-only, originals remain immutable, real facts/adoption unlicensed.
The full task uses a private exact-product generator and finite caps; source/IO/
full-controller policy plus independent/human matching approval precede execution.
New bounded read retries apply only to future newly approved full-task members;
old and RAW49 consumed failures/unknown never refund. Prior RAW50 text below is
retained historical scope, superseded only for the now-completed bounded RAW49 batch.

## Latest RAW50 stop and source binding

See [actual result and scoped repair](../reviews/phase1-raw50-source-version/report.md) and [source-version design](source-version-integrity-design.md). The fixed5672e8f pilot stopped after one SSE2014 UNCERTAIN, zero response/receipt and49 unattempted members. Do not run the old50 plan again or use its approval at the repair SHA. Original V1 and executed V2_5672 adapters remain fixed; conversion uses actual source/plan/approval pins, never a generation's replacement declaration. Missing V2 source pins fail, while proven V1 remains readable.

The new actual capture store is RAW_ONLY. This batch permits read-only audit after the stop; production import/build/interpretation is not licensed. Audit sends no HTTP:

```bash
uv run --offline --frozen python -m astock.phase1 audit --destination data/private/phase1-integrated-v1
```

The ignored delivery index locates the exact remaining49 members/plan/application, baseline and stopped consumption digest. These retain26 calendars+17 pilots+6 market members, have license=false and require new matched final-repair review/human evidence. After such approval, use the same unified `execute --live` template below with those exact new files; no calendar-specific driver or per-member confirmation is needed. A new error stops all remaining calls and consumes its claim permanently. The full-domain coverage plan excludes SSE2014 as a consumed-unknown HOLD; source answers remain unknown because no response was obtained.

## Complete closed verification

```bash
uv run --offline --frozen python -m astock.phase1 specs
uv run --offline --frozen python -m astock.phase1 demo --destination data/private/phase1-v2-demo
uv run --offline --frozen python -m astock.phase1 production-rehearsal --destination data/private/phase1-v2-TEST-root
uv run --offline --frozen python -m astock.phase1 --output data/private/target.json coverage-target --destination data/private/phase1-v2-demo --start 2025-01-01 --end 2025-05-16
uv run --offline --frozen python -m astock.phase1 coverage --destination data/private/phase1-v2-demo --target data/private/target.json
```

Production rehearsal requires a fresh TEST root and closed transport; it creates synthetic policies/documents/licenses clearly labeled TEST_ONLY. Actual repository activation rejects these. Coverage targets bind current fact/input evidence and report known obligations separately from unknown universe/schedule denominators. Default coverage generates the same evidenced-session/listing obligations without manually enumerating missing tuples. Explicit goals can add report/vintage/taxonomy/rule requirements; a changed source generation requires a newly frozen target, never silently reusing the old hash.

## Source versions and independent targets

```bash
uv run --offline --frozen python -m astock.phase1 rebuild --source data/private/phase1-integrated-v1 --destination data/private/phase1-derived-a
uv run --offline --frozen python -m astock.phase1 rebuild --source data/private/phase1-integrated-v1 --destination data/private/phase1-derived-b
uv run --offline --frozen python -m astock.phase1 audit --destination data/private/phase1-derived-a
uv run --offline --frozen python -m astock.phase1 coverage --destination data/private/phase1-derived-a
uv run --offline --frozen python -m astock.phase1 as-of --destination data/private/phase1-derived-a --security APPROVED_SECURITY_ID --event-date 2025-05-15 --as-of 2025-05-15T10:00:00Z
uv run --offline --frozen python -m astock.phase1 rebuild --source data/private/phase1-integrated-v1 --destination data/private/phase1-derived-a
uv run --offline --frozen python -m astock.phase1 increment --destination data/private/phase1-derived-a
```

These production-source commands are templates after actual source approval/admission; this batch deploys nothing. Rebuild targets are DERIVED_ONLY, bound to their source owner, and cannot capture/admit production packages. Source-driven rebuild on an existing target incorporates approved corrections; plain increment verifies/idempotently reuses its existing sources. A/B logical hashes must match for identical input sets. Raw/source/approval bytes are checked on every audit/query; DB self-hashes alone are insufficient.

V1 sources are read-only; archived adapters and registry fix the original bytes. Never replace old plan/approval/receipt pins with current pins. Unbound old production capture is explicitly uncertified; actual adoption needs a separate reviewed policy. Register a reviewed frozen transformation before a future runtime upgrade; unknown versions fail closed. New V2 schema is created only in a fresh isolated/new licensed destination, not installed on the old original three stores.

## Retained integrated operating details

Use Python 3.12 and the existing locked environment. Run from the canonical repository root. Every command defaults to offline; `execute` requires `--live` plus actual matched independent approval and human license files. New production destination is `data/private/phase1-integrated-v1`, separate from all three immutable original databases.

## Offline acceptance

```bash
export PATH="$PWD/scripts:$PATH"
uv sync --locked
uv run --offline --frozen python -m astock.phase1 specs
uv run --offline --frozen python -m astock.phase1 demo --destination data/private/phase1-demo-v1
uv run --offline --frozen python -m astock.phase1 audit --destination data/private/phase1-demo-v1
uv run --offline --frozen python -m astock.phase1 coverage --destination data/private/phase1-demo-v1
uv run --offline --frozen python -m astock.phase1 as-of --destination data/private/phase1-demo-v1 --security S1 --event-date 2025-04-15 --as-of 2025-04-15T10:00:00Z --taxonomy SW2021
uv run --offline --frozen python -m astock.phase1 as-of --destination data/private/phase1-demo-v1 --security S1 --event-date 2025-05-15 --as-of 2025-05-15T10:00:00Z --taxonomy SW2021
uv run --offline --frozen python -m astock.phase1 adjust --destination data/private/phase1-demo-v1 --native 000001.SZ --event-date 2025-01-02 --anchor 2025-01-06 --as-of 2025-05-15T00:00:00Z
uv run --offline --frozen python -m astock.phase1 rule --destination data/private/phase1-demo-v1 --exchange SZSE --board MAIN --state ST --event-date 2025-01-02 --as-of 2025-05-15T00:00:00Z
uv run --offline --frozen python -m astock.phase1 reference --destination data/private/phase1-demo-v1 --native 000300.SH --event-date 2025-01-02 --as-of 2025-05-15T00:00:00Z
uv run --offline --frozen python -m astock.phase1 rebuild --source data/private/phase1-demo-v1 --destination data/private/phase1-rebuild-a
uv run --offline --frozen python -m astock.phase1 rebuild --source data/private/phase1-demo-v1 --destination data/private/phase1-rebuild-b
uv run --offline --frozen python -m astock.phase1 increment --destination data/private/phase1-demo-v1
```

The demo uses 23 nonempty contracts and closed transport. Its values and approvals are synthetic; its namespace cannot be reused for production. Reopen verifies immutable receipts without resending. A stopped demo requires an explicit new recovery plan, not another demo invocation. Code/pin changes require a new fixture directory. Rebuilds retain fixed source descriptors; keep those inputs available. Identical inputs yield identical logical hashes, not necessarily identical physical DB hashes. Increment adds evidenced versions, preserving prior facts and generation timestamps.

## Original evidence and review application

```bash
uv run --offline --frozen python -m astock.phase1 --output data/private/global-consumption.json legacy
uv run --offline --frozen python -m astock.phase1 identity-compatibility
uv run --offline --frozen python -m astock.phase1 --output data/private/recovery-plan.json plan --fixture --destination data/private/recovery-fixture --members data/private/unused-members.json --baseline data/private/global-consumption.json --resume-from STOPPED_CONSUMPTION_HASH
```

The `legacy-resolve` command additionally requires exact source object, zero-based source row, native identifier, dataset, event date and as-of; it never broadens the existing 252 approved observations. `failed-body-candidate` validates the complete retained FAILED body into a separate isolated derivative record; no original receipt, timestamp or status changes. `stopped27` copies the actual stopped eleven-table store, checks its frozen pending membership, and executes only closed mocks in a separate namespace. `application` combines that exact selection, the retained market6 proposal, source pilots, current consumption and protection reference into a license-false review request. Use the supplied private delivery application rather than reconstructing its members manually.

## Future approved runtime

The following is a command template, **not a current license**. Supply actual final-SHA approval and direct-human evidence; configure credentials privately in the environment. Keep Git clean, pins exact, originals read-only and the full protection manifest valid.

```bash
uv run --offline --frozen python -m astock.phase1 execute --live --destination data/private/phase1-integrated-v1 --plan data/private/approved-plan.json --baseline data/private/approved-global-consumption.json --approval data/private/actual-independent-approval.json --human data/private/actual-human-license.json
```

The exact pilot has one attempt per member, no retry/redirect, spacing at least 1.25 seconds and first-error stop. Calendar civil coverage/cross-window checks and physical completion readback precede success. Source pilots retain RAW_ONLY status when caps or vintage completeness remain unknown. A reporting failure is disclosed and stops the driver; SQL readback is the authoritative consumption record. Claims and CALL_ENTERED survive process death and are never refunded.

After a stop, use `audit`, preserve failed raw/events and create a new `plan` with the exact current consumption hash in `--resume-from`. Only untouched members can enter the new matched review/license. Changing fields, directories or contracts cannot make consumed requests retryable. Never replay original133 or unknown calendars.

Documented fact batches use `import-evidence --packages ...`; production adds `--live --approval ... --human ...` with the separate `PHASE1_FACT_ADMISSION_V1` approval. It binds all package bytes, actual official document receipts and an explicit version-specific policy. The engineering package contains no such production approval. Then `build`/`increment` produces atomic facts, DQ and lineage; every historical query verifies the retained inputs. Missing publication precision, industry exit semantics, status, identity or rule evidence remains unknown.

The same fact-batch entry supports a `raw_reference` to already captured source/body hashes. Version-specific financial publication adoption needs matching official evidence and policy; response values and wire scope must remain identical. A complete old FAILED calendar uses the explicit `FAILED_CALENDAR` interpretation kind. Both add normalized lineage without new capture calls/receipts or rewriting old failures. Rebuild queries recheck those dependencies. Fixture interpretation is synthetic and cannot grant production permission.

Full expansion uses `expand-market --start ... --end ... --budget ...` only after explicit civil venue coverage. It produces another license-false request list, excluding consumed scopes and exposing HOLD/reuse decisions. The 30,126 base upper bound is not a complete financial/industry/pagination/storage budget. BSE inception and held historical scope require separate authority evidence. Full target execution cannot start from a pilot-only license.

## Final checks and stop conditions

Run `uv run --offline --frozen pytest`, `astock doctor`, existing v1/v2 contracts and the new `specs` command. Confirm all original hashes, 171 pins and protected historical files; inspect exact staged paths and scan decoded/encoded credentials. No database, raw market row or private approval belongs in Git. Keep the full hash guard before every production call until an equivalent cheaper scheme is independently proven. Transaction failure rolls back SQL; preserve incomplete immutable files and failure evidence, never silently overwrite or restore an original DB.

Only independent final review can approve Phase1 research admission. Old402060 findings, uncovered history and unproven financial vintages remain visible. Engineering acceptance and raw-window validation do not authorize strategies, backtests or broker execution.
