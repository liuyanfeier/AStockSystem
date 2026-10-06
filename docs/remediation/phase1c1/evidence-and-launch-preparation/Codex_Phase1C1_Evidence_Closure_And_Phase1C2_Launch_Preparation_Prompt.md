# AStockSystem：一次完成剩余共享证据、生产运行准备和具体准入提案

本指令由用户明确转交后，授权完成下面一个联合批次，内部依赖步骤连续推进，最终一次集中Review。它不授予任何市场/provider/metadata/calendar/mapping数据API调用，不许可原库写入，不许可启动Phase1C.2或重跑133请求。新增直接官方/provider公开文档HTTP取证总上限24次（含redirect/失败，每次实际请求计数；搜索页面不作为证据），按独立新预算台账计数；旧失败metadata attempt不重置。不得发送邮件、客服、群聊咨询。

允许新版本候选材料、必要独立生产运行模块和合成/隔离离线验证。Phase1C.1已验收的工程与有限45正式应用保持CLOSED；新增模块为未来全量运行准备，不重复修复旧importer或重做finite45。旧171个accepted文件保持不变，新文件追加；若实现确需修改已接受核心文件，先给具体必要性和影响，继续其他不依赖的工作，统一交Review，不默默放宽旧guards。

**0. 准确基线和可直接复用结果。**

项目 `/Users/yanliu/Documents/AStockSystem`。起点干净SHA `222cf660878da3d8fa67bfbce9f896731e83769f`；若只有后续文档提交，明确记录diff并核验171 pins不变，禁止把未知源代码版本当作已接受。原库hash `30953a9ff2622c85724794b268bc878ea2494684d6faccd5ab0fc5cbb378eb81`，无WAL，以managed共享只读锁读取。

