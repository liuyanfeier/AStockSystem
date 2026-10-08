# Phase1C.1 Evidence 与 Phase1C.2 Launch Preparation 独立审查

审查日期：2026-10-06。审查 SHA：`93d605676892459f78607790278bccc7a80e8f29`。

结论：**CHANGES REQUIRED：2 个 P1、2 个 P2。** 本轮新增 runner 尚未通过独立工程审查；36 次日历及 6 次首批行情申请尚不能签发执行许可。此前 R1/finite45 工程修复结论继续有效，Phase1C.1 整体结项仍 BLOCKED，Phase1C.2 实际执行仍 CLOSED。

这轮已经交付了真实的离线实现和材料，且历史保全通过。下面四项都可以在同一批修复并集中 Review；无需重新执行原 133 请求，也无需重新导入 finite45。修复四项只能关闭新增 runner 的工程问题，不能自动补齐仍缺少的历史事实。

## 审查对象与方法

仓库：`/Users/yanliu/Documents/AStockSystem`。HEAD 与上述 SHA 一致，工作区干净。自前次接受的 `222cf660878da3d8fa67bfbce9f896731e83769f` 起，变更为 10 个文件、1,342 行新增，主要是新 runner/catalog/独立 DDL、设计、测试与交付文档。

作者材料目录：`/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-evidence-and-launch-preparation/2026-10-05-v1`。最终 ZIP SHA256：`a9607cbc238d42050b2cc90a84435088b438996b9a3d24ea87b3efbd9984c923`。

本审查读取实际源码、保存的文献正文、原库全行集、固定 metadata 状态与交付引用，并在审查者工作区进行闭合 mock 复现。实际市场/provider/calendar/mapping API 请求 0，新增文献 HTTP 请求 0，原库写入 0；没有执行任何申请或授予许可。作者 DB 通过项目共享只读连接读取；故障只注入审查者的合成副本。

## 必须修复的四项

### F1 / P1：合法的全天停牌 NULL 被当成缺失主键

位置：[full_backfill_v1.py:273](/Users/yanliu/Documents/AStockSystem/src/astock/data/full_backfill_v1.py:273)。`normalize()` 对 natural key 的任意 NULL 一律抛出 `MISSING_NATURAL_KEY`，而 suspend_d 的 natural key 包括 `suspend_timing`。既有冻结 contract v2 明确允许该字段 NULL，并要求保留全天与盘中语义。

这不是仅存在于测试里的边界：当前批准 Context 使用的 21 个 suspend_d raw 对象共 776 行，其中 736 行 `suspend_timing=NULL`。独立 mock 输入一个符合既有 contract 的 NULL 行后，新 capture 留存 body、消耗一次 attempt，然后落为 FAILED、零 receipt；再次调用得到 `TERMINAL_NO_RESEND`。合法响应因此会停住首批行情和后续回填。

要求：按端点 contract 处理允许为空的键组件，保留原生 NULL；完整 tuple 仍须去重，其他必填键仍拒绝缺失。不能用 0/空串填值，也不能顺带放宽 `stk_limit.pre_close` 的历史 DQ 问题。测试至少覆盖全天 NULL、盘中值、必填字段缺失、含 NULL 的重复 tuple 与重开不重发。

### F2 / P1：首次 COMPLETE 缺少提交前的最终物理闭合验证

位置：[full_backfill_v1.py:366](/Users/yanliu/Documents/AStockSystem/src/astock/data/full_backfill_v1.py:366)、[事务提交:371](/Users/yanliu/Documents/AStockSystem/src/astock/data/full_backfill_v1.py:371)。首次 reconcile 先读取 body/source、在内存中生成 typed/manifest，再发布三个派生产物，直接注册 receipt/COMPLETE。提交前没有重新读取最终五文件集合。已有 COMPLETE 的重开分支会校验，但那发生得太晚。

独立复现：在 `after_sidecar` 注入点把已发布 `response.body` 改成 `{}`，首次调用仍返回 COMPLETE，并实际持久化一条 receipt/COMPLETE。source 中记录的 body hash 为 `053ac8fb…`，磁盘实际 hash 为 `44136fa3…`；下一次重开才报 `SOURCE_BINDING_OR_HTTP_CHANGED`。因此首次成功事实可以与当时磁盘 raw 不一致。

