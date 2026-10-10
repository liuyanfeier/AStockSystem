# Phase1 Integrated Independent Review

审查日期：2026-10-10。审查交付 SHA：`b3507877b5d91f700f6ec26b890868fb3ff8b6c5`。实现 SHA：`334f44aa96aa8c3d57127a97294aebe15773f696`，二者之间只有综合报告的八行补充，运行源码相同。

**结论：CHANGES REQUIRED，3 项 P1、2 项 P2。** 本批各数据域已具备非空实现和贯通演示，工程有明显进展；当前“完整 Phase1 软件验收 PASS”还不能成立。以下问题集中为一个修复批次，不要求逐问题、逐数据域申请 Review。Phase1C.1 既有工程关闭结论保持有效；当前工作属于已开始的 Phase1C.2 与全 Phase1 数据基础交付。

50 个真实候选请求的申请在离线范围、预算和消费排除上通过检查，但本报告不签发运行许可证。原请求不重发，已有失败不清除。整个 Phase1 真实数据准入仍为 BLOCKED。

## 审查依据与通过项

- 已检查实际工作树、提交差异、新增 `astock.phase1` 全部核心模块、新合同、DDL、公开操作入口、验收矩阵、私有交付索引和申请。审查结束时原仓库 HEAD 仍为上述交付 SHA，工作树干净。
- 使用 GitHub 连接器直接读取最终 Actions job 和日志，核实 checkout 精确 SHA 及 **967 passed / 5 warnings**，job success。独立运行全部 51 个新集成回归，**51 passed / 117.70s**，禁用真实网络；不重复跑已通过的整个 967 项套件。
- 在审查者隔离目录通过真实合同、mock runner、证据导入和 build 入口重新建立非空 23 数据集、62 facts 的演示；另外构建证券换码场景。没有在原私有演示库中改行。
- 私有 ZIP：CRC、无重复/多余成员、417 个索引文件 SHA256/长度及外部包 SHA256 均通过。包 SHA256 为 `5f8795ff999615d41fa2e2dbe52d0809b8ccdc532d422a7c3d57a74b6542fc14`。
- 保护清单引用 SHA256、146,656 个历史文件条目和 171 个固定项按原保护规则核验，实际对去重/例外后的 146,825 条路径逐字节计算哈希。保护规则中允许变化的旧 capture 数据库另与本次冻结快照的当前 SHA256 比较，三原库均与交付记录一致；无原库 WAL。
- 原库只做字节核验。现有托管只读连接会创建/检查锁文件，因本审查的只读沙箱边界返回 `WAREHOUSE_LOCK_PATH`，因此没有重跑原库 SQL 行集查询，也没有申请写锁文件的权限。原数据库字节完全一致支撑其内容未变；169 条记录、136 条已消费计数引用冻结快照，不冒称新 SQL 读回结果。
- 统一候选 plan 可由当前源码、冻结消费和保护引用精确重建；50 个成员互不重复，预算为 **27 日历 + 17 来源试点 + 6 保留行情请求**。`execution_license=false`；全量预算仍未知。该检查证明申请的离线绑定，不证明账号权限、返回完整性或历史 vintage。

## F1 — P1：派生事实审计只检查库内自洽，没有验证事实确由 raw 产生

位置：`src/astock/phase1/pipeline.py:103–112`、`:175–185`、`:211–227`。

`verify_generation_inputs()` 确实重新解码了 immutable input，但丢弃 `source_decode()` 返回的 facts。`validate_lineage()` 检查的是持久化事实、自带 fact_hash、可改写的 generation content hash 与 source_object 是否互相一致；没有将这些事实与对应输入重新推导出的完整事实集合比较。increment 的 `expected = old + prepared` 又直接信任已存事实。

独立复现保持所有 raw/source/manifest 文件不变，仅在隔离 fixture 库中追加一条内容自洽的 income fact，并更新其 lineage 与 generation content hash。该行引用真实存在的旧 source_object，但将 `basic_eps` 改成 99、published_at/available_at 提前到 2025-02-28，原 source 公告日仍为 2025-05-01。结果：

- 修改前，2025-03-01 查询没有财务数据；修改后出现该伪早知版本。
- capture audit 仍 VALID，35 个输入通过；lineage audit 仍 VALID，63 个 facts 通过。
- increment 返回 ALREADY_VALID，继续保留错误事实。

