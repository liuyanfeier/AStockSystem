# AStockSystem：一次完成导入事务修复和 finite45 隔离预览

用户明确转交本指令，即授权实施这里的一项 P1 修复、必要测试和 finite45 候选隔离预览。连续完成内部依赖步骤，最终一次交付独立 Review，不需要为内部步骤分别等待批准。本批真实 provider API 预算 **0**、原库写入 **0**，不得重跑 133 个请求，不得启动 Phase 1C.2，不得向其他人或 provider support 发送咨询。

本指令授权修复上批固定代码边界暴露的具体 importer 缺陷；它不批准新生产 identity/session 事实，也不恢复上批失败日历执行。当前 limited15 正式 B 验收仍有效。

## 1. 起点和必须读取的输入

项目 `/Users/yanliu/Documents/AStockSystem`，干净起点 `fd1d1b5638a0194ae30adcc59f06fc1ab4a25f62`。读取当前 AGENTS、managed writer/transaction 生命周期，以及：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-04_Phase1C1_Remaining_Evidence_Combined_Independent_Review.md`。
- 同 outputs 下 `private/phase1c1-remaining-evidence-independent-review/independent-artifact-validation.json`、`independent-data-validation.json`、`independent-postcommit-reproduction.json`、`independent-primary-source-verification.json`、`independent-targeted-control-tests.json`。
- `/Users/yanliu/Documents/AStockSystem/data/private/phase1c1-remaining-evidence/2026-10-04-combined-v1/final-handoff.json`、`primary-artifact-index.json`、`review-manifest.json`。
- 上述私有目录的 `case-delta-proposal-v5.json`、`current-resolver-proposal-v5.json`、`context-proposal-v5.json`、`dq-proposal-v3.json`、`finite-endpoint-evidence-closure-v1.json`、`cross-endpoint-exact-candidates-v1.json`、`fixture-preview-blocker.json`、`fixture-internal-delta-v2.json`。
- `src/astock/data/admission_delta.py`、`src/astock/data/reconstruction.py`、`src/astock/data/provider_identity.py`，现有 admission/time-integrity/lifecycle 测试和冻结 `docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md`。

先记录并保全以下基线，所有数据库操作使用项目 managed lock，禁止绕过锁：

| 对象 | SHA256 |
|---|---|
| 原 `data/warehouse/astock.duckdb` | `27aabd6143d977decefefb8eb1f1b2b9e66ee29c14045d9df284871bcecf065f` |
| 固定 `data/private/phase1c1-admission-metadata-live-v1/metadata.duckdb` | `91a2c5d20df935795e0e2b736175af13fb6b7b5f6092231a9e96975fd30b9ece` |
| 上批失败 isolate 的 `isolated-root/data/warehouse/astock.duckdb` | `ec32a43385df4c864fa054be0bc0b736a767552e2a47aaffab79286172a54890` |

失败 isolate 在 `data/private/phase1c1-combined-remediation-b-rehearsal/2026-10-04-remaining-evidence-v1/`；不得删除、修正或继续往该库写。原 Context hash 必须保持 `470017335c3e7fd9f69480b35e2ac3012ceea2892a3f94706fdfcfb5af262475`。原 source402,246 / resolved207 / quarantine402,039，原身份15 bindings/207 observations、2 Contexts/4 generations/4 audits 不变。

如果起点或基线不同，保留差异证据，完成独立读取，停止依赖该基线的写操作；不要覆盖其他人的变更或自行换审批 pins。

## 2. 修复一项 P1，保留既有协议

已确认触发：合法 observations 按 event date 排列，SQL `ORDER BY ALL` 回读按 raw ID/ordinal/date 排列；v2 保留 observations 顺序。`import_approved_cases` 先 COMMIT，`import_delta` 随后才检查 merged hash，故抛错后记录仍在，重试报冲突。

采取下面的最小兼容实现，不做新一轮协议或 SQL schema 迁移：

1. 在核心导入写路径明确校验 incoming binding 的 observations 顺序能按当前持久化读取规则往返一致。当前顺序是 `(raw_object_id 的规范 UUID 排序, raw_row_number 的整数排序, event_date 日期排序)`，须用测试确认与 DuckDB 实际 `ORDER BY ALL` 一致。合法但不兼容该顺序的输入，在任何 INSERT 之前稳定拒绝，给出清楚错误。不要在已签字 payload、canonical resolver 或 importer 内悄悄重排。
2. 在写入前构造并验证 old+delta 的完整预期 v2 resolver，保留原成员所有 metadata。
3. 把 INSERT、SQL readback、完整 merged resolver/hash 核验放在同一个现有 managed transaction 内，核验成功才能 COMMIT。任何校验、readback、hash 比较或注入故障必须回滚所有本次新增 episodes/codes/bindings/observations。事务结果返回已经在事务内核验的 hash，不依赖提交后第一次验证来发现失败。`import_delta` 与直接 `import_approved_cases` 调用均应受到保护，避免仅修外层而留下另一条写路径。
4. 保持已兼容增量首次 `IMPORTED`、严格相同 payload 再次 `ALREADY_VALID`；重复仍执行原有审批/raw 完整性验证。冲突、部分增量、tampered approvals、错误 raw ordinal 继续 fail closed。

可以提取很小的共用 helper；主要改动限于上述 importer 和相关测试。新写一份短设计说明解释“原顺序语义不变、只拒绝不能往返的输入、事务内验证”，不要先发一个 G0 等待。原 frozen addendum、旧 Review/审批/Context/payload bytes 保留。

禁止修改 `R2_RESOLVER_UTC_INSTANT_V2`、aware time 规范、微秒精度、resolver/Context/hash membership、observation 顺序语义、已有 SQL001–010、原133合同、DQ规则/tolerance、identity/alias/asset含义或 metadata live guard/transport。禁止删除 hash 比较、异常转 PASS、覆盖旧成员、更新旧批准时间或将 fixture approval 当成生产批准。

## 3. 一组有意义的事务与兼容回归

先复现再修复，保存必要前后证明，不为每个小改动重复全套。

- 两个真实存在于合成 raw 的 observations 倒序：新实现写前拒绝；关闭重开后完整身份表 rowsets 不变。核验 episodes/codes/bindings/observations，不能仅比较条数。
- 合法持久化顺序：首次导入成功、hash 等于预期、重开后相同；严格重复 `ALREADY_VALID`，原成员 metadata 不变。
- 事务内 INSERT 后注入完整 hash mismatch/readback 异常：所有新增身份表 rollback，重开仍无增量；若真实增量含 episode/code，验证其也回滚。分别覆盖核心导入与 delta 路径，避免只测 preflight。
- 保留 partial/conflict/approval tampering/raw ordinal/FK 的失败控制；无需复制每个已有测试。
- 对已获批192+15的实际旧 payload、数据库 readback 和 pinned Context 做只读兼容比较，证明原 resolver/Context bytes/hash 不变。不得重导入生产来“验证”。
- 在合成 managed store 对相关导入/回读 hash 做 Asia/Shanghai、UTC、America/New_York、Asia/Kathmandu 检查；相同时刻的不同 offset、微秒、null、observation 顺序语义仍符合既有 v2。原 lifecycle/rebuild 四时区规模证明可复用，只有相关兼容验证需重跑。

通过 targeted tests 后继续隔离预览，不停在等待工程 Review；若事务不完整或兼容破坏，先修到通过。

## 4. finite45 新候选版本与一次实际隔离预览

不重新抓取资料，不重新研究15个获批daily事实。复用已核验9 bindings/45 exact observations 的官方/端点/raw证据；3个既有发行主体 × adj_factor/daily_basic/stk_limit，端点各15，新增 episode/code 为0。

本批可以把**未批准的新候选**制作成新版本，其每个 binding 的 observation 次序显式满足持久化顺序。保存原v5 proposal/失败 isolate 原 bytes；新版本明确记录次序变化、旧新 hash，以及 observation **集合和所有事实字段未变**。不得改 native/date/raw ID/零基ordinal/row hash/first-observed时刻或扩大区间。正式 proposal 的 review_ref、approved_at 仍为空，execution_license=false；内部演练只能使用明示 `CANDIDATE_REHEARSAL_ONLY` 的 fixture metadata 和真实本次时间，不冒充 reviewer 签字。新 source pins/最终SHA必须如实记录，不能拿fd旧审批授予新代码与事实。

从原库当前只读基线建立一个**新** managed fixture-only 隔离副本。使用受控现有隔离方式，只写副本，不 hardlink 原DB作为可写副本，不把fixture标记/结果写回原库。失败旧库不得作为新预览起点。基线原records作为只读输入保持原值，不以重新审核替换旧身份。

先在该副本导入新版本9/45：完整 old+new resolver 候选与实际 SQL hash 一致，原成员 metadata 保持，幂等重复通过。然后对原133中126个行情逻辑输出做一次实际受控转换预览，生成可核验输出和 lineage/row dispositions；不能只输出resolver或把252身份observations冒充转换行数。

预览必须逐行/逐集合验证：

- 完整source分母402,246，不增加raw，不删旧source；126逻辑输出成员集合符合原批准输入。
- 原207已解析行的输出值/身份/NULL事实保持；新增恰好是45个有证据的event-native行，不包含42个端点alias候选和原15个daily mirrors。
- 如果实际成功结果是252 resolved/401,994 quarantine，提供完整集合差分、输出hash和旧207保全证明；这是预期检查，不是预先写入的结论。不同结果应调查并如实报告。
- raw `dv_ratio`、`dv_ttm`、`pre_close`各3个NULL保留，原tolerance不变；BSE、普通历史、资产例外和session结论不扩大。
- 原库仍207/402,039，63sessions uncertified。预览只能标`CANDIDATE_TRANSFORMATION_VERIFIED`；未实际运行COMPLETE generation和DQ audit时，不声称新generation COMPLETE或finding已关闭。

这一项修复不改变转换/rebuild/DQ实现，可复用原两代126输出和规模/恢复证明，不再在本批重复生成同样两代。正式原库应用如后续获批，再按正式执行规格完成新增Context、两代126及DQ。本批若为了核验而运行隔离DQ，必须列实际audit IDs/status，保留BLOCKED结果，不能推算关闭数代替audit。

## 5. 日历失败保留，未来方案只写建议

固定metadata store保持上述hash、first member FAILED、已消耗1attempt、6unattempted、0response/0civil rows。禁止再次执行live CLI、重试/补发7members、清零/delete、换DB/store、换endpoint/proxy或重新生成true license逃避终态。新代码提交之后，旧capture license 的SHA仍为旧fd，不能替换成新HEAD。

可以只读已有调用日志、环境说明和计划，制作一页安全诊断与最小后续证据方案：远端收到与否/账户权限UNKNOWN；可以列替代官方日历证据或需要未来独立处置的精确成员及预算。没有响应就不下根因断言；不能通过probe请求测试token/权限，也不能把建议作为执行授权。本批无需外部网络取证和provider support消息。

## 6. 一次 final 交付与停止点

新的 ignored 目录建议 `data/private/phase1c1-import-atomicity-finite45/<本次真实日期>-v1/`；公开报告写到对应 docs/reviews，公开只含聚合结果，不含DB、凭据或证券行级资料。

交付：最小源码diff及短设计说明、回滚/顺序/四时区控制证明、新candidate delta/resolver/Context/DQ proposal与旧新scope diff、实际126转换预览与完整row-set差分、原库/metadata/失败isolate/旧历史保全、下一步日历建议、完整manifest/ZIP/primary index/final-handoff。

保全检查沿用上批已有完整索引：136,599基线历史文件的bytes保持；本批合法改变的源码/新增设计/测试在新的implementation manifest中单列，不能把“全部167 pins不变”继续照抄。strict133、原approved materials、source/curated/identity/receipts/历代audits须保持。无生产新增审批、原库写入和provider请求均为0。

最终一次运行required full suite与离线检查，记录实际数量（原736加新增有效测试，不能预填数字）。final SHA的CI必须独立对应本次最终实现；保留CI URL/head/conclusion/实际日志。只提交代码、测试、说明、聚合报告；私有DB/raw/审批候选/证据/ZIP保持ignored，提交前及ZIP final再做凭据扫描。精确body/hash/文件引用可复核，公开报告不能引用私有fixture PASS为正式admission PASS。

最终状态 `IMPORT_ATOMICITY_AND_FINITE45_PREVIEW_REVIEW_READY`。一次交最终SHA、实际CI、公开报告、private ZIP/manifest/handoff绝对路径，然后停止独立Review。原limited15仍accepted；finite45 production APPROVAL PENDING、global DQ BLOCKED、calendar BLOCKED、Phase1C.2 CLOSED。

本轮不需要重开R1/R2全套设计、不拆多次交付、不扩事实研究或重跑133请求。出现真实无法排除的事务/兼容缺陷时保留失败材料并集中交付准确BLOCKED报告，不能以预期数字伪造完成。
