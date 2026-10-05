# AStockSystem：finite45正式应用与Phase1C.1工程收尾，一次完成

用户明确转交本指令，即授权下面匹配实际审批的一次有限原库追加、验收和工程收尾。内部备份、正式副本预演、原库应用、两代完整输出与最终交付连续完成，不再为每个内部步骤等待批准。真实市场/provider/metadata/calendar/mapping请求 **0**，不重跑133，新增文献获取0，不发送咨询。Phase1C.2仍CLOSED。

这是已批准事实的有限应用，不再做工程修复或candidate approval模板。禁止自行扩大身份、calendar、BSE/ordinary scope，不能把工程收尾命名为全历史数据准入PASS。

## 1. 使用本次真实独立审批

项目 `/Users/yanliu/Documents/AStockSystem`。干净起点、实际approved implementation SHA：`546b57bcbb9af9e8b703a9f8edbfd1986f83bca4`。

阅读当前AGENTS、writer lifecycle与：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-05_Phase1C1_Import_Atomicity_Finite45_Independent_Review.md`。
- 同outputs的 `private/phase1c1-import-atomicity-finite45-independent-review/` 独立artifact/data/CI/119tests证明。
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c1-finite45-independent-approval/` 所有8份JSON：`approval-manifest.json`、`approval.json`、`case-decisions.json`、`approved-case-delta.json`、`approved-resolver-snapshot.json`、`approved-dq-evidence.json`、`approved-context.json`、`independent-actual-sql-admission-validation.json`。

Review ref `2026-10-05_Phase1C1_Import_Atomicity_Finite45_Independent_Review@546b57bcbb9af9e8b703a9f8edbfd1986f83bca4#FINITE45`；真实approved_at/knowledge_as_of `2026-10-05T02:04:22.195893+00:00`。

| Pin | 值 |
|---|---|
| Delta | `fcaddc045a24f2c502c2f1e8b63a310d8aa460f0a35d8eaf4e28ee75aeef8805` |
| Resolver | `31beb026b143497bd001a1b1058c289d47422c1464f8d6c5ded149fa407bea91` |
| DQ evidence | `67333e31c420b759605ddf7a5ebb061fbd45e2ada86ee898b7aee3628248d61f` |
| Context | `5bb73a54850e4328b8cfc0305185a77d001bf7841984bdd5e73ab2190898256c` |

逐bytes、模型parse后的canonical/domain hash校验并复制批准原件到新的ignored执行目录，禁止自行换时间/ref、re-sign、重排批准observations或替换Context。源码/tests/SQL/config/依赖/冻结设计必须匹配manifest的`exact_accepted_file_hashes`。当前candidate的e43内部fixture不是生产批准，本批使用上述匹配546的新实际批准。

本授权仅在精确finite45范围取代AGENTS中的“等待production approval”的历史停止点。保留旧AGENTS、授权和Review；必要公开授权/报告追加即可。禁止生产模块/测试/策略/SQL/DQ/transport新修改。

## 2. 有限范围和原库基线

仅新增9个bindings、45个exact observations：adj_factor/daily_basic/stk_limit各15，复用既有3个episode/18个code intervals，新增episode/code均为0。以实际approved delta中的raw UUID、零基ordinal、event date、dataset、native和binding ID为唯一scope。其余observations不得加入；42端点alias候选和15 daily mirrors继续隔离。

原库当前 SHA256 `27aabd6143d977decefefb8eb1f1b2b9e66ee29c14045d9df284871bcecf065f`。schema001–010、34表已部署，禁止再迁移或恢复旧007库。原来3episodes/18codes/15bindings/207observations，2Contexts/4generations/4audits，181raw manifests、旧133 receipts和历史files保持。

预期新增后身份计数3/18/24/252，正式每代126输出、source402,246、resolved252、quarantine401,994。原207行的全部行情值/identity/NULL不变。新的45行只有knowledge/approval metadata依据本次真实批准；不得强制其hash与e43 fixture一致。原45候选的NULL事实与scope相同，保留原tolerance。

DQ用本次approved envelope：63session仍未认证、1374原有限pre-BSE范围外处置重新授权于新Context，其原envelope/hash/ref/time保留。无新日历事实，无新增asset/NULL/alias政策；audit结果预期仍BLOCKED。finding总数和factor/cross-endpoint关闭变化必须实际计算，不预填90或假定零新增异常。

## 3. 一次正式匹配预演和原库应用

