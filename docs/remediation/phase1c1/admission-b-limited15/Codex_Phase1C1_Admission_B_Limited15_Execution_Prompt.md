# AStockSystem：实际批准后的 Admission B 有限15执行

用户转交本指令，即明确授权下面这一次有限原库追加与验收。独立 Review 和真实批准已完成；连续完成内部步骤，一次交最终 Review，不再做 Admission A、审批模板或源码修复批次。本批真实市场/provider/metadata/calendar/mapping请求0，不重跑133；Phase1C.2 CLOSED。

## 1. 使用现成真实批准，禁止重新签发

项目：`/Users/yanliu/Documents/AStockSystem`。

先读当前AGENTS、writer lifecycle、已批准R1/R2，以及：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-04_Phase1C1_Combined_Independent_Review.md`。
- 同目录`private/phase1c1-admission-b-limited15-independent-approval/`：`approval-manifest.json`、`approval.json`、`case-decisions.json`、`approved-case-delta.json`、`approved-dq-evidence.json`、`approved-resolver-snapshot.json`、`approved-context.json`、`independent-actual-sql-admission-validation.json`。
- 用户同时提供的独立Review/批准ZIP；若使用ZIP，校验随附handoff的ZIPhash、CRC和逐成员bytes。

实际 reviewed/material/Context implementation SHA：`45554a142a8e8d3e1b6cb0147db537bc88d1b55e`。review_ref：`2026-10-04_Phase1C1_Combined_Independent_Review@45554a142a8e8d3e1b6cb0147db537bc88d1b55e#ADMISSION_B_LIMITED15`。approved_at/knowledge_as_of：`2026-10-04T08:13:46.338396+00:00`。

- delta：`39211d73b8308db26130e7ae3ea21c2e81479e4a0620924a1820857ac5a59609`。
- DQ：`8a910a43ef415f7463d825668b576df237152c69d17921a59eb7e1a446f73d2d`。
- resolver：`837d06d825d6852b1a9125ef6f1656876fa535339d84a2dfd3626bba33df36d6`。
- Context：`470017335c3e7fd9f69480b35e2ac3012ceea2892a3f94706fdfcfb5af262475`。
- inputs：`b471998495a4a4f6d2d55796b3fa084c383b32c53f3af91eb37da9afba245a08`。

逐bytes/canonical/domain hash核验并用当前批准模型parse；不要直接对未经模型解析的UTC字符串猜hash。把批准目录原bytes复制到新的ignored执行目录。禁止生成新的review_ref/approved_at、改member时间/顺序、修改批准Context、改fixture hash冒充正式批准。

源码、tests、SQL、config、依赖和冻结设计必须与manifest exact_accepted_file_hashes相同。后续只能追加授权说明、执行辅助材料和公开报告；实际执行/交付SHA单列，Context仍固定45554a1。必要私有辅助脚本调用现有获批接口，不新增或绕过生产guard。遇到真正实现/批准不匹配，保留现场并集中报告，不临时改源码或批准。

本授权在上述精确范围内取代AGENTS中“Formal B等待批准”的历史停止点。保留历史内容，追加本批授权说明；不把仍false的metadata license改true。

## 2. 有限范围与预期

仅新增3个`daily` EVENT_NATIVE bindings、15个单观察日official code区间、15个精确raw observations，0新episode。已有3episode、旧3code区间、12bindings/192observations及其时间/批准不变。merged counts为3episodes/18code intervals/15bindings/207observations。

观察分别为000022.SZ3条、000043.SZ3条、300114.SZ9条；以批准delta里的raw UUID/zero-based ordinal/event为唯一scope。镜像15条仍quarantine，旧2probe不进入新delta或133membership。不批准其他dataset、alias、去重、factor、session或BSE identity。

DQ使用本次实际批准envelope：原63未认证session仍未认证，1374精确pre-BSE source处置仅是新Context中的有限范围外重授权，其原生产审批出处/time/hash已保留。其余缺证保持blocking。

预期每代126输出，402246source、207resolved、402039quarantine；旧192行值不变，新解析精确15行。DQ预期BLOCKED，402147 findings，因果certified0/unknown60。相较当前原代，移除30 findings、新增45：15MISSING_DAILY_FACTOR、30CROSS_DATASET_MISSING_OR_PROVIDER_ONLY。BLOCKED是此次有限执行的真实数据结果，不是自动中止工程验收或放宽门槛的理由。

## 3. 当前原库保全、匹配副本与原库追加

