# Phase1C.1 Combined Remediation 与 B Rehearsal 独立 Review

审查对象：`45554a142a8e8d3e1b6cb0147db537bc88d1b55e`。日期：2026-10-04。

**本轮工程、D1 来源修正和有限 15 条身份候选通过。真实 matched 批准包与生产形状 Context 已生成，并在审查方原库副本完成实际 SQL 导入、注册、幂等及四时区重开验证。现在具备执行正式 Admission B 有限追加的条件，无须再做一轮 Admission A 或修复批次。**

本次 B 范围是 3 个 daily binding、15 个单观察日官方 code 区间、15 条精确 raw 观察；不新增 episode。执行仍为零 provider API，只使用既有 raw。全局数据准入仍 BLOCKED，Phase1C.2 CLOSED。用户转交随附执行 Prompt 后，在本次批准范围内完成原库追加与验收。

## 1. 分项结论

| 项目 | 独立结论 |
|---|---|
| D1 来源版本修正 | CLOSED；准确识别2013年11月修订，不声明2020/2026适用 |
| 专用 exact-seven metadata live 工程 | PASS；实际许可仍 false，账号权限 UNKNOWN |
| 有限身份候选 | APPROVED_LIMITED15；3 bindings、15单日 code 区间、0新 episode |
| 候选 B 演练 | PASS；真实两代126输出、守恒、DQ和四时区重开 |
| 新生产形状批准材料 | PASS；实际 import_delta/register/幂等/父133-126/四时区验证 |
| 正式 Admission B | LIMITED15_READY_FOR_USER_EXECUTION |
| 全局 DQ、历史覆盖、全量准入 | BLOCKED |
| Phase1C.2 | CLOSED |

未发现阻断上述有限 B 范围的新增工程问题。metadata 的结构/传输/持久化证明不等于实际日历认证；本轮没有真实请求或新增 session 批准。

## 2. 有限事实与独立身份裁定

