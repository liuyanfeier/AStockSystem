# AStockSystem：专用 metadata live 准备与有限身份证据提案

2026-10-04。可整段交给实现Codex。一次完成，最终统一Review，不逐小Gate/证券/URL停顿。

## 1. 基线与任务范围

请在 `/Users/yanliu/Documents/AStockSystem` 读取AGENTS、已批准R1/R2与UTC instant v2设计、writer lifecycle、上轮完整A/Evidence授权及：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-04_Phase1C1_Admission_A_Evidence_Independent_Review.md`。
- 同目录 `Phase1C1_Admission_A_Evidence_Independent_Review_Manifest.json`、`Phase1C1_SZSE_Metadata_Plan_Scope_Approval.json`。
- `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-admission-a-evidence/2026-10-04/final-handoff.json`、最终index/plan/原文/15dossiers/候选。
- `/Users/yanliu/Documents/AStockSystem/docs/remediation/phase1c1/admission-a-evidence/concrete-design-v1.md`及已验收的fake metadata代码/测试。

最终基线088b02febccd07f68ddcf2dc6d42613ba69e9d35；离线实现b8c2bd81debebc6f7dce3804b08fe602f3b6a3fe；冻结设计hashb849469d6091718187ff6f0b09a35d952b60e4701874dc61c7dff17967952df5。F1/F2已独立CLOSED，46针对性测试和最终668CI通过。已有30126离线规模、旧完整ledger/raw/receipt证明直接复用。

用户转交本指令后，授权本批次必要的最小live准备实现、离线/mock transport验证、文档取证与候选交付。**本批次真实市场/providerAPI预算0**。当前7请求计划被接受的是scope/design，其实际运行许可仍false。新代码最终SHA须独立Review通过，且用户另行明确授权7请求后，才能实际执行。这个边界来自原A授权和已冻结metadata设计，不因本指令转交而解除。

检查HEAD/worktree保护已有工作。原库及全部raw/curated/批准/Context/generation/audit不变；managed原库只读。旧SQL001–010、SSE133请求guard、原bounded133/126、fake-only接口、冻结政策/hash保持不变；新实现用独立文件/协议/存储。禁止133重跑、credential permission probe、额外API、B执行、Phase1C.2/策略/交易。

## 2. 先冻结专用 live 设计，再实现与连续验证

在新版本中补具体设计：精确HTTP请求、完整响应捕获、attempt状态/时间、immutable证据与恢复、错误停止、运行许可校验和未来外部证据集成。不要修改已验收fake设计来声称原本已有live能力。设计与实现同批交付，原库不部署。

沿用已接受 `szse-metadata-plan-v1.json` 原bytes/canonical/requestIDs/membership，不改7窗口、fields、contract或maxattempt。运行授权独立manifest绑定计划hash、未来reviewed live代码SHA、设计hash、实际批准ref/time及用户许可；保持原plan execution_license=false，不能通过改true再重hash授权。

专用模块只处理这7个trade_cal请求。缺任一许可证/pin/显式live开关即在网络前拒绝。旧通用fetch/retry不能作为绕过入口；不试连、不先请求账号权限、不使用Tushare SDK的隐藏重试。token只在获准实际运行时本地装入请求认证，不进入plan/hash、日志、exception、sidecar、public或ZIP。

HTTP必须固定POST到 `https://api.tushare.pro`，api_name=trade_cal，exchange=SZSE，精确YYYYMMDD参数，ordered fields=`exchange,cal_date,is_open,pretrade_date`。关闭自动redirect与自动retry，明确timeout与代理/transport配置，避免一条逻辑请求暗中多次送出。账号权限未知；正式获准请求出现权限/HTTP/格式错误时按已冻结停止规则处理，不额外probe。

持久化PLANNED/claim/RUNNING/本地CALL_ENTERED后才进入可能联网的调用。每member最多1attempt，最多7actualattempt；失败与不确定也消耗attempt。created/claim/call/finish/retrieved/available/verification分别记录真实时间，CALL_ENTERED不是远端receipt；不回填旧时间。start-to-start间隔至少1.25秒，并在进程重启、时钟异常及并发启动时仍安全；不能只在循环里sleep而无持久化检查。

unknown/超时/崩溃/部分响应停止且不自动重发，不通过换runID/UUID重置同一exact请求预算。恢复只核对已经存在的准确immutable证据并完成未完成登记，不再次发POST；是否继续尚未触及的其他members须按实际冻结stop/reconciliation规则说明并受独立运行授权约束。

实际HTTP完整body与code/msg/data处理分开：保存被批准的原始响应bytes和必要安全HTTP元数据；解析data/typedtable是另一产物，分别hash，不能重新json.dumps(data)后叫完整原始response。秘密扫描拒绝凭据流入可交付产物；错误信息保留sanitized状态，不将请求token/错误body打印出来。

新metadata只落ignored隔离路径，managed store不迁移原库。明确raw、manifest、request/contract/wire、metadata sidecar、response完整性、source时间与完成receipt的精确绑定。最终成功必须由实际immutable证据及全部必要登记/sidecar共同成立，零manifest/fakeobject/孤立sidecar/错误hash不成功。部分文件/登记崩溃不能触发重发；重开后验证exactbody/schema/来源/状态后恢复。重复验证不重写首个终态与原始取得/可用时间。

