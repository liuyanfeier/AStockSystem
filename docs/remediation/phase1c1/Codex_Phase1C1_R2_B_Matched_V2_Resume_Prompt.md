# Phase1C.1-R2-B 匹配 v2 批准后的有限续跑

继续 AStockSystem 原先已授权的有限 R2-B，依据本次独立 Engineering PASS 和实际 reviewer v2 批准，一次完成剩余部署/两代/DQ/rebuild/保全后交付 R2 FINAL REVIEW。无需再制作待审批模板或重新研究已批准历史事实。Phase1C.2 CLOSED，市场/provider请求必须为0。

## 固定实际批准

先读 `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-03_Phase1C1_R2_B_Time_Integrity_Independent_Review.md` 与私有目录 `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c1-r2-b-time-integrity-v2-independent-approval` 的 approval-manifest.json、case-decisions.json、approved-case-set.json、approved-dq-evidence.json、approved-context.json、approved-resolver-snapshot.json、independent-actual-sql-admission-validation.json。核对 manifest 所有 bytes hashes、schema/implementation/frozen pins，并用当前获批模型检查 canonical hashes。将批准目录原 bytes 复制到 ignored `data/private/` 的新版本目录，保留作者包/v1批准/失败现场；不提交私有 payload。不得重新生成 approved_at、review_ref、metadata 或一个不同 Context。

reviewed/materials/Context implementation SHA：`0251e485396fb9e1a4214f71a298ad2777ebde90`；实现提交 `20d2c23bea98d091407f973f491cf89082647e20`。最终CI run37104268298/job111149633530：622 passed。protocol `R2_RESOLVER_UTC_INSTANT_V2`；addendum4 `068054fc25ac0e40eab0e33682f8c5be14debdcf7765e8d842bbb39666dd3e6b`。实际approved_at/knowledge_as_of `2026-10-03T07:21:19.165122Z`；review_ref `2026-10-03_Phase1C1_R2_B_Time_Integrity_Independent_Review@0251e485396fb9e1a4214f71a298ad2777ebde90#MATCHED_LIMITED_V2`。

- case-set `b4b598d0b55e51c94271bf857fe5ea7504d5e664dc17e52393177b13a6002100`
- DQ evidence `42f37df8ccaab7744344914f3b8484133cfd0ae99ddfc4aada3d0dd6c9b6395a`
- resolver `e88a8d9b6f38cd4629a67905124a811e980a374368b31667121f5ad918c8dffb`
- Context `d060739f01a2d7d22bad3a6b0599600efe4263c507069addbda6dd017c62f6cd`
- inputs `b471998495a4a4f6d2d55796b3fa084c383b32c53f3af91eb37da9afba245a08`

不得使用旧v1 Context或 serialization-only candidate 408a3a… 执行。源码、SQL、config、tests、冻结设计/政策必须与批准 bytes 相同。后续仅执行记录、公开报告或 AGENTS 授权说明的追加可单列实际执行 SHA；保留原有内容且不得改 Context implementation SHA，不能以 docs-only 名义修改任何获批语义。

## 一次完成的执行范围

1. 读取AGENTS、既有R2-B授权、保留的各份审查和本报告；以匹配 v2批准解除本次时间修复批次的“等待 matched review”阻断，只恢复已授权有限B。零market/provider包括metadata、mapping、calendar、stock_basic、bse_mapping；禁止capture/resume/replay或重跑133请求。禁止Phase1C.2、策略、信号、回测或订单。

2. 原库仍须预检 schema001–007/19表、原DBhash `2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`、identity/raw/旧252curated、1102保护文件、strict133 VALID/EXACT/0failure，备份必须一致可读。保留旧failed-isolate及2539项既有私有/保护files基线。使用 managed exclusive lock取得新的predeployment backup及recovery record，从验证过的007备份创建**全新的**隔离副本。审查方已经证明实际008–010/import/register/四时区reopen通过；执行方仍须对自己的副本预演，不能复用旧失败库或修改历史记录，也不得关闭writer/source/pinned-member校验。

3. 仅导入3episodes/3official codes/12bindings/192精确观察：001872.SZ72、001914.SZ72、302132.SZ48；dataset只有daily/daily_basic/adj_factor/stk_limit、EVENT_NATIVE。使用获批新metadata，保留观察/evidence时刻与IDs。不得导入旧251drafts、5584carry-forward、248BSE transitions或未批准source；不新增stock_st/suspend_d绑定，不提供旧resolver fallback，不推断alias或无限历史区间。

4. 隔离完整预演通过且原库保全基线仍相等后，按既有恢复协议在原库additive部署008–010/import/register。显式固定真正Context及resolver snapshot；输入133request/raw、126outputs、402246source。出版完整第一代，预期192resolved+402054quarantine；逐source守恒、ordinal从0、NULL/native原样、空resolved输出仍保留schema和lineage。原126旧代逻辑和quarantine须可重建，不改旧结果。

5. 用exact approved-dq-evidence与固定policy跑新COMPLETE代真实DQ。63session全部NOT_CERTIFIED；0reference exception、0operationalBSE transition；1374 exact pre-BSE仅APPROVED_OUT_OF_SCOPE coverage处置，保持quarantine。保留旧15756finding键/severity；只追加audit/处置，不更新旧audit。报告resolved/quarantine/out-of-scope交集、certified/provisional/unknown causal pairs、旧到新finding/source disposition和全部remaining blockers。数据准入仍BLOCKED，不因数量下降宣告历史完整。

6. 用同一实际Context创建第二个独立COMPLETE generation，核对126/126logical hash、schema/units、逐source lineage与quarantine；跨Asia/Shanghai/UTC/NewYork/Kathmandu至少重开managed连接验证两个代的select与固定snapshot，保留两代/DQ/publication/recovery证据。禁止latest/半代/混代，禁止删代、改Context或放宽篡改检查。

7. 在获批实现上完成必要离线验收、全suite一次、decoded secret scan，记录transport denial/spy证明provider/HTTP/socket调用0，历史数据库/文件按内容保全。若出现真正执行阻断，保留现场和具体证据集中交付，不自批准、不扩大数据范围；例行内部步骤连续完成，不逐Gate等确认。公开审查文件和hash/count索引可提交，私有审批/raw/DB/凭据保持ignored。推送后核验最终exact-SHA CI，交付最终SHA、r2-final-review、私有完整索引及handoff。

结束状态R2_FINAL_REVIEW_READY，等待一次独立R2 FINAL REVIEW。工程执行结果与historical completeness/real-data BLOCKED分别报告。STOP：Phase1C.2 CLOSED，禁止自动进入下一phase或新增真实请求。
