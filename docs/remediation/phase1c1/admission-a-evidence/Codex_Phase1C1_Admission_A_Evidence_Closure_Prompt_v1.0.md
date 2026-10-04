# AStockSystem Admission A：集中补足证据与最终审批材料

2026-10-04 · 可完整复制交给实现 Codex。

请在 `/Users/yanliu/Documents/AStockSystem` 执行本批次，一次完成材料纠正、允许的文档取证、有限身份/DQ/Context 提案及准确的新数据取证申请，最后统一 Review。批次内部连续推进，不逐证券、URL 或小 Gate 停顿。

## 1. 目标与审查基线

先读取仓库 AGENTS.md、Admission A 原授权、保留的 A/B prompts，以及：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-04_Phase1C1_Admission_A_Independent_Review.md`。
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C1_Admission_A_Independent_Review_Manifest.json`。
- `/Users/yanliu/Documents/AStockSystem/docs/reviews/phase1c1-admission-a/2026-10-03/`。
- `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-admission-a/2026-10-03/final-handoff.json`、package-manifest、最终 indexed proposals 和完整本地账本。
- 已冻结 R1/R2 specifications、UTC instant v2 设计与政策、writer lifecycle；沿用原 A prompt 指定的主设计与原批准材料。

已审查最终 SHA：`90ced0bac3e305c0e994878645f455ceba4e8f5e`；离线实现：`fc23bcf2c5ef11764d619e3bf377f97c8dfc3e12`；工程设计 hash：`3dd7159f6e9c6554ba4326e09127306cfec363acbaac6024c42427e464b1677e`。

本次独立 Review 已验收新增隔离离线 lifecycle / 30126 membership 恢复 / 增量导入和实际调查账本。复用它们的有效证明，不重复造一轮工程修复或压力跑。当前原库仍是 192 resolved / 402054 quarantine；新可执行 identity delta=0；证据仍 BLOCKED；B 未获运行授权；Phase1C.2 CLOSED。

检查 HEAD/worktree，保护用户已有工作；若有后续差异，解释变更而不 reset 或自动视为已批准。新交付保留 `2026-10-03` 全部原材料，用新目录/版本。

## 2. 本批次授权与限制

用户转交本指令后，授权在原 Admission A 范围继续工作：现有真实材料只读、必要官方公告/规则/字段文档查阅、候选与最小必要离线实现、合成/临时隔离验证及提交。原库用 managed shared/read-only 连接；保持全部 34 表、原 raw/curated、已有 Context/generation/audit/批准、SQL001–010、冻结政策及旧 bounded133/126 guards 不变。

市场/provider API 预算 **0**，包括 trade_cal、bak_basic、stock_basic、mapping 与 permission probe。禁止 capture/resume/replay、133 请求重跑、新证券列表/映射表/批量日历数据集下载、原库新绑定/Context/generation/DQ 和 Phase1C.2 执行。禁止以文档查阅名义绕过新增数据授权。

**只读官方文档查阅已经在 A 授权内，不需要先列每个 URL 等审批后再查。** 允许围绕当前明确缺口搜索、阅读必要公告及文档并保存来源 bytes、真实取得时间、发布精度、hash 与支持命题。采用共同来源，避免无依据的批量 crawl；新市场数据集下载或 API 调用仍需另行批准。普通文档读取失败记录原因并继续其他独立工作；不要每个缺证 case 单独停顿询问。

作者不签生产批准。本报告的工程 review_ref 不能填入 case-set、DQ、Context 的生产批准字段。所有新候选 actual approved_at/review_ref/approved hashes/license 保持未批准；合成 fixture 批准明确隔离。

## 3. 合并纠正两个材料问题

**F1 预算。** 将 full-backfill gross30126、exact reusable、net、前置/分片/另行 reserve 拆开。全部126通过复用时net30000；未确认复用前不扣减的base上界30126。30,100若无明确依据删除；若有100reserve逐项解释用途及许可，不能默认重试。不要把最小调用间隔估算写成含延迟的运行时间上界。统一公开提案、private JSON、checklist、handoff、索引及 hashes，保留旧版本。真实session数、账号权限、截断和追加分片仍未知，计划不执行。

