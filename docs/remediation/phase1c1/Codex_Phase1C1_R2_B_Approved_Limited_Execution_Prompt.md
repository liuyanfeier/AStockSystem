# Phase1C.1-R2-B 有限审批集合：一次完成离线验收

本文件是待用户转交的执行指令。生成本文件不构成 R2-B 授权。用户明确转交本条后，只授权以下有限离线范围；Phase1C.2 仍 CLOSED。

执行 AStockSystem R2-B：应用实际 reviewer 已批准的有限集合，完成既有 raw 的新 Context/完整 generation、同 Context 第二代独立 rebuild、固定 DQ 和历史保留验收，一次交付后等待 R2 FINAL REVIEW。不得开启逐内部 Gate 的重复停顿，也不得自行补全缺证 identity。

## 必须先核对的真实批准

审批报告：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-03_Phase1C1_R2_A_Historical_Approval_Review.md`

私有批准目录：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c1-r2-a-independent-approval/`

读取 approval-manifest.json、case-decisions.json、approved-case-set.json、approved-dq-evidence.json、approved-context.json、approved-resolver-snapshot.json，先验证 manifest 内所有文件 bytes SHA256，再用获批模型验证 canonical hashes。仅在后续运行时复制到仓库 ignored `data/private/` 下的独立批准目录；不覆盖作者原 proposal/旧审查包，也不把私有 payload 提交 Git。原作者材料 ZIP 保持 SHA256 `fda8ecf5e945673d34a484b411226740551396408f130c6e61cc6937aee81a17`。

获批工程 SHA：`2f2592968a7f8e2500ee5e0bd3772a15a5c621f5`；实现 commit：`5108731af43bc0738144b6e835c5b65f5f5fc37f`。材料 SHA：`f2df32b5d722fb3b73bf0e3a9294d5517c6fdfa1`，CI run 37092541651 /job 111115740558，589 passed。逐项核对 schema_and_implementation_hashes；docs-only 后续 commit 可以单列实际执行 SHA，不能篡改已批准 Context 的 implementation_sha。

固定最终 canonical hashes：

- case-set：`5f263b228917e2076984e8a71bcc9c6c4368ab415fab698e771ced9b0dd2c26c`
- DQ evidence：`4f7ad76a9d9613cc3b654c08994b583dc952b45c33051bad8539a32a231aaa19`
- resolver：`5ed2a9d8831ca37efd4f50f754812903b5e52ea54bd34c56c5241ae720c92772`
- Context：`0fd34edc7eb0d19c0cf1b9f39de1a6d3aa378da171e9f68f048890de2f2afda2`

实际 approved_at / knowledge_as_of 均为 `2026-10-03T03:52:23.856708+00:00`。不要重新生成时间、改 approved refs、重算一个不同 Context 后声称同一批准。

## 执行范围与验收

1. 读取 AGENTS、R1/R2 规格和批准报告；记录用户转交此指令的授权。本条只对 B 部署/离线应用解除先前 A 的“不部署”限制。零市场/provider 请求仍包括 metadata、mapping、calendar；禁止重跑 133 请求、capture/resume、bse_mapping/stock_basic，再抓证券列表，Phase1C.2 全部功能仍禁止。

2. 做 R1 strict receipt 输入预检、原 schema001–007/19tables 与内容基线、181raw、旧252curated/lineage、旧identity/历史receipt/attempt/audit文件保全；旧保护文件1102项无差异。原 deployment 前先取得 managed exclusive lock，生成一致可读、hash/库存验证过的备份与 recovery record；在隔离副本完成实际 additive migrations008–010、case import、Context registration 预演。不要关闭 writer/integrity guards。预演失败就提交具体阻断结果，不猜测补 identity。

3. 只导入3episodes、3official codes、12bindings，精确192raw rows：001872.SZ 72、001914.SZ 72、302132.SZ 48；dataset仅daily/daily_basic/adj_factor/stk_limit。批准的 case-set 内容保持完全相同。不得导入旧251drafts、5584carry-forward scopes、248BSE transitions 或未批准观察，不提供旧resolver fallback。不新增 stock_st/suspend_d identity绑定，不扩大old-code interval、推断alias、统一delist+1或未来episode。

4. 用已批准实际 Context 注册并固定 resolver snapshot；核对133request/raw、126output inputs、402246source rows。按已有恢复协议出版 COMPLETE generation，不使用半代、latest通配或旧generation混搭。预期每代192resolved+402054quarantine；394388旧resolved因缺证在新Context隔离，原7666quarantine保留。逐source row守恒，ordinal从0开始，NULL/native不改，空resolved输出也须保留schema、raw lineage和quarantine。原Context及旧代保持可复现，不改旧结果。

5. 用exact approved-dq-evidence及冻结policy运行真实DQ。63session记录全部NOT_CERTIFIED，0reference exceptions、0operationalBSE transitions；1374exact pre-BSE rows保持quarantine，只应用APPROVED_OUT_OF_SCOPE coverage处置。保留所有未解决finding及原15756finding键/原severity；新audit可追加新处置，不UPDATE旧audit、不扩大范围外集合。分别报告resolved/quarantine/范围外交集、certified/provisional/unknown causal pairs和remaining blockers。预期数据仍BLOCKED，不以DQ数下降宣布历史修复或准入。

6. 使用同一个Context在第二个独立generation重建，验证126/126logical hash、schema、units、逐source lineage相等；显式检验旧frozen Context可复现。完整保留两代及publication/recovery/DQ证据。不删除旧代，不关闭Context/pinned-member/source mismatch checks。

7. 从已批准实现运行必要离线检查、全suite一次、decoded secret scan；用transport denial/spy与库存变化证明市场请求为0。对新发现只记录缺证/冲突；若获批实现或政策需要变更，保留结果，集中交付审查，不自行扩展批准。文档/报告后续变化不机械重复全套。

8. 写`docs/reviews/r2-final-review.md`与公开hash/count索引，私有真实材料全部ignored。报告包括执行/实现/材料SHA区分、exact Approval/Context/hash、备份/预演/部署记录、两个COMPLETE generation、完整旧到新finding/source disposition账本、库存与历史保全、零请求证据、缺证限制。提交/推送后读取final exact-SHA CI，交付最终SHA和私有索引，一次等待独立R2 FINAL REVIEW。

作者状态为R2_FINAL_REVIEW_READY；工程执行可PASS，historical completeness / real-data admission保持BLOCKED。STOP：不得自动开始Phase1C.2或扩大历史数据请求。
