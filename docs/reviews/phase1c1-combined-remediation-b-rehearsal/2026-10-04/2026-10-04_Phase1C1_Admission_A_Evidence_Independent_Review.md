# Phase 1C.1 Admission A Evidence Closure 独立审查

审查日期：2026-10-04。材料最终 SHA：`088b02febccd07f68ddcf2dc6d42613ba69e9d35`。新增实现 SHA：`b8c2bd81debebc6f7dce3804b08fe602f3b6a3fe`。上轮已审查基线：`90ced0bac3e305c0e994878645f455ceba4e8f5e`。

**本轮新增离线工程、上轮 F1/F2 纠正、材料一致性与保全验收通过。7 个 SZSE metadata 请求的有限计划可以接受，但尚无可执行的 live transport。10 份官方原文支持的有限事实已核对，其中一份规则的版本标注需追加校正。新增身份/DQ 批准仍为 0；Admission B 暂不能执行，Phase 1C.2 保持 CLOSED。**

本轮无须重新做已验收的 R1/R2/Admission A 离线工程，也不需要为来源标注单独安排修复 Gate。下一批集中准备安全 metadata live 实现、可独立裁定的有限身份候选及仍需人工/供应商资料的准确问题。真实请求留到该实现的 exact-SHA Review 和用户授权之后。

## 1. 分项裁定

| 项目 | 独立结论 | 边界 |
|---|---|---|
| F1 全量预算 | CLOSED | gross30126、verified reuse0、net30126；全部126复用才是30000；reserve0 |
| F2 最终审批入口/保全 checklist | CLOSED | Context 路径/bytes/canonical/实现及语义 pins 一致；最终保全已闭合 |
| 新 metadata 离线设计与实现 | PASS | 闭合 FakeTransport、managed writer、7成员/42行、原库不部署 |
| 官方原文及有限命题 | ACCEPTED_DOCUMENTARY_FACTS | 上市/更码/股东数量连续性/有限开市声明；不等于新的绑定或完整 session 认证 |
| 7 个 SZSE 请求计划 | PLAN_SCOPE_ACCEPTED | 准确范围、fields/contract/requestID/hash、最多7attempts；执行许可 false |
| 原库及历史材料 | PASS | 34 表、181raw、133EXACT；127193既有文件、244baseline tracked 文件保全 |
| 新 identity delta / DQ envelope | EMPTY / NOT_APPROVED | 新 binding=0、新 session=0；无新 Context 或 B 许可 |
| 生产 transport / 限速 / 账号权限 | NOT_IMPLEMENTED / NOT_PROVEN / UNKNOWN | 不允许由 fake PASS 推定 live 可用 |
| Evidence / bounded admission / full history | BLOCKED | 身份、endpoint、BSE、venue session、特殊资产与 NULL 等仍有缺证 |
| Phase1C.2 | CLOSED | 不回填、不重跑133，不执行策略或交易 |

新增冻结设计 hash：`b849469d6091718187ff6f0b09a35d952b60e4701874dc61c7dff17967952df5`。本次接受的是它的离线准备范围，不是未来 live 代码或数据批准。

## 2. 已关闭的 F1/F2

F1 的公开、私有提案、handoff 与纯函数一致：不提前扣除126候选，当前net30126；全部通过精确复用时net30000。start-to-start pacing 是 `(N−1)×1.25` 的下界项，当前37656.25秒，不能当作包含响应延迟的运行时间上界。额外分片、账号权限、真实session数未知；bounded7与future28annual calendar预算独立且均无执行许可。

F2 的最终 approval-request、primary index、handoff 均指向同一 `context-proposal-final.json`；实际 bytes/canonical hash、实现/设计/policy/input/resolver/delta pins全部核验。作者未填生产批准时间/ref/hash/license；原保全项为 AUTHOR_VERIFIED_PASS，并链接真实最终证明。旧材料完整保留，没有覆盖原请求或早期 Context。

## 3. 独立验证

