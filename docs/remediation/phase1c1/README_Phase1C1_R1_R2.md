# AStockSystem Phase 1C.1-R1 / R2 规格与施工单

版本：v1.0，2026-10-02。交付类型：设计文档；没有执行项目 remediation，没有变更仓库或本地真实数据。

## 使用顺序

1. 阅读 [R1 Engineering Integrity 规格](./Phase1C1_R1_Engineering_Integrity_Spec_v1.0.md)。
2. 从 [R1 Codex prompts](./Codex_Phase1C1_R1_Gated_Prompts_v1.0.md) 中只复制 **R1-G0**。后续每次只授权一个 Gate。
3. R1-G0、G1、G2、G3 各完成后停下，独立 Review exact SHA。R1-G3 必须取得明确的 **R1 FINAL REVIEW PASS**。
4. 之后才可启动 [R2 规格](./Phase1C1_R2_Historical_Identity_Coverage_Spec_v1.0.md) 和 [R2 Codex prompts](./Codex_Phase1C1_R2_Gated_Prompts_v1.0.md)。R2-G0 至 G6 同样逐 Gate Review。
5. 任何结果，包括 R1/R2 PASS，均不授权 Phase 1C.2。Phase 1C.2 始终 CLOSED，另行立项与批准。

生成两套规格不等于批准执行 R2。不要把整套 prompt 交给 Codex 后要求“一次全部完成”。实现者可以报告 REVIEW_READY，但不能给自己签 REVIEW PASS。测试通过、CI 绿色、commit/push 均不能代替 Review。

## 核验范围与事实来源

已读取引用对话的完整 Phase 1C.1 总 REVIEW，并通过 GitHub connector 核对以下固定版本的仓库内容：

- [审查基线 2aba10fc143a8b1975b00b7a2a965cd1465942a7](https://github.com/liuyanfeier/AStockSystem/commit/2aba10fc143a8b1975b00b7a2a965cd1465942a7)。
- [公开真实演练证据](https://github.com/liuyanfeier/AStockSystem/blob/2aba10fc143a8b1975b00b7a2a965cd1465942a7/docs/reviews/2026-10-01-phase1c1-review.md)。
- [AGENTS.md](https://github.com/liuyanfeier/AStockSystem/blob/2aba10fc143a8b1975b00b7a2a965cd1465942a7/AGENTS.md)、原 Phase1C1 prompt、`docs/phase1c1_curation.md`。
- `sql/006_bounded_slice_lifecycle.sql`、`slice_plan.py`、`slice_capture.py`、`raw_writer.py`、`slice_curate.py`、`slice_dq.py`。
- GitHub compare 确认 base `c54b85a4cd88abbb9dd6d99553c0dff62cf5977f` 到上述基线共六个 commit。读取时 main 上的公开 review 文档 blob 与该基线相同；不据此断言 main 的所有代码未变。

本次没有访问用户真实 raw/DB，故 133 receipts、181 raw objects、126 outputs/代、DQ 计数均是已核对的公开报告事实，尚未在本地重新逐对象验证。R1-G3 和 R2-G5 明确要求持有私有证据的执行环境验证；缺少证据时保持 BLOCKED，禁止伪造 PASS。

本次没有对三个历史代码、689009.SH 或 delist_date 作事实裁定，也没有新做官方历史资料调查。R2-G0 会登记已有来源和缺证清单；后续可只读检索官方公告及供应商文档，保存来源时间与摘要/哈希。所有市场 API、行情/证券列表/映射/日历重采集均为零预算。

## 总 REVIEW 问题处置表

| 问题 | 处置 Gate | 验收要求 |
|---|---|---|
| COMPLETE 可引用虚构 object；verify_batch 空集合成功 | R1-G1 | exact receipt validator；空集合 fail closed；新增 migration |
| 恢复/claim 并发、事务与一次 attempt | R1-G2 | DB 范围进程锁；原子 claim；故障测试；不重复 HTTP |
| 133 真实 receipts 在严格规则下成立 | R1-G3 | 私有逐条验证，公开脱敏证据；真实数据缺失则 BLOCKED |
| ingestion_run 提前 RUNNING/started_at 误导 | R1-G2 | 保存历史；未来生命周期设计列为 Phase1C.2 前置，不在本轮重写历史 |
| partial curated generation 不可恢复 | R1-G2 登记；R2-G4 修复本轮必要部分 | 显式 generation/context，逐对象恢复，完整集合后原子发布 |
| quarantine 无 FK/SQL 行号 | R2-G1/G4 | 新版本精确 raw 行谱系与 FK；旧记录不猜行号 |
| exchange 与 provider historical code 混用 | R2-G1/G2 | dataset/time/evidence-scoped provider binding；官方代码区间保留 |
| 5,008 interval failures；1,374 PRE_BSE_LEGACY | R2-G0/G2/G5 | 全量台账解释；pre-BSE 不伪造成 BSE 历史行情 |
| 三个历史代码与未知 limit identifiers | R2-G0/G2 | listing episode 与资产证据；不按名称/数字猜测 |
| 1,226 coverage flags；delist boundary | R2-G3/G5 | 按 security/episode/date 解释；UNKNOWN 保持阻断 |
| 689009.SH NULL reference price | R2-G0/G3/G5 | 单案裁定；保留 NULL，禁止补值或调大容差 |
| audit 被 UPDATE；局部质量与 batch gate 混同 | R2-G3/G4 | 新增 append-only DQ audit；local_status 与 batch_gate_status 分开 |
| SSE calendar 推断所有 venue session | R2-G3/G5 | calendar basis 显式；缺 venue 证据的测试为 NOT_CERTIFIED |
| 当前知识与历史 PIT 混同风险 | R2-G1/G4/G5 | 新知识时间；CURRENT_RECONSTRUCTION/OBSERVED_CAPTURE 保留 |
| 越过逐 commit Review；exact SHA CI 缺失 | 全部 Gate | 一 Gate 一次交付后 STOP；独立 Review 与 exact SHA CI |
| secret scan 修复 | 全部 Gate 保留 | bytes + decoded values + schema 扫描；不提交 private data |

## 硬约束

新市场 API 请求 = 0；不得重跑 133 requests；不得增加任何新市场采集，包含旧 47-request probe、stock_basic、bse_mapping、trade_cal。不得删除或改写 raw、旧 curated、旧 lineage、已接受 identity snapshot、旧 review 和 migrations 001–006。R2 仅以新增版本与派生上下文修正。不得增加策略、信号、回测、投资组合、券商或下单功能。

R1 是工程真实性验收。R2 同时报告代码/模型完成度、证据完整度和数据准入结论；证据不足可以完成工程交付，但数据门必须 BLOCKED。R1 PASS 不代表数据 PASS；R2 工程 PASS 不代表 historical PIT 或全历史覆盖 PASS。
