# 交给 Codex：新 runner 四项修复与取证审批准备，同批完成

请在 `/Users/yanliu/Documents/AStockSystem` 执行。起始审查 SHA 必须为 `93d605676892459f78607790278bccc7a80e8f29`；先核验工作区和差异，若出现后续变更，保留并说明，不能覆盖用户或其他任务的工作。

读取独立报告：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-06_Phase1C1_Evidence_And_Launch_Preparation_Independent_Review.md`

读取独立证据及四个复现脚本：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c1-evidence-launch-independent-review/`
以及同一审查交付 ZIP 中的 `scripts/`。它们是审查证据，不是生产 approval/human license。需要再运行复现时，改用全新私有合成目录，不覆盖已交付的复现事实。

## 目标与授权范围

一次完成 F1–F4、必要的完整回归、最终材料闭合及下一次取证许可申请，全部完成后集中提交独立 Review，中途不因每个小修复停下来请求 Review。

本批为离线工程修复与审批准备：真实市场/provider/calendar/mapping API 0，新增文献 HTTP 0，原仓库 DB 写入 0，133 replay 0，finite45 reimport 0，Context/generation/DQ rebuild 0，旧 metadata reset/resume/retry 0。允许在新 private 工作目录保存合成 DB/raw/mock 产物并修改新 runner 的实现、测试、catalog、独立 DDL/设计及新版本提案。

不得开始 Phase1C.2。所有实际执行许可证保持 false，approval/human 的生产批准字段保持待审。不要生成看似正式但实际无人批准的许可。旧 R1/finite45 已 CLOSED；不重新打开旧 importer/schema001–010，不修改既有 171 个冻结文件。若新 runner 必须变更存储协议，写清版本升级设计并隔离合成验证，不部署到旧原库或改写旧 source/失败记录。

## F1：按 contract 保留合法 nullable suspension key

修复 `src/astock/data/full_backfill_v1.py` 的 generic natural-key NULL 拒绝逻辑。依据冻结 `config/contracts/v2/suspend_d.yaml`，`suspend_timing` 可以 NULL；完整自然键仍包含该原生字段，全天与盘中语义必须保留。

实现端点 contract 可追溯的 nullable-key 规则，不用全局放宽。raw/body 与 source-typed Parquet 保留原 NULL，必需的 code/date/type 缺失仍拒绝，含 NULL 的完整 tuple 重复仍拒绝。不得用空串/0/推测值规范化，不修改 `stk_limit.pre_close` DQ 或借用其他端点价格。

回归至少覆盖：合法全天 NULL 成功闭合、盘中 timing、非 nullable 必填键缺失、NULL tuple 重复、同日不同合法 timing、完整文件重开 ALREADY_VALID/零新调用。证明原三个 reference-price finding 未被豁免。

## F2：首次完成前，在事务中验证最终磁盘事实

首次 publication 后和最终 COMMIT 前，不能只相信先前读取的 body 或内存派生对象。共用一个可审查的闭合验证路径，验证准确五文件集合、路径安全与只读事实、body/source绑定、时间、typed schema/原生 NULL/整数/完整内容、manifest/sidecar hashes、对象 UUID、member/params/fields/contract、原计划与许可 provenance、receipt 与 COMPLETE event。

在 receipt/COMPLETE 的同一受管理事务中进行最终 readback/hash 校验，覆盖 `after_registration` 与 `after_promotion` 故障点之后、COMMIT 之前。失败须回滚成功 receipt/event，保留已经消耗的 claim/CALL_ENTERED 和错误/source 事实；不得覆写损坏的原始证据，不得发第二次 HTTP。合法 partial source 的本地 reconcile 仍可恢复。

使用实际文件变异做回归，至少包含 after_sidecar 修改 body、source/typed/manifest/sidecar 任一篡改，登记后/提升后变异，异常中断与重开。断言“返回成功、持久化 COMPLETE、磁盘五文件有效”三个条件同时成立；无效时零成功 receipt、没有假 COMPLETE、零重发。先复现旧 SHA 的缺陷，再验证新实现确实改变结果。

