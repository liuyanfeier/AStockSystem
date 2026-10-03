# AStockSystem 后续两批执行说明

2026-10-03 · 当前独立通过的工程基线：`45e474ef3e6f49b56ea3b1b6f9c4fa7177470f45`

R1及R2有限工程执行已完成，当前历史证据和数据准入仍BLOCKED。后续集中完成三组工作：历史身份覆盖、各venue日历与coverage解释、全量运行安全能力和预算。两批内部连续执行，共两个集中Review关口；必要的缺陷修正或无法取得的证据可能使最终准入延后，不能承诺两轮必过。

两批市场/provider请求预算均为0，不重跑133请求，Phase1C.2全量回填保持关闭。

## 现在转交A

将下面文件的完整内容发给负责实现的Codex：

[准入批次A执行指令](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Admission_Batch_A_Prompt_v1.0.md)

A一次完成完整身份分类/共同证据规则及有限成员提案、日历认证范围、15条missing bar调查及完整历史finding处置、必要的新批次lifecycle和规模恢复离线证明、全量候选计划/API预算、互相匹配的case/DQ/Context审批材料。原库只读，市场/provider调用0，不实施真实新增绑定或派生。最后交付SHA、CI、报告、私有证据包和handoff，统一Review。

预计大量身份finding可以按证据组处理，但每个批准必须限定确切成员和endpoint/event/capture范围；不能因旧resolver曾成功而整体恢复。A中已获批事实和工程证明直接复用。

## A独立Review后再转交B

[准入批次B条件执行指令](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Admission_Batch_B_Conditional_Prompt_v1.0.md)

B现在不授权。A的独立Review必须提供真实、匹配且可SQL导入/重开的批准包。收到批准并由用户明确转交B后，实现Codex一次完成隔离预演、原库有限追加、现有raw两代派生/rebuild/DQ/保全，交付统一准入Review。全量回填仍不运行。

若A证明现有材料不足，先一次交付精确新增取证申请和预算；不要仅为再次取得同一BLOCKED结果执行B。取得新增证券/映射/日历数据与全量回填，均需要之后的具体授权，本次两份prompt不授予这些权限。

## 最终交接

每批完成后，只需把final SHA、公开review路径、私有ZIP/索引和final-handoff路径发回本审查chat。独立审查复用已核实的未变部分，重点验证新增证据、适用范围、实现和真实结果。

Phase1C.2准入与Phase1C.3最终全历史验收分开：本轮证明前置足够、安全可运行、预算明确和研究边界成立；真实全历史raw完整性、年度重建和最终coverage/causal结果在实际回填之后验收。准入Review完成仍须有具体全量执行授权，才能开始2013-01-01至2026-09-30回填。

当前参考：[上轮最终独立审查](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-03_Phase1C1_R2_Final_V2_Independent_Review.md)。
