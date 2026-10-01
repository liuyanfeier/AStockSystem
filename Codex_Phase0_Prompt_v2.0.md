# Codex 第一次正式任务 Prompt v2.0
## AStockSystem — Phase 0: Repository Foundation & Governance

把下面整段原样交给 Codex。目标是**只建地基，不实现任何交易策略，不下载真实行情，不接券商，不自动下单**。

---

You are working on a long-lived personal A-share research system named **AStockSystem**.

This is **Phase 0 only: repository foundation, governance, data contracts, schema skeleton, and testability**.

Do not implement stock selection, signals, backtests, broker integration, live trading, or real data ingestion in this task.

## 0. Working principles

Before changing anything:

1. Inspect the current repository and report what already exists.
2. Preserve useful existing files and do not overwrite user work unnecessarily.
3. Do not use destructive shell commands.
4. Do not install or modify global system packages.
5. Use project-local tooling only.
6. If `uv` is not available, stop and report that clearly instead of installing it globally.
7. Do not request or use any real credential.
8. Do not push to any remote repository.
9. Do not create broker APIs, order submission code, or automation that can place trades.
10. Do not implement any trading strategy or optimize any parameter.

The target machine is macOS.

---

## 1. Technology baseline

Use:

- Python 3.12
- `uv`
- src-layout package
- pandas
- numpy
- duckdb
- pyarrow
- pydantic
- pydantic-settings
- typer
- httpx
- tenacity
- pytest
- PyYAML

Do not add extra dependencies unless they are clearly necessary. If you believe another dependency is needed, explain why before adding it.

Do not add TA-Lib, Backtrader, vectorbt, machine-learning frameworks, web frameworks, Kafka, Redis, Docker, Kubernetes, or databases other than DuckDB in Phase 0.

---

## 2. Project structure

Target a clean structure close to:

```text
AStockSystem/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env.example
│
├── config/
│   ├── data_sources.yaml
│   ├── regime.yaml
│   ├── risk.yaml
│   └── universe.yaml
│
├── docs/
│   ├── architecture.md
│   ├── data_contract.md
│   ├── data_dictionary.md
│   ├── risk_constitution.md
│   ├── strategy_changelog.md
│   └── research_hypotheses.md
│
├── sql/
│   └── 001_foundation_schema.sql
│
├── src/
│   └── astock/
│       ├── __init__.py
│       ├── settings.py
│       ├── paths.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py
│       ├── data/
│       ├── features/
│       ├── regime/
│       ├── sectors/
│       ├── screening/
│       ├── catalysts/
│       ├── portfolio/
│       ├── backtest/
│       └── reports/
│
├── tests/
│   ├── test_settings.py
│   ├── test_paths.py
│   ├── test_schema.py
│   └── test_cli.py
│
├── data/
│   ├── raw/
│   ├── curated/
│   └── warehouse/
│
├── research/
├── reports/
└── skills/
    └── a-share-research/
        └── SKILL.md
```

You may adjust small details if there is a clear engineering reason, but document every deviation.

---

## 3. `AGENTS.md`: non-negotiable engineering constitution

Create or update `AGENTS.md`.

It must be concise and contain these rules in clear language:

### Data integrity

- Never use future information.
- All time-sensitive data must be modeled point-in-time.
- Distinguish at minimum:
  - `period_end`
  - `published_at`
  - `available_at`
- Historical research must not silently use today's knowledge.
- Retain delisted securities in historical universes.
- Preserve historical ST/risk-warning status.
- Preserve historical suspension status.
- Preserve historical board/listing status.
- Preserve historical industry membership when used in research.
- Derived features must be reproducible from stored source data.
- Raw source data must be treated as append-only/immutable whenever practical.
- Every data source must be identifiable.

### A-share execution realism

Backtests and future execution logic must explicitly model, where applicable:

- T+1 restrictions
- suspensions
- board-specific price limits
- risk-warning/ST rule changes
- IPO/new-listing special rules
- non-executable limit-up buys
- non-executable limit-down sells
- trading lots / order-size constraints
- transaction costs
- slippage
- overnight gap risk

Current rules must never be retroactively applied to historical periods without effective dates.

### Research discipline

- Strategy parameters must be version-controlled.
- Historical reports must not be rewritten after the fact.
- Every strategy change must have a documented hypothesis.
- Do not optimize against the final out-of-sample period.
- Do not introduce a strategy because a backtest “looks good” without explaining the hypothesis.
- Strategy modules must be evaluated separately.
- No live broker order placement in V0.1.
- No strategy implementation in Phase 0.

### Security

