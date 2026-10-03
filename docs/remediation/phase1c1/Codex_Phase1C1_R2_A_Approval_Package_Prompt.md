# Codex prompt — R2-A 历史裁定、DQ evidence、Context 一次性申请包

2026-10-03。工程已独立 PASS，批准 SHA `2f2592968a7f8e2500ee5e0bd3772a15a5c621f5`。本条仅授权准备剩余 R2-A 审批材料；不授权 R2-B、不部署真实迁移/绑定、不运行新真实 generation/DQ。已有工程批准见同目录 `Phase1C1_R2_A_Engineering_Approval_Manifest.json` 和 `2026-10-03_Phase1C1_R2_A_Fixes_Independent_Review.md`。

一次完成以下全部材料，统一提交独立 reviewer 裁定，不按每个 case/小步骤暂停。使用现有原库/raw/候选/台账/官方保留证据；市场/provider API 请求预算 0，包括 metadata、mapping、calendar。只读官方公告与供应商字段文档调查沿用既有许可；不得重新下载新增证券/映射列表或用新市场数据替代既有 raw。Phase1C.2 CLOSED。

## 1. 核对基线与申请范围

读取 AGENTS、v1.1 batched prompt、工程批准报告/manifest、冻结 design v1/addenda1–3、当前 operation contract 和源代码 `Approval` / `Context` / `evidence_hash`。

核对当前源码/SQL/policy 与已批准工程 hashes。材料 commit SHA 与 approved implementation SHA 分开记录。本任务不改变已批准 source/schema/policy；发现新工程需求列为 blocker，不自行引入改变后沿用旧工程批准。

原 346 个 case review items、251 个 inactive drafts 和 5,584 个 carry-forward security scopes 留存且不自动激活。已有 26 项证据与上轮修复材料不得覆盖。

## 2. 历史 case 申请与完整处置台账

每案给出：

- case ID、拟议决定及证据充分性；缺证明确 EVIDENCE_REQUIRED，矛盾明确 CONFLICT，范围外提出 OUT_OF_SCOPE。
- raw_object_id / zero-based raw_row_number / dataset / event_date / capture hash / retrieved_at，能与现有 raw 精确对接。
- 拟议 stable security、listing episode、venue、asset_type、官方 code 的实际区间、provider-native representation 与 exact observation scope。
- 原文依据、原文位置、取得时间与知识时间；说明证据支持的具体命题和仍不支持的部分。
- 原/新解析影响、原 quarantine/旧 finding 处置、重复 source 或重复 daily key 风险、尚未解决的身份/coverage 问题。

同一充分证据可以支持一组有明确成员的 case；提交组与成员 hash，reviewer 可批量裁定。不能用 wildcard 扩展 endpoint/capture/event，不能因同名、同后缀、当前 active list 或 observation min/max 推断历史身份/episode边界。原已 resolved 394,580 行的 carry-forward 也必须有明确处理：拟议获批绑定或保留隔离，不能隐式调用旧 resolver 作为 fallback。

整理可执行 **候选** payload：顶层严格为 `episodes` / `codes` / `bindings`，各记录符合现有模型，source observations 精确，表示类型明确。它仍是审批申请，bindings 保留 inactive status；不能自行写真实 APPROVED 决定或伪造 reviewer 的批准引用/时间。批准后最终状态/时间变化会改变 hash，由 reviewer 对最终 payload 再核对并固定。

无需强制将全部案例变为可批准。无法获得的真实历史证据保留隔离与 blocker，提交本轮确实有证据支持的有限候选集合；空集合不能包装成“所有历史身份已通过”。

## 3. DQ evidence 申请

准备完整 envelope，顶层严格为以下四项：

1. `sessions`：venue/episode/event/previous_session、证据出处和认证依据。SSE 证据不能认证 SZSE/BSE；缺证可缺记录或保持不认证，不得凑 certified pairs。
2. `reference_exceptions`：仅提出证据充分的 exact dataset/episode/event/field/source 范围；NULL 原值保留。CDR 身份事实不能自动解释某日 NULL，不能自动获 NOT_APPLICABLE。
3. `bse_transitions`：分别记录官方 code 生效、provider 原始表示与 security/episode 连续性，缺切换侧保留 NOT_OBSERVED。
4. `source_dispositions`：范围外申请精确到 dataset/event/raw-row，保留 case/证据引用。未获 reviewer 裁定时不得伪造 APPROVED_OUT_OF_SCOPE 或实际批准记录。

