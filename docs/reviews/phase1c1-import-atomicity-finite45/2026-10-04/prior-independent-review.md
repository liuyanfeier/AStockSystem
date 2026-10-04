# Phase 1C.1 Remaining Evidence Combined 独立 Review

本批材料、原库保全和按失败分支停止执行的行为通过验收；新增身份导入路径为 **CHANGES REQUIRED，1 个 P1**。45 条有限端点候选的证据得到支持，但尚未完成成功预览和匹配生产审批。日历采集仍 BLOCKED，整体 DQ 仍 BLOCKED，**Phase 1C.2 CLOSED**。

审查基线：`fd1d1b5638a0194ae30adcc59f06fc1ab4a25f62`；独立资料与数据库核验完成于 `2026-10-04T14:45:34+00:00`。本批没有新提交，工作区干净；失败分支要求保留原实施 SHA 和已经使用的 license，作者遵守了该要求。

| 审查范围 | 结论 | 实际结果 |
|---|---|---|
| 材料、引用链、原库和历史保全 | PASS | 原库及 136,599 个基线文件保持原 bytes/hash；167 个实施 pins 不变 |
| exact7 日历执行边界 | PASS，采集 BLOCKED | 1 次 reservation、1 次本地 call-entry、0 成功，另外 6 个未尝试 |
| 新端点候选证据 | SUPPORTED FINITE CANDIDATES | 9 个 bindings、45 个 exact observations；生产审批为空 |
| 新候选导入及预览 | CHANGES REQUIRED | 导入报错发生在提交后，隔离库已持久化 9/45；没有执行转换或新 generation |
| 已正式接受的 limited15 B | 既有 PASS 仍有效 | 原 207 resolved、两代各 126 输出及 Context 保持不变 |
| 全局数据与 Phase 1C.2 | BLOCKED / CLOSED | 402,039 quarantine、63 个 uncertified sessions，未关闭新 finding |

## 唯一工程 finding：P1，失败导入已经提交，无法按相同增量重试

[admission_delta.py 第 70 行](/Users/yanliu/Documents/AStockSystem/src/astock/data/admission_delta.py:70) 先调用 `import_approved_cases()`，再比较导入后的 resolver hash 和提交前构造的候选 hash。[reconstruction.py 第 286 行](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction.py:286) 已经完成 `transaction(db, apply)`，第 287 行才重新读取 resolver。因此外层比较抛出的 `Imported merged snapshot differs` 无法回滚新增身份记录。

本次触发条件是同一 binding 中 observations 的排列次序：输入按 event date 排列，数据库读取按 `raw_object_id, raw_row_number, event_date` 排列。模型接受该输入；v2 canonical serialization 保留 observations 顺序，冻结的 [time-integrity addendum](/Users/yanliu/Documents/AStockSystem/docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md:15) 也明确保留其语义。双方 observation 集合及其字段相同，resolver hash 仍不同。这不是缺失 raw、错误 ordinal 或 alias 证据引起的失败。

对作者保留的失败隔离库只读核验得到：

- 新 9 个 bindings、45 个 observations 已经持久化；总数为 24/252。
- 9 个 binding 的差异全部只有 observation 顺序。
- 预期 hash：`0598ecfb1d4aa845e24215254c00cc326627d28ac95d74fc878a30491ddadef9`。
- SQL readback hash：`b34c6d902c3ca98dc395f5c383bc0b34675bca4bc10d8e3bbdba5cd59216b0c3`。
- 没有新 Context、转换、generation 或 DQ audit；252 是身份 observation 数量，不能作为已解析行情输出数量。

我另建纯合成 managed store 独立复现：合法 raw 的两个 observations 倒序后，首次调用报 `Imported merged snapshot differs`，binding/observation 数却从 1/2 变成 2/4，关闭重开仍保留；再次提交同一 payload 报 `Existing member conflicts with delta`。复现没有写原库，也没有 provider 请求。

