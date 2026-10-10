# 给 Codex 的合并执行 Prompt：Phase1 修复、生产形状验证与执行就绪

在 `/Users/yanliu/Documents/AStockSystem` 完成下面整个工程批次。不要只修一个函数或交一份计划，不逐项停下来请求 Review。用户转交本 Prompt 后即执行源码、必要合同/独立 DDL/测试/工具/文档改动，以及此批脱敏代码的 commit、push、最终 SHA CI。交付一次完整可复核结果。

## 1. 当前基线与授权范围

独立审查基线为 `b3507877b5d91f700f6ec26b890868fb3ff8b6c5`；实际源码实现 SHA `334f44aa96aa8c3d57127a97294aebe15773f696`。最终 CI 967 passed，审查者独立 51 个新回归通过；旧源码和保护项通过证据可复用。若开始时 HEAD 不同，先读差异、保留用户修改，再采用实际工作基线，不 reset。

Phase1C.1 既有工程 CLOSED；Phase1C.2 已 STARTED。不要让旧阶段历史 CLOSED/不得开始指令重新阻止这次工程。Phase1 真实数据准入 BLOCKED；当前新 50 请求申请未获执行许可。本 Prompt 允许整个离线修复和新隔离/合成 store 的开发验证，**不授予新真实行情/元数据 API、新生产数据/审批追加或原库写入许可**。不用为已经授权的离线改动重复询问。