这是持久化派生数据的完整性和 PIT 防泄漏缺口。不是发现真实生产数据已经被污染，也不是假定存在恶意用户；一致性错误、错误导入或中间元数据被一起改动时，现有审计不能以原证据纠正判断。

修复：对每代固定输入使用绑定的合同/转换版本确定性重推导，验证源对象、源行、payload、series、identity、时间、eligibility、完整事实集合及 quality 集合。旧事实只有从保留输入重证后才能进入新代；不能只加一次 self-hash 比较，或只验证本次新准备的行。查询、audit、increment、独立 rebuild 应共享该验证。每代验证其自己的输入集合，避免用最新大集合误判旧代。

## F2 — P1：换码后旧财报被当前 identifier 预过滤掉

位置：`src/astock/phase1/domains.py:160–177`。

`historical_snapshot()` 先取查询 event 日仍有效的 identifier 集合；`belongs()` 只有在事实的 entity 已位于该集合时才尝试历史解析。因此同一 security/episode 的旧 identifier 财报会在解析前被排除。

独立非空端到端场景：S1/E1 的 `000001.SZ` 于 2025-01-06 结束，明确映射的新 `000777.SZ` 自该日开始；四财务域保留旧码的 2024-12-31 报告，2025-04-01/05-01 两个已知版本，共 8 行。旧码在报告期、新码在查询日均正确 resolve 到 S1/E1；但 2025-05-15 的 S1 查询返回 **0 个 financial facts** 并标记 EVIDENCE_REQUIRED。本来应返回四域各自的最新已知版本。

修复：按来源、数据集适用身份、事实事件/报告期及 knowledge cutoff，将事实归入稳定 security/episode；不要用查询日的当前码排除历史事实。报告期与公告期跨换码、供应商用新码返回旧报告的语义也必须有明确证据/unknown 处理。不得用名称、后缀或数值相似性补映射。代码复用、跨 episode 和跨来源冲突仍须拒绝。

## F3 — P1：独立重建只支持 fixture，生产来源一定被 namespace 条件拒绝

位置：`src/astock/phase1/pipeline.py:154–167`；`acquisition.py:33–41`；`fact_admission.py:17`。

source 在唯一 canonical production 目录时 descriptor 的 `fixture_only=false`。任一独立 rebuild destination 不等于该唯一目录，就被判为 fixture；随后要求所有来源的 fixture flag 与目标相同，所以返回 `REBUILD_NAMESPACE_CHANGED`。把 source 和 destination 指向相同目录只是在原库上 build，不是独立 raw rebuild 验收。

审查者在完全隔离、禁网的 scratch root 构造明确标识为合成的 production 形状记录，重建到另一个目录实际返回上述错误。该实验没有真实生产数据、许可证或实际部署；阻断条件可从代码证明对合法 production inputs 同样成立。

修复：明确区分来源性质、可用研究状态和目标操作权限。实现可批准/校验的独立只读输入重建目的地，不把真实来源改标 fixture，也不给新目录 capture 权限。离线生产形状测试覆盖独立两次重建、查询、源证据/许可证复核、原库只读、目的地拒绝非法混入与撤销/变异。只有 fixture rebuild 的现有通过证据不足以宣称生产重建可用。

## F4 — P2：真实采集的独立审批/人类许可没有留存在消费和回执链中

位置：`src/astock/phase1/acquisition.py:123–151`、`:228–259`、`:328–333`、`:390–412`；`sql/offline/phase1_integrated_v1.sql:1–24`。

执行前的 `authorize()` 有实际 SHA、审批文件、人类许可和字节检查，这是通过项。但执行后没有将 approval/human payload、hash、实际证据引用写入 plan/attempt/event/source/receipt；持久化的 plan 仍是 license=false 的提案，重开 audit 也不验证历史批准链。未来交付无法从 store 自身证明某次真实调用对应哪份实际授权。

离线一致性变异实验将一个已闭合 mock 样本的本地副本改成 production 形状，没有任何真实审批/人类许可，现有 audit 却返回 VALID。该实验检验存储的审核能力，**没有证明当前 `execute --live` 可以绕过前置审批，也没有发出任何真实请求**。

