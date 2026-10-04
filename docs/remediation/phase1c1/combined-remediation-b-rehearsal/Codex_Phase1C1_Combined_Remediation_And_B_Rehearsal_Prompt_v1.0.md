# AStockSystem：修正、证据候选与 Batch B 隔离预演合并批次

2026-10-04。可整份交给实现 Codex。内部连续完成，最终一次提交独立 Review，不再为来源标注、单个 case 或内部测试安排人工 Gate。

## 1. 本次授权与目标

用户要求加快推进，并询问能否修复后直接做 Batch B、一起 Review。本指令将可以提前完成的工作合并：来源修正、专用 metadata live 代码准备、有限身份/DQ/Context 候选、候选在隔离副本中的 B 预演及统一交付。

**允许候选隔离预演；原库正式 B 尚不执行。** 本批真实市场/provider API 请求预算仍为 0。原库只读；不重跑 133 个请求，不启动 Phase1C.2。文档网页取证继续允许，单独记录，不能借此调用市场、metadata、calendar 或 mapping API。

这份指令替代上轮 live 准备 prompt 中禁止所有 B 动作的粗粒度停止点：现在允许本文件定义的候选隔离预演。它不签发新证券事实批准、生产 Context 或 API 运行许可证。按这项用户范围更新授权说明与 AGENTS 的当前批次说明，保留历史授权原文。

请在 `/Users/yanliu/Documents/AStockSystem` 完成。当前核验 HEAD 为 `088b02febccd07f68ddcf2dc6d42613ba69e9d35`，worktree clean；开始时再核对，保护已有修改，不 reset 或覆盖其他工作。

先读取当前 AGENTS、已批准 R1/R2、UTC instant v2、managed writer lifecycle，以及：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-04_Phase1C1_Admission_A_Evidence_Independent_Review.md`。
- 同目录 `Phase1C1_Admission_A_Evidence_Independent_Review_Manifest.json`、`Phase1C1_SZSE_Metadata_Plan_Scope_Approval.json`。
- `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-admission-a-evidence/2026-10-04/final-handoff.json` 及其最终引用。
- `/Users/yanliu/Documents/AStockSystem/docs/remediation/phase1c1/admission-a-evidence/concrete-design-v1.md`。
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Metadata_Live_Preparation_Prompt_v1.0.md`，其 live 安全要求继续适用。
- 同目录 `Codex_Phase1C1_Admission_Batch_B_Conditional_Prompt_v1.0.md`，复用隔离预演的真实 pipeline 和验收要求；其原库部署节在本批不执行。

F1/F2 已 CLOSED；既有离线工程已通过独立验证。保留旧 schema001–010、政策、旧 SSE/133 guard、fake-only 接口和历史设计文件。最小新增能力使用独立版本；确有必要改变接口或设计，先写具体新设计，再同批实现、验证、交 Review，不为设计单独停顿。

## 2. 小修直接完成，不设独立 Review

追加纠正 `szse:rules:2023` 对应原 PDF 的来源版本：实际为《深圳证券交易所交易规则（2013年11月修订）》，文件内决定日期为 2013-11-30，基础规则正文写 2013-08-05 施行。URL 的 2023 路径不能作为规则版本；网站首次发布时间未证时保持 UNKNOWN。

保留原 PDF、旧 index 和审查，新增准确索引及 old/new 对照。规则适用期和替代情况没有证明前，不用于认证 2020/2026 session。此修正不要求迁移、重取行情、重建旧 generation 或重复全套验证。

## 3. 一次完成专用 metadata live 准备

冻结并实现最小 live 路径，沿用现有精确 7 个 SZSE `trade_cal` 请求计划。旧 plan bytes、canonical hash、request IDs、fields、contract、windows、membership 和 `execution_license=false` 保持不变；未来执行许可用独立 manifest 绑定计划、实际 live 实现 SHA、设计、Review 及用户授权。

保留以下要求，在真正的 runner 路径用无网络 mock transport 验证：

