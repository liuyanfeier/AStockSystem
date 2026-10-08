# Phase1C.1 Runner Repair 与 Calendar Acquisition Readiness 独立 Review

日期：2026-10-08。最终审查 SHA：`57812dd921df0720680b3034c186734852f13648`。比较基线：`93d605676892459f78607790278bccc7a80e8f29`。

**结论：PASS，范围限定为本批新增 runner 工程修复及 29 个日历取证成员的独立审查。没有发现需要重新打开 F1–F4 的阻断问题，跨根目录许可修复也通过。** 旧 R1/finite45 工程接受结论继续有效。

下一步可以从离线工程修复转入 **29 次限定日历取证**。独立 Review 批准与实际用户执行授权分开保存：本次可以批准确切 29 成员的取证范围；实际用户许可仍未签发，本审查不执行任何真实请求。首批行情 6、其余日历 7、文献 9 和全量回填均不在该批准范围。Phase1C.1 整体结项及全历史数据准入仍 BLOCKED，Phase1C.2 实际执行仍 CLOSED。

## 四项关闭依据

| 项目 | 独立核验结果 |
|---|---|
| F1 / nullable suspension | 只有固定 contract 支持的 `suspend_d.suspend_timing` 允许 NULL。完整 tuple 去重、其他必填键和原生 NULL 保留均通过；完整 capture 重开有效。没有给 `stk_limit.pre_close` 发豁免。 |
| F2 / 首次 COMPLETE | 完成事务在登记、promotion 故障点之后调用同一个五文件 validator。五文件×三个阶段的 15 项实际变异全部阻止成功提交、保留 CLAIMED/CALL_ENTERED 和受损字节；重开零重发。合法 partial 恢复仍通过。 |
| F3 / 跨计划固定 store | append-only plan/membership/authorization registry 与全局 endpoint/dataset/params 消耗键通过。同库三计划 close/reopen、旧 raw/rowsets/license 保全、原 provenance 复核与完全相同 COMPLETE 的跨批 reuse 均通过；FAILED/UNCERTAIN、错 descriptor、orphan 和并发 claim 的拒绝路径通过。 |
| F4 / 申请 hash | 最终 descriptor-set semantic hash、执行顺序的 runtime membership hash 和文件 SHA256 分开绑定。完整描述符文件进入 plan pins，原过期摘要问题已关闭；字段、顺序、member、partition 和索引漂移测试通过。 |
| F3 补充 / root clone | v2.1 外部 Review 固定 canonical absolute destination，用户授权绑定 Review hash；同一许可不能迁往克隆 root 重新消费。独立执行的 regression 确认第二 root 在注册/HTTP 前拒绝。 |

现入口协议为 `FULL_BACKFILL_CAPTURE_V2_1`，固定目标是 `/Users/yanliu/Documents/AStockSystem/data/private/full-backfill-v1`。独立 DDL 位于 `sql/offline/full_backfill_v2_1.sql`。旧 v1/v2 证据与旧失败库保留；本轮没有初始化生产 capture store、升级原仓库或改写原 metadata。

## 独立验证与保全

- 审查者在禁真实 socket 的环境中实际执行两组 runner tests：**120 passed / 26.97s**。
- 从 GitHub 直接读取 [精确 SHA CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/37734475594) 的 job 113170791363 和日志，确认 checkout 本 SHA，**873 passed、4 warnings / 933.23s**；锁定依赖、doctor/contract/spec 各步骤成功。本审查没有重复全套测试。
- 原 34 表使用此前独立全行集核验作为基线，本轮原 DB 字节 hash 完全一致、无 WAL，并通过 managed shared read-only 读取确认当前表数与关键计数。没有把作者报告的“全行集一致”当成未核验的新事实。
- 固定 metadata 的 CLAIMED/CALL_ENTERED/FAILED、1 consumed、6 unattempted、0 receipt 保持原状。
- 171 个接受 pins 与原独立批准值一致；**146,151 个保护文件**逐项 hash 通过，其中此前 145,156 个文件仍是相同子集。增加部分为此前准备包 231 与 superseded 作者包 764 个文件。
- 427 个 manifest 文件、2 个外部 DB、428 个 ZIP 成员、CRC、唯一成员与实际文件字节校验通过。最终 ZIP SHA256：`94c0926ad3afb19411d8e83b3b942dff9d6739fb6db6bb9198edd5c28d9cc182`。
- 独立遍历 **894 条证据引用、192 个 JSON 节点**；历史 v1 catalog 的一个显式 archive redirect 与旧 hash 匹配，不作为当前 runtime pin。
- **22 个实际合成 DB**通过共享只读完整表行集/hash 及凭据核验。复制完整 F1、三计划、calendar29 stores 到审查者目录，**33 个 COMPLETE**重新验证为 ALREADY_VALID，副本 DB 字节保持不变。
- literal/base64/hex/URL 与 **48 个有效 Parquet**解码扫描通过；另三个被故意写成 `{}` 的故障 Parquet 与明确故障清单匹配，不被计作有效数据。