7窗口expectedcivilrows为5/5/5/8/11/5/3合计42。保留contract字段/types/自然键、唯一日期与精确集合、0/1及pretrade_date格式/先于cal_date检查；合法结构不等于venue session事实。缺失、重复、额外/跨window、provider错误code/未知完整性/截断必须保留证据并停止，不加分页或补请求。不要根据live结果放松类型/容差；实际不符合冻结contract时停并交付差异。

新metadata未来只作为versioned external evidence，旧133/126输入不变。为未来DQ/Context给出精确request/contract/raw/bytes/knowledge时间/finite-session引用方式；当前不写入原库、不执行DQ、不签session批准。确需schema扩展先冻结新版本，合成证明，交Review。

## 3. 用离线测试证明实际执行路径

使用无网络mock HTTP transport，测试新专用代码真正的请求构造/调用/持久化路径，不仅测试plan返回值。保留repo网络deny。

测试至少覆盖：无许可/错SHA/错plan/错contract/不在7members在HTTP前拒绝；exact请求body与auth隔离；成功7members重开后不重发/不改times；并发writer及readonly/escaped拒绝文件发布；一次HTTP权限错误、redirect、timeout/unknown、partial/malformed、secret-bearing错误各自停止不retry；持久化pacing；file/sidecar/registration/completion故障恢复；fakeobject/zeromanifest/tamper/orphan/改变source阻断；terminal重复与跨run预算不重置。

断言实际mock transport调用计数和磁盘SQL结果。选代表边界复用已验收lifecycle/immutable故障证明，不再重跑30126stress或为每个日期重复同一测试。新实现必要回归后按仓库要求最终一次全套/doctor/contracts/secret scan与exactSHA CI。

## 4. 同批收缩身份待证命题，追加来源校正

**D1元数据。** 保留原PDF/旧index；追加将 `szse:rules:2023` 对应bytes标识为2013年11月修订版与2013-11-30文件内决定日期。正文base rule写2013-08-05施行。URL的2023路径不是规则版本；网站首次发布时间未知可以保留UNKNOWN。新session使用必须核对适用/替代区间，不把旧rule当当前rule。

**有限EVENT_NATIVE提案。** 复用15dossiers与实际30bounded观察，另2条2020-08-24probe观察单独索引，不混入133members。分别审查当日官方old-native与回溯new-native：有真实issuer/episode/code证据加该endpoint精确观察支持的old-native可以提出独立有限子集，其余行继续quarantine、全部raw保留。R2规格允许observeddate/rawscope，不要求先证明全历史统一alias；但相同字符串/名称/价格不构成独立事实。不得用选择oldnative的理由默默批准newnative或去重。

对每个有依据的候选写exactrawUUID/zeroordinal/event/dataset/episode、官方当时code、source/evidence/hash、表示类型、排除成员、旧审批复用方式、新delta/mergedresolver/policy/Context及预期影响。新增binding引用已有episode时保留旧metadata；新事实使用真实当前knowledge时间。明确只读估计不是generation/DQ PASS。没有充分依据就准确写缺哪项，而不是把所有old/new现象合并成同一种通配阻断。

**供应商问题草案。** 000022、000043、300114三组分别询问：指定pre-switch日的daily为何同时返回old/newnative；是否同一底层bar的别名；哪些精确官方说明/有限选择与overlap规则适用。草案绑定30bounded与2probe的独立成员hash，列已证与待证命题。没有用户直接授权，不发送消息或上传材料；供应商答复不能由代码/作者猜出。公开FAQ/官方文档在原授权内继续读，失败保留来源局限。

普通386249、BSE248、689009/T600018及其他未证scope继续明确缺口，优先共同来源，禁止5930×4默认crawl。无需再次生成402246完整ledger/15756finding账本或运行相同B。旧192批准与1374范围外裁定原样保留。新身份子集无法成立不妨碍完成metadata实现和其全部离线交付。

## 5. 一次交付及停止点

新private/public版本交付：冻结live设计、最小新增代码/协议/schema/必要CLI、mock实际路径证据及tests、旧保全、sanitizedlogs、exact7plan原hash、待运行license模板及准确未来run命令、D1追加校正、有限candidate delta/mergedresolver/DQ/Context或明确空集与缺口、供应商问题草案、最终review/manifest/ZIP/handoff/CI。

所有实际reviewer生产批准字段与运行许可保持null/false，不凭作者self-check签发live或case许可。不改已批准源码/hash以迎合proposal。最小runner不得接收任意provider/dataset/window来扩成回填入口。

最终状态 `BOUNDED_METADATA_LIVE_PREP_REVIEW_READY`。记录本批真实API0、原库写入0、原133未重跑、B未执行、Phase1C.2 CLOSED，给最终SHA与全部hash/路径并停止。该批独立Review和用户7请求授权齐全后，后续获准执行只取这7metadata、准备可审查session证据；它仍不批准身份、B或Phase1C.2。
