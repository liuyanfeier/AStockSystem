# Phase1C.1-R2-B 时间完整性修复：独立 REVIEW

结论：**Engineering PASS；原 P1 两个入口均关闭；匹配 v2 的有限执行批准已生成并通过实际 SQL 注册验证。** 本轮没有新发现的阻断项。R1 FINAL 保留 PASS；R2 FINAL 等待有限 B 执行结果；real-data gate BLOCKED，Phase1C.2 CLOSED。

审查精确最终 SHA `0251e485396fb9e1a4214f71a298ad2777ebde90`；实现提交 `20d2c23bea98d091407f973f491cf89082647e20`，设计冻结提交 `bbd032b5ee3764eecaafb334455676dde941f45c`。从上一阻断 SHA `63a166b89f44850dd9fa2efa8ab06c0e49a8bfd5` 到最终 SHA 的 13 个文件均已核对。新 Approval 与 Context 的 reviewed/implementation SHA 均明确绑定最终 `0251e485396fb9e1a4214f71a298ad2777ebde90`；实现提交单列作为代码来源，不混用。

## P1 关闭依据

`canonical_resolver_member` 仅规范化 7 个指定 aware datetime 字段，转为 UTC、六位微秒和 Z。保留 null publication、日期、区间、native、IDs、证据/批准引用、版本/状态和 observation 顺序。`snapshot_hash`、持久化 resolver payload、pinned/live 成员比较使用同一规则。相同时刻的不同 offset 不再造成误拒绝；真正的微秒差异与实质成员变更仍被拒绝。

Approval 和 Context 显式要求 `R2_RESOLVER_UTC_INSTANT_V2` 及 addendum4 hash `068054fc25ac0e40eab0e33682f8c5be14debdcf7765e8d842bbb39666dd3e6b`。旧 v1 Approval/Context 与 pending template 均不能隐式进入 v2。schema admission、case import 和 Context validation 检查新设计 pin。SQL001–010、R1 receipt serializer/identity、raw、legacy logical hash 与 DQ policy 均没有修改。

## 独立验证

- 当前最终源码的三组相关测试 **100 passed**，其中新增时间完整性测试 33 项。实际 managed synthetic SQL 覆盖 import/register、关闭并重开连接、选择 COMPLETE、独立 rebuild；四个时区分别为 Asia/Shanghai、UTC、America/New_York、Asia/Kathmandu。微秒/naive、native/dataset、source event/raw/ordinal/order、security/episode/code interval、evidence/approval/status/version 和缺失成员/snapshot 的拒绝，以及 F1–F3 回归均通过。
- 独立读取最终 SHA 的 GitHub Actions run 37104268298 / job 111149633530，确认 SHA、全部 job/steps 和日志：**622 passed, 4 warnings, 927.55s**；离线诊断/合约步骤通过。没有以作者文字代替远端结果。
- 失败隔离库只读读回，四个时区均得到 serialization-only candidate `408a3a328da5858a2e400c09675bedb2623f8afb6ff00d2a501854608454dbe3`；成员相等、12 个 binding 的最早 exact scoped raw capture 相等，两条 resolver guard 路径均通过，篡改仍拒绝。该 candidate 不是本次最终执行批准。
- 使用下方真正的新批准，在审查工作目录从已验证的 schema007 备份创建全新副本，实际部署008–010、导入3/3/12/192、注册非 fixture Context，并反复注册验证幂等。关闭连接后四时区重开，完整133输入/126父代及 pinned snapshot 验证均通过。副本有1 Context、1 snapshot、133输入；generation/output/DQ audit均为0，旧19表内容和1102源文件保留。这是隔离审查证据，原库没有部署。

CI：[final exact-SHA run](https://github.com/liuyanfeier/AStockSystem/actions/runs/37104268298)。详细本地证据在私有批准目录的 independent-engineering-validation、independent-focused-tests、independent-final-sha-ci 和 independent-actual-sql-admission-validation JSON。

## 匹配 v2 的实际批准

实际批准时间/knowledge_as_of：`2026-10-03T07:21:19.165122Z`，不是重用 v1 的审批时间。review_ref：`2026-10-03_Phase1C1_R2_B_Time_Integrity_Independent_Review@0251e485396fb9e1a4214f71a298ad2777ebde90#MATCHED_LIMITED_V2`。

显式版本化 episode/code 的 approval_ref、available_at，以及 binding 的 approval_ref、decision_at、available_at。1374项 DQ disposition 仅更新 approval_ref/decision_at。first_observed_at、retrieved_at、published_at、所有 IDs/区间/native/evidence/观察范围和历史事实保留；没有提升 binding_version、扩展范围或覆盖 v1 文件。未批准 case、5584 carry-forward、248 BSE transitions、15756旧finding和63条 NOT_CERTIFIED session 的决定保留。旧 documentary review 按原 bytes 保留，本轮没有声称重新审查历史来源。

| pin | 最终 canonical hash |
|---|---|
| approved case-set | `b4b598d0b55e51c94271bf857fe5ea7504d5e664dc17e52393177b13a6002100` |
| DQ evidence | `42f37df8ccaab7744344914f3b8484133cfd0ae99ddfc4aada3d0dd6c9b6395a` |
| resolver snapshot | `e88a8d9b6f38cd4629a67905124a811e980a374368b31667121f5ad918c8dffb` |
| Context | `d060739f01a2d7d22bad3a6b0599600efe4263c507069addbda6dd017c62f6cd` |
| unchanged input-set | `b471998495a4a4f6d2d55796b3fa084c383b32c53f3af91eb37da9afba245a08` |

因新批准 metadata 和 v2 工程 pins 发生合法变化，最终 resolver/Context 不等于 serialization-only candidate。所有文件 bytes SHA256 在 approval-manifest 中；实际文件/model/SQL读回已交叉验证。

## 保全与下一批

原 DB SHA256 `2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`，schema001–007/19表不变；181raw、旧252curated/lineage、126旧输出、1102保护文件、2539项既有私有/保护文件保留。strict133为 VALID/EXACT/0 failures，evidence hash仍 `0992ccac745f6e5299615caaf7a68e4aabf9fb4d90c49e1d1c742716bf4e3597`。旧 v1批准、可读备份、失败隔离库和上一阻断包原 bytes 不变。原库写入、新 generation、真实 DQ、市场/provider/HTTP/socket调用均为0；Git工作树 clean。解码凭据扫描结果另记 final-delivery-validation。

批准范围仍为001872.SZ 72、001914.SZ 72、302132.SZ 48，共192个 exact raw rows；仅daily/daily_basic/adj_factor/stk_limit、EVENT_NATIVE、CURRENT_RECONSTRUCTION/OBSERVED_CAPTURE。预期每代 **192 resolved + 402054 quarantine**；原7666 quarantine保持，394388旧resolved仅在新Context因缺证隔离。0新calendar认证、0reference exceptions、0operational BSE transitions。工程 PASS 不构成全历史数据/回测准入。

原先用户授权的有限 R2-B 在匹配批准下可续跑；新 prompt 将备份/新隔离预演、原库 additive部署、两个COMPLETE generation、实际DQ、同Context rebuild和保全验收合并为一次执行、一次 R2 FINAL REVIEW。使用全新的批准副本和新007隔离副本，保留旧失败现场；不得重跑133真实请求，不得开始Phase1C.2。

私有批准目录：`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c1-r2-b-time-integrity-v2-independent-approval`。下一批指令：`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_R2_B_Matched_V2_Resume_Prompt.md`。审查副本：`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/work/r2b-timefix-v2-actual-sql-proof`，供审计，不作为原库执行结果。
