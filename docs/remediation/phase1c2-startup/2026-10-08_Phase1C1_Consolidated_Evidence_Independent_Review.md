# AStockSystem consolidated evidence: independent Review

审查日期：2026-10-08。最终文档 SHA：`6f5e3361bb8aff59621b72c38e89de96c668953d`。
真实执行 SHA：`57812dd921df0720680b3034c186734852f13648`。两者之间只有 7 个脱敏文档变化，源码、依赖、合同、catalog、DDL 均未改变。

**结论：本批证据完整性、执行边界及历史保全 PASS；没有发现需要重新打开 R1、finite45 或 F1–F4 的工程缺陷。完整历史数据准入仍 BLOCKED；既有规则下 Phase1C.2 仍 CLOSED。**

这是对失败调用的真实、可复核交付通过，不是日历采集成功、历史身份认证通过或回填执行许可证。

| 对象 | 独立结论 | 实际含义 |
|---|---|---|
| R1/finite45 工程修复 | CLOSED，保持既有结论 | 不重复实施或重新导入 |
| runner F1–F4 / root clone | PASS，保持既有结论 | 本批无源码改变，复用既有独立 120 项验证 |
| 本批请求、证据、包与保全 | PASS | 未越权、未重发、未制造 COMPLETE 或历史事实 |
| 日历 | BLOCKED | 1 UNCERTAIN、0 COMPLETE、28 UNATTEMPTED、0 新响应/认证 |
| 历史身份 / NULL / 研究 Context | BLOCKED | 新绑定、新例外、新 Context、新 DQ 候选均无充分事实 |
| 第一批 6 行情 / 全量回填 | NOT AUTHORIZED | 当前没有匹配的可执行批准 |
| Phase1C.1 整体 / Phase1C.2 | BLOCKED / CLOSED | 不把工程结束改写成全部数据问题解决 |

## 独立验证依据

1. 实时读取 GitHub 的 run `37754101349` / job `113234263086`：成功；原始 job log 明确 checkout 精确 `6f5e3361…`，`873 passed, 4 warnings in 1081.16s`，doctor 与合同/计划离线检查通过。本地 HEAD 精确匹配且工作树干净。没有重复跑相同的完整测试。
2. 校验 86 个 manifest 文件及 2 个外部数据库；ZIP 87 个唯一成员，CRC 正常，各成员与磁盘字节相同；递归校验 1,363 条引用、244 个 JSON 节点。旧 catalog 的唯一历史引用按显式归档路径核验，不替换当前 runtime catalog。
3. 独立重算 146,568 个受保护文件和 171 个批准冻结项；上一轮 146,151 个文件仍为不变子集。原库 SHA256 `30953a9f…` 与旧 metadata `91a2c5d2…` 相同、无 WAL；通过项目共享锁只读复核计数。以完全相同的物理数据库哈希复用既有独立完整 34/4 表行集证明，不声称本轮再次扫描了整个 1.36GB 原库的所有行。
4. 对真实固定采集库和封存副本逐项比较六表完整行集，核验 origin plan、成员、UUID、独立 Review 和实际 human license 的匹配及时间先后。两者数据库 SHA256 均为 `b96fb716…`。只在审查目录副本执行 terminal reconcile，返回 `TERMINAL_NO_RESEND`，副本字节未变，真实网络调用 0。
5. 独立核对 9 个文献成员与实际 durable ledger、单次调用、URL、许可、原始响应/文本哈希、时间及原文定位。重新解析 6 个实际 HTTP 响应的正文，2 个旧正文按原字节复用。4 个成功正文只支持索引/附件位置及字段定义；没有历史证券事实扩张。
6. 独立重新执行 7 份旧发行人 PDF 的文本提取，核验 417 处页/行定位；重新读取 3 个旧 Parquet 原生 NULL 行。未用同数值的其他代码或其他 endpoint 替代。
7. 对 ZIP、公有文档和解码后的真实数据库行集检查本地凭据的 literal/base64/hex/URL 形式，无命中。值未输出。审查没有真实 API/文献请求、原库写入或 Git 提交。

交付 ZIP SHA256：`e2809374baa57ea50ce9e058884bce97adcb84049fa23848b623df87fb9bd75b`，6,997,292 bytes。

## 阻止启动的事实

首个请求为 SSE `20121201..20121231`。事件为：

| 事件 | UTC 时间 |
|---|---|
| CLAIMED | 2026-10-08T08:33:21.973638+00:00 |
| CALL_ENTERED | 2026-10-08T08:33:22.002515+00:00 |
| UNCERTAIN | 2026-10-08T08:33:22.331057+00:00 |