**F2 审批入口。** 新版 approval-request 必须与最终 index/handoff 指向同一 Context proposal。检查实现 pin、设计/policy/input/resolver/delta hashes，全链路一致；不要继续指向 implementation_sha=null 的早期 Context。原材料保全项连接到实际最终 before/after 与本次独立证明，状态不得残留 PENDING_FINAL_CHECK。补自动化材料一致性检查仅用于可复核交付，不扩大生产审批范围。

这两项与下面证据工作一起交付，不再为两个文档字段增加独立 Review Gate。

## 4. 重点补正面证据，复用调查账本

不要重新生产完整402246行账本，只对新增支持命题或候选计算必要增量与hash。旧346 case、251 inactive drafts、5584 carry、248 BSE及15756 findings保留交集与历史处置，不按人数加总。

### 4.1 共同来源与普通连续性

先建立 `claim → existing facts → missing facts → potential shared source → exact covered members/exclusions` 矩阵。优先现有 raw、官方历史规则/发行人披露与供应商说明能够共同支持的有限组。

对于 386249 ordinary-continuity 调查行，确定哪些既有事实可证明 issuer、episode、官方代码区间与具体 endpoint native 表示；不能把 current stock_basic、相同代码/名称、观察最早最晚或旧resolver成功单独当完整连续性证据。不同 endpoint 分别判断，不强求每只证券都制造相同的独立文件，也不降低批准要求。

可先研究官方文档线索 `https://tushare.pro/document/2?doc_id=262`（bak_basic）：分析已有说明中2016起的覆盖、ts_code/name/list_date语义、cap及所需权限，给出能支持和不能支持的命题。这里只读文档，**不调用 API、不下载它的历史证券数据**。它不覆盖2013，不自动证明episode/代码复用/所有endpoint连续性。若确实值得新增取证，放入最小、准确、待批准的数据申请，不能先全面抓取来验证价值。

每份正面文档标明实际 bytes 与抽取内容区别、URL、发布精度/取得时间、hash、定位段落、支持/反驳命题和成员hash。只有搜索摘要或无法取得原文时按线索保留，不伪装成原始证据。

### 4.2 优先完成15 missing-bar 的精确提案

独立 Review 已证明15项全部有old/new native同内容原始观察；无需新bar请求。围绕000022→001872、000043→001914、300114→302132补尚未批准scope的正面身份/endpoint依据，保留原192批准。

对每项写明：两条actualraw UUID/zero-based ordinal/日期/dataset/capture hash、episode与官方代码事实、endpoint-native为何如此表示、并存/重叠处理依据、拟新增binding及精确成员、能解除何种finding、仍需session/reference的条件。相同值不是独立alias证明；不提前dedup、不改native、不关闭旧finding、不复制raw。

只读计算拟议影响，明确是候选估计而非真实generation/DQ PASS。确有证据的非空有限组可作为独立可审批子集，无须等待全部历史case；未证明的仍隔离，并明确不足以开放完整准入。

### 4.3 BSE 与 venue/session

复用248 cases /31248cells。共同材料分别支持2021-11-15开市、2025-05-06六只pilot、2025-10-09其余242只的事实，逐endpoint连接实际观察与episode，缺一侧保持NOT_OBSERVED。

查阅适用的官方开市/休市/交易规则，补21日期及所需previous-session证据。原SSE只证明其范围；不能推算工作日或默认BSE/SZSE=SSE。新增身份scope后重算session需证分母；不能只改旧63项就声明全市场PASS。区分官方更码对、provider-native、episode连续性、venue calendar四种命题。

### 4.4 特殊资产/NULL与其他缺证

689009、T600018、上市/退市/last trading day、代码复用及UNKNOWN资产明确支持/反驳事实。不改前缀、填NULL、统一delist+1或给CDR通配豁免。既有1374 pre-BSE OUT_OF_SCOPE继续隔离且不计resolved；扩大处置必须另提精确证据。

