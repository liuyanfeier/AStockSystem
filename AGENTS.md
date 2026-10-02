# Repository Guidelines

## Scope & Structure

AStockSystem is a macOS A-share research project. Phase 1C.1 completed 133 bounded requests; its real-data gate remains BLOCKED. The user relayed independent G2-fix/G3-copy REVIEW PASS at exact SHA `ac622718d978b85f90680694ec1cc8e0a3bd8b1a` and separately authorized original deployment. Reviewed additive 007, 133 completion bindings and 133 upgrade audits are now deployed; original offline acceptance passed. See `docs/reviews/2026-10-02-phase1c1-r1-g3-final-review.md` and its authorization record. Complete sanitized final commit/push and exact-SHA CI, then stop as R1 FINAL_REVIEW_READY for independent FINAL REVIEW; never author-issue FINAL PASS. Preserve receipts/attempts/status/timestamps, all 17 old tables and schema_version1–6, raw/curated/lineage, 1,102 protected files, frozen identity, SQL001–007, specifications and old reviews. Use managed exclusive ownership and lifecycle rules in `docs/phase1c1_writer_lifecycle.md`; WAL, conflict or changed/missing evidence blocks without guessed repair or original replacement. Deployment authorization is exhausted after this batch; no further original writes without approval. Market API budget zero: no capture/resume/replay, metadata fetch, curation or DQ regeneration. R2 LOCKED, Phase1C.2 CLOSED; no backfill, strategies, signals, backtests, portfolio, broker or orders.

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