要求：在登记与 promotion 的同一受管理事务内、最终 COMMIT 前，重新验证五文件、source/body、typed schema/content、hash、UUID、member、scope 与 receipt/event lineage。校验失败必须回滚 receipt/COMPLETE；保留已消耗调用及原始故障事实，不能覆盖损坏文件或重发。对发布后、登记后、promotion 后等现有故障点进行实际文件变异测试；同时保留合法 partial capture 的本地恢复路径。

### F3 / P2：固定 store 只能容纳一个计划，无法连续执行分批审批方案

位置：[full_backfill_v1.py:180](/Users/yanliu/Documents/AStockSystem/src/astock/data/full_backfill_v1.py:180)。`backfill_pin` 永久保存一个完整计划，初始化要求它与当前计划字节完全一致，member 集合也必须完全相同。生产目标统一为 `data/private/full-backfill-v1/capture.duckdb`。

日历 36、首批行情 6 和后续年度分片是分别审批的不同计划；第一个计划完成后，第二个计划无法注册。独立闭合复现先完成一个 calendar member，再用另一个具有匹配合成审批的新市场计划访问同一 store，得到 `STORE_PINS_CHANGED_NO_RESET`，市场调用 0，旧 receipt 仍保留。现有测试没有覆盖实际设计所需的跨计划流程。

要求：采用同一固定 store 内的 append-only 版本化计划登记及全局逻辑成员消耗账本，或提出等效、可审查的明确方案。每批保留原计划/审批/用户许可 provenance；旧 COMPLETE 按原批次 pins 复核，不能套用新许可。新审批不能清零历史消耗、改名重发 FAILED/UNCERTAIN 或重置旧 metadata。加入日历→市场→后续分片的完整离线集成验证及跨批重复/失败成员测试。

### F4 / P2：最终日历申请的描述符 canonical hash 已过期

位置：`data/private/phase1c1-evidence-and-launch-preparation/2026-10-05-v1/evidence-acquisition-plan-proposal.json:7`，字段 `calendar_member_hash`。

生产材料脚本原本将它定义为 `checksum(venue_calendar_requests)`。最终描述符追加了间隔、适用性、保存位置等内容后，声明值仍为 `9448041e227274ac91f2ea5279497895ef1932497a28a8b36678fdd5f807e78e`，实际 canonical checksum 为 `0ff5d7ff37d2ed2a3a31b3ba8e4ac01204139deac15cbccd577be28d223a1095`。

运行时 requests 的 membership hash `d1666f3c…` 则正确；它与描述符 hash 属于不同输入域，不能相互替代。ZIP/manifest 的文件字节校验也通过，因此这是审批语义摘要过期，而不是 ZIP 损坏。首批市场描述符摘要通过。

要求：冻结最终描述符之后再计算 semantic/member/file/reference hashes，并加入机器断言。生成新版本材料，保留旧版本；不能只修改审查报告里的数字而遗漏主申请、索引或许可绑定。

## 通过的核验及其边界

