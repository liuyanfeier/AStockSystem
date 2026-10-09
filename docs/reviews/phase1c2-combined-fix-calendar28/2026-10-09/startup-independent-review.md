# Phase1C.2 Startup 独立 Review

日期：2026-10-09（Asia/Shanghai）
审查 SHA：`d3b505869cc28d1140c0b9c08863ce3cb8a39853`
交付状态：`PHASE1C2_STARTUP_AND_EXACT_ACQUISITION_REVIEW_READY`

## 结论

**CHANGES_REQUIRED：发现 1 个 P2，修复范围为新 continuation runner 的调用前时间守卫。** 原有 Phase1C.1 工程关闭结论保持有效；Phase1C.2 已进入 startup，继续推进。这个问题不要求重做 R1/R2、finite45、旧 runner 修复、四个文献 GET 或连接诊断。

已经独立核验的文献、保全、消费隔离、最终 mock 回执与精确 SHA CI 均通过。本审查不签发当前 SHA 的真实 exact28 许可证。修正这一处边界、更新精确源码绑定后集中复核；历史身份、session 和研究 DQ 的缺口不作为这 28 个 RAW_ONLY 日历请求的先决清零条件。

## F1 — [P2] CLAIMED 后时钟回拨仍会进入 HTTP 调用

定位：[capture_continuation_v3.py](/Users/yanliu/Documents/AStockSystem/src/astock/data/capture_continuation_v3.py:459)。

`claim()` 已持久化 attempt 和 CLAIMED；随后 `enter()` 重新读取 wall clock，直接插入 CALL_ENTERED。它没有检查新的时间是否早于已持久化的 `claimed`。前面针对授权时间和 pacing 的检查无法覆盖这两个事务之间的回拨。

独立封闭复现：在 `fault('after_claim')` 将 fake wall clock 回拨 1 秒，保持其他条件合法。当前实现的结果为：

- 1 次封闭 MockTransport HTTP 调用；真实网络调用 0，原库写入 0。
- CLAIMED：`2026-10-09T03:24:40.505467+00:00`。
- CALL_ENTERED：`2026-10-09T03:24:39.505468+00:00`，比 CLAIMED 早。
- 响应处理报 `CONTINUATION_SOURCE_TIME_CHANGED`，没有有效 receipt。
- 重开审计报 `CONTINUATION_TIME_ORDER_CHANGED`。

这不会伪造 COMPLETE，但会在已不满足时间完整性的情况下消耗一次不可重发的请求，并留下不能通过审计的新消费历史。部署真实 exact28 前应当在 enter 事务内拒绝这一回拨。

最小候选补丁仅增加两行：在 CALL_ENTERED 插入前验证 `old.instant(at) >= old.instant(claimed)`，否则报 `CALL_BEFORE_DURABLE_CLAIM`。保留已经持久化的 CLAIMED，不退还预算、不重发、不执行后续成员。

[补丁](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C2_Call_Entry_Clock_Guard.patch)已经在审查方目录验证，没有修改仓库源码。候选新增回归确认：HTTP 0、只有 CLAIMED、attempt 1、receipt 0、旧六表行集不变、重开 audit 通过、同成员和后续成员均停止。原有 42 项与新增 1 项合计 **43 passed**。这是候选验证结果，尚不是已提交新 SHA 的发布认可。

## 独立证据

