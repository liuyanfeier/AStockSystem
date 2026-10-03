# Codex prompt — Phase1C.1 R2-A consolidated fixes

继续 AStockSystem 的 R2-A，在一个批次内修复独立 Review 的三项工程缺陷并统一提交复审。当前审查 SHA 为 `68b62ca6fb65e28b4ea059ca8c197c244b5a2253`；结论 CHANGES_REQUIRED。阅读本目录 `2026-10-03_Phase1C1_R2_A_Independent_Review.md` 和 `R2A_Independent_Regression_Repros.py`，以及仓库 AGENTS、v1.1 两批 prompt、冻结设计与 addenda。不要回到 G0/G1/G3/G4 的逐步等待；本轮修复完成后统一停在 R2_A_REVIEW_READY。

本轮仍仅 R2-A：原仓库数据库与真实 raw/旧 curated/lineage/identity/receipts/audits 只读，SQL001–007 与旧 source/spec/reviews 不改。不应用真实迁移或 bindings/episodes，不运行新真实 generation/DQ。新 publication/DQ/rebuild 验证仅在临时合成存储中完成。市场/provider 请求预算为 0，包括 metadata、mapping、calendar；不得 capture/resume/replay。R2-B NOT_AUTHORIZED，real-data gate BLOCKED，Phase1C.2 CLOSED。

1. **F1 / P1 — 每根 daily 的 factor 完整性。** 新 DQ 目前仅检查已有 factor 值和相邻 pair；完整六 dataset 输出、单根合法 daily、空 adj_factor 会返回零 finding 和 PASS。对每根 resolved daily 独立验证匹配 factor 的存在、有限性、正值与正确 identity/event scope，缺失/无效应产生 blocking source-row finding；pair 检查继续保留。不填补 factor、不重新取数、不改变容差。覆盖孤立行情、segment 首根、gap reset、缺 factor、有效 factor 的集成负正例；核验 per-output 和 batch gate。

2. **F2 / P2 — 实际 pair/source 定位。** 新 DQ 将整 episode 的 causal/factor mismatch 记到 max(trade_date)，导致实际异常日 PASS、后续正确日 BLOCKED。按每个实际异常 pair 生成稳定 finding，明确 current/previous event、raw source 与 episode；聚合计数独立保留。逐输出状态基于实际异常 scope。回归使用 2025-05-06/07/08 三天：07 异常、08 正常；07 必须 BLOCKED，08 必须 PASS。追加正常后续 bar 后原异常 key/date/source 不变。公式、价格 0.011、causal 0.011pp、factor `0.011 + 100 * 0.011 / pre_close` 保持原义；不得修改旧 immutable DQ 实现。

3. **F3 / P2 — 固定 context resolver snapshot。** 当前 validate_context 与全库实时 resolver hash 比较，合法追加更晚 approved v2 binding 后，旧 cutoff 仍解析为 v1，但旧 COMPLETE generation 选择失败。设计并持久化 context 专属不可变 snapshot/membership，验证固定内容并用于 conversion/publication/selection/DQ/rebuild。合法追加其他记录或新版本不应使旧 context 失效；引用记录遭篡改仍必须拒绝。禁止删除 hash 检查或自动追随 latest resolver。补充同一个合成库中旧 context COMPLETE、追加更晚版本并创建新 context、旧新明确选择/审计、旧 context 再次独立 rebuild 一致的集成测试，以及 pinned 记录/成员内容篡改负例。

冻结 design v1 保持原字节；设计变更先记录为 append-only addendum，再实现并更新审批所需 artifact hashes。尚未部署的新增 R2 schema 可以在本修复批次调整并接受统一 Review，不能改原库 schema/历史数据，也不能把旧审核报告覆盖成新的结论。没有收到独立批准时，approved_case_set/hash 继续为 null，不能把 candidate payload 自动转换为真实 Approval。

先运行三个针对性回归和必要受影响测试；完成全部修改后运行一次完整 offline suite、doctor/contracts/specs/plans、decoded secret/credential-pattern scan、原库/受保护文件核验。保护摘要必须仍证明 19 原表、181 raw、133 strict receipts、252 旧 curated/lineage、1,102 受保护文件不变；402,246 原 source rows = 394,580 resolved + 7,666 quarantine。测试缓存与合成库放在可写临时目录。

按实际修改提交 focused commits 并推送，核验最终精确 SHA 的 GitHub CI 成功。更新统一 review report/manifest，给出三项修复定位与负正例、最终 SHA/CI、新设计及 schema hashes、现存 evidence/candidate 哈希、原库保护与 0 请求证据、仍待确认的历史事实。完成后停在 R2_A_REVIEW_READY，只提交一份完整材料供独立复审。不得开始 R2-B 或 Phase1C.2，不要求用户逐小项批准。
