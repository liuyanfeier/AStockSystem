# Phase1C.1 剩余取证与启动准入：合并执行，集中 Review

本 Prompt 将已经准备好的取证、全部可做的历史证据分析、政策/Context 提案和启动准入材料合成一个批次。用户必须明确指示执行本 Prompt，才授予下述真实请求范围；阅读或引用它不构成授权。当前尚未执行这些请求，Phase1C.2 仍 CLOSED。

目标是尽量完成剩余准入工作后一次性交付 Review，不按日历、identity、NULL、材料各停一次。不能保证外部证据一定取得；确需新请求/新范围时，将明确申请加入同一个最终交付包，不绕过批准，也不停止其他独立可做的工作。

## 当前已完成的工作

仓库 `/Users/yanliu/Documents/AStockSystem`。已审查实现 SHA：`57812dd921df0720680b3034c186734852f13648`。

R1/finite45 工程线已 CLOSED；新增 runner 的 F1–F4 与 root clone 修复已独立 PASS。120 定向与873完整测试已经核验，不再次开一轮相同离线修复。完整报告：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-08_Phase1C1_Runner_Repair_Independent_Review.md`

原库/旧metadata、171pins、146,151既有保护文件、schema001–010、原raw/curated/审批/Context/generation/DQ均保留。没有授权清零finding、重导finite45或开始回填。

## 用户明确执行本 Prompt 后的请求范围

1. **最多29次 calendar API**：严格使用现有独立批准的SSE15＋SZSE14 plan、external Review和固定store。继承下列 Calendar29执行Prompt的全部许可、SHA/clean root、只读原库、单attempt、1.25秒间隔、保存、停止和交付要求：
   `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Calendar29_Evidence_Execution_Prompt.md`
2. **最多9次公开文献GET**：本合并Prompt新增的独立文献范围，替代Calendar29单独Prompt中“文献HTTP0”的限制；不改变该Prompt的任何API或原库边界。准确请求列表来自：
   `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-runner-repair-readiness/2026-10-08-v2/future9-document-application-v2.json`

文献文件字节SHA256必须为 `8e761ec7b9451a5988873a0c068fcb9cfc16c205938762566158daeadae9769f`；完整descriptor-set摘要为 `75d9762f8c72a973dc61c209d873721ea6ddc4d66471f197890a45d77a4d1043`。9个URL如下，每个最多1次：

- https://www.sse.com.cn/aboutus/publication/factbook/
- https://www.sse.com.cn/assortment/stock/list/delisting/
- https://www.szse.cn/disclosure/notice/company/index.html
- https://www.bse.cn/important_news/200025603.html
- https://www.bse.cn/important_news/200026735.html
- https://www.bse.cn/service/code_mapping.html
- https://tushare.pro/document/2?doc_id=100
- https://tushare.pro/document/2?doc_id=112
- https://tushare.pro/document/2?doc_id=183

旧文献24次预算已经耗尽，这9次是明确授权后的新预算，不复用旧额度。已保存且足够的原文优先复用，不为凑数重复GET。禁止自动retry/redirect；403/空/未知delivery保留失败原物、不继续该成员。附件URL或其他新URL不在该列表内，不能猜测或自动跟链下载；先提出具体新成员/预算申请。文献无token/auth header，不发送provider询问、邮件或其他消息。

本批最多38次已列明外部请求，其中29是calendar API、9是文献HTTP；行情API0、stock_basic/mapping API0、原133 replay0、原库写入0。SZSE2013＋BSE6继续HOLD，首批6行情未获执行批准。先保留本次真实用户指令，生成匹配Calendar29 external Review的实际human authorization与分开的文献授权/台账，不能由作者重签外部Review。

## 同批完成的四类工作

### 1. 真实日历、previous关系与HOLD材料

执行29成员并核验实际source五文件/receipt/event。异常则停止calendar调用，不重发；仍继续不依赖该失败成员的文献和离线分析。用真实响应补全现有63session/previous矩阵的证据定位、可观测相邻窗口、leading predecessor和未知缺口，提出待审认证事实，不能自动认证或跨venue复制。

为SZSE2013与旧FAILED重叠形成明确范围/兼容性决策申请；旧unknown delivery保持unknown，不能凭新的成功响应声称旧调用未送达或已成功。BSE6需要实际provider参数适用性和venue证据；当前文献的“参考SSE/SZSE”不能变成BSE原生calendar响应。两类HOLD解除材料一起交付，不擅自执行它们。

### 2. 历史证券身份与provider native证据

读取已有source ledgers、发行主体PDF、旧raw，以及本批成功取得的官方文献，统一处理ordinary、BSE248/31,248cell、historical aliases57、unknown1,224/special60等分组。

按证券/发行主体/share class、上市退市episode、official code有效区间、具体dataset/provider-native历史表示和观测时间建立可复用证据，再批量验证覆盖；不逐条手改40万raw行。不凭名称、后缀、相似代码、当前stock_basic或数值相同推断证券连续性/alias。

能满足全部事实的候选集中形成case delta与merged resolver提案，保留旧观察顺序和时间规则；不足者继续隔离并给出具体缺证字段、原文定位或缺失附件。landing页、403或当前字段说明不算历史issuer/episode/native证明。候选非空才生成实际候选材料，不用空审批模板冒充进展。只做提案，不导入原库、不制造作者批准。

### 3. 三个NULL finding及端点政策

核验`000022.SZ`在2013-01-04/07/08的`stk_limit.pre_close=NULL`原事实。用原文和具体历史适用区间提出处理政策、影响范围及离线证明；不能填零、用别的端点价格替代，或借用合法suspend_timing NULL规则豁免。无足够依据就保留三个finding。

同批整理启动所需账户权限、各端点历史范围、cap/empty/完整性和available-time证据。明确adj_factor未知cap及未证明的账户事实。已有信息能证明什么、不能证明什么分别写清；需要额外API探测时形成exact params/fields/member/次数/存储/停止条件申请，不自动调用。

### 4. 最终启动准入与Context提案

合并calendar、identity/native和端点政策结果，形成一个统一的准入状态矩阵、非空且证据充分的DQ/Context候选及可执行启动范围申请。首批仍为2013-01-09六端点、预算6、retry/reserve0，本批不执行。

全目标2013-01-01..2026-09-30不变；保留36日历inventory、29/7分组、30,126base上界、verified reuse0和未知额外分片/存储/总预算。启动准入与全历史最终验收分开：全raw完整性、年度真实rebuild和回填后coverage/causal留在获准回填之后，不要求本批已经拥有完整全历史raw。

任何拟议准入政策或范围变化须显式列入独立Review；不得静默缩小目标、隐藏quarantine、把未解决数据当研究可用，或由作者宣布Phase1C.1整体完成。新的case/DQ/Context批准及原库部署仍需后续匹配批准。

## 一次性交付及停止

不为每个候选、每篇文献或每个表单单独停下来请求Review；内部按照真实依赖执行，最后一次性提交全部结果。独立文献失败不阻断其他文献/分析；calendar失败必须停止其后API，并完成所有不依赖它的工作。

交付：真实29成员/9文献台账、成功与失败source原物、证据定位、候选delta/merged resolver、NULL及端点政策、HOLD解除申请、首批6/全计划/Context准入材料、保全与凭据核验、完整manifest/index/ZIP/handoff。新的任何请求申请均列exact成员与预算，不能只写“需更多数据”。

提供一张可直接决策的矩阵：每个剩余门槛、该批获得的事实、可批准的范围、尚缺具体事实、所需下一项外部动作。对缺口区分：缺文献正文/附件、缺实际provider观测、存在事实冲突、尚待独立政策批准或用户授权，避免统称UNKNOWN。

实现不变，复用已核验120/873测试；实际source/重开/保全不可用pytest摘要代替。所有真实调用结束/停止后才编辑和提交脱敏报告，以免破坏执行过程的SHA/clean root检查。最终文档SHA与执行SHA分别记录，关联精确SHA CI。private DB/raw/完整许可证/ZIP不进Git。

状态为 `CONSOLIDATED_EVIDENCE_AND_LAUNCH_ADMISSION_REVIEW_READY`，明确Phase1C.1整体与Phase1C.2尚待独立结论，不自动PASS。最终集中Review之后，才能依据实际事实决定哪些门槛关闭、是否需要额外取证及是否具备启动条件。

这份Prompt合并执行和交付次数，不保证9篇文献包含全部历史事实，也不授权越过证据缺口。若仍缺外部事实，下一轮只处理清楚列明的缺口，不重新开已通过的F1–F4/R1/finite45工程修复。