## F3：固定 store 的多计划登记与全局消耗

目前 singleton backfill_pin 只允许一个计划，实际日历→首批行情→年度分片会报 STORE_PINS_CHANGED_NO_RESET。设计并实现 append-only 版本化 plan registry，生产仍使用唯一固定消费账本与保存根，禁止通过新 store/run 清空消耗。

每个计划独立保存不可变 plan/hash/membership/budget/实现版本/外部 Review/用户许可。每个成员的实际捕获保留它首次消费时的原计划及许可绑定；新计划登记、批准和执行不能修改原批次 provenance。已有 COMPLETE 必须用原批次 pins 验证，不要求它符合新审批摘要。全局逻辑请求 consumption key 与“同逻辑成员”的定义要在设计中明确，不能因 plan/budget/namespace/run 名变化便获得第二次调用。

跨计划重叠 COMPLETE 应在匹配原 immutable receipt 验证后明确 reuse 或 reject；跨计划 FAILED/UNCERTAIN 仍不可隐式重发。重复审批、篡改旧 plan、未知 orphan、超预算和并发 claim 均 fail closed。旧 metadata 的 FAILED/1 consumed/6 unattempted/0 receipt 状态不变；旧逻辑成员拦截不能删除。不同范围但与旧失败窗口重叠的申请保留单独审查处理。

一次做真实离线集成：计划 A calendar 完成→关库重开→独立批准的计划 B 首批 market 完成→再次重开→计划 C 后续新分片完成；旧 receipt/raw/event/pins 逐项保全。覆盖新批预算独立、总消费可审计、旧 COMPLETE 再验证零调用、跨批 FAILED/UNCERTAIN 零重发、旧批审批 hash 篡改/错配、新 store 绕过与入口固定位置检查。

必要时新增独立 runner 协议/DDL版本，写迁移或旧 fixture 只读兼容方案。不要通过删除 backfill_pin 检查解决；不要直接改写旧已冻结 fixture DB。保留旧 v1 原物与 hash，另建新版本合成产物。

## F4：冻结最终描述符后，重新闭合所有 hash 域

旧申请 `calendar_member_hash` 声明 9448041e…，最终 `checksum(venue_calendar_requests)` 实为 0ff5d7ff…。更新生成流程：先完成所有 request/descriptor/purpose/provider applicability/storage/budget/stop fields，再 canonicalize/hash，再生成索引/manifest/ZIP/delivery 引用。

明确三个不同域：运行时 requests membership hash；完整审批描述符集合 hash；文件字节 hash。逐一机器断言，不互相替代。所有申请和将来许可引用必须与最终材料匹配；改任何字段都会使相应审批摘要失效。覆盖描述符字段被追加/修改、reorder规范、成员变化、索引漂移的实际回归。

使用新版本 private 目录与交付链，保留本轮旧 ZIP/申请/描述符。检查主申请、runner plan、first-market proposal、全计划、index/manifest/handoff 的所有 active refs，不能只改报告。

## 同批准备下一次可审批的取证申请

保留 36 个完整日历目标 inventory：SSE15、SZSE15、BSE6，完整参数/fields/保存路径/contract/单 attempt/间隔/预算/停止条件不省略。另生成首批 **29 个 candidate** 的独立 proposal：SSE15 + SZSE14；7 个 HOLD 为 SZSE2013 和 BSE6。它们是取证申请，尚未获准运行。

SSE/SZSE 年份保持旧申请：2013..2025 全年、2026截至09-30；各有2012年12月 previous lookback。29批不包含 SZSE2013。不要自行扩大 lookback，也不要把旧6个 UNATTEMPTED窗口加成额外预算。全36目标与29/7逐member映射、原因及后续解除条件必须机器闭合。BSE参数无文献支持不能套SSE；SZSE2013与旧失败范围重叠不能改名绕过，不把CALL_ENTERED当成远端成功或拒绝。

