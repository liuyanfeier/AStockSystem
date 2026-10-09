# Integrated Phase1 Operations

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