- Secrets never go into Git.
- `.env` is local only.
- Never print secrets into logs or reports.
- Do not request brokerage passwords.
- No broker credentials are part of this project in Phase 0.

### Testing

- Trading-rule logic must have tests.
- Time-availability logic must have tests.
- Historical-rule logic must have tests.
- Data-quality assumptions must be explicit and testable.

Do not put concrete trading parameters such as MA windows, stop-loss percentages, or stock-picking thresholds into `AGENTS.md`.

---

## 4. `.env.example` and settings

Create `.env.example` with placeholders only:

```text
TUSHARE_TOKEN=
ASTOCK_DATA_DIR=
ASTOCK_DB_PATH=
```

Never create a real `.env`.

Implement typed settings using `pydantic-settings`.

Requirements:

- no secret is required for Phase 0 tests;
- sensible local defaults for data paths;
- project paths should be centralized in one module;
- no hard-coded absolute user path.

---

## 5. Configuration files

Create minimal, documented placeholder configs.

### `config/data_sources.yaml`

Only define source names and roles, for example:

- primary market/fundamental source
- official filing verification source
- backup/cross-check source

Do not put real API keys in YAML.

### `config/regime.yaml`

Create schema/placeholders only.

Do not invent final market-regime weights or thresholds.

### `config/risk.yaml`

Create a structured placeholder for future:

- account risk budget
- single-trade planned risk
- portfolio open-risk cap
- sector/theme concentration limit
- special-situation risk multiplier

Do not set these values as “proven optimal”.

If example values are needed for schema demonstration, mark them explicitly as examples and disabled by default.

### `config/universe.yaml`

Create future universe categories:

- core
- special_situations

Do not yet implement stock filtering logic.

---

## 6. Documentation

### `docs/architecture.md`

Describe the intended system boundary:

```text
Data sources
→ PIT warehouse
→ market/industry/theme analysis
→ candidate discovery
→ fundamental/catalyst research
→ strategy-specific setup
→ risk filter
→ trade plan
→ manual human confirmation
→ manual broker execution
→ execution log
→ review / attribution
```

Explicitly state:

- ChatGPT/research layer interprets information and reviews strategy.
- Codex/software layer implements, tests, runs, and reports.
- Git + database + generated reports are the shared source of truth.
- Mac is the research node.
- Broker execution remains manual in early phases.

### `docs/data_contract.md`

Define general rules for every future dataset:

- source
- natural key
- time fields
- availability semantics
- revision semantics
- unit
- timezone
- null policy
- duplicate policy
- data-quality checks
- PIT behavior

Explain the difference between:

- event time
- publication time
- first availability time
- effective time

### `docs/data_dictionary.md`

Create the initial table dictionary described below.

### `docs/risk_constitution.md`

Create a template, not a finished trading system.

Sections should include:

- purpose
- planned risk
- gap/stress risk
- portfolio risk
- concentration
- add-on rules
- stop-moving rules
- behavior violations
- drawdown response
- approval/change log

Do not invent “optimal” numeric limits.

### `docs/strategy_changelog.md`

Create an append-only template with:

- date
- strategy
- version
- change
- hypothesis
- evidence
- approval status
- implementation commit
- validation result

### `docs/research_hypotheses.md`

Create a template with:

- hypothesis_id
- created_at
- question
- economic/behavioral rationale
- data required
- parameter family
- research period
- validation period
- OOS period
- result
- decision
- notes

---

## 7. Foundation database schema

Create `sql/001_foundation_schema.sql`.

It must be valid DuckDB SQL and executable in a fresh local DuckDB database.

Only create foundational/governance tables for Phase 0.

At minimum define:

### `security_master`

Suggested concepts:

- security_id
- ts_code
- symbol
- name
- exchange
- board
- list_date
- delist_date
- security_type
- source
- valid_from
- valid_to

### `trade_calendar`

- exchange
- calendar_date
- is_open
- previous_open_date
- source

### `market_rule_history`

This table is important.

It should be capable of representing historical changes in:

- exchange
- board
- security/risk-warning status
- effective_from
- effective_to
- price-limit rule
- settlement/T+N rule
- lot-size rule
- IPO/new-listing special rule
- notes
- source

Do not hard-code current rules as if they always applied historically.

### `data_quality_log`

- run_id
- dataset
- checked_at
- check_name
- severity
- passed
- observed
- expected
- details

### `research_hypothesis`

Represent the hypothesis fields from the documentation.

### `schema_version`

Track schema version/migration identity.

Use appropriate primary/unique keys where DuckDB supports the intended semantics.

Do not yet create live-order or broker tables.

Do not yet create strategy-signal tables.

