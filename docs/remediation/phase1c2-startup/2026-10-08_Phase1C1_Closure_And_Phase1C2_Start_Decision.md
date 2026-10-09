# Phase1C.1 工程收尾与 Phase1C.2 启动决定

日期：2026-10-08。基线 SHA：`6f5e3361bb8aff59621b72c38e89de96c668953d`，本轮重新确认 HEAD 匹配、Git 干净。

**当前决定：已通过的 Phase1C.1 工程修复收尾冻结；按用户最新直接指令推进 Phase1C.2 启动批次，不再等待阶段确认。**

用户最初对 R1/R2 任务写过“不得开始 Phase1C.2”，这是当时修复范围的边界。最新指令明确要求工程修复通过后尽快进入下一阶段；当前指令取代之前的阶段限制。上一轮 Review 将旧限制继续作为待用户确认的理由，判断不当，现已纠正。

本决定取代上一轮报告及范围提案中的“Phase1C.2 CLOSED／阶段范围仍待用户确认”。原报告的 SHA、CI、真实调用、证据及保全结论不变，旧文件和封存包作为历史版本保留。

## 已关闭与当前状态

| 项目 | 当前状态 |
|---|---|
| R1 / finite45 工程修复 | CLOSED |
| runner F1–F4 / root clone | 独立 PASS，保持关闭 |
| `6f5e3361…` 证据、执行边界及保全 Review | PASS |
| Phase1C.2 启动与运行准备 | AUTHORIZED，进入新阶段工作 |
| 日历 / 历史身份 / NULL / 研究 DQ / Context | 真实证据缺口继续登记，研究准入 BLOCKED |
| 新运行机制上线、28 日历、6 行情、全量回填 | 等新实现及精确申请的集中 Review；本决定不制造匹配的 runtime 许可证 |

没有把 Phase1C.1 所有历史数据问题写成已经修复。它们继续在 Phase1C.2 对应数据准入 Gate 中处理；不要求重复已经通过的工程修复，或用未取得的全历史 raw 结果阻挡新阶段准备工作。

## Phase1C.2 第一批一次性实施内容

1. 诊断 `api.tushare.pro:443` 的实际连接路径：限定 DNS/TCP/TLS，无 HTTP/token/自动重试，补充安全的异常类别和阶段记录。旧 SSE2012 UNCERTAIN 继续 UNKNOWN，不能推断未送达。
2. 在真实停止账本的只读副本上，完成保留旧历史、单全局消费账本和追加匹配授权的继续机制设计、实现及 closed mock。旧消费不清除；28 个真未执行成员可形成精确候选，不直接重跑旧 CLI。
3. 取证四个已核验 literal URL 的官方文献，预算4、每项最多1GET、无重试/redirect。此范围随新启动 Prompt 执行，无需每个文献再单独问用户；本对话仅生成交付，尚未进行这些请求。
4. 集中提交新机制及精确日历/行情申请、实际诊断/文献证据、保全、必要测试和精确SHA CI，做一次 Review。真实采集待运行机制审查通过后按具体许可证执行。

原133不重跑、两个已消费日历成员不重发；原库、旧metadata、171冻结项和146,568保护文件不改。原始采集成功、完整性认证和研究可用分别记录。完整2013-01-01..2026-09-30目标、原venue/端点不缩小。

## 交给 Codex 的当前文件

[Phase1C.2 启动 Prompt](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C2_Start_Prompt_v1.md)

旧 `Codex_Operational_Readiness_And_Phase1C2A_Prompt.md` 与 `Phase1C2A_Raw_Acquisition_Scope_Proposal.md` 仅保留为旧提案，不继续作为当前待批准指令。使用新文件执行，不再问一次“是否允许进入 Phase1C.2”。
