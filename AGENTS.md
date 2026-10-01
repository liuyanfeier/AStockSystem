# Repository Guidelines

## Scope & Structure

AStockSystem is a macOS A-share research project. Phase 1C.0 is complete; Phase 1C.1 permits only the user-approved 21-session historical rehearsal and seven small SSE calendar checks (133 logical requests, one attempt each). Follow Codex_Phase1C1_Implementation_Prompt_v1.0.md and config/slices/phase1c1.yaml. Preserve earlier catalogs/specs, migrations 001–005 and historical reviews. No full backfill, Phase 1C.2, strategies, signals, backtests, portfolio, broker or orders. Stop on identity ambiguity, mapping conflict, lineage break, row cap or schema guessing. Follow the four implementation commits, test, commit/push and verify CI; stop for review.

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