| 范围 | 结论与证据 |
|---|---|
| Git/CI | 本机 HEAD 精确匹配 d3b5058，工作区干净。通过 GitHub 只读连接获取实际 job/log，checkout 命中精确 SHA；[CI run](https://github.com/liuyanfeier/AStockSystem/actions/runs/37875913897) 的 foundation job 113644357432 成功，915 passed、5 warnings，离线检查通过。5 条为 fork 弃用警告，本次不作为阻断。 |
| 当前新增测试 | 独立复跑该 SHA 的 42 项 continuation/diagnostic 回归：42 passed。随后补充 post-CLAIMED 回拨复现才发现 F1。没有重复运行完整 915 项。 |
| ZIP 与引用 | 546 个清单文件、3 个外部数据库、547 个 ZIP 成员全部按字节核验；CRC、成员唯一性、磁盘与 ZIP 内容一致。递归核验 1,077 条引用、232 个 JSON 节点。 |
| 历史保全 | 146,656 个历史文件哈希与 171 个批准 pin 全部不变；上一批 146,568 文件集合仍完整。原库、旧 metadata、真实 capture DB 哈希不变、无 WAL；原库旧 34 表历史行集依据前次独立证明与相同物理 DB 哈希复用，并通过当前托管只读计数核对。 |
| 真实消费历史 | 实际 capture DB 的旧六表完整行集与冻结 baseline 一致，旧首请求 UNCERTAIN、28 个未消费成员、0 旧 receipt 保持不变。没有把旧 UNKNOWN 改成成功或重发。 |
| 最终候选副本 | 旧六表不变；新 28 attempts、84 events、28 receipts 与最终 copy proof 完整行集相符。在审查方副本运行 audit 并逐成员 physical_validate/reopen，全部有效；fixture_only 为 true、research 为 false。 |
| 历史候选 | 失败的 stale-clock 副本与两份被替代的成功副本均保留并解码核验，不作为当前最终协议的通过证据。初始 staging 引用移动前的副本路径，按相同哈希的 retained pre-order-guard 快照解读；最终 staging 使用当前最终副本。 |
| 凭据 | ZIP 及 85 份 Parquet 解码内容按真实本地 secret 的 literal/base64/hex/URL 形式扫描；另对候选 DB 解码行集检查，无命中，未输出 secret 值。 |

提交 ZIP SHA256：
`e4419f669912d668f7e497340ed82ca36c3aa4d6138334eefccc0b3b46d98246`，34,104,505 bytes。

## 真实诊断与文献

诊断许可、账本与结果相符：1 DNS、1 TCP、1 TLS，单 TCP 连接完成证书验证；HTTP 0、token 未发送。它证明该次诊断可连接，不能反推旧 UNKNOWN 的原因，也不能保证未来数据 API 请求一定成功。

四个 GET 精确对应已有 request-set，授权在调用前；8 条请求/响应账本与四个 200、完整 body、哈希及实际原始存储路径一致。每 URL 1 次、retry/redirect 0，无 token。审查没有重发它们。

两个原始 PDF 字节与可读副本一致；独立重提取全文与交付文本逐字节相同，页数为 230 和 206。独立渲染核对：

- 2013 版资料：物理第 130 页/印刷第 122 页为 **2012 年**终止上市表，3 条候选终止事实。
- 2012 版资料：物理第 117 页/印刷第 111 页为 **2011 年**终止上市表，2 条候选终止事实。
- 2013 版物理第 128 页的 2012 年更名表中，600981 的日期确实印为 `2021-5-9`。交付保留 SOURCE_INTERNAL_DATE_CONFLICT，未擅自纠正或用于映射，处理正确。

年鉴索引的 18 个 literal PDF 链接只作为后续定位线索，未跟随下载；静态 table_config 是查询配置，不是历史身份行集。这些材料没有被升级为全期身份绑定、Context 或 DQ 豁免，边界正确。

## exact28 的阶段结论

实际未消费成员 eligibility、逻辑身份、origin、UUID、执行顺序、固定 destination 与 8 个源码/设计/DDL pin 已核验。首成员为 SSE 20130101–20131231；其旧 SSE2012 predecessor UNKNOWN 继续保留，raw 窗口校验与 leading/session/research 认证分开。

当前申请字节哈希为 `b403a9b354eb4f744b6447f8446695eb88603c3e1a8fc43e9c4a4d67a05e9664`；
canonical application hash 为 `36892729ec75d7092afdfdf5087e333366d9f623723d2dd34e19d3fbaf12fddb`；
membership hash 为 `15cbff858f3f5fbbd6873ef6149346902cd4d2f13e76c2f54d62b648e01902f5`。

修复会改变 source pin，必须生成匹配新源码与最终 SHA 的申请，保留该旧版本。不得复用 startup 的零数据 API 许可、fixture license 或旧执行许可。当前 market6 与全量回填也只保持 proposal，不随本次 exact28 自动获准。

研究 admission 仍 BLOCKED：identity 401,994、session 63、reference 3，共 402,060 findings；resolved 252。它们按数据准入工作推进，不重新打开 Phase1C.1 工程关闭或 Phase1C.2 startup。

## 下一批一次完成

直接执行[集中修复 Prompt](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C2_Call_Entry_Time_Fix_And_Exact28_Readiness_Prompt.md)：补丁、一个回归、最终源码绑定、一次新副本 exact28 mock、最终精确 SHA 本地/CI、保全与交付包一起完成，不在内部步骤之间等待 Review。

交付后只复核 F1、最终源码/申请绑定及新执行证据；如果没有新增问题，即可对这一精确 real exact28 范围作明确批准决定。批准绑定实际最终 SHA 和申请，不能预签未知未来版本。

审查期间真实 DNS/TCP/TLS/HTTP 调用 0；GitHub CI 元数据与日志通过只读连接获取。原仓库源码、原库、metadata 与真实 capture store 未写入。

## 审查方本地证据

[artifact 验证](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c2-startup-independent-review/independent-artifact-validation.json)、[原库/副本验证](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c2-startup-independent-review/independent-data-validation.json)、[诊断/文献验证](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c2-startup-independent-review/independent-documents-validation.json)、[CI 实际读取](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c2-startup-independent-review/independent-exact-sha-CI.json)、[原始缺陷复现](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c2-startup-independent-review/independent-clock-boundary-reproduction.json)、[候选补丁验证](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c2-startup-independent-review/independent-candidate-patch-validation.json)。