记录每项拟议决定与事实限制，计算申请 envelope 的 canonical `evidence_hash()`，同时保存文件 bytes SHA256。Reviewer 最终调整后再固定批准 hash。

证明采用已获批固定政策：price0.011、causal0.011pp、原独立 factor 方法及容差；不填补 NULL/factor，不降级以消除异常。批准一个保留 unknown/NOT_CERTIFIED 的 evidence envelope 只表示允许按这些已声明证据和缺口运行审计，不表示它们已认证。

## 4. 更新实际执行 Context 的 proposal

保留旧 `derivation-context-draft-v2.json`，生成新的版本。采用当前 `Context` 字段，包含：

- parent batch/generation、parent identity/plan hash。
- 133 个 exact inputs / 126 个 market outputs；各 request/raw FK/hash/schema/row_count 与原 manifest 一致；source总数402,246。
- 候选 resolver snapshot/membership、spec/policy/design/addenda1–3 hashes。
- DQ evidence proposal hash、实现 SHA、拟议 review reference 与审批后需要填入的真实时间字段。
- `fixture_only=false`、CURRENT_RECONSTRUCTION / OBSERVED_CAPTURE；不得声明 historical PIT。

原草稿尚缺实际审批与 resolver/DQ evidence，也没有修复后要求的 correction_addendum_hash 和完整 parent_plan_hash。新 proposal 必须补齐，不把旧文件改成“已批准”。不能借用合成测试的 Approval 或通过回填旧时间绕过 availability 检查。

在报告中区分：候选 proposal 可以计算的 hashes，以及 reviewer 最终裁定/实际 approved_at 后才可固定的 final case/resolver/evidence/context hashes。不把任何 TBD 当成实际可执行 Context。

## 5. 只读验证、交付与停止

做原 raw source 引用、模型结构、区间/冲突和 canonical-hash 预检。只有准备/校验需要的测试；source/schema/policy 未变时，不要求重复全工程修复。禁止在原库应用迁移、import_approved_cases、register_context 或真实 publication/DQ。

既有原库 hash、schema001–007/19原表、133严格receipt、181 raw、252旧curated/lineage和1,102受保护文件保持不变；保留0市场请求证据。真实行级材料和可执行候选放 ignored private storage，Git只提交脱敏报告/索引/申请摘要。

私有交付建议：

- `case-decision-requests.json`：逐案/分组证据与拟议决定。
- `case-set-proposal.json`：episodes/codes/inactive bindings 精确 payload。
- `dq-evidence-proposal.json`：四项 evidence envelope。
- `context-proposal-v3.json`：新版本执行 context 申请。
- `approval-package-manifest.json`：文件hash、canonical proposal hashes、输入集合、已批准工程SHA、材料SHA、全部 blocker。

公开交付 `r2-a-approval-request.md`，写明一份申请包覆盖上述全部对象、拟议可批准范围、未解决范围和风险、private paths/hash。保留 `approved_case_set/hash=null`，作者 status 标为 APPROVAL_PACKAGE_READY。

完成并推送后核对材料最终 SHA 的既有 CI 状态，保留工程实现 SHA、材料 SHA 和其差异证明，再提交一份材料给独立 reviewer。Reviewer 将基于证据统一出具最终 case decisions、批准的实际 case_set/hash、DQ evidence/hash、Resolver/Context/hash和实际批准时间；用户随后决定是否授权 R2-B。不要自行启动 B，不要求用户逐案点击批准。

## Reviewer 后续批准的最终文件

最终审批应产生相互匹配的 `case-decisions.json`、`approved-case-set.json`、`approved-dq-evidence.json`、`approved-context.json` 和 `approval-manifest.json`。决策、最终 APPROVED payload、真实 approved_at / available_at / decision_at、resolver hash、approval_ref 和 context hash由 reviewer 统一核对固定，不能复制作者申请 hash 后直接认为已批准。

允许仅批准证据充分的有限集合。其余 case 保持 EVIDENCE_REQUIRED/CONFLICT/隔离，缺 calendar 保持 NOT_CERTIFIED；整体历史 universe 不完整时，外部 real-data gate 继续 BLOCKED，即使某个局部输出或审计为 PASS。工程完整 generation 的 publication 与历史数据可研究性分别判定。
