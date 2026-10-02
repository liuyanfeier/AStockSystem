# Repository Guidelines

## Scope & Structure

AStockSystem is a macOS A-share research project. Phase 1C.1 completed 21 sessions and seven SSE calendar checks (133 requests); its real data gate remains BLOCKED. The 2026-10-02 human authorization batches G2's two P2 fixes and related connection/context/fork lifecycle checks with G3 backup verification, isolated-copy 007 migration and offline acceptance. See `docs/reviews/2026-10-02-phase1c1-r1-batch-authorization.md`. This batch overrides intermediate pause/prior-PASS prerequisites only; complete authorized work before one independent review. The G2 review of `26004ac573d6f66fe14cc63bb87b37543109cf22` remains CHANGES_REQUIRED until independently reviewed. Follow `docs/phase1c1_writer_lifecycle.md`: lock before connection/preflight, bind managed connection lifetime to its process/thread/guard, hold through publication/close; read-only audit uses shared ownership and a consistent snapshot. Preserve earlier specs, migrations 001–007, old reviews, raw/curated/lineage, receipts/attempts/timestamps and frozen identity. Market API budget is zero; no real capture/resume or 133 replay. Original warehouse stays read-only: no original 007/binding/audit deployment. Isolated-copy migration/acceptance is authorized; contradictory/missing evidence stays BLOCKED without repair. Test, commit/push, verify final exact-SHA CI and stop for batch review. Distinguish author self-check, isolated acceptance and pending original deployment; never self-declare independent PASS or R1 FINAL PASS. R2 and Phase1C.2 stay closed. No full backfill, strategies, signals, backtests, portfolio, broker or orders.

Use `src/astock/` for Python, `tests/` for pytest, `config/` for versioned configuration, `sql/` for schema, `docs/` for contracts and governance, and `skills/` for workflows. Local data belongs in `data/{raw,curated,warehouse}/`; generated outputs belong in `reports/`.

## Development & Style

Use Python 3.12 and project-local uv. From the repository root, `export PATH="$PWD/scripts:$PATH"`, then `uv sync --locked`, `uv run pytest`, `uv run astock doctor`, and `uv run astock data contracts`. The wrapper keeps tool storage local. Use four-space indentation, type hints, `snake_case` functions/modules, and `PascalCase` classes. No formatter/linter is configured. Explain necessary new dependencies before adding them.

## Data Integrity

Never use future information. Model time-sensitive data point-in-time; distinguish `period_end`, `published_at`, `available_at` and effective intervals. Do not silently apply today's knowledge historically. Retain delisted securities and historical ST/risk-warning, suspension, board/listing and industry membership. Identify every source; keep raw data append-only/immutable where practical. Derived features must be reproducible from stored sources. Follow `docs/data_contract.md`.

## Execution & Research

Future execution/backtests must model applicable T+1, suspensions, board/ST rule changes, IPO exceptions, lots/order constraints, costs, slippage and overnight gaps. Never assume limit-up buys or limit-down sells are executable. Historical rules need effective dates.

Version strategy parameters in configuration, never here. Register hypotheses and changes before experiments; evaluate strategy modules separately. Do not optimize against final out-of-sample data or adopt strategies merely because results look good. Preserve historical reports; append corrections with provenance.

## Tests & Contributions

Name tests `test_*.py`. Test trading rules, time availability, historical rules and explicit data-quality assumptions when implemented. Run the full suite and doctor before review. Use imperative, focused commit subjects, e.g. `chore: establish astock phase-0 foundation`. PRs explain purpose, validation, linked issues, deviations and configuration/migration impacts; include screenshots for UI changes.

## Secrets

Keep `.env` local. Never send token through chat; live requests require `--live` and exact pinned HTTPS. Never commit or print secrets in logs/reports, request brokerage passwords, or introduce broker credentials in this phase. Commit placeholders only. Public Git must exclude raw datasets, private reports, balances, holdings and personal execution history; use ignored `private/` or `data/private/`. Lightweight sanitized review evidence belongs in `docs/reviews/`.