影响是“调用失败却留下持久化的新身份事实”，并破坏正常幂等恢复；因此定为 P1。不能仅调整候选辅助脚本的排序来掩盖它，必须修复核心事务边界。最小兼容修复是在写入前明确拒绝不能按当前 SQL 顺序往返保持 hash 的输入，并把导入后的完整 resolver 核验放在同一事务的 COMMIT 之前，任何失败回滚所有新增表记录。

原 limited15 的获批输入已满足既有读取顺序，其原库和历史材料完全不变，本次不撤销该有限范围验收。但之前“工程修复已经完成”的结论需要收窄：已验收路径仍通过，扩展到新增多 observation bindings 后暴露了这个未覆盖的事务问题。

## 日历：正确停止，实际证据仍为零

专用固定 metadata store 保留 7 个精确计划成员。只有第一个成员出现 `CLAIMED → CALL_ENTERED → FAILED`，失败原因是 `TRANSPORT_UNKNOWN_NO_RESEND`。独立核验有 1 个 reservation、1 个本地 call-entry、0 receipt、0 response body、0 civil rows、0 成功成员，另外 6 个没有尝试。

没有收到 provider response，故远端是否收到请求、账户是否有权限均为 UNKNOWN。不能改写成“provider 拒绝”“积分不足”或“请求成功但数据为空”。最小间隔 1.25 秒已配置，但只有一次调用、没有相邻调用对，实际 pacing 间隔验收为 N/A。

实际 license 与此前获批模板的执行 pins 一致，只按原授权填写真实用户授权和打开 capture license；它没有授予身份或 session 审批。固定 store 的已消耗 attempt、失败事件和原 license 必须保留。此次 Review 不批准重试该成员、补发其余 6 个、重置 store 或建立另一个 store 绕过失败终态。

63 个 venue/date session 均未认证，21 个 SZSE 目标日期没有新增 response 依据。未来日历处置应另行给出已有日志诊断和最小证据获取方案；当前修复批次 provider API 为 0。

## 45 条证据有进展，不能直接变成生产批准

在原 15 个已获批 daily 事实对应的其他端点 raw 中，共定位到 87 个候选。我独立重建并核验其中 45 个使用事件日正式代码的 exact observations：`adj_factor`、`daily_basic`、`stk_limit` 各 15 个，构成 3 个既有发行主体 × 3 个端点的 9 个 proposed bindings。每条均核验 raw object、零基 ordinal、date、row hash、原获批 daily 关联和事件日官方 code，未提出新 episode 或 code interval。

