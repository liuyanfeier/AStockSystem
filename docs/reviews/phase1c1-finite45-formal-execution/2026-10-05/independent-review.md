# Phase 1C.1 Import Atomicity / Finite45 独立 Review

**本批工程修复与实际候选预览 PASS，原 P1 已关闭，没有新的阻断性代码 finding。** 有限 9 bindings / 45 observations 的事实审批通过，并签发匹配最终实现的真实审批包。原库正式应用尚未执行；全历史数据准入与日历仍 BLOCKED，Phase 1C.2 CLOSED。

最终审查 SHA：`546b57bcbb9af9e8b703a9f8edbfd1986f83bca4`。作者预览执行 SHA 为 `e43b521b7b276661b12684378fdbfbe73e8a949f`；两版的生产模块 bytes 相同，最终提交只补充两个未签字合成 fixture 的生成顺序和交付文档。工作区干净。日期采用用户所在地 Asia/Shanghai，2026-10-05。

| 范围 | 独立判定 | 依据 |
|---|---|---|
| 导入顺序与事务完整性 | PASS，原 P1 CLOSED | 写前拒绝不兼容顺序；INSERT/readback/full payload/hash 校验在同一事务内 |
| 两条导入路径、回滚、兼容 | PASS | 独立运行 119 个相关测试全部通过；覆盖四表回滚、重开和四时区 |
| finite45 实际转换预览 | PASS | 126 物理输出、402,246 完整处置；252 resolved / 401,994 quarantine |
| finite45 有限事实批准 | APPROVED EXACT SCOPE | 新独立审批和生产形态 SQL 副本验证；不批准其他 identities/aliases/sessions |
| 原库正式 finite45 应用 | NOT EXECUTED | 原库仍 207 resolved / 402,039 quarantine，审批不等于已落库 |
| 全历史数据准入 / Phase 1C.2 | BLOCKED / CLOSED | 未认证 calendar 与大量历史身份链仍缺证；本批不授予回填许可 |

## 1. 原 P1 的修复是真正的事务修复

`import_approved_cases` 写入前检查每个 binding 的 observations 是否满足持久化回读顺序 `(UUID.int, integer ordinal, event date)`。不兼容输入明确拒绝，没有重排已签字 payload，也没有改变 v2 canonical semantics。

完整 old+delta resolver 的 canonical payload 和 v2 hash 在 INSERT 前构造；事务内 INSERT 后，SQL readback 的完整 payload 和 hash 同时核验，成功才 COMMIT。直接核心调用与 `import_delta` 新增路径均受保护。外层删除的提交后比较已移入核心事务，不是取消验证。严格重复仍检查 approval、原 raw 和最早捕获时间。

独立运行以下五个模块得到 **119 passed in 203.54s**：`test_import_atomicity.py`、`test_admission_delta.py`、`test_resolver_time_integrity.py`、`test_reconstruction.py`、`test_reconstruction_regressions.py`。其中新回归覆盖合法 raw 倒序在 INSERT 前拒绝、两条路径在 INSERT 后 hash/readback 故障时四种身份表完整回滚、关闭重开、同 payload 幂等、UUID 符号边界和四时区一致性。

两个旧 test fixture 仅在未签字生成阶段排序，之后才计算合成 approval；业务事实和既有断言未删除。没有变更生产 signed data、SQL001–010、时刻/微秒/NULL、v2 member/order/hash protocol、原合同、DQ tolerance、metadata guard/transport。

我通过 GitHub connector 独立获取最终运行的 job 和实际日志，确认 checkout 正是 `546b57bc…`，locked dependencies 成功，**753 passed、4 warnings、821.44s**，离线步骤全部通过。[最终 SHA CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/37215567429)。作者本地 753 passed、1 warning 是另一份实际运行，不能与 CI warnings 数混写。独立 Review 没有重复运行已经通过的全套 753。

## 2. 126 个真实预览输出与完整行集通过核验

核验每个物理 Parquet 的 logical hash、schema hash、Context metadata、lineage 和完整 dispositions。126 输出与原批准 Context 的 output inputs 集合相同，未添加任何 raw 或修改原133输入。逐行核验全部 402,246 条处置的 raw ID、ordinal、唯一性、状态及剩余 quarantine facts/reasons。

独立从 raw 重新转换所有 27 个受增量影响的 dataset/date 输出，结果与作者物理输出及 quarantine 完全一致；没有为了 Review 再生成同样两代历史 generation。

- 实际 source402,246 / resolved252 / quarantine401,994。
- 原207行所有 value、identity 与 NULL hash 不变。
- 新增恰好45条、9 bindings，raw UUID/零基ordinal/date/row hash 和事件日官方 code 相符。
- v5→v6只改变九个未批准 observation lists 的顺序，集合、first-observed时刻和其他事实字段不变。
- 42个未证实端点aliases和15个daily mirrors仍quarantine。
- `dv_ratio`、`dv_ttm`、`pre_close` 各3个raw NULL保留。
- 新 COMPLETE generations=0、新 DQ audits=0；预览为 `CANDIDATE_TRANSFORMATION_VERIFIED`，没有声称已经关闭生产finding。

Scope hash：`fefb1760a8b79f217243b6415eedc33129ba1d1e033c1049a7cd11e7bdb87907`。

文献依据复用上次独立核验并再次 hash 保全的发行主体/事件日 code 和 provider 端点原文；本次没有重新采集文献或数据。适用结论仅为有限 `EVENT_NATIVE / CURRENT_RECONSTRUCTION / OBSERVED_CAPTURE`，不构成 provider-wide alias、完整历史 code 区间或 historical PIT 批准。

