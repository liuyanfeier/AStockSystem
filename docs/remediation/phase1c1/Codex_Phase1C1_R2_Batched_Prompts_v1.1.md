# Phase1C.1-R2 批量执行指令 v1.1

2026-10-02。原 R2 规格的工程与数据不变量保留；建议把七个逐 Gate 交付点合并为两个执行批次。用户将相应批次指令交给实现 Codex 后，该指令才构成该批次的执行授权。本文件本身不启动 R2，也不授权 Phase1C.2。

R1 FINAL REVIEW PASS exact SHA：`cc458ce2e8229dcc914e9a45ae2ac6186f48c45c`。
对应 CI：[36986260440](https://github.com/liuyanfeier/AStockSystem/actions/runs/36986260440)，480 passed。
独立批准记录：[R1 最终独立报告](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-02_Phase1C1_R1_Final_Independent_Review.md)。

## 两批与原 Gate 的对应

| 批次 | 原 Gate 范围 | 交付与审查关口 |
|---|---|---|
| R2-A：调查、设计与工程实现 | G0 + G1 + G3 + G4；G2 的候选裁定和 dry-run 准备 | 只读真实证据、完成工程与合成测试；统一审查实现、政策及每案候选证据。真实 binding 不生效，新真实 generation 不出版 |
| R2-B：获批裁定与离线验收 | G2 应用 + G5 + G6 | 应用明确获批的有限裁定；仅使用既有 raw 派生、重建、DQ、历史保留与最终报告；统一 R2 FINAL REVIEW |

正常路径有两次集中独立 Review。发现阻断缺陷时修正对应批次，重新审查新的 exact SHA。每批内部可保留多个聚焦 commit，不为每个 commit 单独暂停、跑完整套件或请求授权。

这项流程修订替代上述范围内的中间 STOP、逐 Gate 人工授权及先前独立 PASS 前置条件。它保留 A 独立审查后才能执行 B 的边界，且不把作者的候选历史裁定当作独立批准。

## R2-A — 可直接转交的执行指令

执行 AStockSystem Phase1C.1-R2 批次 A：完成证据调查、具体设计、provider/episode 模型与 resolver、DQ 政策、derivation context/generation/quarantine/audit 机制和必要合成测试。全部完成后统一交付，等待一次独立 R2-A REVIEW。

本条授权替代原 G0/G1/G3/G4 中间暂停及逐 Gate 批准要求。先写出并冻结具体设计，再实施；批次内保持设计、实现和候选裁定版本可追溯。原库、旧派生与历史证据只读，真实新 bindings/episodes 不生效，真实新 generation 不出版。

前置：读取 R1 FINAL REVIEW PASS 与 exact-SHA CI，批准基线为 cc458ce2e8229dcc914e9a45ae2ac6186f48c45c；核对当前 HEAD 和后续差异，读取 R1/R2 规格、AGENTS 与既有 Phase1C.1 完整审查。实现范围使用本批次流程修订，工程与数据要求遵循原 R2 规格。

全程市场/provider API 预算为零，包括 metadata、mapping、calendar；禁止重跑 133 请求、capture/resume、stock_basic/bse_mapping 再抓取。允许只读查阅官方公告及供应商字段文档，记录来源与时间；不得下载新增证券列表、映射或市场数据替代既有 raw。Phase1C.2 CLOSED。

完成以下工作：

1. 从现有真实证据建立异常台账，覆盖原 7,666 quarantine、5,008 interval failures（4,515 code-start /493 venue-start）、1,374 PRE_BSE_LEGACY、1,284 NO_IDENTIFIER_MAPPING、2,512 ERROR、13,244 REVIEW 和 1,226 coverage flags。核对 flags/source rows/unique anomalies 及交集，不能把重叠计数当作独立问题。

2. 建立 dataset/event/capture 分开的 BSE 表示证据矩阵，区分 6 pilots 与 242 remaining；分别调查 000022.SZ、000043.SZ、300114.SZ、未知 limit 资产、delist 边界以及 689009.SH/2021-11-12 NULL。每案列原 raw 行、官方/provider 依据、episode/venue、知识时间、影响范围及拟议裁定。证据不足标 EVIDENCE_REQUIRED，冲突标 CONFLICT，明确范围外标 OUT_OF_SCOPE。证据充分的映射只能列为待批准候选，不能直接生效。

3. 设计并实现 provider-native binding 与 official EXCHANGE_CODE 分离、security/listing episode、dataset/capture/event/knowledge scope 和唯一解析。保留旧 frozen resolver/context；不推断 wildcard alias、公司继承关系、代码复用或 pre-BSE venue。保留 native 值；T600018.SH 不自动规范化。真实记录只能形成私有提案/dry-run，实施测试使用合成绑定或临时副本。

4. 冻结并实现 coverage/delist/NULL/calendar/BSE DQ 政策，政策 hash 必须在运行新真实 generation/DQ 前批准。观察与处置分开，不用当前 active 列表定义历史 universe，不用统一 delist+1、NULL 填补、扩大容差或降级 severity 消除错误。缺 venue session 证据为 NOT_CERTIFIED；未知、冲突仍影响数据门。固定原因果与 factor 方法及容差。

5. 设计并实现新 derivation context、完整 generation 出版/恢复、raw FK 和 zero-based row quarantine、append-only finding/quality/batch audit。旧 batch identity/knowledge 时间不改；新知识有新可用时间。DQ 必须选择明确 COMPLETE 的 126 输出集合，不能选半代。resolved+quarantine 逐 source row 守恒，旧 audit 不 UPDATE，旧 context rebuild 不关闭 hash 检查，新输出保持 CURRENT_RECONSTRUCTION/OBSERVED_CAPTURE。

6. 在临时合成存储测试 scope/knowledge/episode 冲突、venue 边界、NULL/coverage、部分出版恢复、file/lineage/DB/promotion 故障、并发与幂等、row conservation、quarantine FK、append-only audit 和旧/新 context rebuild。新增迁移文件使用未占用编号；本批次不部署到原库。

7. 形成可供独立批准的 case proposal 清单及 hash，每案给出确切 dataset、event/capture/raw-row scope、binding/episode、证据与影响行。同时提交 schema/context/publication 设计、实现 diff、DQ policy hash、未解决缺证和 bounded/full-history 限制。不要等待无法取得的市场数据；记录缺口并继续完成可推进的工程任务。

8. 开发中运行针对性测试；实现和报告完成后运行一次必要全套离线检查及 secret scan，提交/推送并核实最终 exact SHA CI。修改或失败时再执行相应验证，不为每个内部 Gate 重复完整套件。保持 SQL001–007、raw、旧252 curated/lineage、旧 identity/receipts/audit/reviews 不变。数据库、备份、行级证据和真实提案留 ignored private storage。

交付 `r2-a-review.md`、私有证据索引/候选清单及摘要、聚焦 commits、最终 SHA/CI。作者结果 R2_A_REVIEW_READY，不自行批准历史事实或宣布 data PASS。

STOP：等待一次独立 R2-A REVIEW。该 Review 须分别裁定工程、DQ/context 政策和每案可执行集合，并生成明确的 approved_case_set/hash；总体工程 PASS 不等于所有候选 binding 已批准。R2-B 尚未授权，Phase1C.2 CLOSED。

## R2-A 的独立审查输出

Reviewer 核对最终 SHA、源码/迁移/测试/CI及真实私有证据，给出：

- 工程实现 PASS / CHANGES_REQUIRED / BLOCKED。
- 获批 DQ policy、context/publication 方案及版本 hash。
- 逐案 APPROVED / EVIDENCE_REQUIRED / CONFLICT / OUT_OF_SCOPE，明确获批 binding/episode 的作用范围；形成 approved_case_set/hash。
- 历史保留、零市场请求证据及未认证 session/PIT 限制。

缺证案例可保留隔离，工程审查可独立通过；未批准案例不能在 B 中自行转为 resolved。B 的启动仍需用户明确授权。

## R2-B — A 通过后转交的执行指令

执行 AStockSystem Phase1C.1-R2 批次 B：应用 R2-A 独立审查明确批准的有限裁定，完成既有 raw 的离线新派生、同 context 重建、DQ、历史保留验收及 R2 最终报告，一次完成后等待独立 R2 FINAL REVIEW。

前置必填真实批准：R2-A reviewed exact SHA、对应 CI、独立 Review、approved_case_set/hash、获批 DQ policy/context/publication hashes。没有批准证据则不执行；R1 FINAL PASS 仍须保留。本条仅在用户转交后授权 B，不授权 Phase1C.2。

1. 先用 R1 strict validator 核对既有 133 回执及冻结输入。在独占锁、可读已验证备份和隔离副本预演之后，部署 A 中获批的 additive migrations/context，并追加获批 bindings/episodes。只应用 approved_case_set；新增发现及缺证/冲突案例继续隔离，不能自行补 alias。

2. 仅从既有 raw 创建新 derivation context 和完整 generation；按批准设计出版 126 非 calendar 输出。预计每代 402,246 source rows 逐行恰好一次进入 resolved/quarantine/明确可追溯处置；如库存不同，调查并报告 BLOCKED，不强制凑数。旧 raw/NULL/native 值不变，新 context 不宣称 historical PIT。

3. 使用 A 已批准的固定 DQ policy，对明确 COMPLETE generation 运行 DQ。形成所有旧 flags/quarantine 到新处置的账本，报告重叠、新出现的 findings、remaining blockers 和各 venue certified/provisional/unknown causal pairs。不得根据新 DQ 总数改政策或容差；需要政策变更时保留结果，返回审查。

4. 同一新 context 在第二个新 generation 中独立重建，要求 126/126 logical hashes、schema/units/source lineage 相等。解释新旧 context 差异，证明旧 context 仍可复现；不要删除旧代或关闭 mismatch 检查。

5. 独立重算验收：133 exact receipts、181 raw、旧252 curated/lineage、旧 frozen identity、历史 receipts/attempts/audits 不变；新增记录仅限批准的 append-only 数据与版本。验证 row conservation、完整出版/恢复、全 finding 处置，以及 transport denial/spy 和原库存共同支持零市场请求。失败按批准的 rollback/recovery 流程处理，不能猜测修复。

6. 完成一次必要全套离线检查、decoded secret scan 和最终 exact-SHA CI。汇总 `r2-final-review.md`，区分 execution/tested implementation SHA 与 final artifact SHA；列批准记录、input/context/policy/binding hashes、私有证据索引、基线到新结果、全部缺证与限制。无需另开 G6 文档批次。

作者交付 R2_FINAL_REVIEW_READY，分别报告 Engineering/Model、Evidence completeness、Bounded data admission。缺证可能使 data 保持 BLOCKED；不能为了零错误强行映射或隐性丢行。私有数据不提交 Git。

STOP：等待一次独立 R2 FINAL REVIEW。无论结果 PASS/PARTIAL/BLOCKED，Phase1C.2 仍 CLOSED，不新增市场请求，不自动进入全量回填、策略、回测或交易功能。