| 核验 | 独立结果 |
|---|---|
| 精确 SHA CI | [run 37409069290](https://github.com/liuyanfeier/AStockSystem/actions/runs/37409069290)，确认 checkout 本 SHA；814 passed、4 warnings，离线诊断/contract/spec 步骤成功 |
| 新 runner 原有测试 | 审查者禁真实 socket 执行，61 passed / 5.61s；上述复现证明其覆盖仍有缺口 |
| 作者六端点完整 fixture | 复制到审查者工作区后逐个重开，均 ALREADY_VALID，副本 DB 未改变 |
| 原库保全 | 原 34 表完整行集逐项一致；181 raw 对象、252 observations、3 Context、6 generations/6 audits 保持原状 |
| 固定 metadata | 四表全行集一致；CLAIMED/CALL_ENTERED/FAILED，1 consumed、6 unattempted、0 receipt 保持原状 |
| 历史文件 | 171 个批准 pins 与既有批准值一致；145,156 个保护文件 hash 全部通过 |
| 交付闭合 | 233 个索引文件、4 个外部 DB、233 条 active 引用、234 个 ZIP 成员、CRC 与字节 hashes 通过 |
| 凭据检查 | literal/base64/hex/URL 与 12 个 Parquet 解码检查无命中 |

完整 suite 使用已核验的精确 SHA CI，本审查没有重复运行全套。原库 SHA256 仍为 `30953a9ff2622c85724794b268bc878ea2494684d6faccd5ab0fc5cbb378eb81`，metadata DB 仍为 `91a2c5d20df935795e0e2b736175af13fb6b7b5f6092231a9e96975fd30b9ece`。

新 runner 的独立入口、单 attempt、CALL_ENTERED 先持久化、禁止网络重试/redirect、跨重开 1.25 秒间隔、闭合 mock 与许可默认关闭等方向正确。它没有调用旧 bounded133 `_fetch`。这些通过项不能抵消首次完成验证和分批流程的问题。

## 历史事实与许可状态

作者文献 HTTP 账本为 24 次 attempt、48 个成对进入/终态事件：15 次 ConnectError、6 份 HTTP200、3 次 BSE HTTP403；没有发现 24 次预算超支。本审查直接解析了保存的 stock_st、suspend_d、bse_mapping、SZSE2013、SSE2025 正文，支持报告中限定的起点/cap/字段/休市事实。它们没有提供额外完整的证券 identity/native binding 或完整 session/previous 认证。

新增 identity 候选 0、DQ exception 候选 0、实际新 Context 候选为空，63 个 session 中生产认证数仍为 0。当前 DQ 仍为 401,994 identity + 63 session + 3 reference-price = 402,060。`000022.SZ` 原 `pre_close=NULL` 不可填值、隐藏或用新 suspend_timing 的合法 NULL 规则豁免。

36 次 calendar 申请还存在以下明确前置缺口：

- 36 个 member 均未提供 `completeness_evidence`，catalog 的 trade_cal cap 为 UNKNOWN；生产 guard 会拒绝，即使以后另行批准计划。需准备可审查的完整 civil-date 集合验证规则与 pins，并由真实响应证明覆盖；不能删除 guard 或伪造已采集事实。
- BSE 6 个年度请求的 provider 参数适用性尚未在现有原文中证实，继续保留为 HOLD。
- SZSE2013 年请求与旧 FAILED 的 20130104–08 范围重叠，需要独立的 scope/兼容性和 reconciliation 决策。旧 CALL_ENTERED 既不证明远端收到，也不证明 provider 拒绝；不能用新 run/store 名绕过。

为了减少等待，可在四项修复后优先提交 **29 个候选日历请求**：SSE 15 + SZSE 14，暂不包含 SZSE2013 和 BSE6。这个分组只用于取证许可申请，不是本审查批准；必须保留完整 36 个目标及 7 个 HOLD 的理由，不能静默缩减全目标。旧 6 个 UNATTEMPTED 窗口是非叠加替代，不能增加到 36/29 预算上。未来文献 9 次申请也没有在本审查获准执行。

首批 2013-01-09 六端点提案维持 BLOCKED，仍需 calendar、历史 universe/native、账户权限、端点 cap/empty/完整性规则、匹配独立 Review 与实际用户许可。全目标继续为 2013-01-01..2026-09-30；30,126 只是六端点×civil days 的保守 base 上界，verified reuse=0，额外分片/存储/总预算尚未证明。

全历史 raw 完整性、年度真实 rebuild、回填后的 coverage/causal 终验仍归回填后验证。本审查没有把这些移为“首次取证前必须已经拥有全历史 raw”的前置条件。

## 状态与下一步

| 对象 | 本次独立结论 |
|---|---|
| 前次 R1/finite45 工程修复 | CLOSED，接受结论继续有效 |
| 新增生产 runner | CHANGES REQUIRED，F1–F3 |
| 新取证审批材料 | CHANGES REQUIRED，F4 与上述明确许可前置缺口 |
| Phase1C.1 整体结项 | BLOCKED，历史事实尚未齐备 |
| 全历史数据准入 | BLOCKED |
| Phase1C.2 真实执行 | CLOSED；未签发任何执行许可 |

下一批集中完成四项修复、跨计划集成回归、材料哈希闭合与 29+7 可审批取证分组，最后一次性提交新 SHA/CI/完整 package 供独立 Review。四项通过之后可审查日历取证许可；只有实际取得并批准所需历史事实、完成启动准入与匹配用户授权，才能宣告整体结项并启动 Phase1C.2。

复现与核验 JSON 位于本审查目录下 `private/phase1c1-evidence-launch-independent-review`，附带脚本及决策包只用于独立审查，均不是生产许可文件。
