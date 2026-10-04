# AStockSystem 准入批次 B：获批证据应用、离线验收与统一准入审查

2026-10-03 · 条件执行模板

**此文件现在不构成执行授权。** 只有准入批次A已完成独立Review、实际批准包已生成，且用户随后明确转交本指令授权B，才能执行。模板和作者候选hash都不是实际批准。新增取证与Phase1C.2全量运行仍未授权。

## 可直接转交的执行指令

请在 `/Users/yanliu/Documents/AStockSystem` 一次完成获批身份/日历/DQ证据的应用、隔离预演、原库有限追加、既有raw离线派生、重建和最终验收。内部连续推进，保留聚焦commits；完成后一次交付独立Phase1C.2准入Review。市场/provider请求必须为0，禁止重跑133请求和开始全量回填。

## 1. 必须具备的真实前置

先读取本批次A、当前AGENTS、既有R1/R2批准，以及：

- A的reviewed exact SHA、对应CI和独立Review报告。
- 实际批准包目录/ZIP、批准manifest及完整bytes/canonical索引。
- 实际review_ref、approved_at、工程/设计/schema/policy pins。
- 实际approved-case-set、case decisions、DQ evidence、resolver snapshot、Context；若已有成员复用旧批准，批准包必须明确允许的引用组合。
- B的实际允许动作、原库追加范围、恢复方案和仍未获准的证据/数据取得清单。
- 准入条件表中哪些必须在B被证明，哪些仍EVIDENCE_REQUIRED；全量计划和API预算是否已被裁定，但尚未启动。

逐文件校验bytes、模型解析和canonical hash一致，用managed SQL临时副本验证真实批准的import/register round-trip。继续使用已批准UTC instant协议；不能只验JSON序列化而省略实际数据库重开/pinned-member验证。

任一必要批准缺失、Context与snapshot不匹配、实现不一致，或Review未允许执行B时，保存集中诊断并停止依赖动作。若A只完成缺证调查、没有足够可应用材料，不得为了“完成B”重复现有两代和同一BLOCKED结果。

将实际批准包原bytes复制到新的ignored目录；**不得修改或自行生成approved_at、review_ref、最终case/DQ/resolver/Context hash。** 源码、迁移、config、政策和冻结设计须等于获批版本。后续授权说明/执行记录/脱敏报告可有独立SHA，明确区分approved implementation、execution及final delivery SHA；文档提交不改变Context implementation pin。

## 2. 授权范围与保全

本条在满足前置并由用户转交后，只授权独立Review明确允许的有限追加、现有raw派生与验收。新增market/metadata/mapping/calendar调用为0；禁止capture/resume/replay、全量batch注册/执行、策略/回测/交易。若A申请了新的取证预算但未另获具体执行授权，本文件不允许取得那些数据。

当前原库已经是008–010及matched-v2执行后的库。以B开工时的真实受保护状态建立新baseline：原有全部表/记录、133回执和attempt、181raw、旧252派生及所有matched-v2输出/Context/generation/audit、旧批准/失败现场/备份/审查。新追加改变整库hash是正常的；证明旧记录内容和受保护文件不变，不能把“整库hash相同”作为部署后保全条件。

先取得managed exclusive owner、确认无竞争者，建立**当前库**的可读备份，核对bytes和所有旧记录。保留旧007备份，不能拿它覆盖当前库。完成回滚/恢复方案后，从当前受保护基线建立全新的隔离副本；不覆盖旧失败隔离库。

## 3. 隔离预演，一次覆盖全部获批材料

1. 用现有managed owner API按批准顺序应用必要新schema和case数据。SQL001–010原文件保持不变，获批的新迁移使用独立编号。重复执行先按批准协议精确检查：已有records完全匹配时确认已应用，部分/冲突时阻断；不能盲目重复INSERT或忽略PK异常。无半完成schema/version或隐性记录替换。
2. 只导入实际获批的新增delta episodes/codes/bindings及精确members，再验证旧成员+新成员组成的完整snapshot。共同规则批准不能扩到未列明证券、dataset、capture、event或raw ordinal；未批准部分保持quarantine。保留已有192行及旧有限批准的历史事实、原批准ref/时间，不重插旧record或覆盖旧版本。
3. 导入获批session、reference、BSE transition和source处置，核对实际episode FK、venue/session范围及所有来源。BSE两批切换和pre-BSE边界不混用；范围外行保留源行及quarantine，不进入resolved。
4. 注册获批的新**bounded** Context及固定resolver snapshot。仍用原133exact inputs/126outputs和402,246source rows；新的证据并不自动成为新的raw输入。使用Review实际批准的parent Context/generation、输入顺序和全部pins，不能推断“latest”。若库存不同，调查后报告，不强制凑数。
5. 创建显式第一代完整输出，用获批固定DQ evidence/policy进行真实DQ；再以同一Context独立生成第二个完整generation。逐source守恒，每行精确一次进入resolved/quarantine及可追溯处置；保留native值、NULL、typed empty partitions、schema/units和lineage。
6. 对两个完整代验证126/126 logical hashes、schema、source lineage、quarantine语义和固定snapshot一致；在Asia/Shanghai、UTC、America/New_York、Asia/Kathmandu重开managed连接，实际选择完整代并验证Context、成员和hash，不能只测fixture时间字符串。
7. 补足批准要求的真实材料导入/出版/恢复证明，复用A已通过的合成故障测试；不为每个内部步骤重跑全套。不把未来全规模合成证明当作真实历史数据覆盖验收。

