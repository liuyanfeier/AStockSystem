# Architecture and Phase 0 boundary

## Intended workflow

```text
Data sources → PIT warehouse → market/industry/theme analysis
→ candidate discovery → fundamental/catalyst research
→ strategy-specific setup → risk filter → trade plan
→ manual human confirmation → manual broker execution
→ execution log → review / attribution
```

这是未来流程图，不是已实现功能。Mac 是研究节点；早期由用户在券商终端手工执行，研究软件不持有券商凭据。

## Responsibilities and shared facts

- ChatGPT／研究层解释原始信息、形成研究假设、审查策略与方法学。
- Codex／软件层按规格实现、测试、运行并报告；不能因回测好看自行改变策略。
- 用户拥有风险与最终决策，并批准阶段升级。
- Git 中的规格／配置／代码、DuckDB／Parquet 数据和不可变报告共同构成事实来源。聊天不替代版本记录；尚未配置 GitHub 连接。

## What exists now

Phase 0 仅实现设置、路径管理、诊断 CLI 和基础 SQL。SQL 在内存中验证；没有自动创建磁盘数据库的入口。其余 Python 模块目录是空占位。

数据目录分别预留 raw、curated、warehouse。原始数据未来保持不可变，curated 承载有来源的 PIT 清洗结果；派生特征需记录输入版本、代码、参数和运行标识。

基础表：`security_master`、`trade_calendar`、`market_rule_history`、`data_quality_log`、`research_hypothesis`、`schema_version`。没有行情、策略信号、订单或券商表；不填充真实证券或交易规则。

`doctor` 不访问网络，也不修复目录、创建磁盘数据库或展示原始配置／异常内容。运行 `uv sync` 下载的软件依赖不属于市场数据接入。

## Scope resolution and future gates

本轮以根目录 Phase 0 Prompt v2.0 为准；总 REVIEW 的 Phase 0+1 表述不扩大任务。统一使用 Phase 0～7 正式路线图，Intraday 位于 Phase 6。

突破、回踩、催化启动最终应独立评估。市场状态标签仅用于展示，底层向量用于研究；正式行业与动态主题分开。以上都尚未实现。

Phase 0 验收报告经用户及 reviewer 审查后，才开始 Phase 1 数据接入。届时必须先验证供应商权限、历史覆盖和可重建程度。PIT 契约不能使缺失的历史自动变完整。总 REVIEW 中的价格、规则和论文引用未在本阶段重新核验，不作为已验证数据入库。

## Deliberate limitations

- 仅支持 `uv sync` 安装的 editable checkout；schema 和治理文件留在仓库中，不设计独立 wheel 部署。
- 没有 YAML 风险／策略解析器、PIT 查询引擎、数据检查执行器或迁移框架。
- 相同表结构可以重复建表，但不会自动升级已存在的不同结构；修改已审查 schema 时新增迁移。
- `.gitignore` 排除数据和生成报告。长期不可变归档、备份和校验机制需在产生真实数据／报告前确定；Git 不替代数据备份。