先读AGENTS和以下准确输入，保留原bytes，不覆盖旧交付：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-05_Phase1C1_Finite45_Formal_Execution_Independent_Review.md`，同目录`private/phase1c1-finite45-formal-independent-review/`三份独立结果JSON及handoff。
- `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-finite45-formal-execution/2026-10-05-v1/final-handoff.json`、`review-manifest.json`、`primary-artifact-index.json`、`complete-row-set-evidence.json`及精确引用；原8份finite45审批和171 pins从实际`approval-manifest.json`读取。
- `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-admission-a-evidence/2026-10-04/full-backfill-plan-v2.json`和`reused-proof-index.json`，既有生命周期/30,126规模及恢复证明。上轮独立Review中的F1/F2已关闭，不重新修正原预算算术或索引模板。
- `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-remaining-evidence/2026-10-04-combined-v1/`的`identity-group-dossiers-v3.json`、`remaining-identity-groups-v3.json`、`group-native-endpoint-event-matrix-v3.json`，以及原完整source和BSE矩阵引用。旧remaining-gates-v3记录的是过去状态，须用本轮实际正式增量叠加，不照抄已关闭factor/cross-endpoint/事务缺口。
- 固定metadata store `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-admission-metadata-live-v1/`和旧license。DBhash `91a2c5d20df935795e0e2b736175af13fb6b7b5f6092231a9e96975fd30b9ece`，1 consumed / 6 unattempted / 0 responses；不retry、不换store、不改旧license实施SHA。

本轮只读基线：3 episodes / 18 codes / 24 bindings / 252 observations，3 Contexts / 6 generations / 6 audits，181 raw；当前正式Context `5bb73a54850e4328b8cfc0305185a77d001bf7841984bdd5e73ab2190898256c`。source402,246 / resolved252 / quarantine401,994，DQ401,994identity+63session+3reference price。原207+新45已经独立接受，不重新import/register/build/audit。

**1. 共享证据按组补齐，同时交准确的剩余获取申请。**

以既有完整账本叠加当前finite45作为唯一分母；不重新生成不变的数十万行账本，使用原完整ledger+精确delta的active chain即可。每个组列命题、适用成员集合/hash、原文版本/有效期/获取时间、具体页段、已有支持、反证、仍缺最小事实、受影响规则和新增候选数量。

优先已有原文，读其内容，不能只复制旧结论。公开取证先列去重清单，24次预算内集中获取能覆盖最多成员的官方公告/发行主体历史列表/provider端点语义；遇403/空内容只能保留denial，不能当作事实。未发送的provider问询标UNSENT，不能当回复。无需为每个case或网页中途等待人工批准。

- 普通历史386,249行：按法律issuer/shareclass、listing/termination episode、event-date official code和endpoint native共同证据建立可规模化membership规则。优先能覆盖批量成员的权威历史名录/事件记录，不逐raw行爬网页；现代stock_basic、同数字code、同名字、旧resolver成功均不证明全部历史连续性。已有5,584 carry项是证据调查分组，不能自动转成获批identity。
- BSE13,030行：复用248主体/31,248cell完整矩阵，分开6先行与242迁移调查范围；逐成员有明确官方旧/新code事件、episode连续性、endpoint原生表示和BSE venue日历依据。两种迁移不可推断合并，403不能填空。1,374已有pre-BSE范围外处置继续原批准，不重签、不转identity成功。
- 历史code/alias57行：42 endpoint aliases和15 daily mirrors仍不批准；值相等不证明alias。按endpoint实际文献提出精确候选，证据不足维持隔离。
- unknown1,224 / special60：复用既有CDR689009与provider STK冲突、T600018及code reuse调查；证券后缀和数值相似不构成资产类型/episode证明。
- 新3条MISSING_REFERENCE_PRICE：000022.SZ，2013-01-04、07、08，stk_limit pre_close原NULL；daily已有10.17、10.03、10.15。只寻适用历史端点的权威缺失/字段语义及明确处理依据，保留源NULL。不得直接复制daily、填0、放宽tolerance或关闭规则。没有支持则保持EVIDENCE_REQUIRED；新文档不能自动变成全历史NULL政策。

候选决策只能PROPOSED，生产review_ref/approved_at为空、execution_license=false。不要以早期finite审批时间替新事实签字。能支持的组一次生成候选case delta/member hash/merged resolver/DQ/Context请求；不能支持的组只交具体获取计划，禁止制造可执行假批准。仅对新候选使用受控fixture-only预览，有必要才运行一次，不为未变化输入再做相同两代。

**2. venue calendar与失败metadata的可执行处置方案。**

复用当前63 session matrix，逐SSE/SZSE/BSE/date链接独立calendar、is_open及真实previous；不能把SSE复制到SZSE/BSE，也不能把previous_candidate改certified。没有开市前BSE交易所session依据时，准确区分前身市场与BSE范围。完整2013-01-01至2026-09-30目标calendar需求单列，63有限episode sessions不代表全市场日历完成。

只读诊断固定metadata失败日志与网络配置，不调用API试token/积分/连通性，不打印凭据。CALL_ENTERED不证明远端收到，TRANSPORT_UNKNOWN_NO_RESEND不证明provider拒绝。旧1 consumed永远保留；6 unattempted不能凭旧license补发。

若现有公开资料不足，联合交`evidence-acquisition-plan-proposal.json`：每个拟取得的venue/date/metadata或历史identity源、参数和fields、contract、真实目的、完整分母、exact request/member hashes、计划预算/限速/每member最大1attempt、停止/未知调用/保存路径、原133不重复证明。明确与旧FAILED member的关系；禁止重新命名同logical request以绕过NO_RESEND。所需旧成员reconciliation或新的授权/实现兼容性写清，执行license仍false。该申请是可直接Review的实际计划，非“以后再研究”的问题清单；本批不执行。

**3. 一次完成未来生产执行入口的必要离线准备。**

先查实际路径。已接受`admission_offline.py`只接收FakeTransport，旧TushareClient.fetch_slice锁定133；不能把这两者称为已能启动全历史生产。如果没有其他已验收真实全量入口，新冻结独立版本full-backfill设计并追加最小必需模块/CLI/独立存储schema，保持旧171文件和bounded133/126协议不变。不得直接调用旧私有_fetch逃过scope guard。

新版本须清楚区分：未批准plan、测试fixture、实际reviewed plan、用户运行授权。默认execution_license=false；需要exact reviewed implementation/design/contract/member set/预算和实际user authorization才可能触达真实transport。真实路径关闭所有自动重试，TLS验证、无环境代理/redirect、至少1.25秒start间隔；不能靠参数切换进入无预算通用fetch。原store与固定metadata store在本批仍只读，合成模块不得迁移进原库。

持久化plan不计attempt；claim/CALL_ENTERED先durable，再进入transport；FAILED/UNCERTAIN不自动重发；receipt必须引用可校验immutable body/raw manifest，0manifest/fake UUID/缺文件拒绝COMPLETE。关闭重开、同成员重复、换run逃预算、预算超限、许可/pin冲突、tamper/orphan必须拒绝。真实完整body、typed/source/hash/sidecar和explicit COMPLETE membership需可审核；call-entry不能冒充remote receipt。若复用既有组件，说明实际复用接口和保持不变的证据，不复制整套已通过恢复系统。

只在隔离/合成环境用闭合fake HTTP响应验证新生产入口分支和真实持久化顺序；所有真实socket/API预算0。测试必须覆盖实际新runner路径，不能只再次测试旧FakeTransport。做代表性非空正常、cap/截断/empty、permission/schema失败、transport未知、publication/registration/promotion故障和reopen/resume；复用原30,126完整membership与故障证明，不重复制造旧空partition压力产物。旧bounded模型不能直接扩大数组。明确typed curation是否仍等待事实批准；raw immutable capture能力不等于已获研究数据准入。

完整事实未取得时仍完成不依赖它的runner离线安全验证；不能伪造已认证日历、账号权限或全历史IO性能。若严格生产设计需要新schema/contract/version，把差异和必要范围写进本次候选设计，不改旧SQL001–010、v2hash/order/time/NULL/DQ/identity规则。

**4. 形成匹配证据的全量计划及一个明确的启动申请。**

更新`full-backfill-plan-v2.json`为新提案，旧版保持：2013-01-01至2026-09-30，六market datasets，venue/calendar/universe前置、CURRENT_RECONSTRUCTION / OBSERVED_CAPTURE边界，historical PIT eligibility=false。不得自行改成年份子集、3issuer范围或raw-only策略后把原全目标写PASS；若确有分阶段方案能加快，作为明确范围/验收变更提案，说明仍未解决部分与风险，由独立Review及用户另行裁定，本批不执行。

逐endpoint列真实contract/fields、cap、分页/分片/截断识别、权限说明与本账户UNKNOWN区别、历史可用期、empty/suspend/ST缺证处置。未取实际calendar前只能给依据明确的上下界，不能以全部civil days充当真实session。既有30126是synthetic上界；当前126仅reuse candidates。对最终未来exact参数/fields/contract及immutable lineage逐项核验，只有实际通过才能扣除reuse。gross/reuse/net、calendar/identity前置、分片、reserve分别计算，不含未知额外分片、不预扣126、不隐含retry额度。

形成首个拟执行批次与其后全量批次的依赖图：exact members/预算/已证适用范围、未证事项、stop conditions、checkpoint/reconciliation、磁盘/备份预算、source保全与可选择COMPLETE条件。首批仍execution_license=false，无实际capture；方案不能将未来回填后的全历史完整性、年度真实rebuild或coverage/causal终验写成准入前已完成。

为每个准入条件交当前已关闭/本批候选可关闭/外部EVIDENCE_REQUIRED/未来回填后验证状态。只在计划所执行的确切范围前置全部有据时提出READY_FOR_PHASE1C2_AUTHORIZATION；否则BLOCKED，说明最小外部取得动作及具体request plan，不重复提交同一个不变BLOCKED结论。

**5. 一次最终交付和Review边界。**

新ignored目录建议`data/private/phase1c1-evidence-and-launch-preparation/2026-10-05-v1/`，公开报告对应`docs/reviews/phase1c1-evidence-and-launch-preparation/2026-10-05/`。保存实际新来源、完整成员集引用/增量、候选case/DQ/Context或明确未能形成的理由、metadata只读诊断、evidence-acquisition精确申请、runner冻结设计/新代码pins/离线验收、full-plan/首批请求提案、完整remaining checklist。

原库hash/34旧行集/历史文件和固定metadata终态保持；复用已接受的原库两代及raw/strict133证明，主要核验未变保全，不为本批重复已完成finite45。来源、设计、候选、implementation/final SHA、tests/CI、bytes/canonical/member hashes和active索引一致，保留全部旧版本。credentials扫描包含literal/编码/压缩Parquet解码；full row/raw/DB/ZIP均ignored。新增实现运行有意义针对性回归，最终一次完整离线suite和exact-SHA CI；仅文档变化则复用171pins对应既有测试，不为每个内部步骤重复全套。

作者状态`EVIDENCE_AND_PHASE1C2_LAUNCH_PREPARATION_REVIEW_READY`。最终一次提供SHA、CI、公开报告、private ZIP/manifest/handoff，分别报已闭合工程、候选证据、仍缺外部事实、实际document请求数、数据API0、原库写入0、原133未重跑、Phase1C2 CLOSED。缺证不阻止其他独立工作交付；需要API或真实生产部署时，只交精确申请，不执行。

STOP只在最终集中独立Review及后续匹配的用户运行授权处。没有再次的finite45正式应用，没有逐case人工Gate，没有把本批候选或新runner离线PASS当作全量执行授权。
