# Phase 1C.1-R1-G1 Independent Review

日期：2026-10-02，Asia/Shanghai。

**判定：CHANGES_REQUIRED。两项阻断发现：P1 一项、P2 一项。R1-G2 不放行。**

审查 exact SHA：`86d3b94fc50f93e52768016b85e83a0c42f70a69`。Base / 已审 G0：`a69cba7bcd722de461eee695469b99e7ea21fe43`。本判定覆盖 G1 实现及其迁移、验收入口、合成测试；不替代 G2 并发/claim 验收或 G3 真实证据验收。

## 1. [P1] PENDING 仍可能掩盖既有 capture 事实，导致再次 fetch

位置：[receipt_integrity.py L219–230](https://github.com/liuyanfeier/AStockSystem/blob/86d3b94fc50f93e52768016b85e83a0c42f70a69/src/astock/data/receipt_integrity.py#L219-L230)。相关调用：[迁移预检查 L53–58](https://github.com/liuyanfeier/AStockSystem/blob/86d3b94fc50f93e52768016b85e83a0c42f70a69/src/astock/data/receipt_migration.py#L53-L58)、[capture preflight / fetch L185–208](https://github.com/liuyanfeier/AStockSystem/blob/86d3b94fc50f93e52768016b85e83a0c42f70a69/src/astock/data/slice_capture.py#L185-L208)。

`validate_slice_batch(complete=False)` 只对 `status == COMPLETE` 的行验证执行证据。冻结计划匹配检查没有检查 PENDING 与其 ingestion run、raw、binding 是否矛盾。因而某行即使已有成功 run 和已注册 raw，只要 receipt 声称 PENDING、attempts=0、object_id=NULL，就会逃过显式升级、resume 和 capture preflight，重新进入 pending 队列。

独立复现采用临时合成 legacy006 库，未修改真实库：

1. 创建冻结 batch；为一个 request 正常 claim、写入一个 raw 与完整 sidecar/capture-contract，并使 ingestion run 为 SUCCEEDED、request_count=1。
2. 在没有 007 binding 的 legacy006 测试库中，将该 receipt 人为置为 PENDING、attempts=0、object_id=NULL，保留全部既有 raw/run 事实。这是故障注入，并非真实 batch 已发生此问题。
3. `apply_receipt_integrity_upgrade()` 返回 `UPGRADED`；`resume_batch()` 返回这条已捕获请求；`claim_request()` 也接受它。
4. 另一份磁盘合成库执行完整模拟 capture，统计到对该已注册 run 的 `SyntheticCaptureClient.fetch_slice()` 调用 **1 次**。随后 RawWriter 的禁止覆盖检查才令结果变为 `BLOCKED / LINEAGE`。

阻断发生在 fetch 之后，因此不能保证“已有执行证据的请求不重发”。这不是 G2 尚未实现的 claim 多语句原子性问题；即使加上事务与进程锁，完整性 preflight 继续忽略这类行，仍会把它当作一次新的合法 claim。

要求在本 G1 内补修：共享 batch preflight 必须检查 PENDING 的未执行一致性，至少核实 attempts/object_id、对应 ingestion run 的状态/请求计数/raw 计数，以及是否已有 raw manifest 或 accepted binding。任何已有执行/完成证据与 PENDING 的矛盾均须在升级登记及 client/claim/fetch 前阻断，输出稳定原因码，保留矛盾事实。不能通过清空 raw、重置 run/counter 或改写旧 receipt 来使检查通过。保持旧预创建 RUNNING/started_at 的既有语义，合法未执行的 PENDING 仍可通过。

必须新增 legacy006 升级前及 007 正常 preflight 的负向回归：PENDING + 成功 run / 非零 request_count / 已注册 raw；断言不进入 claim、不构造真实 provider、不 fetch、旧 rows/files 不变。IN_FLIGHT 的精确本地恢复与 FAILED/UNCERTAIN 的阻断行为继续按已审设计保留。

## 2. [P2] 两个表名存在不等于 007 schema 有效

位置：[receipt_migration.py L47–49](https://github.com/liuyanfeier/AStockSystem/blob/86d3b94fc50f93e52768016b85e83a0c42f70a69/src/astock/data/receipt_migration.py#L47-L49)，以及 [receipt_integrity.py L110–117](https://github.com/liuyanfeier/AStockSystem/blob/86d3b94fc50f93e52768016b85e83a0c42f70a69/src/astock/data/receipt_integrity.py#L110-L117)。

重复升级的顶层检查只比较最高版本与两个表名的数量。正常 admission 虽额外检查 migration_id，却仍不检查表结构及 007 必需约束。空库没有 batch 时，循环中的正常 schema 检查甚至不会执行。

独立合成复现：

| 故障状态 | 实际结果 |
|---|---|
| 已升级空库的 version7 migration_id 改为错误值 | repeat upgrade 返回 `ALREADY_VALID` |
| version7 保留，将两张 007 表换成同名 `dummy INTEGER` 表，库中无 batch | repeat upgrade 返回 `ALREADY_VALID` |
| 有合法 COMPLETE/binding 的合成库，将 validation_audit 换成同名 `dummy INTEGER` 表 | 默认 `validate_slice_receipt()` 仍接受；repeat upgrade 返回 `ALREADY_VALID`，batches_checked=1 |

因此当前“repeat verifies rather than repairing; incompatible partial schema blocks”的交付声明过宽。缺失约束、错误结构或错误版本登记不能因表名相同而获得有效 schema 判定，也不能等到下一次写审计才失败。

要求共享 schema 验证明确覆盖 version7 的准确 migration_id、schema/表身份、必需列与类型/可空性，以及 007 的 PK、UNIQUE、FK、CHECK 保障。以当前锁定 DuckDB 的目录信息核对规范化结构，避免依赖未经验证的 SQL 文本字符串比较。重复升级和正常 admission 均使用此检查；不兼容时 fail closed，保留原库，不自动删表重建或补齐约束。检查空库同样必需。

必须新增错误 migration_id、两张同名错误结构表、完整 batch 下错误 audit 表、缺少关键约束等负向回归；同时保持 fresh/合法 repeat/升级/失败回滚测试通过。

## 3. 本次已确认的有效改进

- 通用 raw verification 已关闭空 run 列表、零 manifest 和缺失 run 的 vacuous pass，同时保留合法 multipart 与有对象的零行数据。
- COMPLETE 的共享证明覆盖 receipt/object/run 的精确对应、冻结请求/contract、typed JSON、物理 hash/schema/count、sidecar 精确集合和安全路径；普通 FK 没有被当作完整 lineage 证明。
- resume、capture、finalize、promotion、curation 和 DQ 的 COMPLETE admission 已接入共享证明。默认 admission 不授予 legacy 无 binding 的隐式通过；离线 legacy preflight 使用不同结果。
- 007 为追加方案，001–006 没有修改；通用 migrate 仍止于006。DDL、绑定、审计与版本登记在一个事务中，现有故障测试验证回滚。finalize 条件更新与登记也在同一事务中，重复完成保留原时间。
- 离线 audit 使用已有库的只读一致事务，不要求 Settings/token/provider，不迁移、claim 或修复历史事实。捕获失败不把非法历史 COMPLETE 伪装成可重试 PENDING。

这些改进值得保留。上述两个发现要求补强异常状态与 schema 验证，不要求重做整个 G1。

## 4. 验证与保留性证据

- 本地工作树干净，HEAD 与审查 SHA 一致。审查 G0→G1 的 22 个变更文件、相关调用路径、新增测试、SQL 和交付报告。
- 独立读取 [CI run 36962701212](https://github.com/liuyanfeier/AStockSystem/actions/runs/36962701212)：push / completed / success；head_sha 精确等于 `86d3b94fc50f93e52768016b85e83a0c42f70a69`。实际 job 日志为 **353 collected / 353 passed in 249.57s**，doctor Overall PASS，token configured NO；contracts/plan/specs 步骤通过。
- 本次没有重复运行整套353测试；独立补充测试针对上述未覆盖的故障状态，实际确认升级/验收错误接受和模拟重复 fetch。CI 绿灯不能覆盖这些已复现失败。
- 独立重算 G0 库存中 **1,102 个既有文件**的大小/哈希，差异为0。原 DB SHA256 仍为 `924bf429b25c4ac2fafc557bdbc67667b39de902b3175a7d7828461207fd4617`，与 G0 一致。私有 G0 inventory artifact SHA256 仍为 `f5c30de4f0e0ccb7f526914f047fcccfe65e52d3100784744039dbc158848e9c`。
- 原 DB 只读检查：schema_versions 仍1–6，007 两张表均不存在；133 条 COMPLETE，attempt sum133。结合 DB 字节不变与1,102文件不变，支持原181 raw、252旧curated及冻结identity未受本次修改影响。这是保留性证据，不是 G3 strict acceptance。
- 本次独立 Review 的新增真实市场请求为 **0**。故障注入与模拟 capture 仅用临时合成存储及合成 client，并拒绝 socket 网络；真实 warehouse 仅只读检查。未执行真实 capture/resume、迁移、curation 或 DQ。

## 5. 修复与重审边界

继续停在 **R1-G1**：补两项修复及必要负向测试，更新交付说明，运行必要完整检查，推送新的 exact SHA 后重新独立 Review。不得把本次反馈当作 G2 执行授权。

G2 的 OS writer lock、claim 原子性和多进程故障验证仍按已审规划另行授权；本次没有因这些已明确留到 G2 的工作未完成而新增阻断项。真实007部署、133严格验收和最终R1验收仍留到G3。R2须等R1 FINAL Review通过后才能开始；Phase1C.2继续关闭；不得重跑133个真实市场请求。

```text
gate_id: R1-G1
reviewed_exact_sha: 86d3b94fc50f93e52768016b85e83a0c42f70a69
review_base_sha: a69cba7bcd722de461eee695469b99e7ea21fe43
ci_url: https://github.com/liuyanfeier/AStockSystem/actions/runs/36962701212
ci_result: SUCCESS; 353 passed; doctor/contracts/plan/specs PASS
reviewer: 此会话 Codex，独立于实现会话
review_date: 2026-10-02 Asia/Shanghai
verdict: CHANGES_REQUIRED
blocking_findings: P1 pending-with-capture-evidence; P2 incomplete-schema-verification
next_action: FIX_WITHIN_R1_G1_AND_REVIEW_NEW_EXACT_SHA
r1_g2_execution_authorization: NOT_GRANTED
r1_final_review: NOT_READY
r2: LOCKED
phase1c1_real_data_gate: BLOCKED
phase1c2_authorization: CLOSED
review_new_real_market_requests: 0
```