1. managed exclusive owner确认无并发writer，取得当前一致可读备份，记录34表原rowset内容hash、旧Context/generation/audit以及protected文件基线和恢复索引。验证strict133 VALID/EXACT/failure0、181raw、原两代COMPLETE；当前基线有非本批差异就保留现场调查，禁止覆盖。
2. 建立**全新**正式匹配隔离副本，可复用`admission_rehearsal.copy_snapshot`和其允许的 `data/private/phase1c1-combined-remediation-b-rehearsal/<new-run>/isolated-root` 路径。使用真实approval和fixture_only=false，不用`admit_fixture`、不打开allow_fixture、不接着写旧failed/candidate/reviewer副本。
3. 副本managed writer导入actual delta，完整old+new resolver/hash必须等于本审批；严格重复ALREADY_VALID、旧15binding metadata不改。注册exact approved Context，校验真实parent133/126、raw、design、policy和v2 pins。两旧Context仍有效。
4. 同一approved Context创建两代各126个显式COMPLETE outputs，用实际approved evidence做append-only DQ；比较logical/schema/raw/source/quarantine，关闭重开/四时区选择相同Context的两代。全source守恒，局部DQ、NULL、空表和lineage如实保留。可以复用既有规模/故障工程证明，不重新跑全套故障研究。
5. 副本全部验收通过且原库保护基线仍一致，managed exclusive owner在原库同样有限import/register并创建两代126/append-only DQ。只有新批准允许的delta、Context/input/snapshot、generations/outputs/manifest/quarantine/audit追加；旧34表rowsets、旧192+15批准与旧Context历史保持内容。
6. 在原库核验252/401,994和精确45增量、旧207完整值、两旧Context有效、两个新COMPLETE generations与DQ、四时区同Context一致、正式副本与原库语义结果一致。严格repeat无新增。整体DBhash因合法追加变化，记录新hash，不要求部署后仍等于旧库hash。

错误时事务回滚或按既有恢复流程保留现场，不删除/重写失败历史，不把错误当成继续扩大scope的授权。不要用author fixture和正式Context的physical/logical hash差别制造假冲突；Context metadata和45行新的批准时刻确实不同，原207值保持。

## 4. fixed metadata与历史必须保持

固定metadata DB仍 `91a2c5d20df935795e0e2b736175af13fb6b7b5f6092231a9e96975fd30b9ece`，旧失败isolate仍 `ec32a43385df4c864fa054be0bc0b736a767552e2a47aaffab79286172a54890`；新candidate isolate保持`f34052365af0963ab6096db4246ffcbfbdeb5b8d31e690583c3ac9133c7fc6d5`。

metadata first member FAILED/1consumed/6unattempted/0response/0civil rows、旧true license固定fd1d1b5，禁止live CLI、resend/reset/store替换、补发余6、re-sign到546、endpoint/proxy fallback、token/积分probe。本批全部网络数据预算0，deny/spy证明provider constructor/fetch、HTTP/socket未调用。

136,599个旧protected文件、旧failed isolate和上批Review/审批材料原bytes保留。新增文件写新ignored目录，不覆盖v5/v6候选或旧审批；新原库rowsets与旧rowsets差分可重建。旧generation物理files/receipt/manifest/审计不能改。

## 5. 工程收尾与真实门状态，一次交付

新ignored目录建议 `data/private/phase1c1-finite45-formal-execution/<真实日期>-v1/`，公开报告对应 `docs/reviews/phase1c1-finite45-formal-execution/<真实日期>/`。

交付：原实际approval副本、baseline/备份/恢复说明、正式匹配副本与原库acceptance、exact Context/generation/audit IDs、两代126完整输出/row/finding差分、旧207/旧历史保全、网络预算0、credential decoded/encoded扫描、source pins、manifest/ZIP/primary index/final-handoff。公开只写聚合，不force-addDB/raw/完整证券行级证据。

源码/tests/SQL/config/依赖pins不变时，本批明确授权复用本次已独立核验的753完整测试和119相关回归，不再本地重复753；只补真实新应用路径的必要验收与doctor/contracts/离线checks、secret/staging检查。commit/push聚合授权与报告后核验最终exact-SHA CI，记录实际日志。实际执行implementation546、Context546和最终文档交付SHA另列；不为内部步骤重复同样测试或规模证明。

最终报告必须清楚区分：

- Engineering remediation与finite45正式应用可验收，旧limited15仍有效。
- 全历史 identity准入/63session/BSE/provider alias证据不足仍BLOCKED；本批新的factor/endpoint findings以实际audit为准。
- 以前形成的完整分组/最小外部事实台账继续有效，1,374个已有范围外处置不重复列为待新身份批准；ordinary/BSE/unknown/special不因45批准整体放行。
- Phase1C.1工程修复线收尾；Phase1C.2实际运行仍CLOSED，需匹配venue/calendar、历史identity/native范围、新版full-plan/API预算与用户授权。不得启动Phase1C.2或写“整体数据PASS”。

状态 `FINITE45_FORMAL_EXECUTION_AND_PHASE1C1_ENGINEERING_CLOSURE_REVIEW_READY`。一次交最终SHA、CI URL、公开report、私有ZIP/manifest/handoff绝对路径，再停独立最终执行验收。不再追加另一轮同项工程修复或重新准备approval模板。
