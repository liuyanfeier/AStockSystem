# Phase 0 Completion Report

日期：2026-09-30（Asia/Shanghai）。本报告记录工程验收，不代表 reviewer 已批准进入下一阶段。

## PHASE 0 STATUS

**PASS — 工程验证通过，等待人工 REVIEW。**

## WHAT I CREATED

- 项目内 uv 0.12.21、受管理的 Python 3.12.14 和 `.venv`；无全局软件或 shell 配置改动。
- src-layout Python 包、锁文件、集中路径管理、类型化设置、只读离线 doctor。
- 362 词的 `AGENTS.md` 工程宪法、README、空凭据示例和 Git 忽略规则。
- 四份默认禁用的配置、六份架构／治理文档和研究 Skill 骨架。
- 六张基础表的事务化、幂等 DuckDB SQL；五个测试模块与离线测试环境。
- 本地 Git 仓库；两份用户规划原文完整保留。

## TEST RESULTS

`uv sync --locked --offline` 成功；`uv run --offline --frozen pytest`：**58 passed，2.05 秒**。

| 测试模块 | 数量 | 主要行为 |
|---|---:|---|
| test_settings.py | 6 | 无秘密、空值默认、根目录 dotenv、环境优先及秘密序列化排除 |
| test_paths.py | 8 | 与 cwd 无关、存储覆盖、无创建副作用、内部路径穿越／符号链接拒绝 |
| test_schema.py | 33 | 六表范围、重复执行、版本保留、主键与时间／区间／研究分段约束 |
| test_cli.py | 10 | PASS／FAIL、token 脱敏、只读、缺目录／schema／数据库能力等失败 |
| test_config.py | 1 | YAML 格式、默认禁用、风险／权重／股票池条件未设定 |

Python 网络连接与 DNS 在测试中被拒绝。所有测试数据为合成数据，不使用实际证券或凭据。

独立于 pytest，在新内存 DuckDB 连续执行 SQL 两次，六张表均存在，schema_version 仅一行。Skill frontmatter／结构校验通过。敏感信息模式检查和生产代码人工范围检查通过；检查不是通用秘密检测工具的替代品。

## DOCTOR RESULTS

`uv run astock doctor`：**Overall: PASS**，退出码 0。

- Python 3.12.14，base prefix 位于项目 `.tools/python/`。
- 所有要求目录和基础 schema 文件存在。
- 默认数据目录 `data/`，数据库路径 `data/warehouse/astock.duckdb`。
- Tushare token configured: **NO**。
- 内存 DuckDB 能力通过；没有创建磁盘数据库。
- 从项目外目录直接运行已安装 CLI 也为 PASS。

doctor 不执行 SQL 建表，只检查 schema 文件存在与数据库能力；SQL 有独立验收，避免诊断变成初始化工具。

## PROJECT TREE

忽略 `.git/`、`.tools/`、`.venv/`、缓存和 editable 构建元数据。

```text
AStockSystem/
├── AGENTS.md
├── AStockSystem_Trading_System_Review_v1.0.md
├── Codex_Phase0_Prompt_v2.0.md
├── README.md
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
├── scripts/uv
├── config/
│   ├── data_sources.yaml
│   ├── regime.yaml
│   ├── risk.yaml
│   └── universe.yaml
├── docs/
│   ├── architecture.md
│   ├── data_contract.md
│   ├── data_dictionary.md
│   ├── risk_constitution.md
│   ├── strategy_changelog.md
│   ├── research_hypotheses.md
│   └── phase0_report.md
├── sql/001_foundation_schema.sql
├── src/astock/
│   ├── __init__.py
│   ├── paths.py
│   ├── settings.py
│   ├── cli/{__init__.py,main.py}
│   └── data/, features/, regime/, sectors/, screening/,
│       catalysts/, portfolio/, backtest/, reports/
│       （每个目录仅有占位 __init__.py）
├── tests/
│   ├── conftest.py
│   ├── test_settings.py
│   ├── test_paths.py
│   ├── test_schema.py
│   ├── test_cli.py
│   └── test_config.py
├── data/{raw,curated,warehouse}/.gitkeep
├── research/.gitkeep
├── reports/.gitkeep
└── skills/a-share-research/SKILL.md
```

