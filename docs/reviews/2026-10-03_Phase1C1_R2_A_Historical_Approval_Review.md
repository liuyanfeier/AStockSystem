# Phase1C.1-R2-A 历史案例、DQ evidence 与实际 Context 独立审批

审查材料 SHA：`f2df32b5d722fb3b73bf0e3a9294d5517c6fdfa1`。工程批准 SHA：`2f2592968a7f8e2500ee5e0bd3772a15a5c621f5`；实现 commit：`5108731af43bc0738144b6e835c5b65f5f5fc37f`。

结论：**本审批包通过有限范围审查，已生成真实 reviewer 决策、最终 case-set、DQ evidence、resolver snapshot 和 Context。无需再提交一轮审批包。历史完整性和真实数据准入仍 BLOCKED，R2-B 尚未获得执行授权，Phase1C.2 CLOSED。**

这次批准的用途是有限离线工程完整性验收。它没有完成全历史 identity/coverage remediation，也没有授权可回测数据。没有发现本次材料新增的工程阻断缺陷；先前 F1–F3 工程批准继续有效。

## 审查覆盖与完整性

`2f259…→f2df32…` 仅新增 6 个文档，现有实现、迁移、政策及已批准设计均未改变。最终 SHA 的 [GitHub Actions](https://github.com/liuyanfeier/AStockSystem/actions/runs/37092541651) 状态 success，已独立读取 job 111115740558 的步骤与日志：589 passed、4 warnings。没有对未改动的实现重复跑全套测试。

对原 warehouse 取得共享协调锁，以 managed read-only connection 核验：schema001–007、19 张表及基线内容哈希均一致，原库没有 WAL。181 个 raw 的 bytes/schema/manifest 均验证通过；旧代 126 个输出与 quarantine 逐行守恒；133 个 strict receipts 为 VALID/EXACT，0 failures，evidence hash 不变。

原库 SHA256：`2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`。

旧 identity hash：`83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c`。

原 1,102 个保护文件的路径集合、大小、字节哈希均保持不变。旧 26 项证据及修复 17 项证据全部按原索引核验。私有 ZIP 的 66 个唯一成员经过 CRC 与解压字节逐项核对，全部等于本地提交所指材料；不含 warehouse 或完整 raw Parquet。

原审批 ZIP SHA256：`fda8ecf5e945673d34a484b411226740551396408f130c6e61cc6937aee81a17`。

独立检查了全部 402,246 条 source-resolution dispositions：native、event、ordinal、capture hash、旧 resolved/security 或 quarantine reason 均与真实保留材料一致。原 15,756 条 finding 与旧台账完全一致，没有因本次有限 identity 审批直接关闭旧 finding。

## 历史案例裁定

346 个案例请求的裁定为：3 个 APPROVED（仅明确子集）、341 个 EVIDENCE_REQUIRED、1 个 CONFLICT、1 个 OUT_OF_SCOPE。另 5,584 个 carry-forward security scopes 全部保持 EVIDENCE_REQUIRED。作者旧 251 个 inactive drafts 和原证据保持原状，没有整体提升为 active。

| 案例 | 获批 listing start | 获批新代码生效日 | 精确源记录 | 裁定范围 |
|---|---|---|---:|---|
| 000022→001872 | 1993-05-05 | 2018-12-26 | 72 | 新代码生效后 EVENT_NATIVE，4 个 dataset，每个 18 条 |
| 000043→001914 | 1994-09-28 | 2019-12-16 | 72 | 新代码生效后 EVENT_NATIVE，4 个 dataset，每个 18 条 |
| 300114→302132 | 2010-08-27 | 2025-02-17 | 48 | 新代码生效后 EVENT_NATIVE，4 个 dataset，每个 12 条 |

000022 案例的上市、SZSE 与普通 A 股类别取自[发行报告](https://static.cninfo.com.cn/finalpage/2019-11-01/1207055051.PDF)，PDF index 5/7；[代码变更公告](https://static.cninfo.com.cn/finalpage/2018-12-26/1205690369.PDF) index 2–3 明确新旧代码、启用日期以及投资者股份类别和数量不变。000043 案例的上市与人民币普通股依据为[2022 半年报](https://static.cninfo.com.cn/finalpage/2022-08-27/1214420211.PDF) index 60、印刷页 61；[变更公告](https://disc.static.szse.cn/download/disc/disk02/finalpage/2019-12-16/a5a3d55e-cc2e-42e6-91c1-ea98235594fb.PDF) 明确新代码启用日期和持续上市主体。

300114 案例的上市日和原代码见[IPO 上市公告](https://disc.static.szse.cn/disc/disk01/finalpage/2010-08-26/0d5a2794-89fc-4d16-9a69-8b3372d778ad.PDF) index 3–4；普通 A 股类别见[股份流通公告](https://static.cninfo.com.cn/finalpage/2011-08-24/59867420.PDF) index 0；[2025 变更公告](https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF) index 1 明确 2025-02-17 启用 302132，原投资者股份类别和数量不变。公告签署日、披露 URL 日期和未知精确发布时间仍分开保存。

三个上市证券沿用与旧逐行结果一致的 stable security_id；没有把收购目标公司合并为上市证券。批准 3 个 episode、3 个 official EXCHANGE_CODE、12 条 binding，dataset 仅 daily、daily_basic、adj_factor、stk_limit。每条 binding 均精确列出 raw_object_id、zero-based ordinal、event；没有 stock_st/suspend_d binding，没有 RETROSPECTIVE 或 wildcard alias。

192 条均为旧代已 resolved 的记录。它们没有解救原 7,666 条 quarantine 中的任何一条。三个案例分别还有 24/21/72 条请求观察不获批准；这些数含案例材料中的请求范围，不能把补充 capture 都当作父 batch 源行。旧代码最早使用边界仍 EVIDENCE_REQUIRED。episode/code 的 null end 只表示未提供权威终止事实，不批准未来或全历史区间；精确观察集合限制了实际准入范围。

`VENUE:PRE_BSE_LEGACY` 的 1,374 条精确源记录批准为 **BSE coverage 范围外**。逐行核实旧原因 PRE_BSE_LEGACY，event 均早于 2021-11-15。[证监会原文](https://www.csrc.gov.cn/csrc/c101800/c7161925/content.shtml) 与保留的 BSE authority 均支持该开市日期。这些记录继续保留 raw/quarantine；该裁定不证明前身 venue、上市 episode 或经济意义上的行情不存在。

689009 的 [SSE 上市公告](https://www.sse.com.cn/disclosure/announcement/listing/c/c_20201027_5242851.shtml) 明确证券类别为存托凭证。该事实不解释 2021-11-12 的 provider STK/NULL，故仍 CONFLICT；不批准 STK identity 或 NULL/reference exception。

剩余历史代码、88 个 unknown limit asset、delist、episode/venue start 与历史 universe 继续缺证。248 个 BSE transition requests 只有部分官方 code-pair 与原观察，不能据此认证 episode 连续性、边界或交易日历；不进入本次 operational transition evidence。

## DQ evidence 裁定

冻结的 r2-v1 policy、设计 addendum 1–3 和 schema008–010 hash 继续获批，均与先前工程审查相同；价格/factor/因果容差和 NULL 策略未修改。

批准的 DQ envelope 含 63 个 `certified=false` SZSE session records 和 1,374 个 `APPROVED_OUT_OF_SCOPE` source dispositions。63 个 session 所引日期、previous_session、SSE venue 与原 calendar raw 均逐条核对。SSE 日历不能认证 SZSE；调用 session_basis 验证结果全部 NOT_CERTIFIED。没有认证 SZSE/BSE 日历，没有 reference_exceptions，没有 operational bse_transitions。

这批准的是 **用于如实产生 BLOCKED 审计的证据输入**。本次未运行真实 generation DQ，未认证 causal pairs，未裁定 factor 连续性通过。1,374 条独立范围外处置的效果由获批固定政策处理；它们不允许作者扩大范围或直接关闭旧 finding。

## 实际 Context 与最终 hash

实际 reviewer approval / knowledge 时间：`2026-10-03T03:52:23.856708+00:00`，即北京时间 2026-10-03 11:52:23.856708。episode/code availability 与 binding decision/availability 使用这个真实时间；first_observed_at 继续等于各 binding 精确 capture 的最早 retrieved_at。文档仅有日精度时保持 published_at=null，没有补造历史时刻。

Context 的 133 个 request/raw 配对与原 R1 回执集合完全一致；其中 126 个 output inputs 与父 generation=1 完全一致，共 402,246 行。parent identity、plan、knowledge、specs 均独立验证。CURRENT_RECONSTRUCTION / OBSERVED_CAPTURE 固定，fixture_only=false，不宣称 historical PIT。

| 最终语义对象 | Canonical hash |
|---|---|
| approved_case_set | `5f263b228917e2076984e8a71bcc9c6c4368ab415fab698e771ced9b0dd2c26c` |
| approved_dq_evidence | `4f7ad76a9d9613cc3b654c08994b583dc952b45c33051bad8539a32a231aaa19` |
| resolver snapshot | `5ed2a9d8831ca37efd4f50f754812903b5e52ea54bd34c56c5241ae720c92772` |
| actual Context | `0fd34edc7eb0d19c0cf1b9f39de1a6d3aa378da171e9f68f048890de2f2afda2` |
| input set | `b471998495a4a4f6d2d55796b3fa084c383b32c53f3af91eb37da9afba245a08` |

Canonical hash 与文件 bytes SHA256 分开记录，不能互换。批准元数据使 final payload/hash 与作者 proposal/hash 不同。实际 Context 使用工程批准 SHA `2f259…`，材料 SHA `f2df32…` 单独记录；6 个新增文档不会被误报为新实现。

离线纯模型预检通过：192/192 精确记录解析到正确 episode/security/new official code；实际 approval 之前 1 微秒全部拒绝；同 native/event 的其他 capture 全部拒绝。case-set/resolver/Context 规范序列化、Context JSON round-trip 和各批准 hash 相互一致。

未对原库执行 schema008–010、import_approved_cases、register_context、真实 generation 或 DQ。完整注册、出版和重建验证属于获授权后的 R2-B，当前模型预检不替代这些运行证据。

## 有限范围带来的数据结果

如果只应用本次获批集合，预期新 Context 每代 **192 resolved +402,054 quarantine =402,246 source rows**。其中 394,388 条旧 resolved 因缺乏独立历史证据，在新 Context 保持 quarantine；7,666 条旧 quarantine 继续保留。1,374 条开市前记录也仍属于 quarantine，只获得明确范围外 DQ disposition。

旧代 394,580 resolved、7,666 quarantine 以及旧 Context/文件保持原状。这不是覆盖旧结果，也不是丢弃缺证源行。批准该有限集合不代表新数据覆盖率改善；它验证严格证据准入的工程路径。需要有用的广覆盖数据，仍须进一步补足历史证据，另行审批，不能由 B 自行加 carry-forward 或回退旧 resolver。

| Gate | 本次裁定 |
|---|---|
| R2-A Engineering | PASS，沿用已批准修复实现 |
| Historical case-set | APPROVED_LIMITED_SCOPE |
| DQ evidence | APPROVED_FOR_BLOCKED_OFFLINE_AUDIT |
| Actual Context | APPROVED_LIMITED_INTEGRITY_ONLY |
| Full historical completeness / Real-data admission | BLOCKED |
| R2-B | NOT_AUTHORIZED；材料齐全，可在用户授权后做有限离线验收 |
| Phase1C.2 | CLOSED |

## 交付与下一步

公开审批索引：[Historical Approval Manifest](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C1_R2_A_Historical_Approval_Manifest.json)。

私有目录：[approval-manifest.json](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c1-r2-a-independent-approval/approval-manifest.json)，包含 case-decisions.json、approved-case-set.json、approved-dq-evidence.json、approved-resolver-snapshot.json、approved-context.json、documentary-review.json 与三份独立验证结果。私有 payload 不提交 Git。

完整私有交付：[独立批准包 ZIP](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/Phase1C1_R2_A_Independent_Approved_Package.zip)。ZIP 字节哈希、最终文件集合和凭证扫描结果另列于 [Final Handoff](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C1_R2_A_Approval_Final_Handoff.json)。

后续执行指令：[有限 R2-B Codex prompt](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_R2_B_Approved_Limited_Execution_Prompt.md)。只有用户明确把该指令交给实现 Codex 后才授权 B。本次没有迁移、导入或发布真实数据，市场/provider 请求为零；只读访问上述官方公告不属于市场数据请求。
