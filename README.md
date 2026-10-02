# AStockSystem

**AStockSystem is a research and risk-management project. It does not guarantee investment returns.**

本项目在 Mac 上建立可审计的 A 股研究、风险管理与交易训练基础。**Phase 0 已获 REVIEW 通过**；当前已完成 **Phase 1C.1 有界历史演练**，真实数据门为 **BLOCKED**，正在按 Gate 修复审查发现。历史证据见 [演练报告](docs/reviews/2026-10-01-phase1c1-review.md)；当前交付为 [R1-G0 库存与设计](docs/reviews/2026-10-02-phase1c1-r1-g0-design.md)，等待独立设计 REVIEW。

本轮已执行固定 21 个交易日和 7 个小窗口日历检查，共 133 次请求；后续仅审查已有本地证据。已生成带身份隔离和谱系的 Parquet 审查输出，没有全量回填、生产行情表、选股、信号、策略、回测引擎、券商接口或自动下单。后续早期交易由人确认并在券商终端手工执行。

## 本机运行

环境已安装在被 Git 忽略的 `.tools/` 和 `.venv/` 中，不修改系统 Python 或 shell 配置。从项目根目录执行：

```bash
export PATH="$PWD/scripts:$PATH"
uv sync --locked
uv run pytest
uv run astock doctor
```

`scripts/uv` 将 uv 缓存及 Python 安装位置限制在项目内。首次同步需要联网下载软件依赖；这不涉及市场数据。依赖准备好后可以离线验证：

```bash
uv run --offline --frozen pytest
uv run --offline --frozen astock doctor
uv run --offline --frozen astock data contracts
```

`doctor` 只检查 Python、路径、目录、schema 文件和内存 DuckDB；不创建数据目录或磁盘数据库、不调用外部 API。失败退出码为 1。缺少 token 不影响 PASS。`data contracts` 仅校验并列出 `config/contracts/v1/`，未知行数上限显示 UNKNOWN，不读取凭据或下载数据。

## 新机器准备

需要 macOS、curl、tar 和 Git；基线是 Python 3.12。参考 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)。以下固定 uv 版本，按 Mac 架构下载并校验官方包：

```bash
mkdir -p .tools/bin .tools/downloads
case "$(uname -m)" in
  arm64) astock_target=aarch64-apple-darwin ;;
  x86_64) astock_target=x86_64-apple-darwin ;;
  *) printf '%s\n' 'Unsupported Mac architecture'; exit 1 ;;
esac
astock_archive="uv-${astock_target}.tar.gz"
curl -fL "https://github.com/astral-sh/uv/releases/download/0.12.21/${astock_archive}" -o ".tools/downloads/${astock_archive}"
curl -fL "https://github.com/astral-sh/uv/releases/download/0.12.21/${astock_archive}.sha256" -o ".tools/downloads/${astock_archive}.sha256"
(cd .tools/downloads && LC_ALL=C shasum -a 256 -c "${astock_archive}.sha256") &&
  LC_ALL=C tar -xzf ".tools/downloads/${astock_archive}" -C .tools/bin --strip-components=1
export PATH="$PWD/scripts:$PATH"
uv python install 3.12.14 --no-bin
uv sync --locked
```

若下载或校验失败，先解决错误再继续。以 `uv.lock` 为依赖复现依据，不提交 `.tools/` 或 `.venv/`。当前采用 editable checkout；不支持脱离仓库运行的 wheel 部署。

## 配置与秘密

`.env.example` 仅含空占位符，Phase 0 无需创建 `.env`。未来真实凭据只存本地 `.env` 或适当的秘密存储，不发到聊天、不进入 Git。设置加载仓库根目录的 `.env`，进程环境优先；空值采用默认值。

- `ASTOCK_DATA_DIR` 默认 `data/`；相对路径以仓库根目录为基准。
- `ASTOCK_DB_PATH` 未设定时跟随数据目录，默认 `data/warehouse/astock.duckdb`。
- `TUSHARE_TOKEN` 使用秘密类型，诊断仅显示 YES/NO。
- `config/*.yaml` 均 `enabled: false`，`null` 表示未设定，不是零风险或无限额度；尚无运行时策略配置解析器。

## 目录与依赖

`src/astock/` 放代码，`tests/` 放 pytest，`sql/` 放基础 schema，`docs/` 放契约和治理模板，`skills/` 放研究流程骨架；`data/` 与 `reports/` 的内容不会进入 Git。