## DESIGN DECISIONS

1. Prompt v2.0 控制当前范围；路线图统一为 Phase 0～7，不沿用总 REVIEW 的旧编号或 Phase 0+1 表述。
2. 生效区间为 [from, to)，知识时间独立为 published_at／available_at；未知发布时间不能变成虚构的历史可用时间。没有财务表，所以本轮不增加无意义的 period_end 列。
3. 主表、日历和规则允许来源／可用时间版本；研究假设用 revision 保留原登记及后续结果。
4. 仅建六表；除 schema_version 元数据外不种入记录。规则描述并非执行引擎。
5. 所有风险配置禁用且未设值；示例预算没有转成默认值。
6. 路径按源码仓库定位，显式外部存储可以配置，内部资源不允许逃逸仓库。
7. setuptools 仅用于标准 editable 构建；未增加 formatter、服务框架或迁移引擎。
8. httpx、tenacity、pandas、NumPy、PyArrow 等按规格安装，但 Phase 0 不启用其接入／分析用途。逐项依赖说明在 README。

## DEVIATIONS FROM REQUEST

- 用户随后授权准备环境，因此采用项目内 uv／Python 安装，覆盖原 Prompt 的“uv 缺失即停止”要求。增加 `scripts/uv` 以保持缓存和解释器安装目录在项目内，不修改 shell profile。
- `.python-version` 固定为本轮准备的 3.12.14；仍符合 Python 3.12 基线。
- 首次测试 57 通过、1 失败：DuckDB Python 读取 TIMESTAMPTZ 需要 pytz。已先说明原因，再增加唯一额外运行依赖 `pytz`，重跑 58 项全部通过。
- 增加独立配置测试模块、研究假设修订键和知识时间字段，验证配置未启用及版本不丢失；无策略实现。
- 增加本治理验收报告。没有安装全局 Skill，仅保留要求的仓库骨架。

## RISKS / OPEN QUESTIONS

- 时间字段和契约不证明供应商具备完整 PIT 历史；Phase 1 需核验权限、退市／状态／行业历史和公告精度。
- 当前 DDL 不实现跨行区间重叠检测、冲突规则选择、PIT 查询或预登记工作流；本轮测试只证明已实现约束与存储行为。
- 幂等 DDL 不升级或验证不兼容的既有表。后续变化需要独立迁移及验收。
- schema 与治理文件留在源码仓库，当前仅支持 editable checkout；没有独立 wheel 部署要求。
- 尚无真实数据／报告备份与不可变归档机制；需要在真实接入前确定。
- 原方案中的实时行情价格、交易规则和学术引用未在本轮复核；不将其作为已验证规则数据。
- 风险宪法未批准。数值、预算单位、策略 Gate、退出参数及真实账户费用仍待研究层定义。

## GIT STATUS

本地仓库已初始化，无 commit、无 remote、无 push；所有项目文件保留为未暂存的新文件。未自动提交，避免将两份既有用户规划混入代理创建的提交。未修改全局 Git 配置。

忽略规则验证：`.env`、`.env.local`、`.tools/`、`.venv/`、数据库、下载数据和生成报告被排除；`.env.example` 与数据／报告目录 `.gitkeep` 可进入 Git。

## WHAT I DID NOT DO

- 没有下载真实行情或接入 Tushare／外部市场数据 API。
- 没有实现策略、信号、选股器、回测器或参数优化。
- 没有创建券商 API 或 live-order 功能。
- 没有请求或保存真实秘密，没有创建项目 `.env`。
- 没有创建磁盘数据库、填充真实历史交易规则、启动自动任务或进入 Phase 1。

软件工具和依赖下载仅用于本阶段环境准备；测试字符串不是真实凭据。

## RECOMMENDED NEXT TASK

先由用户和 reviewer 审查本报告、数据契约、六表 schema 与风险空模板。通过后单独下达 Phase 1 规格，先核验数据源覆盖及 PIT 可获得性，再实现接入与数据审计。**本次执行到此停止。**