| 核验 | 结果 |
|---|---|
| 新模块及已接受组件的针对性测试 | **46 passed，3.77s**；tests/conftest拒绝市场网络 |
| 最终SHA远端CI | **668 passed，4 warnings，953.57s**；foundation全部步骤SUCCESS，实际checkout SHA对齐 |
| 新私有索引 | 145 artifacts，80 canonical JSON hashes；逐actualbytes/size通过 |
| 最终审批引用图 | 220条引用、52个JSON材料，解析到实际文件及hash通过 |
| 最终作者ZIP | 78唯一成员，CRC及每个成员与本地源bytes相等 |
| 历史文件/源码 | 127193既有文件逐bytes保全；244baseline tracked保持原bytes，AGENTS仅授权追加 |
| 原库 | 实际34表有序行内容hash与本轮及既有基线一致；DBbytes before/after一致 |
| raw/receipt | 实际181raw验证；strict133VALID/EXACT，failure0 |
| resolver/Context | 原resolver、3episode/3code/12binding、旧133inputs/126outputs实际核对不变 |
| missing15 | 15原finding保留；30条bounded观察及另2条旧probe观察实际source逐项核验 |
| 合成metadata库 | 7exactraw/7sidecars/21events/42civilrows重新核验；ALREADY_VALID7，时间和DBbytes不变 |
| 官方原文 | 7PDF从原字节独立抽取、3HTML原字节解析；10个支持命题与原文hash核对 |
| 秘密扫描 | 当前本地凭据literal对145artifacts与ZIP78展开成员无命中；未打印凭据或用于请求 |

