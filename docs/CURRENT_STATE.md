# 当前状态

核查日期：2026-10-11；开始基线 c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db。
这是代码、文件、数据库与 GitHub CI 的现场核查；不是历史完整覆盖或收益承诺。
本次结果见 [清理记录](REPOSITORY_RESET.md)。

## 已实现与未实现

| 能力 | 实际证据 | 可用于什么 / 缺口 |
|---|---|---|
| 本地环境、设置、CLI | Python 3.12.14、uv.lock、doctor、秘密类型、路径校验 | 可离线诊断；仅 editable checkout |
| 契约与单位 | 旧 v1 12、v2 9 个契约；统一 Phase1 23 个可执行契约 | 真实解码/范围/空值验证；契约数不是数据覆盖 |
| raw / 回执 / durable consumption | 不可变 Parquet/sidecar、首错停止、历史全局消费、原子回执 | 可保留与审计真实来源；已停止批次不重跑 |
| 身份与时间 | identity/provider_identity、availability、R2 resolver、domains | 原生代码、有效区间、as-of、保守知识时间；不凭代码或名字猜映射 |
| 数据库生命周期 | warehouse_connection、系统锁、事务和读写权限 | 新存储可复用；旧库仍只读 |
| 统一数据派生 | pipeline、domains、versions：facts、generation、lineage、coverage、rebuild、increment | 合成/闭合演练机制已实现；本地统一生产 store 的 facts/generations 都为 0 |
| 复权、规则与财务/行业 as-of | domains 中 adjusted_price、rule_at、known_versions 等 | 有算法及回归；未证明全市场真实历史覆盖，没有完整回测引擎 |
| Market Regime / Features / Screening / Reports | 现有包均仅一个 Reserved docstring | 没有趋势/宽度计算、筛选器或股票研究报告生成 |
| Sectors / Catalysts / Portfolio / Backtest | 同为空占位；risk/regime/universe/data_sources YAML disabled | 没有主题、催化核实、仓位退出、撮合、策略验证或日志服务 |
| 研究流程 | skills/a-share-research/SKILL.md 是旧 Phase0 工作流骨架 | 可参考研究检查顺序；不是已实现产品，旧阶段限制不主导当前授权 |

仓库源码/兼容/测试共 140 份已跟踪 Python 文件做了解析与依赖盘点；
166 份已跟踪 Markdown 在清理前做了内容/引用/重复核查。关键实现进一步阅读了事务、
来源重推导、版本 adapter、知识时间、CLI 与历史消费路径。未根据文件名批量判断无用。

## 本地真实数据

四个主要数据库通过现有受管只读连接核查，读取前后文件 SHA256 相同，均无 WAL。

| 存储 | 现场结果 | 研究限制 |
|---|---|---|
| data/warehouse/astock.duckdb | 34 表；181 raw manifests；133 slice 回执；252 curated manifests；6 generations、3 Context | 21 个离散交易日，2013-01-04 至 2026-09-30，不能当作连续 2013–2026；基础 security_master、trade_calendar、market_rule_history 均为空 |
| 旧 metadata store | 4 表；7 members、3 events、0 receipts | 失败执行证据，不是可用 metadata |
| 旧 capture store | 11 表；29 members；旧 receipt 与 continuation receipt 均为 0 | UNKNOWN/FAILED/UNCERTAIN 事实保留，不能当作交易日覆盖 |
| data/private/phase1-integrated-v1/catalog.duckdb | 50 attempts、47 receipts；末态 26 COMPLETE、21 RAW_RETAINED、2 FAILED、1 UNCERTAIN；0 facts、0 generations | RAW_ONLY；47 回执不等于 47 个通过研究准入的数据集 |

旧库 listing_episode=3、official_exchange_code=18、provider_native_binding=24、
provider_binding_observation=252；这些是精确有限事实，不是全市场身份认证。
旧真实 raw 包含日行情/因子/每日估值/限价/ST/停牌、stock_basic 与 BSE 映射样本；
来源抓取时间是 2026-10-01。当前行情新鲜度不足，不能生成冒充 2026-10-11 最新行情的报告。

重建日志累计 2,412,678 finding observations 和 2,412,174 quarantine rows 属于多个 generation
的重复观察，不能等同于独立证券数或当前独立缺陷数。历史交付记录的 402,060 findings
没有在本批消解；本批没有重新执行 DQ。index_member_all 与 stock_basic 空返回 HOLD 仍存在。
没有检验真实交易账户/持仓，不能因基础 research_hypothesis 表为空就断言用户没有交易记录。

数据总计 155,655 个普通文件、17,998,464,927 逻辑字节（约 18.00GB），其中 186 个数据库文件；
大头是私有演练与历史证据副本。详细大小、实际 blocks 和候选清理见 [存储治理](STORAGE_GOVERNANCE.md)。

## 当前用途判断

- 旧真实样本：可供只读来源/字段验证和带截止时间的历史观察开发；需逐输入验证，
  不能自动成为新 Research Store 已准入事实。
- 当前候选观察：下一批先获得已授权最新来源或用户真实文件，再按当次 universe、字段、时间与用途验证。
  可以明确输出局部观察与 UNKNOWN，不要求所有历史域先全部完美。
- 历史 PIT 回测：仍缺连续日历、完整历史证券/状态/规则、独立对照与财务 vintage 等，当前不满足。
- 真实入场/退出/组合/交易执行：未实现，也没有本批执行授权。业务报告先标为 OBSERVATION_ONLY。

## Git 与验证

开始位于 main，有用户未提交的完整宪章文件和 docs/handoffs/2026-10-11-session-handoff.md。
宪章已逐字纳入 PROJECT_CHARTER；交接原文保持不变，作为历史快照保留。
开发分支 codex/project-reset-research-v1 不改写历史；保留冻结版本/来源与旧实际消费。

基线 HEAD 的 [GitHub CI 38043097292](https://github.com/liuyanfeier/AStockSystem/actions/runs/38043097292)
经 GitHub API 实时核实 completed/success。它认证文档交付 c1a9ef7，
实际 RAW49 执行 SHA 为 66b1cec4914d51f75b0cf4f5211623a03dd9de2d，两者分开记录。
本批最终验证和提交状态以 [清理记录](REPOSITORY_RESET.md) 为准。