原库 hash：`30953a9ff2622c85724794b268bc878ea2494684d6faccd5ab0fc5cbb378eb81`。metadata hash：`91a2c5d20df935795e0e2b736175af13fb6b7b5f6092231a9e96975fd30b9ece`。本审查真实 API 0、文献 HTTP 0、原库写入 0、133 replay 0。

## 29 成员取证批准的准确范围

36 个目标窗口与旧申请逐项比较，params/fields/contract 范围完全相同。候选为 SSE15＋SZSE14；HOLD 为 SZSE2013＋BSE6。2012 年 12 月 lookback、2013–2025 年度窗口及 2026 截至 09-30 的边界保持不变。没有新增窗口、补充 reserve 或叠加旧六个未调用窗口。

完整 descriptor-set hash：`5492df81969e004cf6fdca3913d4042192b98f818411359fdcff77b0b039a0e4`。runtime ordered membership hash：`2a2869f97b841fd8d707c6d16d250325a13c9e0aa58de48806383af5148c46a3`。作者 PROPOSED plan checksum：`c1b8599f8f18ed76b40bca9ecdb7cfea923a9425fb262b9094e52f5284efa6fa`。

审查者的可执行范围文件仅将该 plan 的 namespace 从 PROPOSED 改为 PRODUCTION，production plan checksum 固化为 `dd89dad8c44ca437c743f77f396d7633cb05b2d01a34d2831ec1c4c81373501e`。requests、预算29、单次 attempt、四项 source/design/catalog/DDL pins、证据文件、descriptor 引用、禁止重发列表及 `historical_PIT_eligible=false` 不变。plan 的 execution_license 仍按协议要求为 false；真正运行还必须同时提供匹配的外部 Review 和实际用户授权。

已直接解析此前保存的 trade_cal 原 HTML，hash 为 `942d0ff91c4d15ab65e0e2c02bffb89732f1f605e667cf61c5af875ef0242461`，验证 SSE/SZSE 参数及 `pretrade_date`、`is_open` 的字段定义。无需新 HTTP 来补这一项。该文献不证明账户权限、每年实际覆盖、历史正确性或 BSE 参数可用性。

29 个 byte-pinned 完整性规则可以作为这次**取证捕获**的校验依据：完整 civil-date 集合、唯一键、venue/date 范围、原生类型、0/1、previous 关系与可观测相邻窗口一致性。实际账户/cap仍 UNKNOWN，异常响应必须停止；leading predecessor 和缺失窗口不自动认证。完整响应只能成为 immutable source capture，不能自动写入原 trade_calendar、建立 Context、通过 DQ 或授予研究准入。

## 保留的门槛

| 状态对象 | 本次结论 |
|---|---|
| 原 R1/finite45 工程 | CLOSED，接受结论有效 |
| 本批新 runner 工程 | PASS，F1–F4 与 root clone 修复关闭 |
| 确切29日历取证范围 | 独立 Review 可批准；必须匹配实际用户许可才可调用 |
| SZSE2013＋BSE6 | HOLD，分别等待旧失败重叠审查、参数/venue 证据 |
| 首批6行情 / 文献9 / 全量回填 | 未获本次执行批准 |
| 实际日历生产认证 | 0；mock 不能算认证 |
| 新 identity / DQ exception / Context | 0 / 0 / 空；本轮未补历史事实 |
| Phase1C.1 整体结项 | BLOCKED |
| 全历史数据准入 | BLOCKED |
| Phase1C.2 实际执行 | CLOSED |

402,060 个 finding 仍由 401,994 identity、63 session、3 reference-price 组成。全目标保持 2013-01-01..2026-09-30，30,126 为 base 保守上界，verified reuse=0，额外分片/真实吞吐/存储与全执行预算未知。全历史 raw 完整性、年度真实 rebuild、回填后 coverage/causal 终验继续留在获准回填后。

本批不再需要一轮 F1–F4 离线修复。下一批在明确用户授权后执行限定29日历取证，保留成功/失败/未知调用的真实证据，集中提交 calendar/previous 的证据提案和所有保全结果。取证结果通过后再决定剩余历史事实与启动准入，不能把取证成功称为 Phase1C.1 全部完成。

本报告和证据包保存在审查者目录。匹配 Review 文件只覆盖确切29日历请求；待签的用户许可不是实际授权，本审查不会替用户签发它。