- 固定 POST `https://api.tushare.pro`；只接受计划中的 7 members；ordered fields 为 `exchange,cal_date,is_open,pretrade_date`。禁止 SDK 隐藏重试、redirect、权限 probe、额外分页或补请求；token 不进入计划、hash、日志、sidecar、公开报告或 ZIP。
- 每 member 最多 1 attempt，整体最多 7；失败和不确定调用也消耗 attempt。持久化 claim/CALL_ENTERED 后才可能调用 HTTP，unknown/timeout/crash 停止，不通过换 run ID 重置预算。恢复只完成已有准确证据的登记，不重发。
- start-to-start 至少 1.25 秒，证明并发、重启和时钟异常下仍安全。created/claim/call/finish/retrieved/available/verification 为各自真实时间，不回填或重写首个终态时间。
- 完整 HTTP response bytes、安全 HTTP 元数据、解析后的 typed table 分开保存与 hash。raw、manifest、sidecar、member、contract、source 时间和 receipt 必须闭合；零 manifest、fake UUID、tamper、orphan 和部分完成均不能声称成功。
- 42 个精确 civil dates：各窗口 5/5/5/8/11/5/3 行。严格字段/types、SZSE、唯一日期、0/1、pretrade_date 格式与先于 cal_date；缺失、额外、重复、截断、错误 code 或未知完整性保留证据并停止。结构合法不能直接认证真实 session。
- 使用独立 ignored managed store；旧入口、原库、原 133 inputs/126 outputs 不变。未来 metadata 是 versioned external evidence。原 plan 接受不能代替新 live 代码和实际 session 事实 Review。

测试实际 mock 调用次数及落盘 SQL/bytes，包括许可缺失/错 pin 在网络前拒绝、exact request、成功重开不重发、writer/readonly/escaped 拒绝、并发、pacing、HTTP/权限/redirect/timeout/malformed/secret 错误、文件和登记故障恢复、终态幂等及跨 run 预算。复用已验收证明，不重复 30126 stress。

本批不实际发出这 7 次请求。交付准确待运行命令、运行 license 模板和取得后 session 证据构造方式。当前账号权限 UNKNOWN，不能为了“完成本批”先试连。

## 4. 证据候选与 B 预演连续推进

### 4.1 优先形成可以单独裁定的有限候选

复用 15 dossiers、30 条 bounded 观察及另 2 条 2020-08-24 probe 观察；probe 不混入原 133 membership。继续读取共同官方来源，分别评估当日官方 old-native 与提前出现的 new-native 回溯表示。

有实际 issuer/episode/code 证据和该 endpoint 的精确观察共同支持的 old-native，可提出有限 EVENT_NATIVE 子集。明确日期、dataset、raw UUID/zero-based ordinal、native、episode、官方 code、来源/hash、排除成员、knowledge 时间和预期变化。复用已有批准 episode 时保留其旧 metadata；新增 code/binding 用独立 delta。相同名称、字符串、价格不能补事实；old-native 候选不能默默批准 mirrored new-native 或去重。

候选不必等所有普通证券、BSE、特殊资产和 NULL 问题一起闭合。未证范围继续 quarantine；不推断通用 alias、上市/退市边界或 session。已有原始 bar 的 15 项不再请求行情。3 组供应商问题写成未发送草案；未经用户明确授权，不发送消息或上传材料。

分别交付证据充分的 candidate delta、完整 old+new resolver、DQ evidence 与 Context 提案。生产批准字段仍 null/false。只有依据充分的成员进入候选；其余给出具体缺什么、取得方式以及它是否真的阻断当前有限子集。

### 4.2 有实质新输入就直接预演，不等待中间 Review

候选非空且具备必要证据时，直接从当前原库的受保护快照建立新的隔离 root/store，在其中走真实 import/register/derive/DQ/rebuild 路径。使用 managed shared/read-only 原库连接形成一致副本；不要绕过锁、硬链接可写文件或覆盖旧失败隔离现场。

隔离 root、DB、raw/curated/output 路径全部位于本批 ignored 专用目录。允许复制现有 raw，证明与原 bytes/hash 一致；禁止新 API 或篡改现有 raw。运行前拒绝任何 output/DB/symlink/path escape 回原库的配置。

作者候选与预演专用材料分开保存。生产候选保持未批准；预演所需 Approval 形状使用明确 `CANDIDATE_REHEARSAL_ONLY` namespace 与专用 material hash、真实本次时间及实际代码/设计 pins，不能冒用独立 Review ref。Context 必须 `fixture_only=true`，所有允许 fixture 的选项只在隔离入口显式设置。原有真实批准成员的 metadata 不变；新增 fixture 决定不得进入任何生产批准包。至少证明 fixture Context/generation 不能被默认生产入口接纳，不为预演关闭既有生产 guard。

按现有 B pipeline 连续完成：