| 依赖 | 用途 |
|---|---|
| pandas / NumPy | 按规格预留未来结构化计算；Phase 0 不计算因子 |
| DuckDB | 内存诊断、schema 验证和本地谱系治理 |
| PyArrow | 不可变 raw 与类型化 curated Parquet |
| Pydantic / pydantic-settings | 类型校验、环境配置与秘密包装 |
| Typer | 离线诊断与显式有界采集 CLI |
| httpx / tenacity | 固定 HTTPS；旧 probe 至多一次重试，Phase 1C.1 每请求仅一次尝试 |
| PyYAML | 配置文件格式校验；后续配置加载 |
| pytest | 开发测试 |
| pytz | DuckDB Python 驱动读取 TIMESTAMPTZ 的运行时支持；首轮测试发现必需 |
| setuptools | src-layout editable 安装的构建后端 |

没有额外 formatter、linter、Web 服务或回测框架。测试无数值覆盖率门槛，重点是时间约束、主键、配置和诊断行为。

## 路线图与规格优先级

| 阶段 | 范围 |
|---|---|
| Phase 0 | Governance |
| Phase 1 | Data Foundation |
| Phase 2 | Market / Sector Radar |
| Phase 3 | Strategy Prototypes |
| Phase 4 | OOS / Walk-forward |
| Phase 5 | Paper + Small Live |
| Phase 6 | Intraday |
| Phase 7 | Broker API |

保留的 [总 REVIEW](AStockSystem_Trading_System_Review_v1.0.md) 是长期背景；[Phase 1C.1 Prompt](Codex_Phase1C1_Implementation_Prompt_v1.0.md) 记录已完成演练的范围。当前修复由 [R1 规格与逐 Gate Prompt](docs/remediation/phase1c1/README_Phase1C1_R1_R2.md) 控制：R1-G0 仅库存与设计，G1 需独立设计 REVIEW 通过和明确授权；R2 锁定。数据门 BLOCKED，新增市场请求预算为零，不开始 Phase 1C.2。旧规划不扩大本轮任务。

详见 [架构](docs/architecture.md)、[数据契约](docs/data_contract.md)、[数据字典](docs/data_dictionary.md) 与 [风险宪法模板](docs/risk_constitution.md)。

## Phase 1A 安全边界

正式 SDK 默认 HTTP，不能直接用于真实凭据。无凭据探测观察到 HTTPS 证书验证成功并返回鉴权错误；这不是供应商正式 HTTPS 支持声明，也没有验证真实鉴权。详见 [传输审计](docs/reviews/2026-10-01-phase1a-transport-audit.md)。Phase 1B 增加独立 REST client，精确固定 api.tushare.pro，拒绝 HTTP 和全部重定向，保持证书验证且不使用环境代理。

本公开仓库禁止包含 provider token、券商凭据、余额、持仓、个人成交历史、私密报告和原始供应商数据。`private/`、`data/private/`、市场数据及运行报告均被忽略；不要 force-add。审核摘要放在 `docs/reviews/`，只使用脱敏的元数据。

## Phase 1B bounded probe（历史命令，本轮不重跑）

```bash
uv run --offline --frozen astock data probe plan
uv run --offline --frozen astock data probe status
# Only after configuring TUSHARE_TOKEN in local .env outside chat:
uv run --offline --frozen astock data probe run --live
```

`--offline` controls uv dependency resolution; only explicit `--live` enables provider
requests. The fixed plan is 47 logical calls maximum, 1.25 seconds between attempts,
and at most two attempts for eligible transient errors. Missing token performs no
request/storage write. First real request is the September 2026 SSE calendar;
auth/TLS/redirect failure stops. Permissions or unexplained DQ findings prevent PASS.

Raw captures and sidecars stay in ignored `data/raw/`; governance rows alone use
ignored default `data/warehouse/astock.duckdb`. Local aggregate status lives in
ignored `data/private/phase1b/`. Public summaries contain aggregates only. No token
belongs in GitHub Actions. Observed historical records become available at actual
retrieval time, and cannot be used for historical strategy backtests.

## Phase 1C.1 有界演练

```bash
uv run --offline --frozen astock data slice plan
uv run --offline --frozen astock data slice specs
```

以上两条只验证固定配置。现有 DQ 会写入治理状态，R1-G0 不运行；新的只读审计入口尚待设计审查和实现。
真实请求、主动中断和恢复已执行完毕，禁止重跑或扩展预算。整理与重建不调用 API。
配置、空表类型、单位、身份区间、隔离、逐行谱系、因果审计及恢复限制见
[整理说明](docs/phase1c1_curation.md)。当前整理输出不能作为已验收研究输入。
