# AStockSystem

长期个人 A 股投资研究与交易决策系统：市场环境 → 行业/主题与催化 → 个股研究 →
入场和退出计划 → 组合风控 → 人工执行 → 交易日志、回测与复盘。
用户拥有最终风险与交易决策；系统不保证收益、不自动下单。

## 从这里开始

- [长期项目宪章 V2](docs/PROJECT_CHARTER.md)：完整业务目标。
- [当前状态](docs/CURRENT_STATE.md)：已有软件、真实数据与缺口。
- [业务路线](docs/ROADMAP.md) · [架构与迁移](docs/ARCHITECTURE.md)。
- [Research V2 市场与行业雷达](docs/RESEARCH_V2.md) · [原Research V1契约](docs/RESEARCH_V1.md)。
- [Git内真实业务报告与合成样例](docs/research/results/2026-10-13-research-v2/README.md)。
- [代码迁移清单](docs/CODE_MIGRATION.md) · [存储治理](docs/STORAGE_GOVERNANCE.md)。
- [历史证据索引](docs/HISTORY.md) · [本次清理记录](docs/REPOSITORY_RESET.md)。
- [当前 Review 入口](docs/REVIEW.md)：交付范围、提交基线、验证证据及未完成项。
  审查时提供 PR 或分支链接即可，从此入口读取材料并核查实际 diff 和当前 HEAD 的 CI。

## 当前能做什么

已有独立Research Store、来源链/用途/连续窗口检查、默认20/60候选卡、私有持仓/交易日志，
以及按供应商当前池和申万2021一级行业生成市场宽度、行业扩散、板块差异和前日变化的雷达。
沿用同一features/screen/service；未引入第二套数据平台。

已有10股/2指数128日真实报告，4候选/6排除；雷达复算仍是有限样本，真实行业来源未采集。
完整行业雷达当前只有合成软件验收，不能称真实全市场通过。业务报告已脱敏提交Git供GPT Review，
Raw/DB、实际许可、账户与持仓/个人成交仍私有。新[299请求方案](docs/RESEARCH_V2_ACQUISITION.md)
尚未获批，当前新增真实市场API调用0。行业真实覆盖、公司研究/催化、正式交易计划/退出、
组合风控和策略验证仍须逐步建设，不自动下单、不继承旧全历史许可。

## 本机运行

Python 3.12；使用 uv.lock 和项目本地工具，不修改系统 Python。

~~~bash
export PATH="$PWD/scripts:$PATH"
uv sync --locked
uv run --offline --frozen astock doctor
uv run --offline --frozen astock data contracts
uv run --offline --frozen pytest
~~~

首次同步会下载软件依赖。已有环境可直接离线运行上述检查；doctor 与 data contracts
不采集行情、不创建磁盘数据库。仓库仅支持 editable checkout，schema/契约随仓库使用。
历史统一数据契约可通过 uv run --offline --frozen python -m astock.phase1 specs 只读查看；
具体历史工具见 [Phase1 操作资料](docs/phase1/operations.md)，其中生产命令不是当前执行指令。

TUSHARE_TOKEN 只存本地 .env，诊断仅显示有无。ASTOCK_DATA_DIR 默认 data/，
ASTOCK_DB_PATH 默认 data/warehouse/astock.duckdb；Research Store 使用 data/private/research-v1/research.duckdb，
不迁移或写入这个旧库。当前四份顶层 YAML 均 disabled，只是待验证的业务配置骨架。

## Research V1

~~~bash
uv run --offline --frozen astock research --help
uv run --offline --frozen astock research import --bundle 私有输入bundle.json
uv run --offline --frozen astock research report --bundle 输出的bundleID \
  --as-of 带时区的研究截止时间 --watch 原生股票代码
uv run --offline --frozen astock research journal-add --event 私有人工记录.json
~~~

输入schema、保留来源adapter与复现见[Research V1](docs/RESEARCH_V1.md)。
报告存 reports/private/research-v1/，行情不足就缺项或空列表，观察卡不生成订单。
原10股窗口已真实采集并独立接受；新[全市场预算](docs/RESEARCH_V2_ACQUISITION.md)待批准。
雷达运行、增量来源与Git业务输出见[Research V2](docs/RESEARCH_V2.md)。

## 仓库边界

src/、tests/、config/、sql/、docs/ 是版本资产；data/、private/、reports/
存真实来源、私有记录和生成结果，受 Git 忽略。整体容量目标 50GB，上限 100GB。
公开 GitHub 不含行情原始行、凭据、账户、持仓、交易历史或私密报告。

[AGENTS.md](AGENTS.md) 是长期开发规范。当前用户授权和项目宪章决定新任务；
历史 Phase1 Prompt、审批与修复报告保留来源价值，不再自动主导业务路线。
[旧总 REVIEW](AStockSystem_Trading_System_Review_v1.0.md) 保留为历史业务设计依据。


Research V1.1支持九类供应商原JSON直接入库、连续窗口候选Setup观察和人工持仓复盘提醒。
`uv run --offline --frozen astock research capture`默认只显示39请求待批准清单；
`capture-import --capture-dir 私有捕获目录`离线转换/导入；报告仍走research report。
真实新API未授权，128日默认20/60验证目前是合成软件验收，真实来源仍是既有5股3日样本。
当前整批变更/验证与数据边界见[REVIEW](docs/REVIEW.md)，一次采集预算见
[RESEARCH_ACQUISITION](docs/RESEARCH_ACQUISITION.md)。