36个calendar成员当前 completeness_evidence全为None，生产guard会拒绝。为29候选准备**可审查但尚未批准的完整性规则证据**和 exact pins：每个请求窗口内 civil dates 完整集合、唯一(exchange,cal_date)、日期与venue边界、is_open合法值、pretrade_date的合法/递增/跨窗口关系、previous lookback关联，以及失败/cap/空响应处理。字段定义必须与 provider 原文一致。完整 civil 集合匹配可以用于判断小窗口响应是否完整，不能宣称未知cap已变KNOWN、账户已验证或真实calendar已认证。证据规则进入提案引用，后续独立 Review 通过后才能成为许可 pins。

闭合mock测试证明：无实际approval/human/live时零HTTP；完整响应通过候选规则；漏一天/多一天/重复/错venue/错误previous关系/空或截断响应停止；29批不会请求任何HOLD成员。actual calendar认证数仍0，直到未来真实捕获和独立批准。

首批行情仍为2013-01-09六端点、6次、reserve/retry0，保留所有未齐依赖：历史universe/native、真实calendar、账户权限、端点cap/empty/完整性、adj_factor未知cap与新runnerReview。不得把29日历取证申请理解为行情或全回填许可。

保留未来9个公开文献GET申请及exact URL/hash/单次预算、失败停止与保存路径，它们不消耗或复用已耗尽的24次预算，本批不执行。已有原文可继续离线解析并为准确事实做定位；搜索摘要、landing页、403、未知字段不能变成identity证据。仍缺原始附件的事项列清可审查获取计划，不凭猜测造URL。

历史identity/native、BSE248主体/31,248cell矩阵、历史alias57、unknown1224/special60、3个reference-price缺口按实际事实保留，不生成空模板冒充候选。新证据不足时，明确新增候选0及原因。不要以“为了结项”合并证券episode、推断alias或改DQ规则。

全目标保持2013-01-01..2026-09-30；30,126仍为base保守上界、verified reuse0，额外分片与真实吞吐/磁盘开销仍按证据标UNKNOWN。全历史raw完整性、年度真实rebuild和回填后coverage/causal终验留在回填后；无需为了本批修复制造全历史raw。

## 验证、保全与单次交付

先保存保全baseline，修复后比较原库34表完整行集、原DB hash、旧metadata四表/状态/hash、schema001–010、171旧pins与145,156保护文件；使用项目managed只读连接。不得因锁失败换不受管理的连接或写原库。对新合成store/多计划产物独立验证，保留实际文件与receipt/event全链，不只交pytest文字。

运行有意义的F1–F4回归和多计划集成，确认实现稳定后运行一次完整suite及项目现有doctor/contract/spec检查，推送并等待精确最终SHA的CI。后续变更必须使相关检查和SHA绑定重新匹配。扫描literal/encoded及压缩/typed Parquet的凭据，DB/raw/完整private申请/ZIP不入Git。

交付一份总报告、一份machine decision、完整且引用闭合的私有package、manifest/index/handoff、新SHA及精确SHA CI。总报告逐项给出四项旧复现→新结果、固定store跨三计划证据、29+7分组与全部剩余依赖。最终状态只能是：

`RUNNER_INTEGRITY_REPAIR_AND_CALENDAR_ACQUISITION_READINESS_REVIEW_READY`

同时明确：旧R1/finite45工程线CLOSED；新runner等待独立Review；Phase1C.1整体结项BLOCKED；full_history_data_admission BLOCKED；Phase1C.2 CLOSED；所有execution_license=false。本批完成后停止，不执行任何待审批申请。

修复通过之后，独立Review者可一次审查新runner及29日历取证申请，再由用户签发匹配计划的真实运行许可。历史证据与整体结项仍须根据未来实际结果审查，不能承诺“这次修完必然进入Phase1C.2”。