## 3. 真实独立审批已经生成并验证

为避免继续停在“候选审批待准备”，本次签发新的有限45实际审批。审批时间为真实 UTC `2026-10-05T02:04:22.195893+00:00`，implementation/reviewed SHA 均固定最终 `546b57bc…`。旧审批、v5/v6 proposals、作者内部 fixture approval 和失败历史保持原样。

Review ref：`2026-10-05_Phase1C1_Import_Atomicity_Finite45_Independent_Review@546b57bcbb9af9e8b703a9f8edbfd1986f83bca4#FINITE45`。

| Pin | 实际批准值 |
|---|---|
| Case delta | `fcaddc045a24f2c502c2f1e8b63a310d8aa460f0a35d8eaf4e28ee75aeef8805` |
| Merged resolver | `31beb026b143497bd001a1b1058c289d47422c1464f8d6c5ded149fa407bea91` |
| DQ evidence | `67333e31c420b759605ddf7a5ebb061fbd45e2ada86ee898b7aee3628248d61f` |
| Production-shaped Context | `5bb73a54850e4328b8cfc0305185a77d001bf7841984bdd5e73ab2190898256c` |

实际审批目录：[phase1c1-finite45-independent-approval](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c1-finite45-independent-approval/approval-manifest.json)。包含 approval、case delta、merged snapshot、DQ evidence、Context、decisions 和独立 SQL 验证。

已在 reviewer 工作区的原库一致副本中使用真实批准 import/register，fixture_only=false、无 allow_fixture；首次 IMPORTED，严格重复 ALREADY_VALID，45个精确解析成功，计数3 episodes / 18 codes / 24 bindings / 252 observations。两个旧 Context 保持有效，新 Context 关闭重开和四时区 resolver/payload 验证通过。该副本未创建 COMPLETE generations 或执行新 DQ。

DQ只重新授权同一1374个已获批pre-BSE范围外事实以适配新Context，引用保留原envelope/hash/ref/time；63session继续未认证。不新增asset/NULL/alias/日历裁定。

**有限事实批准不等于原库部署授权。** 当前 execution license=false；将附带的有限正式应用 Prompt 明确交给执行者，才授权那一次原库追加。该 Prompt 的内部备份、正式副本、原库应用、两代生成和验收可连续执行，无需逐小 Gate 询问。

## 4. 原库、失败记录和交付保全通过

独立核验517个交付文件、4个external数据库、443条active引用、ZIP518成员的CRC/唯一性/逐成员bytes。ZIP SHA256：`0d8035c3ff290b1ce6c4f074b4f9e25e1bdf80220f1d9dff42ce0911351185a8`。

136,599个历史基线文件和2,283个旧失败isolate文件保持原bytes。167个原accepted implementation pins中163个不变，合法变动恰好是两个生产importer模块和两个未批准测试fixture文件；新回归模块和设计单列。当前材料和archive按凭据literal及base64/hex/URL编码形式扫描通过，未公开凭据。

原库 SHA256 `27aabd6143d977decefefb8eb1f1b2b9e66ee29c14045d9df284871bcecf065f`；旧 Context `470017335c3e7fd9f69480b35e2ac3012ceea2892a3f94706fdfcfb5af262475` 保持原样。原库还是15 bindings/207 observations、2 Contexts/4 generations/4 audits、181 raw manifests。strict133独立审查为 VALID/EXACT、133 checked、0 failures。

固定 metadata store保持 hash `91a2c5d20df935795e0e2b736175af13fb6b7b5f6092231a9e96975fd30b9ece`：第一个成员 FAILED、1 consumed attempt、6 unattempted、0 response/0 civil rows，远端delivery/账户权限UNKNOWN。旧license继续固定fd1d1b5，禁止替换SHA、resend、reset或新建store绕过终态。

Reviewer原库写入0、provider/市场/文献请求0；真实网络动作仅GitHub只读CI核验。原limited15验收继续有效。

## 5. Phase 1C.1 如何收尾，下一阶段还差什么

**Phase 1C.1 的工程修复线可以按已验收范围收尾，不再因本项进口事务问题增加修复轮次。** 本次限定45已可进入正式应用，附带审批和执行Prompt已准备完整。

不能把工程收尾写成全历史数据准入通过。即使45全部正式应用，source仍402,246，identity quarantine仍401,994；其中386,249普通历史行、13,030 BSE transition行、1,224 unknown identity/asset行、60 special行及剩余历史code/alias范围需要其实际证据链。已获批1,374 pre-BSE out-of-scope可以继续按原处置，不应重复作为“等待新身份”的未决项。45只补足有限三端点scope，不能整体放行普通/BSE主体。

63个venue/date sessions仍未认证；失败metadata没有响应支持可用于补齐日历。本次审批和正式应用均不允许再次采集。新执行的factor/cross-endpoint finding变化只能由实际audit决定，不能提前宣称90个finding关闭或总DQ PASS。

进入 Phase 1C.2 实际数据请求至少还需：确切 venue calendar/predecessor 证据、计划覆盖成员的历史identity/native范围处置、匹配适用范围的新版准入裁定及全量plan/API预算授权。原规格允许工程完成且数据BLOCKED，并明确要求Phase1C.2另行批准；不能以本批测试/有限批准替代这些条件。

下一步是完成[有限45正式应用和工程收尾 Prompt](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Finite45_Formal_Execution_And_Engineering_Closure_Prompt.md)，一次交正式执行验收。剩余共享外部证据按完整分组台账处理，不再重新开发已通过的importer或重复做同样审批模板；证据不足继续标明EVIDENCE_REQUIRED。当前不启动Phase1C.2。