本次核查的 provider 原文支持这些端点的股票代码字段范围，结合已有发行主体/历史 code 资料，可支持上述有限事件日 native 候选。它不能证明未覆盖的历史区间、别名或当时已公开可知的时点。[复权因子文档](https://tushare.pro/document/2?doc_id=28)、[每日指标文档](https://tushare.pro/document/2?doc_id=32)、[涨跌停价格文档](https://tushare.pro/document/2?doc_id=183)。

因此结论为 `SUPPORTED_FINITE_EVENT_NATIVE_CURRENT_RECONSTRUCTION_PENDING_ENGINEERING_AND_MATCHED_APPROVAL`：保留为可继续预览的有限候选，reviewer 生产审批为空，execution license=false。需要先修复上述工程问题、成功完成新版本隔离预览，才可生成匹配新 SHA/事实范围的正式审批包。

42 个新代码端点表示仍缺 alias 依据，原 15 个 daily mirrors 也继续隔离。值相等或发行主体相同不构成 provider alias 语义。原 raw 中 `dv_ratio`、`dv_ttm`、`pre_close` 各 3 个 NULL 原样保留；没有填 NULL 或修改 tolerance。

其他新增原文的作用也有限：CSRC 文档支持北交所于 2021-11-15 开市，不补足 248 主体的历史 episode、代码迁移或独立 session；SSE 公告支持对应特殊证券的 CDR 属性及 2020-10-29 上市，不解释 provider STK 标签或价格字段 NULL。[CSRC 开市资料](https://www.csrc.gov.cn/csrc/c101800/c7161925/content.shtml)、[SSE 上市公告](https://www.sse.com.cn/disclosure/announcement/listing/c/c_20201027_5242851.shtml)。作者保留的 3 份 HTTP403 denial body 没有被用作迁移事实。

## 完整分母和原库保持不变

独立读取完整旧 membership 并核验唯一性、当前 Context input raw 集合、24,809 个分组/native/endpoint/event matrix cells。原 402,246 行分母没有被正例子集替代。

| 组 | source rows | 当前 quarantine |
|---|---:|---:|
| Ordinary continuity | 386,249 | 386,249 |
| Historical code change | 117 | 102 |
| 已获批 pre-BSE out-of-scope | 1,374 | 1,374 |
| 既有 approved192 | 192 | 0 |
| Unknown identity/asset | 1,224 | 1,224 |
| Special native/asset | 60 | 60 |
| BSE transition | 13,030 | 13,030 |
| 合计 | 402,246 | 402,039 |

原库仍有 207 resolved，402,147 findings = 402,039 identity + 63 session + 15 factor + 30 cross-endpoint；本批没有实际关闭新 finding。60 个 causal relationships 仍 UNKNOWN。248 主体/31,248 cells 的 BSE 专用矩阵及已获批范围外处置被保留，两个迁移阶段未合并推断。

原库 SHA256：`27aabd6143d977decefefb8eb1f1b2b9e66ee29c14045d9df284871bcecf065f`。

原 Context hash：`470017335c3e7fd9f69480b35e2ac3012ceea2892a3f94706fdfcfb5af262475`。

metadata store SHA256：`91a2c5d20df935795e0e2b736175af13fb6b7b5f6092231a9e96975fd30b9ece`。

失败隔离库 SHA256：`ec32a43385df4c864fa054be0bc0b736a767552e2a47aaffab79286172a54890`。

独立读取前后这三个数据库 hash 一致。原 15 bindings、207 observations、2 Contexts、4 generations、4 quality audits、181 raw manifest 保持原数量与 bytes；没有向原库 import/register/build/audit/migrate。原 limited15 的两个 COMPLETE generations 和每代 126 输出沿用已独立核验的保全证明。

## 验证与交付完整性

独立校验 148 个 manifest 文件、10 个 external 文件、156 条 active reference edges；作者 ZIP 的 149 个成员 CRC、唯一名称和内容均通过，原授权 Prompt/Review 副本与 reviewer 原件一致。原材料和 ZIP 的当前凭据 literal 扫描通过，没有显示或公开凭据。

作者 ZIP SHA256：`4129d2e9525cff530df0c679d83814210d91cc2b416a3a8a31f8d684f2a206e6`。

独立 strict133 检查为 VALID、133/133、0 failures。新增复现得到 P1；现有 `tests/test_admission_delta.py` 控制测试为 **2 passed in 1.46s**，没有覆盖该顺序和提交后失败场景。[同 SHA 既有 CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/37196377082) 的 736 passed、4 warnings 复用此前独立核验的 exact-SHA 证据；本轮没有重跑全套，也没有把其通过当作新候选或日历证据通过。

本轮 reviewer 的 provider/市场 API 请求 0、原库写入 0。公开文档核查与 provider 数据 API 分开计数。

独立可复核材料保存在本工作区 `outputs/private/phase1c1-remaining-evidence-independent-review/`：artifact validation、data validation、纯合成 postcommit reproduction、primary-source verification、targeted control tests 五份 JSON；ZIP 同时收录三个独立核验脚本。脚本的本轮结果是实际执行产生的；纯合成复现若复跑须选择新空目录，不能覆盖本轮失败历史。

## 下一步一次完成

使用同目录 [Codex 合并修复与预览 Prompt](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Import_Atomicity_And_Finite45_Preview_Prompt.md)：一次完成最小事务修复、有效回归、新版本 45 条候选的真实隔离转换预览、最终测试和 exact-SHA CI，再集中 Review。

本批不改 v2 hash/order/time 语义、不重写旧审批、不重新研究既有 15 个 daily 事实、不重跑同样两代历史 rebuild、不再次采集 metadata。修复与新候选预览是内部依赖步骤，可连续执行；原库正式应用和任何失败日历成员的未来执行仍在独立批准之外。Phase 1C.2 保持 CLOSED。
