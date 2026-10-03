# Repository Guidelines

## Scope & Structure

AStockSystem is a macOS A-share research project. R1 FINAL independently passed at `cc458ce2e8229dcc914e9a45ae2ac6186f48c45c`. The user authorized R2-A under `docs/remediation/phase1c1/Codex_Phase1C1_R2_Batched_Prompts_v1.1.md`; see `docs/reviews/2026-10-02-phase1c1-r2-a-authorization.md`. Freeze concrete design before implementing provider/episode resolution, DQ policy, context/publication/quarantine/audits and synthetic regressions. A replaces intermediate G0/G1/G3/G4 pauses and permits G2 proposals only. Original warehouse, raw, old252 curated/lineage, frozen identity/receipts/audits, SQL001–007 and old specifications/reviews remain immutable; no real new bindings/episodes or generations take effect. Use scoped managed connections per `docs/phase1c1_writer_lifecycle.md`. Missing evidence is EVIDENCE_REQUIRED, conflict is CONFLICT; never infer aliases, merge company successors, rewrite native identifiers or relax NULL/tolerances. Zero market/provider requests, including metadata/mapping/calendar; no capture/resume/replay. Read-only official/provider documentation is allowed. Complete all A work with focused commits, one final full offline verification/secret scan and final exact-SHA CI, then stop as R2_A_REVIEW_READY for independent policy/context/approved_case_set review. R2-B NOT_AUTHORIZED, real-data gate BLOCKED, Phase1C.2 CLOSED; no backfill, strategies, signals, backtests, portfolio, broker or orders.

Current repair batch: F1–F3 from the retained 2026-10-03 independent review and consolidated fix prompt; see `docs/reviews/2026-10-03-r2-a-fixes-authorization.md` and frozen design addendum 3. Complete together with synthetic regressions, offline preservation/secret checks and final exact-SHA CI; retain previous review packages. No original deployment or real R2 approvals.

Latest authorized batch supersedes that historical repair scope: R2-B time-integrity P1 engineering fix per `docs/reviews/2026-10-03-r2-b-time-integrity-fix-authorization.md` and new frozen addendum 4. Repair both resolver digest and pinned-member time comparison, require explicit v2 protocol/design pins, run managed synthetic SQL/reopen/rebuild/tamper regressions and actual-material read-only checks. Preserve all v1 approvals and failed isolation; no original writes or author production approval. Deliver once as R2_B_TIME_INTEGRITY_FIX_REVIEW_READY with final exact-SHA CI; real B execution awaits matched reviewer reapproval. Zero market requests; Phase1C.2 CLOSED.

Matched-v2 execution authorization now supersedes that waiting boundary: see `docs/reviews/2026-10-03-r2-b-matched-v2-resume-authorization.md` and the verbatim matched-v2 resume prompt. Independent repair PASS and actual approval pin reviewed/Context SHA 0251e485396fb9e1a4214f71a298ad2777ebde90. After verified007 backup and fresh full isolated rehearsal, deploy approved008–010/import/register on original, publish two explicit COMPLETE generations, exact-evidence DQ and four-timezone same-Context rebuild; preserve original19 tables,1102 files, all old approvals/failed isolates/reviews. No source/schema/policy/test/design changes or author approval. Finish full offline checks and final exact-SHA CI, deliver once as R2_FINAL_REVIEW_READY, then stop. Zero market requests; real-data gate BLOCKED, Phase1C.2 CLOSED.

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
