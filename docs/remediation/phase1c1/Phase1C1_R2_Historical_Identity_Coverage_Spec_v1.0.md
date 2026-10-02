# Phase 1C.1-R2 — Historical Identity & Coverage Remediation

规格 v1.0 · 2026-10-02 · 状态：DESIGN READY / LOCKED UNTIL R1 FINAL REVIEW PASS。

依据：[完整演练证据](https://github.com/liuyanfeier/AStockSystem/blob/2aba10fc143a8b1975b00b7a2a965cd1465942a7/docs/reviews/2026-10-01-phase1c1-review.md)、[旧resolver与rebuild](https://github.com/liuyanfeier/AStockSystem/blob/2aba10fc143a8b1975b00b7a2a965cd1465942a7/src/astock/data/slice_curate.py)、[旧DQ规则](https://github.com/liuyanfeier/AStockSystem/blob/2aba10fc143a8b1975b00b7a2a965cd1465942a7/src/astock/data/slice_dq.py)，以及引用对话的全量 REVIEW。本规格提出调查和证据要求，不预先裁定历史证券身份或异常原因。

## 1. 入口与范围

只有 R1-G3 的 exact SHA 获得独立 **R1 FINAL REVIEW PASS**、对应 CI PASS、真实133 receipt验收成立，并且用户明确授权 R2-G0，才可开始 R2。本文件现在只交付设计，不构成执行授权。

本轮只处理同一133-request batch、原7 slices/21dates和已有早期证据。不增加市场API调用，不重跑probe、stock_basic、bse_mapping、日历或任何行情。允许只读官方/供应商文档调查；不调用带token接口、不下载新的证券列表/映射/行情数据冒充文档调查。若需要新增数据才能确认，登记 EVIDENCE_REQUIRED，保持隔离与BLOCKED。

不得重写 accepted identity/venue records、旧snapshot、raw、generation0/1、旧DQ报告、旧migrations/reviews。采用新版本、追加证据和独立派生context。当前身份重建不是历史PIT知识；不增加策略、信号、回测、组合、券商或下单。

## 2. 原始问题账本

下表为已核对公开演练报告的基线，不是本次新做的真实验证：

| 项目 | 基线 | R2必须回答 |
|---|---:|---|
| source rows / generation | 402,246 | 新context是否完整守恒，逐source row处置是什么 |
| resolved / quarantined | 394,580 / 7,666 | 每一新增resolved行依据哪条证据/绑定 |
| NO_IDENTIFIER_MAPPING | 1,284 | 三个daily代码及未知limit资产逐案处置 |
| OUTSIDE_IDENTIFIER_INTERVAL | 5,008 | provider回溯代码与venue区间失败分别解释 |
| interval诊断子类 | 4,515 before-code-start；493 before-venue-start | 不能把493全部解释成改码问题 |
| PRE_BSE_LEGACY | 1,374 | 留作旧venue证据/隔离，不伪造BSE开市前交易 |
| daily未映射三个代码 | 15 rows | episode、重组/退市、复用、provider身份 |
| ERROR flags | 2,512 | 1,285 unresolved traded +1,226 coverage +1NULL case |
| REVIEW flags | 13,244 | 稳定台账、阻断属性、证据状态，不整体降级 |
| causal相邻pairs | 64,678 | 新resolved集另报覆盖，不强求pair数不变 |
| BSE官方切换 | 6 pilots /242 remaining | 2025-05-06与2025-10-09区分；不得全套用10月日期 |

5,008不是5,008个证券；2,512不是唯一异常数；DQ与quarantine、coverage可能重叠。台账提供flags计数、source rows计数、unique security/episode/date计数及交集，不通过减法宣称修掉重复异常。

## 3. 语义模型

至少拆分三层：

1. **Security/listing episode**：证券稳定ID与某次上市/挂牌、venue、资产范围；公司、证券、代码不能互换；重组、借壳、转板、代码复用不自动合并。
2. **EXCHANGE_CODE**：官方证券代码及真实 `[valid_from, valid_to)`；六pilot与其余改码按官方事件证据；venue区间单独成立。
3. **PROVIDER_NATIVE_IDENTIFIER**：供应商某endpoint在某次capture/表示版本下，用什么原字符串表示历史证券。它可以回溯使用新代码，但不能延长官方代码或venue区间。

推荐新增 provider binding表，不原地改变旧 `identifier_type='ts_code'` 的语义。逻辑字段（物理名称在R2-G0确定）：

```text
binding_id / binding_version
provider = tushare
dataset_scope = 一个明确dataset；没有证据不使用 wildcard
native_identifier = 原样字符串
security_id / listing_episode_id
event applicability = [event_from,event_to) 或显式已观察日期集合
representation_scope = capture/raw object set 或 capture版本/检索时间区间
representation_kind = EVENT_NATIVE | RETROSPECTIVE | UNKNOWN
evidence_ids / source_raw_object_ids + source_row_numbers
first_observed_at / available_at / decision_at
knowledge_basis = CURRENT_RECONSTRUCTION
decision_status / reviewer_decision_ref / supersedes_binding_id
```

没有证据不能填“全历史有效”区间。只有三个日期的观测，不得自动覆盖中间和此前所有日期；可用显式observed dates + raw object scope。未来新capture或endpoint语义漂移默认UNKNOWN。

证据记录区分：官方exchange事件证明、供应商文档陈述、既有raw观测、分析推断、独立批准。官方新旧code mapping不能单独证明endpoint在过去返回新code；raw见到新code不能单独证明它必属某security。必须组合真实证券/episode证据和该endpoint的观测绑定。

knowledge_as_of与event_time、retrieval_time分开。新绑定在R2才获知，available_at取真实可用时间；不塞回旧batch的knowledge_as_of。相同event_date在不同知识时间可以有不同解析结果，旧解析必须可重现。

## 4. Resolver契约

建议 `resolve(provider, dataset, native_identifier, event_date, capture_context, knowledge_as_of)`。输出security_id、episode_id、venue、binding/evidence IDs、basis，或明确quarantine reason。参数不能省略dataset后回退到所有endpoint共享alias。

顺序：精确native string校验 → 当前知识时间已知版本 → dataset/capture scope → event applicability → 单一security/episode候选 → 独立venue/episode区间 → 显式provider exchange/asset字段一致性 → resolved。

官方代码解析是另一条查询路径。provider新code在官方旧code期间可映射到同一security，但exchange_code_at_event仍是官方旧code；不得把native ts_code改写成旧code。native identifier只在带scope的provider层有效，不因此宣称官方早已改码。

同scope/event/capture两个候选，即使security_id相同但episode证据冲突也阻断；不能first-row-wins。names、digits/suffix猜测、自动去T前缀、以价格相近推同一证券一律禁止。`T600018.SH`继续NON_NORMALIZED_IDENTIFIER隔离。

对于BSE开市前记录，2021-11-12不是BSE上市交易证据。若证据证明它属于其他历史venue，独立建episode但本轮BSE A-share准入仍OUT_OF_SCOPE/PRE_BSE_LEGACY；没有证据继续quarantine。provider `.BJ`后缀不能创建BSE venue。before-venue-start的493rows逐案审查，不整体放行。

## 5. BSE evidence与DQ拆分

R2-G0先从现有raw列出每endpoint、slice、event_date、retrieved_at、native code、相关official pair的观察矩阵。只公开聚合与少量已公布案例，全部行级证据在private。

保留旧Phase1B `stock_st 2025-08-13` 返回 `835305.BJ /839680.BJ` 的证据；若私有raw不在执行环境，标NOT_AVAILABLE。不能从daily的RETROSPECTIVE推断stock_st也RETROSPECTIVE。

分别测试：

- 官方exchange code确在自己的effective_date切换、venue不冲突，6/242集合按已有官方证据核实。
- provider native representation符合当前dataset/capture binding；允许新code在切换两侧相同，前提是明确RETROSPECTIVE证据。
- 两侧bar解析为同security/episode，source lineage完整，作为identity continuity；价格走势不能证明身份。
- 事件日是否相邻session必须有该venue的calendar basis，否则price continuity/causal session判断NOT_CERTIFIED。

现有 `bse_switch_identifier_unchanged` 基于两侧raw ts_code相同判ERROR的规则在新context中改为以上语义规则；原规则/旧报告保留。不得仅把ERROR改为REVIEW而不给新证据和测试。缺任一侧bar为NOT_OBSERVED，不是连续性PASS，也不触发补请求。

## 6. 三个历史identifier和未知limit资产

分别为 `000022.SZ`、`000043.SZ`、`300114.SZ` 建case dossier，禁止在规格里预填其公司/继承关系。每案包含：

```text
现有raw dataset/date/row引用与原native值
官方listing/termination/restructuring/code-change事件
证券与公司关系、是否是同一security、listing episodes
code reuse检查与有效区间
已有stock_basic缺失现象及原因：CONFIRMED / UNKNOWN
provider表示证据、知识时间、冲突来源
拟新增binding/episode与影响行集合
结论：VERIFIED_BINDING / EVIDENCE_REQUIRED / CONFLICT / OUT_OF_SCOPE
```

未确认的current stock_basic omission原因保持UNKNOWN。不得因为“现代列表没有”删除历史universe，也不得直接接到现存同名公司/后继代码。三个代码分案Review，一案通过不批准其他两案。

NO_IDENTIFIER_MAPPING中余下limit identifiers需同样检查显式asset_type/exchange和来源定义；不能从六位数字猜股票、债券、CDR等类型。已明确非STK的行继续可追溯OUT_OF_SCOPE，资产UNKNOWN保持隔离。

## 7. Coverage与delist规则

覆盖键为 `(security_id, listing_episode_id, venue, trade_date)`，再分dataset。禁止用当前active stock list定义历史universe。把身份失败导致的“假缺bar”与真实未观察bar分开，identity修复后重新计算expected/observed集合。

先确定universe与venue session证据，再描述observation，最后做裁定。推荐coverage记录：

```text
universe_basis / episode_status / venue_session_basis
observation = OBSERVED_BAR | NO_BAR
identity_status
disposition = VERIFIED_IN_SCOPE | EXPLAINED_FULL_DAY_SUSPENSION |
 VERIFIED_OUTSIDE_EPISODE | VERIFIED_OUT_OF_SCOPE |
 BOUNDARY_REVIEW | UNEXPLAINED_MISSING | SESSION_NOT_CERTIFIED
evidence_ids / decision_ref / local_gate_impact
```

先标OBSERVED_BAR，不能因date≥provider_delist_date就遮掉真实bar。官方终止事件与bar相互矛盾是CONFLICT；不能修改区间消除冲突。一个coverage键有一个主disposition，允许多个supporting flags，计数须可重建。

full-day suspension需要同证券、同日、已解析的S及明确全天语义；盘中停牌不解释缺全天bar；S/R同日或全天停牌仍有bar保留冲突/REVIEW。stock_st空表不能证明无ST，未开通接口或早期数据不足另列证据缺口。

`provider_delist_date` 保持unclassified元数据，直到官方事件和provider文档支持其语义；拆分last_trading_date、termination_effective_date、provider_reported_delist_date。不要统一执行 `effective_to=delist_date+1`，不要删掉delisted securities。不用稀疏21dates建立全供应商约定；缺证的boundary不计“已解释”。

对于1,226基线coverage flags，生成旧finding→新处置映射：identity修复恢复bar、充分证据停牌/episode边界/范围外、仍无法解释。没有证据不得归为已解释；未解决项仍blocking。

## 8. 689009.SH / 2021-11-12

逐dataset查existing raw、schema、asset_type、exchange、daily/stk_limit对应行及原NULL位置；官方上市/产品资料与供应商字段语义用于独立确定资产范围和NULL是否允许。名称和代码数字不作证据。

三种可能结论：本轮A-share范围内且字段必需→保持ERROR；有确切证据属于范围外或该字段在该产品/日期明确not-applicable→带单案证据的规则；证据不足→仍BLOCKED。原raw/NULL均保留，不从daily补pre_close，不填0，不扩大0.011容差。数值差异、MISSING_REFERENCE_PRICE、NOT_APPLICABLE分开，不能把NULL与numeric mismatch混为同一桶。

单案not-applicable规则必须限定dataset/asset/episode/date或证据适用范围，并独立Review；不可演变为所有stk_limit NULL自动豁免。

## 9. Calendar与causal audit

现有7calendars全部SSE，本轮禁止获取新calendar。允许使用既有可信官方文档证明具体有限窗口的其他venue session，须说明证据与scope；没有证据则保留SSE basis / NOT_CERTIFIED，不能假定SZSE/BSE共用所有session。

previous_session查询使用venue/episode/date，跨未知session、跨gap、跨episode重置segment或判not-certified，不能用SSE预交易日替所有venue。分别报告certified pairs、provisional SSE-basis diagnostics、excluded/unknown pairs；不把停止测试称作0错误PASS。

保留因果链 `scale_t=scale_(t-1)*close_(t-1)/pre_close_t`；factor仅独立audit。固定price 0.011、causal 0.011 percentage points、factor `0.011+100*0.011/pre_close`，新增身份后pair数可变，但旧scope差异逐项解释；不使用latest_factor qfq，不改变历史前缀。全venue calendar认证仍是以后Phase1C.2前置。

## 10. 新派生context与rebuild语义

旧batch冻结的identity hash和knowledge_as_of不改。新 `derivation_context` 明确引用：parent_batch、parent_generation、raw_input_set/hash、capture_plan/hash、baseline_identity_hash、new provider bindings snapshot/hash、episode/venue overlay/hash、curation spec/version/hash、DQ policy/hash、knowledge_as_of_R2、代码SHA、审批证据。

新知识不塞进旧snapshot。raw.available_at/retrieved_at保持原capture时间；identity binding/newdecision可用时间独立记录。输出metadata保持CURRENT_RECONSTRUCTION与OBSERVED_CAPTURE，并加入derivation_context_id/identity_binding版本等必要lineage；不能标HISTORICAL_PIT。

旧generation0/1精确rebuild仍使用旧resolver/spec，必须继续可复现。R2新增派生generation使用新context，允许逻辑hash不同，但每项差异必须来自批准identity/spec/policy变化。不能用旧 `--rebuild` 比generation0，把hash mismatch关掉，或直接修改旧snapshot绕过FROZEN_INPUT_CHANGED。

同context、相同代码/spec/inputs的两次重建仍要求全部logical hashes一致；包括typed schema、单位、usage、raw行、native值和语义绑定。排除新运行UUID/出版时间等非逻辑字段；不得排除真实语义字段来求相等。

## 11. 出版、隔离和append-only审计

R2-G4为本轮新增最小完整generation机制，先synthetic测试，R2-G5才接触真实派生输出：

1. 固化expected object set：133raw全部验证、126非calendar request输出；每source row恰一种处置。
2. generation/context state：PLANNED→BUILDING→COMPLETE，故障可BLOCKED；状态事件追加记录，current state可由事件推导。
3. 每输出staging/new-only文件、lineage，checksum后DB事务登记；expected key `(context,generation,request_id)`唯一。
4. 中途失败重启：只重用经验证同context exact object；未登记文件为orphan，验证后按明确协议登记或保留隔离，不按文件存在自动成功。
5. 126expected全部存在且通过logical/schema/source守恒后，事务登记complete manifest/promote。DQ选择显式完整generation，禁止 `max(generation)`选到半代。
6. COMPLETE表示派生集合完整，不表示data accepted。publication不得删除旧代、覆盖旧文件或修改旧binding。

新增quarantine版本行至少包含raw_object_id FK、zero-based raw_row_number、dataset、event_date、native_identifier、context/generation、reason、evidence refs。新行从实际raw/sidecar验证；旧SQL quarantine行缺row_number时保持legacy，不能由顺序猜或按字符串重复匹配随意补值。新generationresolved+quarantine逐raw row守恒。

不再UPDATE旧 `dataset_date_audit`。新增curation quality和batch acceptance audit记录，包含audit_id、generation/context、policy、被测codeSHA、时间、finding集合hash、local_status、batch_gate_status、supersedes/ref。重跑追加新audit；旧结论可引用但不能改写。REVIEWED不代表独立人工Review，也不能替代Gate授权。

## 12. Finding台账与数据门

稳定finding key使用rule/dataset/date/raw_object+row或episode key；记录旧新reason、severity、evidence、decision、blocking属性。新audit需列出新出现的finding，不能只统计基线减少数。对全7,666 quarantine rows、2,512error flags、13,244review flags进行可追溯归类；不要求无证据清零。

局部检查PASS但batch BLOCKED可以同时存在：local_status展示dataset/date实际质量，batch_gate_status表示整体准入；不把126局部表全改BLOCKED掩盖质量信息。

数据门规则：

- **BLOCKED**：任一receipt/schema/lineage/冲突错误；unexplained in-scope coverage；未决身份影响traded行；必要reference price缺失未裁定；必需session/episode证据不足。
- **PARTIAL**：无硬错误，但待Review的非关键观察/未证实覆盖或边界；不得作为已接受研究输入。
- **PASS（仅bounded reconstruction）**：本轮要求的范围全部证据充分、每项blocking finding已按独立批准结论解决、全lineage与rebuild成立；仍不是historical PIT或全历史ready。

规格不承诺R2能PASS。离线证据不够时，正确交付是完整台账+明确EVIDENCE_REQUIRED+data BLOCKED。工程/模型可Review PASS，但不能冒充data admission PASS。无论R2结论如何Phase1C.2均CLOSED。

## 13. 验证矩阵

必须覆盖：同event不同knowledge时间；daily retrospective/stock_st event-native互不回退；未知endpoint/新capture未知；官方旧code区间不变；pilot5月与remaining10月边界；pre-BSE无venue；同code不同episode/复用；多候选冲突；T前缀拒绝；missing/native strings保留；明确资产类型与UNKNOWN隔离。

coverage测试：旧名单survivorship偏差；bar与delist metadata同时出现；最后交易日与termination不等；S全天/盘中/SR冲突；identity修复消除假gap；NULL case仍不补值；无BSE calendar证据为NOT_CERTIFIED。

publication测试：第k/126对象文件写入、sidecar、DB登记、完成promotion各处故障；跨进程锁；orphan处理；显式完整generation；重复resume不双登记；未知context拒绝；旧审计行/文件不变。

rebuild测试：旧context仍复现；新context两次独立构建126/126逻辑hash相等；新旧差异台账完整；typed empty partitions；resolved+quarantine精确source row集合；decoded secret扫描继续通过。

真实验证只在R2-G5：133exact receipts、181raw保留、旧252curated保留、新126objects/source402,246完整处置（范围外行仍保留quarantine/明确处置，不隐性丢掉）；源行数量不同先调查。旧因果64,678pairs作为基线，新集按venue证据另报。不把合成fixture通过写成真实历史结论。

## 14. 严格Gate与交付

| Gate | 范围 | Review关注 |
|---|---|---|
| R2-G0 | 只读证据账本、官方资料/缺证调查、具体schema/context设计 | R1 final批准；scope；逐case证据；不能应用映射 |
| R2-G1 | provider/episode模型、resolver、migration、synthetic测试 | dataset/capture/knowledge隔离；旧snapshot不变；不用真实新绑定 |
| R2-G2 | 证据充分且获准的具体bindings/episodes，追加私有版本 | BSE各endpoint、493venue cases、三个历史代码、未知limit；缺证仍隔离 |
| R2-G3 | coverage/delist/NULL/calendar和BSE DQ规则，合成测试 | 先固化policy再看新真实DQ；不调容差；append-only/local-batch设计 |
| R2-G4 | context/generation publication、quarantine/audit新schema、synthetic恢复 | 旧rebuild保留；partial可恢复；显式完整代；不跑真实派生 |
| R2-G5 | 仅existing raw的离线新派生、同context二次rebuild与DQ | 零请求、126完整、source守恒、旧代不变、全finding处置 |
| R2-G6 | 汇总脱敏证据、未来前置清单，最终独立Review | 分开工程/证据/data结论；Phase1C.2 CLOSED |

每Gate一个聚焦commit交付后STOP，exact SHA CI和独立Review后才授权下一个。真实绑定/episode记录是私有追加数据，不能force-add供应商数据；公开commit提供模型/导入校验与脱敏review，handoff包含私有input摘要hash，不提交整份证券列表。

R2-G2只应用此前Review明确批准的case；新增发现需要单独裁定，不由实现者自行补alias。证据不足不妨碍记录UNKNOWN与继续获批的有限工程任务，但不得跳过Gate或把缺证映射投入resolved结果。

最终artifact建议 `docs/reviews/YYYY-MM-DD-phase1c1-r2-final-review.md`，包含每GateSHA/CI/批准、旧新context、baseline→newfinding台账聚合、remaining blockers、原样NULL处置、未证实calendar范围、PIT限制、0新市场调用证据、raw/旧代保留、双重rebuild结果。实现者标REVIEW_READY；独立reviewer给Engineering/Model、Evidence completeness、Bounded data admission三个判定。

Phase1C.2未来前置至少包含：真实网络lifecycle精确语义、全规模generation恢复验证、各venue calendar、历史identity/episode与scope证据、historical PIT研究使用边界、新全量plan/API预算另行批准。本规格不提供全量运行prompt。