修复：在首次 claim 前原子保留真实授权记录/字节引用，将其 hash 绑定 plan、attempt 和 source/receipt；重开以执行时版本校验授权范围、许可、时间和消费，不要求旧批准重新匹配未来 Git HEAD。fact admission 已有保留 approval/human 的做法，可借鉴其完整性原则。缺失或变异授权的 production 记录只能报告不完整，不能自动推断为已授权成功；不要回写旧批准或由作者伪签。

## F5 — P2：覆盖命令缺少目标分母，整天缺行只有人工传 expectations 才能发现

位置：`src/astock/phase1/pipeline.py:231–255`、`:282–287`；`__main__.py:128`。

默认 coverage 统计已有行，并检查已有行的身份、日历、冲突等问题。检查缺失 observations 的入口只有可选 Python `expectations`；CLI 不传这个参数，也没有把目标期间、上市宇宙、日历、报告期/行业规则转换为冻结覆盖目标。未知目标始终 BLOCKED 是诚实的，但“完整覆盖验收能力 PASS”尚缺关键软件路径。

独立场景：2025-01-03 已有开市日历、明确有效上市身份，但 daily 缺行。默认覆盖命令不产生 expected-missing finding；只有人工传入那条 expected observation 才出现 1 个 finding。现有缺口会在整日或整证券没有行时漏出默认报告。

修复：在公共入口接入可版本化的目标/期望清单或确定性生成器，保留目标 hash、来源、分母已知/未知状态、实际数、缺失/重复/未认证/有证据不适用数，按域/年/venue/security/episode 展开。日历、身份或状态未认证时明确 UNKNOWN，不凭缺行情推断停牌；缺报告/行业/规则证据同理。该能力先以闭合 fixture 验证，不要求这批虚构全量历史分母或发新请求。

## 不新增为独立阻断的事项

旧 402,060 findings 保留、UNKNOWN 日历不重发、2013–15 来源缺口、BSE HOLD、真实财务 vintage 不足和账号权限未验证均是已披露的真实数据问题；不能要求靠本次代码修复凭空消失，也不再逐件建立小 Gate。53.95s 完整保护扫描会限制吞吐，保留现有保护并测量即可，本轮不为性能单独暂停工程。环境变量配置 token 已在操作手册明确，本审查不将它与 `.env` 的使用差别列为阻断。文件命名、交付 HEAD 与实现 SHA 的文档差别也不单独要求重做。

## 一次完成的下一批与剩余进程

请执行配套合并 Prompt：一次修复 F1–F5，完成生产形状的离线链路、目标覆盖/全量候选计划及更新后的统一试点申请，复用已通过旧证据，一次全套/精确 SHA CI，一次交付。本报告不是新代码的预先 PASS 或真实请求许可。

通过该统一 Review 后，下一件实际工作是按获批范围连续执行试点并回收证据，不再逐接口询问。试点确定权限、cap/空结果/时间与来源语义后，形成或完善各域真实成员/预算与证据政策，再执行获批历史覆盖、增量/重建和最终准入验收。可压缩为三个工作包：**修复与离线就绪 → 真实试点与覆盖计划 → 获批覆盖与最终验收**。这不是承诺“三次交互一定结束”；现阶段不可能给出可信的最终全量请求数、天数，完整 vintage/历史来源是否可得仍要靠实际证据。

如原 2013–2026 目标确实存在无法补齐的历史 vintage 或来源空白，最后应集中提交一次范围决策，提供可证实的缩限研究产品与原目标 HOLD 两个具体选项，不能反复增加固定规模身份小批次或宣称 full Phase1 完成。

## 独立复现与证据位置

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/work/review_phase1_integrated.py`
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/work/review_phase1_production_shape.py`
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1-integrated-independent-review/independent-probes.json`
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1-integrated-independent-review/production-shape-probes.json`
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1-integrated-independent-review/application-check.json`
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1-integrated-independent-review/live-ci-verification.json`

所有变异只发生在审查者 scratch fixture/生产形状的模拟目录。此次审查真实行情/元数据/文献 HTTP 请求 0，原库 SQL 写入 0。GitHub CI 读取属于只读证据访问。
