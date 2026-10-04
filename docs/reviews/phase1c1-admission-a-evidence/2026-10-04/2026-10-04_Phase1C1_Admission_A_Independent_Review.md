# Phase 1C.1 Admission A 独立审查

审查日期：2026-10-04。最终材料 SHA：`90ced0bac3e305c0e994878645f455ceba4e8f5e`。离线实现 SHA：`fc23bcf2c5ef11764d619e3bf377f97c8dfc3e12`。已批准 R2 基线：`45e474ef3e6f49b56ea3b1b6f9c4fa7177470f45`。

**结论：Admission A 的新增离线工程与调查账本验收通过；完整审批材料需要两项 P2 纠正。历史身份与日历证据仍不足，新增生产批准为 0，Admission B 暂不具备执行条件，Phase 1C.2 保持 CLOSED。**

这次验收可以结束已完成的离线工程和账本建设。剩余工作集中到证据与可执行取证方案，不再重复修复已通过的 R1/R2，也不运行相同 B 来再次得到 BLOCKED。两项材料纠正与证据补齐可以同批交付。

## 1. 分项裁定

| 审查项 | 裁定 | 精确范围与限制 |
|---|---|---|
| 新 lifecycle、完整成员发布/恢复、增量导入能力 | PASS，限隔离离线实现 | fake transport、合成 SQL/Parquet；不批准原库部署或生产 transport |
| 冻结设计与旧实现保全 | PASS | 新文件扩展；旧 SQL001–010、bounded133/126、政策和旧批准不变 |
| 源行、历史 finding、BSE 与 missing-bar 调查 | PASS，调查真实性与完整性 | 账本可追溯；分类不等于新增身份批准 |
| 完整审批请求与全量预算提案 | CORRECTIONS_REQUIRED | 本报告 F1、F2；当前均无执行许可 |
| 新 case delta / DQ evidence 批准 | 未批准 | 新可执行 delta=0；DQ 提议 envelope 为空 |
| 身份与 venue session 证据完整性 | BLOCKED | 普通历史连续性、endpoint-native、BSE episode/session、边界及例外仍缺证 |
| 实际生产 lifecycle / 全历史 I/O | NOT_PROVEN | 现实现只接收闭合 fake transport；合成规模不能证明真实吞吐 |
| Admission B | NOT_AUTHORIZED / NOT_EXECUTABLE | 没有匹配的新 case、DQ、resolver、Context 批准包；不重跑原 B |
| Phase 1C.2 | CLOSED | 无新数据取证、全量回填或策略执行许可 |

工程验收的设计 hash：`3dd7159f6e9c6554ba4326e09127306cfec363acbaac6024c42427e464b1677e`。这一裁定只覆盖被冻结的离线设计，不批准提案中的未知历史事实、预算或执行许可证。

## 2. 两项需要纠正的材料问题

### F1 — P2：全量 base 请求预算的算式与总数不一致

位置：[capability-and-budget-proposal.md](/Users/yanliu/Documents/AStockSystem/docs/reviews/phase1c1-admission-a/2026-10-03/capability-and-budget-proposal.md:29)，及私有 `full-backfill-plan-proposal.json:230–232`、`final-handoff.json` 的对应字段。

提案给出 `5021 × 6 = 30126` 个 civil-day base 成员，可复用候选最多 126 个，却将新增 base ceiling 写为 30,100，并以其乘 1.25 得到 37,625 秒。按照所写公式，全部 126 个均满足精确复用时净数应为 **30,000**；复用尚未逐项确认时，不扣减的 base 上界是 **30,126**。30,100 缺少明确的保留量来源，也不能代表全部复用失败时的上界。

纠正时分别列 gross、实际通过复用核验的数量、net、另行申请的分片/前置预算；未知项保持未知。若有 100 个 reserve，必须说明用途与授权条件，不能充当默认重试额度。将 `min_base_seconds_upper_bound` 改成准确的限速等待项或假设估算；最小调用间隔不能证明包含响应耗时的实际运行时间上界。同步公开报告、JSON、checklist、handoff 与 hashes，保留原版本。本项不否定离线工程验收。

### F2 — P2：完整审批请求仍引用早期 Context，最终 checklist 未闭合

位置：[approval-request-complete.json](/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-admission-a/2026-10-03/approval-request-complete.json:11) 与 [admission-checklist-final.json](/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-admission-a/2026-10-03/admission-checklist-final.json:60)。

`approval-request-complete.json.context_proposal` 指向 `context-proposal.json`，其 `implementation_sha=null`；最终 handoff/索引指向 `context-proposal-final.json`，实现 pin 为 `fc23bcf…`。两条审批入口解析出的 Context 提案不同。同时，最终 checklist 的 Original preservation 仍为 `PENDING_FINAL_CHECK`，而最终保全材料及本次独立核验已完成。

