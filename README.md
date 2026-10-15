# AStockSystem

长期个人 A 股投资研究与交易决策系统：市场环境 → 行业/主题与催化 → 个股研究 →
入场和退出计划 → 组合风控 → 人工执行 → 交易日志、回测与复盘。
用户拥有最终风险与交易决策；系统不保证收益、不自动下单。

## 从这里开始

- [长期项目宪章 V2](docs/PROJECT_CHARTER.md)：完整业务目标。
- [当前状态](docs/CURRENT_STATE.md)：已有软件、真实数据与缺口。
- [系统设计与整体实施计划](docs/SYSTEM_DESIGN.md)：资产取舍、存储生命周期、架构、目标日期和验收。
- [业务路线](docs/ROADMAP.md) · [架构与迁移](docs/ARCHITECTURE.md)。
- [Research V3 公司/催化与条件化决策](docs/RESEARCH_V3.md) · [简明研究摘要](docs/research/results/2026-10-14-company-v3/DECISION_BRIEF.md)。
- [Research V2 市场与行业雷达](docs/RESEARCH_V2.md) · [原Research V1契约](docs/RESEARCH_V1.md)。
- [真实全A股/31行业业务报告](docs/research/results/2026-10-14-real-market-v2/REPORT.md) · [此前真实样本与合成示例](docs/research/results/2026-10-13-research-v2/README.md)。
- [代码迁移清单](docs/CODE_MIGRATION.md) · [存储治理](docs/STORAGE_GOVERNANCE.md)。
- [历史证据索引](docs/HISTORY.md) · [本次清理记录](docs/REPOSITORY_RESET.md)。
- [当前 Review 入口](docs/REVIEW.md)：交付范围、提交基线、验证证据及未完成项。
  审查时提供 PR 或分支链接即可，从此入口读取材料并核查实际 diff 和当前 HEAD 的 CI。

## 当前能做什么

已有独立Research Store、来源链/用途/连续窗口检查、默认20/60候选卡、私有持仓/交易日志，
以及按供应商当前池和申万2021一级行业生成市场宽度、行业扩散、板块差异和前日变化的雷达。
沿用同一features/screen/service；未引入第二套数据平台。

2026-10-14已按用户授权完成002固定299请求：297成功、2失败、0 UNKNOWN、0未尝试。
真实当前池5574股、31行业、128日行情；末日已上市5573、有效价格5561，缺口明确披露。
两份CSI指数身份空返回保留FAILED，离线复用旧已验证的两指数身份，不重发。
默认20/60筛选1347合格，程序排序展示10；18股108项Raw独立数值与新Store重建通过。
完整中文日报/JSON已脱敏入Git供GPT Review；Raw/DB、实际许可及个人记录继续私有。
这批299预算已全部消费，未来新请求需要准确新授权。下一步优先公司基本面/公告催化、交易与退出计划；
组合风险和策略验证继续逐步建设，不自动下单、不继承旧全历史许可。

Research V3已在固定真实截面上形成16只分散研究短名单、8份公司卡、101项有原表定位的财务数字，
含基本面、催化、反面证据、UNKNOWN和条件化入场/退出草案。31份公开披露原始文档保持私有，
必要财务事实、来源URL/Hash与简明日报进入Git。未新增Tushare请求，单日45请求方案只是未授权提案。

## 本机运行

Python 3.12；使用 uv.lock 和项目本地工具，不修改系统 Python。

~~~bash
export PATH="$PWD/scripts:$PATH"
uv sync --locked
uv run --offline --frozen astock doctor
uv run --offline --frozen astock data contracts
uv run --offline --frozen python scripts/managed_pytest.py
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
原10股窗口及旧来源保留；[全市场002方案](docs/RESEARCH_V2_ACQUISITION.md)已执行完毕，不自动滚动采集。
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
历史V1.1试点之后已完成真实128日样本与当前全市场雷达；实际覆盖和未来许可边界以上述当前状态为准。
当前整批变更/验证与数据边界见[REVIEW](docs/REVIEW.md)，一次采集预算见
[RESEARCH_ACQUISITION](docs/RESEARCH_ACQUISITION.md)。
# 当前主线：日常工作流整体实施

真实市场/行业与8家公司研究已形成起点；当前补持续判断、持仓退出、组合风险和复盘。
[三案例决策报告](docs/research/results/2026-10-14-decision-loop-v0/README.md)、
[收盘命令与边界](docs/DECISION_LOOP_V0.md)、[当前状态](docs/CURRENT_STATE.md)。
行情仍截至2026-10-12；真实持仓未知、风险参数未授权、无真实订单。

2026-10-15开始按系统设计连续实施，GPT仅由用户按需介入。首批日常入口把原收盘命令的多个参数放入一个配置，复用原计算与来源验证：

```bash
.venv/bin/astock research daily --profile config/daily/retained-evidence.json --check
.venv/bin/astock research daily --profile config/daily/retained-evidence.json
```

此示例固定重查10月14日研究/10月12日行情，不获取新行情或自动改写日期。`--check`仅校验配置/路径，不打开数据库，不证明行情已可用；正常运行使用新的小型私有Journal和报告目录。后续个人配置放ignored私有目录，不提交账户信息。

M1已增加中文问答录入，并与下一次观察接续：

```bash
.venv/bin/astock research record --profile config/daily/retained-evidence.json
.venv/bin/astock research daily --profile config/daily/retained-evidence.json \
  --observe-now --market-date 2026-10-14
```

`record`只保存你提供的备注、持仓快照或已发生成交；演示成交请使用独立模拟工作区。
明确补录成交后股数才更新持仓；已阅不解除风险。新观察需同时提供时间与行情要求日期，
不联网补行情、不改冻结配置、不产生订单。详见[日常任务说明](docs/DAILY_WORKFLOW.md)和
[完整合成闭环样例](docs/research/results/2026-10-15-daily-workflow/README.md)。
