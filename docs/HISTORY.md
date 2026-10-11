# 历史设计、来源与审查索引

历史资料解释已发生的开发、来源、授权和消费，不是当前待执行任务。
新任务依据用户当前授权、[宪章](PROJECT_CHARTER.md)、[当前状态](CURRENT_STATE.md)
与 [路线](ROADMAP.md)。旧 Phase1C.2 CLOSED、R2 LOCKED、作者 REVIEW_READY、
“下一步全历史任务”等均保留当时语境，不能自动套用到现在。

## 优先查哪些资料

| 需要核查什么 | 重要资料 | 保留原因 |
|---|---|---|
| 早期完整业务设计 | [总 REVIEW v1.0](../AStockSystem_Trading_System_Review_v1.0.md) | 历史业务依据；收益/规则/报价等旧引用不是本轮重新核实的事实 |
| 数据真实性与单位 | [data_contract](data_contract.md)、[data_dictionary](data_dictionary.md)、[证券标识历史](security_identifier_history.md) | 仍有长期语义价值；历史实施状态以 CURRENT_STATE 为准 |
| 风险与研究登记 | [risk_constitution](risk_constitution.md)、[research_hypotheses](research_hypotheses.md) | 模板和方法；风险参数未批准、策略未证明有效 |
| 锁/回执与R1原库部署 | [writer lifecycle](phase1c1_writer_lifecycle.md)、[R1 final](reviews/2026-10-02-phase1c1-r1-g3-final-review.md)、[独立结论](reviews/2026-10-02-phase1c1-r1-final-independent-review.md) | 实际保护与部署出处；中间作者临时报表已由最终资料替代 |
| R2身份/时间/事务与有限正式事实 | [R2 final v2](reviews/r2-final-v2/r2-final-review.md)、[import atomicity](reviews/phase1c1-import-atomicity-finite45/2026-10-04/repair-and-preview-report.md)、[finite45正式结果](reviews/phase1c1-finite45-formal-execution/2026-10-05/execution-and-engineering-closure-report.md) | 有限实际导入/Context的证据，不能放大全域 |
| C1关闭/C2开始与停止执行 | [阶段决定](remediation/phase1c2-startup/2026-10-08_Phase1C1_Closure_And_Phase1C2_Start_Decision.md)、[Calendar28边界](reviews/phase1c2-combined-fix-calendar28/2026-10-09/execution-scope.md) | 区分工程关闭、启动、真实许可和研究覆盖 |
| 统一数据机制 | [contracts/time](phase1/contracts-and-time.md)、[operations](phase1/operations.md)、[acceptance v2](phase1/acceptance-matrix-v2.md) | 用于代码理解与历史操作；生产命令仅是历史条件模板 |
| F1–F5及来源版本修复 | [consolidated report](reviews/phase1-consolidated-fix/report.md)、[RAW50 report](reviews/phase1-raw50-source-version/report.md)、[source version design](phase1/source-version-integrity-design.md) | 重推导、原生财务身份、独立重建、授权与版本绑定 |
| RAW49停止现场 | [report](reviews/phase1-raw49-controlled/report.md)、[independent review](reviews/phase1-raw49-controlled/independent-review.md)、[authorization](reviews/phase1-raw49-controlled/authorization.md) | 已消费49新请求；旧SSE2014 UNCERTAIN保留，RAW_ONLY不是生产facts |
| 当时的全历史提案 | [full task](phase1/full-historical-delivery-task-v1.md)、[coverage v2](phase1/coverage-plan-v2.md) | 历史资源/源缺口参考，已退出当前路线；未许可，不按2TiB方案推进 |
| 本轮前用户交接 | [2026-10-11 handoff](handoffs/2026-10-11-session-handoff.md) | 原文保存；其中旧任务优先级和下一步不能覆盖此次方向重置 |

## 文档分类与使用方式

- 当前主入口：PROJECT_CHARTER、CURRENT_STATE、ROADMAP、ARCHITECTURE、RESEARCH_V1；
  CODE_MIGRATION、STORAGE_GOVERNANCE、REPOSITORY_RESET 是维护清单。
- 持续契约/方法：data_contract、data_dictionary、security_identifier_history、writer lifecycle、
  risk_constitution、research_hypotheses，以及版本化数据域契约。区分有效语义和已过时实施状态。
- 冻结设计：remediation 中 R1/R2设计与addenda、manifest、runner设计、phase1 design/source版本设计，
  以及 config 中冻结 registry。存在实际 hash/adapter 依赖，不能按“重复文件”直接删。
- 历史执行/来源/审查：reviews/ 中实际授权、独立结论、final reports、manifest 与原 Prompt 保留；
  remediation 中仍被这些记录引用的 Prompt 保留但不列为当前待执行事项。
- 根目录尚存 Phase0/1A Prompt 与三个旧数据设计：有历史引用/设计解释价值；
  不再是开发入口。三份无当前引用的旧实施 Prompt 已从工作树移除。
- 重复设计在 compat 与 docs 都存在是冻结 pin 所需；重复 Conditional Prompt 两份也在171 pin内。
  本轮保留原因是可验证依赖，不是默认永久保留所有重复文档。
- 两份无现存引用的 G1/G2 作者中间报告从工作树退出；独立审查、修复结论和最终结果仍在原目录。

不新建庞大 archive 目录，不改写历史。移除文档以原提交和 blob/hash 索引恢复；
重要资料仍在有意义的原路径，见 [精确清理与恢复清单](REPOSITORY_RESET.md)。

## 私有来源导航

以下只有目录导航，没有真实数据或实际许可证内容：

- data/warehouse、data/raw、data/curated：旧原库、raw与有限整理/重建输出。
- data/private/phase1-integrated-v1：真实 RAW_ONLY catalog、对象和持久消费。
- data/private/phase1-raw49-controlled-execution/2026-10-10-v1/delivery-index.json：
  最近停止审计、实际执行/交付SHA、原始对象与包的来源。
- data/private/phase1-raw50-source-version-fix/、phase1-consolidated-fix/：
  上一版来源绑定与修复证明。
- data/private/repository-governance/2026-10-11/：本次盘点、文件hash、DB只读统计、
  删除文档恢复信息及尚未批准的17条冗余DB清理提案。

旧总 REVIEW、审批、实际响应和源版本不改写。今后的 Research 输入/报告与交易日志另存私有目录，
用途按当次验证判断，不能通过修改旧审批或消费账本宣布旧全历史数据合格。