从 CALL_ENTERED 到 UNCERTAIN 为 0.328542 秒。没有 HTTP 响应正文、typed 文件、manifest 或 receipt。这个时长不能证明服务器没有收到请求，也不能证明账户权限不够。

`full_backfill_v1.py:573` 将传输异常统一记录为 `TRANSPORT_UNKNOWN_NO_RESEND`，不保存异常类别或连接阶段。不能从现有证据还原 DNS、TCP、TLS、代理、沙箱、服务器断连或其他异常的具体原因。下一次改进应保存经过严格脱敏的类别/阶段；旧结果继续保持 UNKNOWN。

`full_backfill_v1.py:553` 遇到任意 FAILED/UNCERTAIN 或未形成 receipt 的 CLAIMED，会禁止该固定库所有后续发送。另有两道约束：

- `:269` 禁止新 plan 接管尚未 COMPLETE 的已注册逻辑成员。
- `:283` 禁止覆盖已经钉住的原 plan 许可证；当前 docs HEAD 也不能直接复用旧执行 SHA 的 Review 进行新调用。

因此，**不能只删掉首项、重新命名 plan、换目录或简单重跑旧 CLI 来执行余下 28 项**。停止是已有设计的正确执行；若决定允许无依赖、未消费成员继续，应先实现和审查明确的追加授权/隔离机制。

文献实际为 7 次 GET：4 HTTP200、2 HTTP403、1 ConnectError/UNKNOWN；复用 2 份正文。BSE 的两份 403 和一次 UNKNOWN 没有提供映射/原生交易日历证明；成功的 namechange/stock_company 页面仅为定义，不是受影响证券的实际历史观测。

原 DQ 的 402,060 个 findings 仍保持：401,994 身份、63 session、3 reference price。新增原库 binding/observation、Context 和 DQ 解除均为 0。这些缺口不可能仅靠 CI、重新打包或作者填写批准字段关闭。

## 对下一步的决策

不要求重新实施已关闭的工程工作，也不要求先取得回填后的全历史 raw、年度 rebuild 和最终 causal 结果。

若维持之前的完整启动准入定义，需要补足真实 calendar/previous、历史身份/native 与 endpoint/account/NULL 事实，再集中审查启动；外部取证能否成功决定实际轮数，不能承诺某个 Prompt 后一定完成。

为了缩短等待，建议用户明确批准下列阶段边界调整：

- 将已完成的 Phase1C.1 **工程修复与 rehearsal**正式关闭并冻结；未解决数据问题转为持续登记的研究准入阻断项。
- 新增 **Phase1C.2-A：独立原始采集与运行准备**。先做连接诊断、停止账本的受审查继续机制、精确成员/预算/来源保全。后续每批真实请求仍须匹配独立 Review 和实际用户许可。
- 允许取得并保存证据不充分的原始响应；这不使数据研究可用。物理采集状态、完整性认证、身份解析、DQ 和研究准入分别记录，禁止以 raw 保存成功代替完整性 PASS。
- 原 Phase1C.2 的全历史/研究准入目标不变：2013-01-01..2026-09-30，全部原定端点与 venue。BSE/SZSE2013 HOLD、旧 133、两个已消费日历请求、NULL/identity/Context 门槛都不静默豁免。

这是一项明确的范围/顺序变更建议，**本 Review 没有替用户批准它**。用户先前要求“不得开始 Phase1C.2”，而本次请求是“没问题的话”进入；当前实际数据仍阻断，因此需要明确批准新边界。

已经形成合并执行 Prompt，集中完成连接诊断、未来受控继续机制的离线设计/实现/验证及精确启动申请，一次交付。它不允许在新实现审查前执行 28 项或行情、不改原库、不重发已消费请求。四个新官方文献 URL 可作为可选、单独限定预算的取证范围；六个新 metadata API 仍未批准。

后续至少需要一次新运行机制/精确范围的集中 Review；若获准真实采集，再以真实结果进行批次 Review。成功取得响应后可推进受批准的 raw 阶段；网络继续失败时如实报告，不再要求作者重做无变化的工程或包装。

## 本地文件

- 审查证据：[独立证据目录](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c1-consolidated-evidence-independent-review)
- 下一阶段边界提案：[阶段范围提案](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C2A_Raw_Acquisition_Scope_Proposal.md)
- 合并执行材料：[Codex Prompt](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Operational_Readiness_And_Phase1C2A_Prompt.md)
- [精确 SHA CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/37754101349)

没有签发新 calendar/market/backfill 的执行 Review 许可证；实际采集权限仍关闭。