1. 非空 delta 的实际 managed SQL 导入、old+new snapshot 与 exact raw observation 核验、重复导入精确幂等。支持的 DQ 候选使用同一专用 fixture 命名空间；缺证 session 不得由 mock metadata 填充。
2. fixture Context 固定原 133 exact inputs、126 outputs、全部 resolver/policy/design/implementation pins 和实际 external evidence 引用。取得时间、可用时间与审批时间不冒充历史 PIT。
3. 第一代 126 个完整输出、真实 DQ；同一 Context 第二代独立 rebuild。每个源行精确进入 resolved/quarantine，保留 native、NULL、typed empty、units 和 source lineage；不通过排除所有行制造 PASS。
4. 两代 logical/schema/quarantine/lineage 对比，以及四个时区 managed close/reopen 后的 Context/member/完整代选择核验。保留 BLOCKED 的局部 finding 与准确分母。
5. 原 192 resolved 和旧批准原样保留；生成本批新增影响的精确行级/finding 差异，引用旧完整账本。不重复生产相同的 402246 行全账本或 15756 finding 账本。

记录预演是否走到 import、Context、generation、DQ、rebuild，每一步实际产物与缺口。工程预演成功、候选数据 DQ BLOCKED 可以同时成立。不得写“Admission B 完成/批准”或“Phase1C.2 READY”，也不要求用全局 PASS 才交付。

### 4.3 新候选仍为空时避免空跑

当前已核验新 delta 与 DQ envelope 都为空。完成证据调查后若仍没有实质新候选，不重复执行与旧 B 相同的两代重建。记录 `REHEARSAL_NOT_RUN_NO_NEW_EVIDENCE`，明确哪些事实缺失及下一步取得方法；其余修正、live 准备、mock 安全验证和交付照常完成。

只能用合成材料补证新工程路径，不能把合成事实算为历史身份/session 闭合。不要为了状态好看造非空 delta。

## 5. 测试和交付集中一次

开发期间跑受影响路径的必要测试；修复故障后聚焦复验。最后统一执行仓库要求的全套离线 tests、doctor、contracts、decoded secret scan 和 exact-SHA CI。已验收且未改变的旧能力证明用文件 hash、pin 与引用保全复用，不为内部步骤反复跑全套或 stress。

新增源码/设计/文档可按必要提交集中推送。区分 implementation SHA 与最后材料提交 SHA，避免自引用 hash；最终所有索引、候选 Context、代码 pins、ZIP 与 handoff 指向一致的实际文件。

交付新目录：

- `docs/reviews/phase1c1-combined-remediation-b-rehearsal/<run_id>/`：脱敏最终报告、授权范围、来源校正、准入条件表、tests/CI 与准确状态。
- `data/private/phase1c1-combined-remediation-b-rehearsal/<run_id>/`：live 设计/安全验证、原 plan 引用、候选与预演材料分别索引、隔离产物/证据、原库保全、旧证明引用、manifest/ZIP/final-handoff。

只提交一个最终 Review 请求，给 final SHA、CI URL、公开报告、私有 ZIP/完整索引/handoff。最终状态 `COMBINED_REMEDIATION_B_REHEARSAL_REVIEW_READY`；同时报告候选数量、预演实际状态、仍缺事实、真实 API=0、原库写入=0、133 未重跑、Phase1C.2 CLOSED。

## 6. 联合 Review 后的应用边界

本次联合 Review 可以一起裁定修正、live 工程、证据充分的有限 case/DQ 和隔离 B 结果。无须回到逐个小 Gate。

Review 真正批准的材料才进入后续正式 B。批准 ref/time、member hash 或实现 pin 变化时，Context/hash 必须重新计算；不能把 fixture hash 直接当生产 hash。正式 B 使用实际批准材料完成必要的匹配副本核验，再有限追加到原库；实现未改变时复用工程证明，只补验批准材料及实际应用路径。

若需要真实 7 次 metadata 请求，须有本次通过的 live 代码、计划匹配的运行许可和用户对这 7 次请求的明确授权；取得的实际响应还要作为 session 候选提交裁定。当前 0 API 批次无法保证全部历史身份、BSE 或日历缺口闭合。

不得把一轮联合工程 Review 写成正式 B、全历史数据或 Phase1C.2 执行授权。优先推进有依据的部分；一次说明剩余外部依赖，不重复不变输入制造审查轮次。