隔离完整预演通过、原库受保护基线仍匹配后，才执行下一节；预演失败按已批准恢复方案保留现场，禁止自行重签批准、放宽guard或修改政策。

## 4. 原库有限追加与实际验收

按获批方案在原库追加schema/证据/Context，再创建两代COMPLETE及所需append-only DQ audit。严格复用已通过预演的批准bytes和实现；不在部署中临时修source/policy或扩大历史事实。

验收至少包括：

- 原133receipts仍VALID/EXACT、失败0，raw181及全部受保护历史文件不变。
- 旧007历史表、008–010已有记录、旧和matched-v2 Context/generation/audit/批准保持内容；只增加允许的新行/新版本。
- 新两代126/126完整输出、402,246源行守恒、native/NULL不变、全部raw UUID/zero-based ordinal及lineage可追溯。
- 新两代相同Context的logical/schema/quarantine/lineage相等，显式COMPLETE选择成立，无半代、混代、额外orphan或重复登记。
- 新snapshot/Context完整成员与批准一致，SQL导入及跨时区实际重开验证通过。
- 每个dataset/date局部DQ和batch gate由自己的真实findings计算；不能为“整批通过”改写局部结果。
- 全部旧15,756finding与新基线finding均有可追溯旧新处置；旧key即使不再出现也保留payload、severity和关闭依据，不更新旧audit。
- 已批准范围外、待证、冲突仍分别报告，不用删除行或改变分母制造清零。
- 因果检验报告eligible/certified/provisional/unknown/failed分母、factor及reference依据；0 eligible或全部排除不能标PASS。

原库和隔离库完整结果比对；旧Context继续可重建，复用当前未改变部分的独立证明，对实际受影响路径补验。输出全量source/finding处置账本及hash，以精确集合和原因解释差异，不只比较总数。

## 5. 最终准入判断材料

维护逐条件表，依据原规格的Phase1C.2前置和A独立Review的明确范围，列出：

| 条件 | 必须报告的实际依据 |
|---|---|
| 既有bounded数据门 | 新真实DQ、身份/覆盖/reference/session阻断的逐项裁定；如仍有in-scope hard blocker则BLOCKED |
| 历史identity/episode及endpoint scope | 获批范围、未证范围、普通/更码/BSE/上市退市例外；bounded批准不能自动外推全历史 |
| 各venue日历 | bounded已认证范围、未来全量所需范围、来源和尚未完成的取得条件 |
| trade_cal / stock_basic / identity前置 | 实际已有状态、各自准备/取得/批准依赖，不以当前active名单替代历史universe |
| 新批次lifecycle | A已获批实际离线持久化/transport模拟证明及部署状态；call entry不冒充远端接收 |
| 全规模membership与恢复 | A已获批规模证据、限制、未来计划兼容性及分片/截断/resume保障 |
| 全量候选计划和预算 | 2013-01-01至2026-09-30范围、逐endpoint cap/权限/请求与attempt/限速/失败停止、精确批准状态 |
| 研究使用边界 | CURRENT_RECONSTRUCTION/OBSERVED_CAPTURE，历史PIT及估值字段使用限制 |
| 保全/CI/凭据 | 旧事实不变、零市场调用、必要检查与exact-SHA CI/secret scan |

明确哪些是“开始全量回填之前必须满足”，哪些是“回填后Phase1C.3验收”。全历史raw完整性、真实年度curated rebuild、全历史coverage/causal最终结果等回填后才能取得的验收，不能被写成开始回填前已完成；也不得把尚缺的前置挪到回填后。

作者结束状态为`ADMISSION_B_FINAL_REVIEW_READY`，分别报告Engineering/Model、Evidence completeness、Bounded data admission、Full-backfill prerequisites和候选Plan/API budget批准状态。独立Review裁定`READY_FOR_PHASE1C2_AUTHORIZATION / BLOCKED`及原因。**准备就绪不等于全量运行已授权；本批次结束时Phase1C.2仍未启动。**

## 6. 一次性交付与停止点

使用新的`data/private/phase1c1-admission-b/<run_id>/`保存备份索引、原始批准副本、隔离/原库验收、Context/generation/audit IDs、完整source/finding账本、能力证明引用、baseline before/after、调用保护、secret scan、manifest和final-handoff。禁止覆盖原matched-v2或A目录。

公开交付到`docs/reviews/phase1c1-admission-b/<run_id>/`：最终脱敏报告、准入条件表和hash/count索引。完成一次仓库要求的全套离线检查、doctor/contracts、decoded secret scan，提交/推送并核实最终exact-SHA CI。源码未改时仍按仓库要求完成该交付检查，内部不逐步骤重跑；新修改/失败才触发相关复验。

交付final SHA、CI URL、公开报告、私有review ZIP/完整索引/`final-handoff.json`路径。所有真实批准、历史证券列表、raw、DB和完整行级账本保持ignored。

**STOP：等待一次最终独立准入Review和后续具体全量执行授权。** 不自动启动Phase1C.2；不新增取证请求、不重跑133请求。若数据或全量前置仍BLOCKED，一次报告完整缺口和具体所需行动，不反复执行同一不变输入制造新的审查轮次。