原库基线SHA256：`c687fc514a78ef8b68b6c89907b9932a42465d2b2cab5ae383647616287ca0e2`；34表/schema001–010已经部署。不要再次迁移001–010，不用旧007备份覆盖当前库。

1. managed exclusive owner确认无竞争者，建立当前库一致可读备份、34表/旧记录和protected文件基线、恢复方案，校验strict133VALID/EXACT/failure0、181raw及所有历史批准/Context/generation/audit。若基线发生非本批变化，调查后报告，不覆盖。
2. 从当前一致基线建立全新隔离副本。可使用已验收`admission_rehearsal.copy_snapshot`，其允许路径为`data/private/phase1c1-combined-remediation-b-rehearsal/<new-run>/isolated-root`；该路径中的正式匹配预演使用真实批准、`fixture_only=false`，不调用`admit_fixture`或打开allow_fixture。保存实际路径及一致snapshot证明，不覆盖任何旧候选/失败root。
3. 在副本managed writer连接下用`admission_delta.import_delta`导入批准delta；核对完整old+new resolver，重复导入ALREADY_VALID且旧metadata不改。只注册实际approved-context；校验父133/126与全部design/policy/protocol/raw/resolver pins。不要使用候选Context或只挑新member组成snapshot。
4. 按现有pipeline创建第一代126完整输出、精确批准DQ；同一Context第二代独立126输出及DQ。逐source守恒，保留native/NULL/schema/units/empty/lineage；比较同Context两代logical/schema/quarantine/source。四时区managed close/reopen验证两个显式COMPLETE代。保留局部DQ与完整分母，0eligible不标PASS。
5. 副本通过且原库受保护基线仍匹配后，managed exclusive owner按同一原批准bytes在原库有限import_delta/register，生成两代及append-only DQ/audit/处置证据。执行前后核对旧记录内容，仅追加新允许行和版本；整个DBhash会因追加变化，不能要求部署后整库hash与旧库相同。
6. 在原库再次验证每代126/402246/207/402039、旧192行不变、scope精确15、四时区相同Context两代选择及旧Context仍可重建/有效。原133 receipts/attempts/times、181raw、旧252curated和既有matched-v2历史结果/批准保留原bytes和内容。

原库和正式匹配副本使用相同真实Context，比较它们的语义结果。不要把候选fixture的logical/physical hash强行套给正式Context：新审批时间/Context不同，schema metadata及15行binding_available_at会正确变化。核对不受新批准影响的原192行全部值；新15行的原行情值/raw lineage保留，identity/knowledge metadata按真实批准。

## 4. 差异与真实准入状态

用现有完整source/finding基线加本批精确增量，提供可重建、无遗漏的旧新处置索引；无需重复写一份内容不变的全账本。保留旧15756 findings及其payload/severity/关闭依据和全部旧audit；不可删旧key或改旧finding制造清零。

逐项解释15行新增解析、30旧finding消失、45新增finding，以及1374处置在新DQ中的ref/time/provenance变化。没有新依据的finding保持缺证；身份已解决不代表因子/其他endpoint或交易日已认证。

分别报告工程执行、有限身份追加、全局DQ、全历史前置、Phase1C.2许可。此次全局数据准入仍BLOCKED；不要以207resolved或两代COMPLETE宣称完整Admission B准入PASS。

## 5. 一次验收与交付

复用既有工程、故障/30126规模、历史账本和本轮候选演练证明；只补真实批准材料与实际原库应用路径验证，不重新研究获批15条事实或为内部步骤重复跑全套。必要针对性验收后，最终一次仓库要求的全套离线tests/doctor/contracts/decoded secret scan；推送后核对最终exact-SHA CI。

运行期间deny/spy证明所有provider constructor/fetch、HTTP/socket真实调用0；不调用live metadata CLI，不新增calendar/stock_basic/identity取证、不capture/resume/replay。授权说明/公开报告可提交，全部批准、DB/raw、历史证券及完整行级材料保持ignored。

输出新的`data/private/phase1c1-admission-b/<limited15-run>/`与对应`docs/reviews/phase1c1-admission-b/<limited15-run>/`，包含实际批准副本、备份/恢复索引、正式匹配副本和原库验收、真实Context/generation/audit IDs、基线保全、精确增量及完整账本引用链、calling0/secret/CI、manifest/ZIP/final-handoff。

最终状态`ADMISSION_B_LIMITED15_FINAL_REVIEW_READY`；一次交final SHA、CI URL、公开报告、私有ZIP/manifest/handoff路径，并明确有限追加完成、DQ BLOCKED、市场API0、133未重跑、Phase1C.2 CLOSED。停在最终独立Review，不自动扩大证据或启动回填。