在新的材料版本统一审批入口、最终候选路径及 bytes/canonical hashes；将作者已完成的保全状态连接到最终 before/after 证明。review_ref、approved_at、生产批准 hash 与运行许可继续保持未批准状态。当前没有执行，因此没有错用 Context 的实际数据污染；但现有“完整审批请求”不能直接用作后续执行依据。

未发现本次新增离线实现需要阻断验收的 P0/P1 问题。上述两项属于审批材料与计划纠正，建议并入下一次证据交付，不单独增加一次工程 Gate。

## 3. 独立核验结果

本次实际读取代码、SQL、冻结设计及原始材料，运行针对性离线测试，并通过 managed shared/read-only 连接验证原库。没有执行新的市场/provider 请求、capture/resume/replay、原库迁移、binding 导入、Context、generation 或 DQ audit。

| 核验 | 独立结果 |
|---|---|
| 针对新增功能测试 | 20 passed，3.39 秒；市场网络路径拒绝 |
| 最终 SHA 的远端 CI | foundation SUCCESS；642 passed、4 warnings、947.02 秒；实际 checkout SHA 对齐 |
| 私有材料索引 | 76 个 artifact 的实际 bytes/size，40 个 canonical hash 全部一致 |
| 作者 ZIP | 93 个唯一成员、CRC 和本地源 bytes 全部一致 |
| 旧文件 | 6,590 个既有文件 bytes 保全；225 个旧 tracked 文件保持原 bytes；AGENTS 仅追加授权段 |
| 原数据库 | 全部 34 表有序行内容 hash 与保全基线一致；DB before/after bytes 一致 |
| raw 与 receipts | 181 个实际 raw 完整性通过；133 EXACT receipts，failure=0，VALID/EXACT |
| 源行账本 | 402,246 行全部逐 raw UUID、zero-based ordinal、native/event/dataset/capture/request/取得时间核验 |
| 历史处置与 finding | 全源行旧处置一致；15,756 个旧 finding key/payload/severity 全保留，关闭 0 |
| BSE | 248 cases、31,248 个矩阵 cell、15,683 条实际观察核验；观察缺失未伪写成已观察 |
| missing bar | 15 项对应的 30 条 old/new native 原始观察均存在；去掉 ts_code 后内容相同 |
| 合成规模 | 30,126 个实际 typed 输出/sidecar/登记/精确完成成员重新验证；synthetic DB 不变 |
| 凭据检查 | 当前本地凭据 literal 对全部 76 indexed artifact 和 ZIP 93 个展开成员无命中；凭据未显示或用于请求 |