Do not yet create market data ingestion tables unless absolutely necessary for schema consistency.

---

## 8. CLI: diagnostic only

Create a small Typer CLI.

Entry point:

```bash
uv run astock doctor
```

The `doctor` command should only report:

- Python version
- project root
- configured data directory
- configured DuckDB path
- whether a Tushare token is configured: YES/NO only
- whether required project directories exist
- whether the foundation schema file exists
- whether DuckDB can create an in-memory database
- overall PASS/FAIL

Never print a token.

Do not download data.

Do not contact Tushare.

Do not contact any external API.

---

## 9. Tests

Create meaningful tests.

At minimum verify:

### Settings

- settings can load with no real secrets;
- secret values are not represented in normal diagnostic output.

### Paths

- project-relative defaults work;
- expected directories can be resolved safely.

### Schema

- `001_foundation_schema.sql` executes successfully in an in-memory DuckDB database;
- expected foundation tables exist;
- rerunning the schema should either be safely idempotent or fail in an explicitly documented, controlled way.

Prefer idempotent schema creation if cleanly achievable.

### CLI

- `astock doctor` runs successfully in the Phase 0 environment;
- it does not expose a token.

Do not write fake strategy tests because no strategy exists yet.

---

## 10. Git and ignore rules

If this directory is not already a Git repository, initialize it.

Do not push anywhere.

`.gitignore` must exclude at minimum:

```text
.env
*.duckdb
*.db
data/raw/**
data/curated/**
data/warehouse/**
reports/**
__pycache__/
.pytest_cache/
.venv/
.DS_Store
```

Keep placeholder `.gitkeep` files where needed so the intended directory tree remains visible.

Do not modify the user's global Git configuration.

Do not commit automatically unless Git author identity is already configured locally and there are no existing uncommitted user changes that would be mixed into the commit.

If a clean commit is safe, use a commit message similar to:

```text
chore: establish astock phase-0 foundation
```

Otherwise leave changes uncommitted and report why.

---

## 11. Skill skeleton

Create:

```text
skills/a-share-research/SKILL.md
```

This is only a skeleton for future research workflow.

It should define the order of research:

```text
1. Verify timestamps / information availability
2. Market context
3. Industry + theme context
4. Primary-source verification
5. Business / fundamentals
6. Catalyst / expectation change
7. Price / relative strength / setup
8. Risks / invalidating evidence
9. Trade-plan readiness
```

Do not include stock recommendations.

Do not include fixed numeric buy/sell thresholds.

Do not claim any strategy has positive expectancy.

---

## 12. README

Create a concise README that explains:

- what AStockSystem is;
- what Phase 0 contains;
- what it explicitly does NOT contain;
- installation with `uv`;
- running tests;
- running `astock doctor`;
- where secrets belong;
- the current roadmap:
  - Phase 0 Governance
  - Phase 1 Data Foundation
  - Phase 2 Market / Sector Radar
  - Phase 3 Strategy Prototypes
  - Phase 4 OOS / Walk-forward
  - Phase 5 Paper + Small Live
  - Phase 6 Intraday
  - Phase 7 Broker API

State prominently:

> AStockSystem is a research and risk-management project. It does not guarantee investment returns.

---

## 13. Validation before finishing

Before you finish:

1. Run dependency sync.
2. Run all tests.
3. Run `uv run astock doctor`.
4. Execute the foundation schema against a fresh in-memory DuckDB database.
5. Check `git status`.
6. Inspect for accidental secrets.
7. Inspect for unnecessary dependencies.
8. Inspect for accidental strategy implementation.
9. Inspect for any live trading or broker code.

Fix issues before reporting completion.

---

## 14. Required final response format

At the end, output one concise report with these exact sections:

```text
PHASE 0 STATUS
PASS / PARTIAL / BLOCKED

WHAT I CREATED
...

TEST RESULTS
...

DOCTOR RESULTS
...

PROJECT TREE
...

DESIGN DECISIONS
...

DEVIATIONS FROM REQUEST
...

RISKS / OPEN QUESTIONS
...

GIT STATUS
...

WHAT I DID NOT DO
...

RECOMMENDED NEXT TASK
...
```

For `PROJECT TREE`, show enough depth to verify the architecture, but do not dump virtual environments or ignored data.

For `WHAT I DID NOT DO`, explicitly confirm:

- no real market data was downloaded;
- no strategy was implemented;
- no broker API was created;
- no live-order functionality was created;
- no secret was requested or stored.

Then **stop**.

Do not begin Phase 1 automatically.

Do not implement Tushare ingestion until the user and reviewer approve Phase 0.