新增000022原始公告及独立抽取文本已核对。公告明确旧000022/200022改为001872/201872、2018-12-26启用，以及上市法人主体和股份类别/数量连续性。只裁定其 A-share 有限观察；B-share、供应商全历史 alias 与去重均未批准。[发行人实施公告](https://static.cninfo.com.cn/finalpage/2018-12-26/1205690369.PDF)

000043和300114原官方上市、股份类别及更码材料在上轮已独立核对，本轮重验原 bytes/hash 保全，复用有限事实。新结论组合官方发行人/episode/code 证据与该 endpoint 的实际观察；不是仅凭同名或同价，也没有把代码公告外推成无限历史映射。

| native | dataset | 获批 event dates | 精确观察数 |
|---|---|---|---:|
| 000022.SZ | daily | 2013-01-04、07、08 | 3 |
| 000043.SZ | daily | 2013-01-04、07、08 | 3 |
| 300114.SZ | daily | 2013-01-04、07、08；2020-08-21、24、25；2021-11-12、15、16 | 9 |

每个 binding 只适用于批准文件列明的 dataset/raw UUID/zero-based ordinal/event。官方 code 用15个单观察日半开区间，不认证未列日期。已有3个 episode及12个 binding/192条观察的审批 metadata 保持不变。

15条镜像 new-native 保持未批准与 quarantine；另2条旧probe不加入原133或新delta。没有批准其他 endpoint、factor、reference exception、BSE transition 或新的 session。可用时间和决定时间是本次真实 Review 时间，仍为 CURRENT_RECONSTRUCTION/OBSERVED_CAPTURE。

## 3. 独立验证

| 验证 | 实际结果 |
|---|---|
| 当前 HEAD/worktree | exact45554a1、clean；没有修改实现仓库 |
| 远端 exact-SHA CI | 736 passed、4 warnings、969.07s；checkout和全部job步骤实际核对 |
| 独立针对性测试 | 96 passed、11.34s；live、snapshot、delta及metadata回归 |
| 作者最终包 | 6375实际artifacts逐bytes/size；最终176 ZIP成员、CRC和源bytes一致 |
| 最终有效材料引用图 | 309引用、76 JSON解析到实际hash；归档draft manifest不作为激活依赖 |
| 历史保全 | 127354既有文件、255基线tracked逐bytes；AGENTS仅授权追加 |
| 原库 | 实际34表有序内容hash不变；181raw逐manifest/sidecar核验；strict133VALID/EXACT/0failure |
| 有限观察 | 15 selected+15 excluded mirrors+2 probe共32条真实raw引用逐项核对 |
| 合成metadata实际产物 | 7 raw bodies、typed tables、manifest、sidecar、receipts闭合；28events、42rows；最小实际mock start间隔1.345947s |
| 候选隔离代 | 两代每代126输出；逐source402246行守恒；207resolved/402039quarantine |
| 两代与四时区 | 实际重新选取、重建校验logical/schema/source/quarantine；Shanghai/UTC/NewYork/Kathmandu均一致 |
| 旧192行 | 全部值保持相同；新增15行与候选精确集合一致 |
| 新批准包 | 新真实delta/DQ/Context在审查方副本实际import/register及幂等，四时区重开验证；旧Context仍有效 |
| 凭据/调用 | 作者包和展开ZIP当前凭据literal扫描无命中；仓库decoded scan与远端CI核对；独立数据/批准验证provider、HTTP、socket均0 |

[实际远端CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/37185824437)。已验收且未改变的30126规模和旧完整source/finding账本复用，不重新生成。

原库 SHA256：`c687fc514a78ef8b68b6c89907b9932a42465d2b2cab5ae383647616287ca0e2`。

作者最终 ZIP SHA256：`0a2286ec0c959771a8c2559197eb5437e148953b02d0a59b73e22fef58361865`。

## 4. DQ 结果及新的批准材料

隔离代每代402147 findings，真实local/batch gate均BLOCKED。相较旧代移除30条finding，新增45条：15个MISSING_DAILY_FACTOR和30个CROSS_DATASET_MISSING_OR_PROVIDER_ONLY。63个session仍未认证，因果certified0/unknown60，不能用0 mismatch宣称PASS。

身份解除部分隔离后，因子/其他endpoint缺口被更明确地暴露。这不撤销已闭合的15条有限身份事实，也不允许其进入回测或自动开放Phase1C.2。

批准包重新生成实际 reviewer ref/time、正式 delta、完整old+new resolver、DQ envelope及 `fixture_only=false` Context。原1374条精确pre-BSE范围外处置在新DQ中重新授权，保留原approval ref/decision time/evidence hash和原始文件；不是改写原审批。63条session原样保留NOT_CERTIFIED。

review_ref：`2026-10-04_Phase1C1_Combined_Independent_Review@45554a142a8e8d3e1b6cb0147db537bc88d1b55e#ADMISSION_B_LIMITED15`。

实际 approved_at/knowledge_as_of：`2026-10-04T08:13:46.338396+00:00`。

| 正式批准对象 | canonical/domain hash |
|---|---|
| case delta | `39211d73b8308db26130e7ae3ea21c2e81479e4a0620924a1820857ac5a59609` |
| DQ evidence | `8a910a43ef415f7463d825668b576df237152c69d17921a59eb7e1a446f73d2d` |
| resolver | `837d06d825d6852b1a9125ef6f1656876fa535339d84a2dfd3626bba33df36d6` |
| Context | `470017335c3e7fd9f69480b35e2ac3012ceea2892a3f94706fdfcfb5af262475` |
| inputs | `b471998495a4a4f6d2d55796b3fa084c383b32c53f3af91eb37da9afba245a08` |

Context implementation SHA固定最终45554a1。pipeline内仍使用已批准R2 design/policy/UTC协议 pins；combined design和本轮官方证据绑定在独立approval manifest中，不能把combined design hash替换进旧pipeline字段。所有必要文件hash由manifest列明。

生产批准的hash与fixture不同。审查方已证明真实生产形状材料可在当前库副本导入、注册、精确解析15行并重开；执行方仍须对自己新副本生成两代验证，再追加到原库。不能直接搬fixture Context/generation/approval。

## 5. 直接进入有限正式 B

将随附 [有限B执行Prompt](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Admission_B_Limited15_Execution_Prompt.md) 交给实现Codex：核验真实批准包，当前原库备份、新匹配副本两代验收、原库有限追加、真实DQ/重建/保全，完成一次统一交付。无需重新研究这些获批事实或制作另一轮待审批模板。

本轮metadata live工程已通过；它的真实7次请求尚无用户许可。有限B不依赖这些新请求，保持API0即可执行。将来用户明确授权exact7后，用匹配的独立许可证获取有限metadata；实际session事实仍需裁定。

剩余普通历史身份、BSE episode/native、镜像alias/overlap、因子/其他endpoint、各venue session、特殊资产和NULL缺证，统一留在后续证据任务中。不要为相同输入再次提交Admission A，也不要把这15条有限追加包装成完整历史准入。