先读取完整独立报告及复现脚本：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-10_Phase1_Integrated_Independent_Review.md`
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/work/review_phase1_integrated.py`
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/work/review_phase1_production_shape.py`
- 对应 `outputs/private/phase1-integrated-independent-review/` 内四份独立结果 JSON。

结合原 Phase1 master Prompt、路线图、`docs/phase1/`、交付 report/application/index 和实际停止消费整体实施。旧 original133、所有 FAILED/UNKNOWN/UNCERTAIN、原 capture11 表和仓库34 表、旧 raw/curated/批准事实、171 pins/保护清单保持不变。所有新真实请求为0，不能换 fields/日期/目录绕开消费。审查者的变异样本不是生产事实，不得导入原库或当批准证据。

## 2. F1：从固定 raw 重证派生事实，而非信任可重写的 DB 自带哈希

修复 `pipeline.verify_generation_inputs`、`validate_lineage`、`build/increment` 与消费查询路径。

每个 generation 必须根据自身固定 input manifest、绑定合同/转换版本、实际 source/body/证据政策确定性重推导允许存在的 facts 与 quality。把数据库持久化集合与这一真值比较，至少覆盖：成员集合、dataset/domain/series/entity/source_object/source_row、payload、event/effective/known/retrieval 时间、precision/knowledge_basis/eligibility。拒绝额外事实、丢失事实、错误源行和自洽但非源推导的值/时间。旧代只对应自身输入；新代完整涵盖被合规保留的旧输入和新增输入。

increment 不能把未经源验证的 `old + prepared` 当真值，不能继续传播被一起重算 fact_hash/lineage/content_hash 的错误。保持事务内必要物理读回和 SQL 读回；失败回滚，旧已发布 facts/generations/时间不改写。正确幂等和更正 append 仍须通过。

回归至少包含独立报告的 99 EPS/提前知悉攻击；自洽源行错配、额外行、删除行、时间/eligibility 变异；旧代合法保留及新版本增量。对 audit/as-of/adjust/reference/coverage/increment/rebuild/expand 等读取入口一致阻断，避免只修 CLI 的一个入口。用源码到持久化的完整证据检验，不以数据库约束或自带 checksum 代替。

## 3. F2：以有证据的稳定 security/episode 关联跨码财务事实

修复 snapshot 的当前 native 集合预过滤。依据数据集、source-native 范围、有效身份/episode 和 knowledge cutoff 解析事实归属，再执行该域的时点筛选。

同一明确 episode 换码后，旧码发布的旧报告和其后续修订应继续按可见时点检索。同时处理报告期与公告期跨码、供应商用新码返回旧报告等场景：有匹配证据才关联，不能假定报告期的交易代码就是供应商此记录 native 的唯一含义。身份来源、数据集或区间无法支持时保留具体 unknown/conflict。不得拓宽原有限身份审批或用字符串猜测。

端到端 fixture 验证四财务域两次公告版本、事件日在换码前/后、as-of 在第一次/修订前后、代码复用跨 episode、并发身份冲突和新码返回旧报告。保留 BSE/退市案例、半开区间和不提前可见的既有回归。

## 4. F3：真正可运行的独立生产来源重建与版本处理

把 capture destination 权限、source 证据性质、rebuild 目标用途和 research eligibility 分开建模。新增目录可作为被校验/批准的独立派生重建目标，但不能因可重建就获得 HTTP 或生产采集权限。

实现 production inputs → 独立重建 A/B → audit/coverage/as-of/逻辑 hash 比较的完整入口；目标不能被简单按“非 canonical 就是 fixture”错误分类，也不能改写真实 source 的 fixture flag、放松实际源/批准/证据字节验证或修改原源库。保留 fixture 和实际来源严格区别。独立目标应绑定 root、源 manifest/版本、目标身份和操作范围，拒绝非法混入。

一并审清版本变更后旧 inputs/批准/plan 如何按其冻结版本重证。既有旧 pins 不能被覆盖成新 pins；不能要求旧实际批准重新匹配新 HEAD，更不能因新版运行审计需要旧版本信息就改写旧 receipt。若采用兼容版本注册或可审查迁移，明确边界/固定版本/只读依赖，离线验证即可，真实启用仍留在统一执行申请。

在隔离 production-shaped store 做完整离线演练，所有 transport 禁网。任何 mock 审批都要明确 TEST/FIXTURE 作用域并不可用于 canonical 原项目生产；模拟目录不是真实部署。至少覆盖 A/B 逻辑一致、源 bytes 不变、query 读回、increment 更正/幂等、旧代/不同版本、无权限目标、源许可/合同/证据变异和失败回滚。不能只把报告里的生产重建 PASS 改成待定来代替实现。

## 5. F4：将采集授权保留为真实消费证据的一部分

保持现有严格前置 authorize。在首次 durable claim 前，以事务一致方式保存实际 independent approval、人类许可、审批/许可 hash、原实际证据 path/hash、执行 SHA/版本、plan/root/destination/消费和时间绑定。将授权身份贯通到 attempt、事件、source/receipt，并在重开 audit 复核，不只在传参时检查。

历史审核检查执行时的实际许可和固定版本，不能要求历史许可成为未来 HEAD 的新许可。生产记录无授权链、license=false、时间/范围不符或实际证据缺失/变异时，明确拒绝或标记未认证；fixture 数据不能经 namespace/元数据自洽改动就通过为已授权生产证据。保留人工授权原文，不代签 independent PASS、人类确认或实际 evidence。

新增必要 DDL/metadata 时采用新版/兼容方案并在隔离副本验证，不改原三库、旧DDL/171冻结项。授权持久化出错时先停止，不发HTTP；进程中断、首错停、输出失败、重开和未消费恢复应继续保持单次调用身份。

## 6. F5：把覆盖目标接入公共入口并形成能推进全量的候选计划

实现目标/期望 manifest 或确定性生成器，接到 `coverage` 和最终验收路径；目标至少有范围、版本/hash、来源/依赖、域/时间/venue/证券/episode 维度。支持已认证民用日历和有证据的历史上市宇宙生成市场期望；证券状态、财务报告/vintage、行业版本/区间、规则覆盖要能表示已知目标与未知分母，不能只统计实际已有行。

报告分列 expected、observed、missing、duplicate/conflict、uncertified、source-backed not-applicable，以及未知分母/未认证前置。缺日历/身份不虚构分母；缺行情不能自动等于停牌；没有状态行不能自动 NORMAL；没有旧报告/行业成员不能自动不存在。默认公共命令必须发现“已知开市/已知有效上市但整行缺失”的受检范围，不要求调用者手写每个 missing tuple。

以非空闭合样本验收整天缺失、整个证券缺失、上市/退市边界、已证停牌、未知状态、缺财报/vintage、分类换版/成员退出和无规则版本。目标冲突/过期/变异必须拒绝或明示 UNKNOWN；缺口没有被无条件硬编码 BLOCKED 掩盖。

同一批完成真实覆盖规划：保留 2013-01-01–2026-09-30 原目标，把当前 27+17+6 请求、复用/禁发、其他各域的候选展开规则、必要前置和依赖、未知权限/cap/空结果/vintage、请求和 IO 成本列入一份统一计划。可确定的数量应计算，不继续用一个30,126上界覆盖所有域；未知项有对应试点要回答的明确问题。没有证据的数量/身份/vintage保持未知，不发新请求。

## 7. 一次做好执行准备，不为形式增加交接

修复后更新现有 50 请求申请到最终代码 SHA、pins、实际消费和新目标/目的地/授权持久化模型。保留 27 日历原成员来源、6 行情原提案、17 来源试点；有合理变更时明确原因、前后差异和预算，不偷偷替换日期、返回空试点或已消费范围。

候选计划的实际 independent reviewer/approved_at/human 仍为空，execution_license=false。这次交付不是自己签发许可。把未发送恢复、首错停、空结果/截断/真实权限失败、raw-only 与研究准入、日历旧FAILED完整响应的离线采用政策等整合到同一运行手册和申请，而不是再写专用 calendar26/25 工程。

生产形状闭合 mock 按拟议阶段贯通执行→消费/回执/授权→build→覆盖→as-of→独立两次 rebuild→increment→完整审计，实际调用0。缺少真实 vintage 或历史来源的部分应列入实际试点/证据政策，没有证据不能编造。旧有限身份批准的252观察兼容检查一次复用，不再人为拆15/45条批次。

继续复用完整保护，披露成本。可做必要性能测量/实现常规优化，但保护等价性没证明时保留原方式；不要把性能研究另设一个必须用户逐项审批的 Gate。凭据只由已配置的私有环境读取，不显示、不复制进报告或 Git。

## 8. 测试与一次交付

开发阶段只跑相关有意义回归。全部改动完成后，一次完整本地 suite、doctor、适用旧合同/新specs、全量保全、decoded/encoded 凭据与暂存审计；最终真实代码 SHA 的 CI 通过。修复导致失败时补跑必要检查，不用旧967结果替代新增实现。避免为 ZIP 自指 hash 或纯文档 SHA 制造多轮代码交付。

一个交付索引定位：

1. 综合报告与更新验收矩阵：F1–F5 的实际实现、端到端证据和限制；软件、真实覆盖、实际许可分列。
2. 确定代码 SHA/交付 SHA/CI、运行入口、兼容/版本/新目的地方案。
3. 一个私有证据包：原变异回归现在被拒绝，跨码四财务域正常，生产形状 A/B 重建、目标缺失可见、真实授权链模拟闭合、消费/旧证据/原库保全、最终凭据审计。不要重复打包巨大原库。
4. 更新统一候选执行申请及明确全量规划，实际批准字段仍空/false。
5. 可直接运行的批准后命令和停止后审计/剩余成员恢复操作，不要求逐函数/接口再产生 Prompt。

最终状态：`PHASE1_CONSOLIDATED_FIX_AND_EXECUTION_READINESS_REVIEW_READY`。如果有不能完成的具体必需能力，写真实 PARTIAL、原因和可验证的剩余动作；仍完成其他工作，不用空实现或作者自审 PASS 凑结论。

修复、验证和准备全部完成才统一交付并停止，等待一次独立 Review。本批真实请求0、原库写入0；后续收到匹配的真实批准/人类授权时，已批准范围内按阶段自动连续运行，不逐成员再询问。试点通过不自动获得未批准全量预算。Phase1 最终完成以实际目标覆盖、PIT/身份/状态/规则完整性、第二来源抽查、重建/增量和最终独立准入验收为准，不能承诺本次软件修复就等于全历史数据完成。
