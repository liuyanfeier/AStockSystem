# AStockSystem 准入批次 A：证据集中补齐与离线运行能力验证

2026-10-03 · 基线 `45e474ef3e6f49b56ea3b1b6f9c4fa7177470f45`

## 可直接转交的执行指令

请在 `/Users/yanliu/Documents/AStockSystem` 执行本批次，一次性完成下列调查、证据提案、必要工程补齐、离线验证和交付。批次内部连续推进，保留聚焦 commits；完成后统一交付一次独立 Review，不逐小 Gate 停顿。

目标是为 Phase1C.2 的准入提供完整、可执行、可独立裁定的材料。当前 R1、R2 工程已通过，历史证据和数据准入仍 BLOCKED。本批次只处理尚未完成的准入条件，不重复实施已通过的修复。

用户将本指令转交给实现 Codex 后，构成本批次授权：允许读取现有真实材料、查阅官方文档、编写候选证据与最小必要工程、在临时合成存储和隔离副本验证。原库保持只读；真实新增绑定、episode、Context、generation、DQ audit 均不在原库生效。Phase1C.2 仍 CLOSED。

## 1. 基线和必须读取的材料

首先读取：

- `/Users/yanliu/Documents/AStockSystem/AGENTS.md`。
- `/Users/yanliu/Documents/AStockSystem/AStockSystem_Phase1C_Core_Market_Data_Foundation_Design_v1.0.md`，特别是第24–25节。
- `/Users/yanliu/Documents/AStockSystem/docs/remediation/phase1c1/Phase1C1_R1_Engineering_Integrity_Spec_v1.0.md`。
- `/Users/yanliu/Documents/AStockSystem/docs/remediation/phase1c1/Phase1C1_R2_Historical_Identity_Coverage_Spec_v1.0.md`。
- `/Users/yanliu/Documents/AStockSystem/docs/remediation/phase1c1/Codex_Phase1C1_R2_Batched_Prompts_v1.1.md`及已冻结的 R2 设计、addenda 1–4。
- `/Users/yanliu/Documents/AStockSystem/docs/phase1c1_writer_lifecycle.md`。
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-03_Phase1C1_R2_Final_V2_Independent_Review.md`及同目录 `Phase1C1_R2_Final_V2_Independent_Review_Manifest.json`。
- `/Users/yanliu/Documents/AStockSystem/docs/reviews/r2-final-v2/r2-final-review.md`。
- `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-r2-b-v2-execution/2026-10-03-matched-v2/final-handoff.json`和完整索引。
- `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-r2-a-approval/`中的原候选、case/impact/来源/finding 台账，以及 matched-v2 实际批准。

上轮已验证事实：

| 项目 | 基线 |
|---|---|
| R1 FINAL / R2 Engineering / 有限 R2-B execution | PASS |
| Evidence completeness / Bounded data admission | BLOCKED |
| 原批次 | `1d34d71f-c711-4893-9729-0b719bbba6dd` |
| 请求 / 原库 raw 库存 | 133 exact receipts / 181 raw objects |
| 每个有限 generation | 126输出；402,246 source rows；192 resolved；402,054 quarantine |
| 原 matched-v2 Context | `0b1906ee-52af-485b-98eb-a4f4b3e54706` |
| 两个原库 COMPLETE generation | `5347e862-2505-4272-8c3a-f43d8c169809`、`90d90069-776a-458c-a06b-c408ace1045d` |
| 每代新 finding | identity 402,054；session未认证63；未解释missing bar15 |
| 因果检验 | certified pairs 0；unknown排除45；不能由0 mismatch声称通过 |
| 待证候选 | 5,584 carry scopes、248 BSE transitions；它们与旧case/行存在交集 |
| 当前原库基线 SHA256 | `c687fc514a78ef8b68b6c89907b9932a42465d2b2cab5ae383647616287ca0e2` |
| 当前实现特点 | `reconstruction.Context`生产检查固定133 inputs/126 outputs；旧限制必须保留 |

核对 HEAD 和工作区。若 HEAD 后续有变化，逐项说明差异及授权来源，不能自动当成获批基线；不 reset 用户工作。上轮审查已验证源码、真实执行与 exact-SHA CI，直接引用有效证明。

当前原库已经完成008–010及有限追加，不是旧007库。新保全基线必须覆盖当前全部已有表/记录、旧和 matched-v2 Context/generation/audit、全部历史私有批准/失败现场/报告。不得用旧007备份覆盖当前库。

## 2. 授权范围、取证边界和连续执行

本批次市场/provider API预算为 **0**，包括 metadata、mapping、calendar、stock_basic、bse_mapping。禁止 capture/resume/replay、重跑133请求、注册或执行全量回填；不加载凭据来试探API权限。

允许查阅并保存必要的官方公告、发行人披露、交易所历史规则/休市/开市公告和供应商字段文档，作为文档证据，记录URL、发布精度、实际取得时间与bytes hash。不得下载新的证券列表、映射表或批量日历数据集来绕过零新增数据约束。保留已缓存证据，实际无法取得的材料标明缺口。

原库采用 managed shared/read-only connection；协调锁按现有协议处理，不能偷锁、删锁或用未受管理的 DuckDB 连接。私有候选、验证输出、临时副本和合成存储写入新的 ignored 目录。禁止修改原 raw、旧派生、既有批准、历史audit、原SQL001–010和冻结政策/设计；需要扩展时使用新文件和新版本。

本指令替代本批次内旧文档的逐小 Gate STOP。允许必要的准入工程实现与合成/隔离验证，但不解除真实数据批准和原库部署边界。普通实现选择无需再次询问；证据缺失时记录并继续其他工作。只有锁冲突、来源损坏、授权外数据取得或无法安全继续的变更需要保留现场并集中交付具体阻断。

## 3. 工作包一：按证据组完成历史身份提案

### 3.1 完整分类与有限范围

从既有 raw、旧resolver、批准记录和新旧台账建立单一调查账本。覆盖全部402,246父输入行、原7,666 quarantine、全部15,756旧finding、346旧case items、251 inactive drafts、5,584 carry scopes和248 BSE transition候选。确认交集，分别报告source rows、unique securities/episodes、bindings、cases、finding observations，不能把重叠数量相加。

把身份问题分为普通直接匹配/连续性、历史代码切换、BSE开市及两批2025切换、上市/退市/代码复用/资产类型冲突、特殊native表示、证据不足等组。每行在源行账本中恰好有一个当前处置；不同问题标签可重叠，并保留原因。

优先建立可批量核验的共同证据规则。允许多个有限case共享同一份结构化来源或官方规则，统一申请Review；不要求普通证券逐个制造相同的人工审批流程。每个拟放行binding仍须有明确episode、dataset、native identifier、capture/raw UUID、zero-based ordinal、event date及证据链接，必要时用有hash的私有membership文件表达。

**批量规则必须有充分依据和明确排除项。** 代码相同、名称相近、当前active名单、旧resolver曾成功、字符串后缀、观察的最早/最晚日期，均不能单独证明历史身份连续性或上市/退市边界。不得把5,584候选整体标APPROVED，不得恢复无证据的旧resolver fallback。

### 3.2 各组要交付的具体依据

1. **普通连续性组**：列出可复用的既有stock_basic/其他raw事实、历史事件范围、provider-native表示依据、证券/episode归属、冲突检测和未证区间。逐dataset评估daily、daily_basic、adj_factor、stk_limit、stock_st、suspend_d；一个endpoint的表示证据不能自动扩到其他endpoint。提案只覆盖能够证明的精确观察，有限观察不自动扩展到全历史。
2. **三个历史更码组**：保留000022→001872、000043→001914、300114→302132既有有限批准。调查尚未批准的pre-switch观察及其他dataset，补足旧代码起始/证券连续性/provider表示依据；已批准192行不重审批，任何扩大范围使用新的明确候选版本。
3. **BSE组**：分别处理2021-11-15 venue边界、6只pilot的2025-05-06切换和242只remaining的2025-10-09切换。每组区分官方代码事实、实际provider-native观察、episode连续性、dataset/capture/event scope和session证据。官方新旧代码对不能单独证明完整episode，也不能证明所有endpoint都回溯改码。248候选逐项纳入统一证据矩阵；不把缺失的一侧观察写成已观察。
4. **边界和例外组**：列明上市、退市、last trading day、provider delist date之间的区别；处理代码复用、UNKNOWN资产、689009 CDR/provider-STK/NULL冲突、T600018等。未证明的边界保持UNKNOWN，不能用统一delist+1、观察包络、改前缀或填NULL消除问题。
5. **已批准范围外组**：保留1,374 exact pre-BSE的既有coverage处置及quarantine。扩大范围外裁定必须独立提出证据和精确成员；范围外仍留源行，不计入resolved。

为每个证据组生成：group id、现有事实、共同规则、每个有限成员及scope hash、支持/反驳材料、拟议裁定、明确排除项、预计影响行数、剩余缺口。保留`PROPOSED / EVIDENCE_REQUIRED / CONFLICT / OUT_OF_SCOPE`的区别。作者只能请求批准，不能签发生产批准。

## 4. 工作包二：session、coverage和因果检验依据

### 4.1 交易所日历

对现有21个market dates及所需previous session，建立SSE/SZSE/BSE证据矩阵。根据真实episode/venue适用范围确认session、休市和前一交易日；BSE开市前按有据的范围边界处理。原7个SSE calendar结果只证明它自己的范围，不认证SZSE/BSE。

现有63条NOT_CERTIFIED只是3个有限episode的基线；身份范围扩大后按新增episode/event重新计算需证集合，不能只修这63条就宣布全市场日历通过。也要单列未来2013-01-01至2026-09-30各venue日历所需范围、已有可用材料和缺口。

认证使用来源足够的文档/既有raw，并说明精确覆盖范围。工作日推算、默认沿用SSE、当前calendar回填历史、把NOT_CERTIFIED改成CERTIFIED的状态编辑，都不构成证据。

### 4.2 当前15条missing bar及历史覆盖finding

对当前15条`UNEXPLAINED_MISSING_BAR`逐项追溯：episode、dataset/event、原raw是否已有对应观察、是否被未批准resolver隔离、是否与pre-switch/上市/退市/全天停牌相关、需要的session证据，以及拟议处置。

分别识别“raw缺观察”“raw存在但新有限Context未解析”“episode/日历导致预期范围错误”。当前DQ缺bar不等于原raw缺bar。不能补造行情、复制前收盘、插值或改容差。原1,226 coverage flags及其他旧finding全部给出可追溯处置，保留完整旧key、payload和severity。

补足需要的停牌证据和reference-price例外，严格区分全天/盘中/恢复交易；NULL例外必须有确切理由和范围。无证据的例外仍EVIDENCE_REQUIRED。

### 4.3 固定政策与候选证据

复用已批准DQ政策和容差；若发现政策缺少必要语义，在运行新真实DQ之前提交独立版本、具体差异、依据和合成回归。不得根据真实DQ结果降级severity、扩大容差或排除难例。

形成待批准的sessions、reference_exceptions、bse_transitions和source_dispositions。报告可认证、待证和范围外的分母；只有真正有适用session/factor证据的pair才进入causal检验。“全部排除后0 mismatch”不算通过。

## 5. 工作包三：全量运行准入能力，只做离线证明

先建立矩阵：`required capability / existing proof / remaining gap / action / validation / limitation`。已有R1/R2有效证明直接引用。只实施下列原来已登记而仍缺的能力，不扩大到策略或其他数据域。

### 5.1 新批次精确lifecycle

选择并冻结未来新批次的PLANNED→RUNNING模型或create-at-claim模型，明确created_at、claimed_at、http_attempt_started_at、finished_at以及retrieved_at/available_at/verification time。

若当前实现仅保留旧预创建RUNNING语义，补齐新的版本化模型、必要schema草案/迁移和可测状态操作。只在合成/临时隔离存储运行，不创建真实全量batch，不改旧ingestion_run状态和时间，不把旧reservation重新解释成已HTTP。

用注入的本地fake transport验证：仅plan不计真实attempt；durable claim后才可调用transport；claim失败不调用；call-entry与remote receipt区别；claim后崩溃或transport未知不自动重发；存在exact immutable raw才完成；零manifest/fake object_id不能成功；重复finalization不改旧终态。记录实际持久化状态，而非只测mock返回值。

### 5.2 全规模membership和恢复

原`reconstruction.Context`生产规则固定133/126，不能仅把`fixture_only=true`扩成大数组就声称真实全量路径已验证，也不能放宽旧Context来兼容未来计划。

先冻结未来完整membership、dataset-year拆分、输入/contract/输出、checkpoint/完成条件和重复resume语义。必要时增加独立版本的离线计划/manifest/恢复能力，保留旧bounded模型、hash和guard。未来真实计划的运行许可保持false；本批次只验证新的离线能力。

在合成存储做一次覆盖拟议完整规模membership的演练。有可信calendar时按实际预计成员数；没有时用明确推导的保守规模上界，标为合成压力条件。生成可验证的typed测试partition；空partition仅证明membership/完成与恢复，另选代表性的非空数据验证内容、schema、hash和row conservation，明确真实全历史IO/吞吐尚未验证。

在publication、sidecar、DB登记、完成promotion等已有故障边界注入中断；验证partial不被select、恢复后成员精确一次、未知/orphan/tamper阻断、完整generation可显式选择、dataset-year跨年恢复、重复resume不双登记。复用已有故障测试，优先补规模/跨分区缺口，避免对每个日期重复同一测试。

记录成员数、时间、峰值内存/磁盘、逐层hash/状态和恢复结果。只有草图或小fixture的结论标DESIGN_ONLY/NOT_PROVEN，不能标准入PASS。准入证明覆盖安全和恢复；真实全历史数据质量及年度真实重建留在回填后的验收。

### 5.3 全量计划和预算提案

准备2013-01-01至2026-09-30六个market datasets的候选全量计划，以及trade_cal/stock_basic/identity前置。计划为**非执行提案**，不注册到原库、不生成可直接调用live的执行授权。

逐endpoint列contract、时间/venue范围、provider cap、权限/分页或分片语义、去重/截断识别、请求数计算、最大attempt、最小间隔、失败停止与resume边界、存储估计。复用已冻结准确请求时，列明可复用条件；禁止为试连或证明一致性重跑133请求。文档证据不足时，预算留明确unknown/上下界，不能假装已有精确请求数或账号权限。

单列CURRENT_RECONSTRUCTION/OBSERVED_CAPTURE研究边界：现在取得的历史数据不追认historical PIT；估值等字段不能自动成为当时可用alpha输入。准入不要求伪造历史可用时间，必须明确未来研究能用/不能用什么。

## 6. 取得不足证据时的唯一集中交付

若现有raw和允许查阅的文档无法补齐，不要重复运行相同有限重建来再次得到相同BLOCKED，也不要把任务拆成若干人工逐案往返。

一次列出`evidence-acquisition-request.json`：每个缺口的准确证券/venue/dataset/日期、需要取得的材料、现有材料为何不足、拟议来源和调用方式、预算上限/限速/最多attempt、预计新增文件及私有保存位置、所解除的准入条件，以及不重复133请求的证明。区分新增数据取证预算与Phase1C.2全量回填预算。

这是待用户/独立Review裁定的具体申请，**本批次不执行**。作者不得把文档查阅授权延伸为新的provider数据调用。缺证申请与所有其他工作一起交付；不等待不可取得证据而停掉可完成的工程和设计。

## 7. 一次准备完整批准材料

在新的ignored目录`data/private/phase1c1-admission-a/<run_id>/`准备：

| 文件/索引项 | 必需内容 |
|---|---|
| baseline-manifest.json | 当前HEAD、已批准源码/设计/policy、现有全部表/记录和文件保护基线、strict receipts、原库before/after |
| identity-evidence-groups.json | 全组、共同规则、有限成员/例外/候选决定与证据 |
| source-scope-ledger及index | 全402,246源行的现状、拟议处置、重叠问题和exact scope；大文件可Parquet/JSONL，索引pin bytes/schema/行数 |
| case-set-proposal及member index | 适配现有导入模型的候选episodes/codes/bindings；批量证据与每个有限成员的联系 |
| dq-evidence-proposal.json | session/reference/BSE/source处置、证据范围及缺口 |
| context-proposal.json | 新候选bounded Context、133 exact inputs/126 outputs、固定snapshot、实现/设计/policy pins与待审批字段 |
| capability-validation.json及logs | lifecycle与规模/恢复实际验证、已有证明复用、缺口和限制 |
| full-backfill-plan-proposal及budget | 非执行计划；无真实运行许可；前置和预算分别列明 |
| admission-checklist.json | 每条准入条件、证据、当前状态、拟议B动作、阻断属性 |
| evidence-acquisition-request.json | 需要新增取证时的准确申请；无需新增时显式空清单 |
| approval-request.json | 请求独立裁定的工程、政策、证据组、有限成员、DQ、Context、预算和运行边界 |
| package-manifest.json / final-handoff.json | 所有bytes/canonical hashes、路径、counts、实施/材料/最终SHA、CI、保全、零调用证明、未完成项 |

将**新增导入delta**与**导入后完整resolver snapshot**分开索引和pin：当前`import_approved_cases`校验本次case-set的批准ref/时间，并与已有resolver合并。不能把旧已批准records换新批准时间后重新INSERT，也不能把新批准时间套在旧payload上。新增binding引用已有episode时，明确复用依据和FK；完整snapshot包含旧成员及新成员，按其原批准依据保留。用合成增量+既有记录的临时模型/SQL路径证明合并、重复执行的精确检查、冲突阻断和snapshot计算可行。

采用实际模型的canonical算法，复用`R2_RESOLVER_UTC_INSTANT_V2`。保留published_at精度及原观察/取得时间；新知识按真实当前时间记录。候选申请里的实际review_ref、approved_at、最终批准hash保持未批准状态，不能由作者签发。模型需要生产批准字段时，以候选申请层表达；合成批准仅用于明确fixture并隔离保存。

Review需要同时产出互相匹配的工程/设计/policy、case decisions/approved-case-set、DQ evidence、resolver snapshot、Context和批准manifest。把材料一次准备完整，避免先交报告再追加一轮“审批包准备”。提出有精确成员的批量规则并不自动获得批准。

用只读分析/候选影响计算估计拟解决多少行、还有哪些阻断；它是提案预估，不能叫真实generation/DQ PASS。已批准成员保留原批准依据，新增成员采用新批准版本，不改旧approved payload。

## 8. 验证、提交与统一停止点

开发中做针对性必要验证；完成实现后运行一次全套离线检查、doctor、contracts及decoded secret scan，按仓库要求核实最终exact-SHA CI。每个内部commit无需完整重跑；新的代码变更或失败再执行相应检查。

使用provider fetch/HTTP等拒绝或计数保护市场路径，同时分别记录允许的官方文档查阅。不能一边获取文档，一边声称全部HTTP/socket调用为0。以市场路径计数、raw库存、receipt/attempt历史和原库/文件保全共同证明零市场请求。

公开交付到新的`docs/reviews/phase1c1-admission-a/<run_id>/`目录：脱敏审查报告、准入条件表和hash/count索引；敏感原始材料和完整证券列表留private。报告明确列出已批准结果复用、新完成工作、提案可覆盖范围、仍缺证范围和是否具备执行B的材料。不要修改旧Review结论。可追加本批次授权说明，保留AGENTS历史内容。

最终交付：final SHA、CI URL、公开report路径、私有ZIP/索引/`final-handoff.json`路径。ZIP应便于审查，不打包完整DB或所有raw；大账本可索引原路径，记录完整hash且可独立读取。

结束状态 `ADMISSION_A_REVIEW_READY`。这是作者交付状态，不是独立PASS。**STOP：等待一次集中独立Review；B尚未授权，Phase1C.2 CLOSED，新增市场调用0。** 缺证时本批次仍可完整交付，但不得承诺只要运行B就能取得Phase1C.2准入。