保留15756旧finding的exactkey/payload/severity及1226coverageflags。新candidate裁定连接旧finding，不覆盖历史。复用固定DQ政策和容差；确需新语义时新版本冻结与合成回归后提Review，不根据结果降低门槛。没有适用session/factor的causalpairs按unknown分母报告，0 mismatch不能声称PASS。

## 5. 新数据取证申请必须做到可批准；本批不执行

复用现有7个SZSEtrade_cal窗口：

| start_date | end_date |
|---|---|
| 20130104 | 20130108 |
| 20200821 | 20200825 |
| 20211112 | 20211116 |
| 20250430 | 20250507 |
| 20250930 | 20251010 |
| 20260703 | 20260707 |
| 20260928 | 20260930 |

exchange=SZSE。每项最多1attempt，最小间隔至少1.25秒；unknown call停止且不自动重发。metadata取证与future full-backfill预算分别列。

补成准确候选计划：endpoint/method、api_name、params与fields及类型、contract版本/canonicalhash、canonical算法、确定requestID、membershiphash、预算、隔离destination、返回上限/截断判断、来源与取得时间、immutable raw/manifest/sidecar/hash、会解除的精确session缺口及仍不足以证明的BSE/identity条件。参数采用contract要求的实际格式，不能把展示日期的连字符误用进请求。

检查实际安全路径：现`TushareClient.fetch_slice`只批准旧SSE窗口，新offline模块仅支持fake transport。禁止改旧SlicePlan/SSEguard或借genericfetch/自动retry绕过。若没有可用的专用metadata执行路径，先冻结独立最小设计，补必要隔离离线计划/状态/落盘验证，保留旧guards；不部署原库、不试连、不把execution_license切true。实际transport启用须待该设计/代码及exactrequest计划被审查并获用户授权。

不能承诺只需7个calendar请求就解除全体身份和BSE缺口。其他新数据提案只在能解释增益和局限时提出，精确列scope/预算/权限未知/调用方式/失败停止/存储；未知URL、dataset或分片数量不得伪造执行计划。不要实施5930×4的默认逐证券抓取循环；23720是旧粗估，先用共享来源减少真实取证需要。

## 6. 一次完整交付及停止点

在新的 ignored private目录准备：

- 本次已有证明复用及实际变更矩阵；F1/F2纠正与全链路一致性结果。
- 正面证据与缺口矩阵、按有限成员的groups/规则/排除项及支持来源hash。
- 非空可证明子集的candidate case delta与existing+delta完整resolver，或明确空delta及不能生成的具体原因；旧成员原批准时间/ref不变。
- 匹配的DQ evidence proposal、bounded133/126 Context proposal、实现/设计/policy/input/resolver/delta pins；新批准字段未批准。未来新增metadata如何进入冻结DQ/Context的来源体系须在设计中解释，不能偷偷变动旧133/126成员。
- 可批准的最小evidence-acquisition-request；单列7metadata、新历史身份数据建议、允许文档查询记录与未来full-backfill预算。
- checklist、approval-request、package-manifest、final-handoff，全部入口/bytes/canonicalhash/counts一致；每条仍BLOCKED的条件连接具体事实与下一步。
- sanitized公开review与最小ZIP；大账本/数据只以私有索引pin，不公开原始数据或凭据。

变更实现时按仓库要求运行必要合成回归、一轮最终全套/doctor/contracts及exactSHA CI；不在文件生成stress仍运行时做原目录不变断言。材料变更复用已有有效工程证明，做索引/hash/入口/算式/保全/secret扫描；依仓库要求核验最终SHA CI，不为每个内部commit重复全套。市场API路径用deny/counters，允许的文档HTTP单独记录；凭据不试探、不打印。

交付状态使用 `ADMISSION_A_EVIDENCE_REVIEW_READY`，并逐项列 engineering/evidence/bounded admission/production integration/full history状态。一次给最终SHA、报告、ZIP、handoff及未完成事实。最后停止，等待独立裁定和任何真实新增取证/B运行授权；不得自行宣称进入Phase1C.2。

如果允许的文档与现有raw不能补足正面依据，仍完成所有独立工作及最小取证申请，交付BLOCKED原因。不要再交一个仅把原缺证行重复列出、也没有可批准取证方案的包。