远端：[CI run 37173553085](https://github.com/liuyanfeier/AStockSystem/actions/runs/37173553085)。作者本地全套668passed、1warning、424.45s；writer guard修正前的中断日志保留。没有更改旧测试/政策来使验证通过。

原库 SHA256：`c687fc514a78ef8b68b6c89907b9932a42465d2b2cab5ae383647616287ca0e2`。

作者 ZIP SHA256：`b6b94ab207f1a87b167b1dc2f89beba6fb2cace8e79cc7e49612cf073f9457de`。

新增plan canonical hash：`fb2c0792fdb6548c5849df398a56206e52802ca4bfab78da6f4ca3cdf5553a35`。

新增plan membership hash：`1825fff72f718d90f2beb82e96d8a58936cabdf52217aae454e854670cb885c8`。

市场/provider请求0，原库数据写入0。本次协调锁按managed shared/read-only协议使用，没有绕过锁。文档HTTP与市场网络计数分开；独立文档网页读取没有调用市场API。

402246源行、15756旧finding、BSE248/31248cell矩阵和30126规模证明在上轮已逐项独立验证。本轮重核其原库/raw/完整账本/矩阵/合成产物的bytes保全，复用有效语义与恢复证明，没有重新制造账本或重跑stress。此前生产状态仍是192resolved/402054quarantine。

## 4. 新工程验收的具体行为

`admission_metadata.build_plan`固定7个SZSE窗口、POST origin、api_name、YYYYMMDD参数、四字段顺序、现有v2contract bytes/canonical hash与确定requestID。validate_plan拒绝重hash或未重hash的venue/date/fields/contract/license/budget/member变更。

capture入口先 require_writer。readonly或escaped连接即使已有COMPLETE且缺sidecar，也不能在磁盘补写。闭合fake transport复用已接受的durable claim/CALL_ENTERED/raw completion；未知调用不重发，重复reopen保留第一次时间。响应拒绝missing/extra/duplicate civil dates、错venue/字段/宽度、bool伪装整数、非法pretrade_date和sidecar篡改。

这些是结构、成员、存储与恢复安全证明。合成payload包含故意简化的is_open/pretrade_date，不能认证真实市场session。最小间隔目前是计划约束；生产pacing及HTTP调用尚未实现。未来live必须独立验证完整HTTP响应处理、one-attempt、停错、不重发、凭据保护和持久化证据；不能将FakeTransport改名即执行。

## 5. 官方事实与一处非阻断来源标注纠正

六份发行人PDF实际支持：000022组基本情况中的1993-05-05上市时间及本次A股发行；000043组1994-09-28上市及2019-12-16更码、股东股份数量不变；300114组2010-08-27上市及2025-02-17更码、股东股份数量不变。两份更码实施公告也通过独立网页读取核对：[000043实施公告](https://disc.static.szse.cn/download/disc/disk02/finalpage/2019-12-16/a5a3d55e-cc2e-42e6-91c1-ea98235594fb.PDF)、[300114实施公告](https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF)。法定发行人/股东连续性不能单独证明所有历史endpoint的双native表示或其去重规则。

两份原HTML支持：2013元旦休市、1月4日明确开市、1月5/6周末休市；当前2026日历页面明确9月25日休市、9月28日恢复。后者网站原发布时间未知，保持UNKNOWN。两份交易规则支持相应文本中的每周交易安排/公告休市及临时停市可能性；不能自动证明每个过去日期没有异常停市或直接认证previous_session。

**D1 — P2，来源版本元数据。** `document-claim-index.json` 的 `szse:rules:2023` 指向 `P020231230545235004039.pdf`。原文标题实际是《深圳证券交易所交易规则（2013年11月修订）》及修改第3.1.4条的决定；封面日期2013-11-30，基础规则正文写2013-08-05施行。2023是URL文件路径时间线索，不能当法规版本。

在新索引追加准确的source identity/rule version/notice date；区分文件内公告日期与网站首次发布时间，后者仍可UNKNOWN。原PDF及旧索引保留。源规则有效期及后续替代没有证明前，不能以它认证2020/2026适用规则。本次没有生产session批准，因此此项**不阻断当前离线工程与7请求计划验收**；与下一轮工作一起纠正，后续session使用前必须处理。

10份原文和每项限定事实的独立决定记录在 `private/phase1c1-admission-a-evidence-independent-review/independent-documentary-claim-decisions.json`。这是DOCUMENTARY_FACT裁定，不是approved-case-set或approved-DQ evidence。

## 6. 身份与日历为什么仍不能批准

case delta为空、DQ新增envelope为空、候选Context保留原133/126成员和resolver。15dossiers保留全部原key/raw及所有未批准状态。准确分母是**30条bounded133观察，另有2020-08-24旧probe的2条补充观察，共32条实际引用**；补充观察未混入133成员。

发行人资料增强了事实基础，但材料没有提出已满足官方代码区间/具体native/有限scope要求的新binding；普通386249行、BSEepisode/native/session、特殊资产及NULL等仍未闭合。当前因果certified0/unknown45，不构成PASS。不能在空提案上签出新的Context许可，也不能以COMPLETE或0 mismatch代替准入。

**可以进一步收缩待证命题。** 后续应分别评估“event当时官方有效的old-native有限观察”和“提前出现的新native回溯表示”。前者如能由真实issuer/episode/code证据及该endpoint的精确观察共同成立，可单独提EVENT_NATIVE子集；其他行继续quarantine，raw全部保留。R2规格允许explicit observed dates/raw scope，不强制先证明全历史统一alias。但只凭字符串或同价依然不能批准，作者必须写完整有限提案并指明实际依据/剩余冲突。供应商双native/overlap答复仍是回溯alias或重叠处置的重要缺口。

当前3组供应商clarification问题可以接受为未发送草案，不能当答案或批准。未经用户明确授权，不向供应商发送消息或上传私有证据。

## 7. 下一步集中批次

本次接受7请求计划的范围与离线设计。参数与字段的文档依据另经独立读取：[Tushare trade_cal文档](https://tushare.pro/document/2?doc_id=26)。文档积分要求不是本账号权限证明。下一轮直接准备**专用metadata live路径及全部离线安全验证/准确执行材料**；保留旧SSEguard与fake模块不变。此准备批仍为0API、原库只读；最终SHA独立通过并获用户对7请求的明确授权后，才能调用。

同批追加D1元数据校正，评估上述有限EVENT_NATIVE子集，准备3组具体供应商问题及尚缺资料。每组有充分依据便提出具体非空candidate；无法证明的给出缺口和取得方式。不要再次交只有相同BLOCKED分组的材料；也不为每个case增加人工Gate。

7次calendar取得只解决SZSE有限窗口，不能承诺结束BSE/普通历史身份/NULL问题。Admission B与Phase1C.2许可仍独立。下一轮Prompt：[专用metadata live准备与有限证据提案](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Metadata_Live_Preparation_Prompt_v1.0.md)。

有限计划裁定：[Phase1C1_SZSE_Metadata_Plan_Scope_Approval.json](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C1_SZSE_Metadata_Plan_Scope_Approval.json)。它的actual API执行许可为false，不是可直接调用的许可证。

审查 manifest：[Phase1C1_Admission_A_Evidence_Independent_Review_Manifest.json](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C1_Admission_A_Evidence_Independent_Review_Manifest.json)。本轮确认F1/F2 CLOSED、离线实现及有限计划接受；没有制造新case/DQ/Context批准或开放Phase1C.2。