远端 CI：[run 37168881442](https://github.com/liuyanfeier/AStockSystem/actions/runs/37168881442)。作者本地最终全套是 642 passed、1 warning、407.44 秒；之前 stress 并行造成 read-only 诊断失败的现场已保留，停掉文件生成后全套通过，旧测试没有被改弱。

原库 SHA256：`c687fc514a78ef8b68b6c89907b9932a42465d2b2cab5ae383647616287ca0e2`。

作者 ZIP SHA256：`5b461f00378d22b10f2a33295653602e7b4424a7f8beec23276c0cb6f6544967`。

strict133 evidence hash：`0992ccac745f6e5299615caaf7a68e4aabf9fb4d90c49e1d1c742716bf4e3597`。

## 4. 已验证的工程行为与限制

**生命周期。** plan 不制造 attempt；claim 和本地 CALL_ENTERED 先持久化，再进入注入 fake transport。未知调用与崩溃状态拒绝自动重发。COMPLETE 必须绑定实际 immutable raw、登记及 checksum，随机 UUID/空 manifest 不能成功；重复终结保留最初时间。这证明合成持久化路径的安全语义。CALL_ENTERED 不能视为远端收到请求，新模块没有 live-client 入口。

**成员与恢复。** 新 schema 和 manifest 与旧 production Context 分开，execution_license=false。按 2013-01-01 至 2026-09-30 全 civil dates × 六 dataset 压力验证 30,126 members / 84 dataset-year groups；30,042 typed-empty、84 nonempty partition / 252 representative rows。覆盖 file、sidecar、registration、promotion 故障，partial 不能选中，恢复后精确成员、重复执行、内容/source conservation、orphan/tamper 拒绝。作者记录 236.74 秒、峰值 RSS 441,696,256 bytes、磁盘 50,427,670 bytes；本次重新验证产物，未重测其性能。大量空 partition 验证成员管理，不是全历史真实数据吞吐证明。

**增量批准导入。** 新 wrapper 校验 exact delta、实现/设计/时间 pin、existing+delta snapshot；旧成员与批准时间保留，新 binding 可明确引用已有 episode。合成 SQL close/reopen、完全相同 repeat、冲突与部分安装拒绝已验证。空 delta 不作为一次新批准导入；当前没有真实新增 delta。

生产 transport 集成、真实账号权限、截断/分片的确切运行计划仍是未来执行前的条件。这些未知不能由合成验收自动转成 PASS。

## 5. 调查结果不会改变生产身份状态

| 当前调查处置 | 行数 | 本次裁定 |
|---|---:|---|
| EXISTING_APPROVED_UNCHANGED | 192 | 保留原有限批准，未扩大或重审批 |
| EXISTING_APPROVED_OUT_OF_SCOPE | 1,374 | 保留原 pre-BSE 范围外处置及 quarantine，不计 resolved |
| EVIDENCE_REQUIRED | 400,679 | 接受缺证分类，不签发新 binding |
| CONFLICT | 1 | 689009 冲突保留，不批准 NULL/资产类型例外 |
| 合计 | 402,246 | 每行恰好一个当前调查处置 |

生产有限 generation 仍是 **192 resolved / 402,054 quarantine**。400,679 是调查分类的缺证行数，不是新的生产 quarantine 总数。原 3 episodes、3 codes、12 bindings、192 observations 及 resolver hash `e88a8d9b6f38cd4629a67905124a811e980a374368b31667121f5ad918c8dffb` 保留。

当前 candidate Context 的 133 输入逐项与既有 Context 对齐，input hash 为 `b471998495a4a4f6d2d55796b3fa084c383b32c53f3af91eb37da9afba245a08`；case delta 与 DQ envelope 仍为空。不能用本报告的工程验收 ref 填入真实 case/DQ/Context 批准字段。

15 missing bar 的实际 raw 已有观察，因此本次同意**不申请补抓行情**。但同内容不能独自证明两个 native identifier 是同一合法 episode，也不能直接授权 alias/dedup。下一步需精确的 issuer/episode、endpoint-native 与重叠处置证据，再提有限成员和预期 DQ 影响；旧 finding 继续保留。

BSE 248 个官方更码事实与 provider 观察应共享矩阵核验；不必制造 248 套重复审查。官方代码对不能单独证明完整历史 episode、所有 endpoint 回溯规则或 venue session。

## 6. 下一次集中交付

1. 同批纠正 F1/F2，保留本次工程证明，只对变更与最终材料做必要验证。
2. 在既有 Admission A 授权内继续查阅官方公告、规则与供应商字段文档，优先共同来源和有限成员规则。原 A 已允许这种只读文档查阅；不能把每个普通 URL 都新增为一次人工授权 Gate。
3. 把普通连续性、15 missing-bar alias/overlap、BSE episode/session、特殊资产与 NULL 例外变成有正面依据的有限候选。仍无法证明的成员保留缺证，禁止通配 fallback。
4. 将 7 个 SZSE trade_cal metadata 提案补成可独立批准的 exact request/contract/fields/hash、one-attempt lifecycle 与隔离落盘方案；本轮不调用 API。这些请求只解决 SZSE 的有限日历缺口，不解决全部历史身份/BSE 证据。
5. 一次交付互相匹配的 case delta、merged resolver、DQ、Context、批准请求、取证预算、checklist 与最终 SHA/CI/hashes。新增数据取证或 B 的实际运行均另需具体批准与用户授权；Phase 1C.2 不开放。

**效率判断。** `5930 tasks × 4 = 23720` 的文档发现 ceiling 算式正确，但 URL 与真正共享来源未知，它是粗估提案，不是必须实施的 23,720 次抓取计划。应先找共享来源证明，按实际能解除的条件形成最小取证方案。

本次发现的共享来源线索：[Tushare bak_basic 官方文档](https://tushare.pro/document/2?doc_id=262) 描述了 2016 年起的历史每日基础信息，含 ts_code/name/list_date，单次最多 7,000 条。它值得做文档层面的适用性分析，但不能覆盖 2013，也不能单凭这些字段证明 issuer/episode/所有 endpoint 连续性；文档权限要求不证明本账号权限。没有查询这个 API，没有批准新的证券数据下载。

[trade_cal 官方文档](https://tushare.pro/document/2?doc_id=26) 列出 SSE/SZSE 参数；新 7 窗口与旧 SSE 请求除 exchange 外一致。现有 `TushareClient.fetch_slice` 只准入旧 SSE 窗口，新离线模块也仅支持 fake transport，不能仅将参数改成 SZSE 就执行。需先冻结专门的 metadata 计划及持久化安全路径，离线验证后申请实际调用。

完整下一轮指令见：[集中证据补齐 Prompt](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Admission_A_Evidence_Closure_Prompt_v1.0.md)。本报告及审查 manifest 是离线工程/调查范围的裁定，**不是 approved-case-set、DQ evidence、Context 或市场请求许可证**。

## 7. 复核文件

本报告的审查 manifest：[Phase1C1_Admission_A_Independent_Review_Manifest.json](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C1_Admission_A_Independent_Review_Manifest.json)。五份独立核验 JSON 位于同目录 `private/phase1c1-admission-a-independent-review/`，记录材料/原库/合成规模/远端 CI/取证与秘密扫描结果。最终 handoff 与轻量 ZIP 将这些证明一起封装；没有复制 raw、数据库或凭据。
