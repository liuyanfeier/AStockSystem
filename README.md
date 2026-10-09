# AStockSystem

**AStockSystem is a research and risk-management project. It does not guarantee investment returns.**

本项目在 Mac 上建立可审计的 A 股研究、风险管理与交易训练基础。**Phase 0 已获 REVIEW 通过，Phase 1C.1 工程修复已独立关闭，Phase 1C.2 已开始；研究数据准入仍为 BLOCKED。** 阶段依据见 [关闭与启动决定](docs/remediation/phase1c2-startup/2026-10-08_Phase1C1_Closure_And_Phase1C2_Start_Decision.md)。工程关闭、采集许可和研究准入分别验收，不能互相替代。

截至 **2026-10-09**，126 个旧备份已同字节脱离硬链接并通过独立维护审查，主文件 inode 和历史内容保留，严格保护检查通过。已审查代码为 `9784f86cd6b2f647f54b2a31454dd8ec9b83b20b`，对应 [CI：916 passed](https://github.com/liuyanfeier/AStockSystem/actions/runs/37895930473)。最新直接授权获得正常审批，原 capture store 已追加五张 v3 表。首个 SSE 2013 年日历请求返回 HTTP 200、provider code 0 和 365 行，但响应新增字段被冻结解析器拒绝：**1 次真实请求、1 个 FAILED、0 回执、27 个成员未发送**。已按首错停止；原响应和消费事实保留，不重试、不放宽解析规则。driver 的异常日志记录同时存在重复键错误，需单独审查。

原 warehouse/旧 metadata、旧 capture 六表、所有历史文件及 171 个固定证据均保留。现有 402,060 条 DQ findings 和身份/session/reference 研究阻断未清除。行情六接口仅完成离线申请准备，license=false；全量回填、策略、回测及券商交易均未开始。固定 21 个交易日、7 个日历小窗口和 133 次请求属于历史演练，禁止重跑。早期交易仍由人确认并在券商终端手工执行。

历史审查材料继续保留：[演练报告](docs/reviews/2026-10-01-phase1c1-review.md)、[R1-G0 设计](docs/reviews/2026-10-02-phase1c1-r1-g0-design.md)、[G1 补修](docs/reviews/2026-10-02-phase1c1-r1-g1-fix-review.md)、[G2 独立审查](docs/reviews/2026-10-02-phase1c1-r1-g2-independent-review.md)、[G3 副本交付](docs/reviews/2026-10-02-phase1c1-r1-g3-copy-review.md)、[原库部署授权](docs/reviews/2026-10-02-phase1c1-r1-g3-deployment-authorization.md)及 [R1 最终审查包](docs/reviews/2026-10-02-phase1c1-r1-g3-final-review.md)。这些文档记录当时的审批边界；当前进度以本节及 AGENTS.md 的最新状态为准。

## Phase1 整体工程交付（待独立 Review）

统一版本已实现采集/恢复、证券与状态/规则历史、行情与因果复权、财务 PIT、行业 PIT、质量覆盖、历史查询及重建/增量。作者离线自检 **967 passed（新增51项）**；23个非空合同、62条合成事实及两次同逻辑摘要重建用于软件验收，不能代表真实历史覆盖。原库写入和新增真实市场/元数据请求均为0，旧消费、402,060条DQ和171个冻结pin保持不变。

运行入口为 `uv run --offline --frozen python -m astock.phase1`。查看[操作手册](docs/phase1/operations.md)、[验收矩阵](docs/phase1/acceptance-matrix.md)和[综合报告](docs/reviews/phase1-integrated/report.md)。统一真实申请提出27日历＋17源试点＋6行情，预算50；许可仍为false，需要匹配最终实现的独立批准及人类执行授权。全量财务/行业/vintage/预算仍有外部缺口。

冻结旧driver的异常日志问题保留为历史事实；新统一driver已回归验证主错误保留、次级输出错误披露和首错停止。未重跑旧driver或修改其pin。

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

保留的 [总 REVIEW](AStockSystem_Trading_System_Review_v1.0.md) 是长期背景；[Phase 1C.1 Prompt](Codex_Phase1C1_Implementation_Prompt_v1.0.md)、[R1 规格与逐 Gate Prompt](docs/remediation/phase1c1/README_Phase1C1_R1_R2.md) 和[旧批次授权](docs/reviews/2026-10-02-phase1c1-r1-batch-authorization.md)是历史记录。后续 R1/R2、limited15 和 finite45 工程工作已经完成，不能把旧文档中的 R2 LOCKED 或 Phase1C.2 CLOSED 当作当前阶段。当前采用独立审查、精确成员许可、真实人类授权及运行时保护；旧规划或文档状态更新均不扩大执行范围。原两个 UNKNOWN/UNCERTAIN 禁止重发，133 请求禁止重跑；Calendar28 已在首个 FAILED 后停止；旧driver不得重跑，27个未消费成员及行情6只进入新统一版本的未许可申请，全量回填需具体预算与后续授权。

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

以上两条只验证固定配置。现有 DQ 会写入治理状态，本轮不运行。`astock data slice audit --batch UUID` 是无 token 的只读回执审计；`--legacy-preflight` 检查旧证据而不迁移或放行。原库已授权部署 007，严格回执审计返回 VALID / EXACT；该结果仅证明回执完整性，历史行情的数据语义门继续 BLOCKED。
真实请求、主动中断和恢复已执行完毕，禁止重跑或扩展预算。整理与重建不调用 API。
配置、空表类型、单位、身份区间、隔离、逐行谱系、因果审计及恢复限制见
[整理说明](docs/phase1c1_curation.md)。当前整理输出不能作为已验收研究输入。


G2 的[仓库锁与生命周期政策](docs/phase1c1_writer_lifecycle.md)要求在磁盘连接前取得系统锁，覆盖全部写入入口和文件发布。竞争写入立即 BUSY；只读审计使用共享锁和一致快照。锁不证明历史数据、部分 generation 或大规模执行已经就绪。
