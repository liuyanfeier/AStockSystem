# Phase1C.1 R2-A F1–F3 修复独立复审

日期：2026-10-03（Asia/Shanghai）。**工程复审结论：PASS。F1、F2、F3 全部关闭；本次范围内未发现新增阻断项。**

本次批准精确 SHA 的工程实现、修订后的 DQ/context/publication 设计与列出的 artifact hashes。历史 case_set、实际 DQ evidence 和真实 derivation context 尚未批准；不能将此工程 PASS 解释为完整 R2-A 历史审批完成、R2-B 执行授权或 real-data PASS。Phase1C.2 继续 CLOSED。

## 1. 版本与审查范围

| 项目 | 版本 / 证据 |
|---|---|
| R1 FINAL 已批准 baseline | `cc458ce2e8229dcc914e9a45ae2ac6186f48c45c` |
| 上次 R2-A CHANGES_REQUIRED | `68b62ca6fb65e28b4ea059ca8c197c244b5a2253` |
| 修复设计先行冻结 | `e59d012e65a2d12301dd0ce76ed80bff60df906e` |
| 修复实现 | `5108731af43bc0738144b6e835c5b65f5f5fc37f` |
| **本次独立批准的最终 SHA** | **`2f2592968a7f8e2500ee5e0bd3772a15a5c621f5`** |
| 最终精确 SHA CI | [Actions 37088585949](https://github.com/liuyanfeier/AStockSystem/actions/runs/37088585949)，job `111103850242`，SUCCESS |

审查覆盖三个修复 commit 的全部差异：两个 source 模块、尚未部署的 SQL009、设计 addendum 3、原测试更新、新回归测试、operation contract 和交付材料。最终 SHA 与实现 commit 的差异仅为 `r2-a-fixes-review.md` / `r2-a-fixes-manifest.json`；原三份冻结设计文件及 DQ policy 保持原字节。设计 addendum 3 在实现前提交。

## 2. 原三项缺陷关闭

| Finding | 独立复审结果 |
|---|---|
| **F1 / P1 — 孤立 daily 缺 factor 仍 PASS** | **CLOSED。** 每根 daily 按 security/episode/event 查找唯一有限正 factor。缺失、无效、重复或错误 scope 均有实际 daily source-row finding。原单根 daily + typed empty adj_factor 的复现现在为 1 finding，local/batch 均 BLOCKED。 |
| **F2 / P2 — pair 异常定位到最后一天** | **CLOSED。** finding 指向实际 current event/raw row，并把 previous event/raw row/episode 纳入稳定 key。原三天复现中的异常日 May 7 现在 BLOCKED，正常日 May 8 PASS；causal/factor finding 均正确记为 May 7。追加正常后续行情的集成回归保持既有 finding payload/key 不变。 |
| **F3 / P2 — 追加 binding 版本使旧 context 失效** | **CLOSED。** 新增 context 专属持久化 resolver snapshot，注册时与 context/inputs 原子落库。旧 context 使用固定 membership；校验 hash 和 pinned live records，不自动改用新版本。独立复现中旧、新 context 均可选择并通过合成 DQ，旧 context 再建与原 generation 的 logical/schema/source 相等；篡改 pinned binding 后选择被拒绝。 |

实现定位：[逐 daily factor 检查](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction_dq.py:257)、[实际 pair finding](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction_dq.py:141)、[context resolver snapshot 验证](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction.py:179)。

F3 没有删除 hash 检查：缺失 snapshot、修改 snapshot payload/membership、修改或删除被固定的 episode/code/binding/observation 均拒绝。注册、conversion、publication、COMPLETE selection、DQ 和 rebuild 均使用该固定 resolver。原 R1 resolver/curation/DQ 与 SQL001–007 未改。

## 3. 独立验证结果

- **精确 SHA CI：589 passed，4 warnings，927.07s。** 已通过连接器读取远端 run/job/log，核对 SHA、success 与实际测试汇总；offline diagnostics、contracts、specs/plans 步骤均成功。
- **本地独立运行相关四组测试：109 passed，169.19s。** 包括原三组及新增 26 个回归，也包括生产形状 admission、事务/并发恢复和防篡改检查。
- **独立重跑原三个复现：全部得到正确行为。** 使用本 Review 自有合成 fixture，未调用作者的私有运行脚本。F3 另外构建新 context、旧 context 的第二个完整 generation，并验证 pinned record 篡改拒绝。
- **数学语义独立对照：200 个合成 scenario、600 个组、4,200 根 bar。** 新 runner 与未修改的旧 `causal_audit` 的 causal series 和 aggregate mismatch/pair counts 精确一致；覆盖认证、provisional、未知 session、gap 和缺失/无效 factor。1,696 个 certified pairs、2,559 个 pair findings 的 current/previous source scope 校验通过。

固定政策保持：price `0.011`；causal `0.011` percentage points；factor `0.011 + 100 * 0.011 / current pre_close`。没有放宽容差、改变因果链、填补 NULL/factor 或使用 latest-factor 前复权。

测试缓存与合成库仅写当前 Review 的工作目录，关闭 Python bytecode。独立 probe/保护审计阻断 provider construction/fetch、HTTP/socket 和 settings 入口；计数均 0。没有运行新真实 generation、真实 R2 DQ 或市场请求。

## 4. 原库、历史材料与交付证据

原库保护与数据引用已重新独立核验：

| 项目 | 复审结果 |
|---|---|
| 原 schema 与表 | 001–007、19 张原表内容摘要一致，无真实 R2 部署 |
| Raw | 181 个对象 manifest/run 验证有效 |
| Strict receipt | 133 条 VALID / EXACT，failure 0；completion bindings / upgrade audits 各 133 |
| 旧 curated/lineage | 252 个旧对象、文件及对应保护记录未改变 |
| 旧 generation1 | 126 输出；逐 source ordinal 证明 402,246 = 394,580 resolved + 7,666 quarantine |
| 受保护文件 | 1,102 个路径/大小/哈希与 R1-G0 inventory 一致，差异 0 |
| 旧跟踪资料 | 旧 source、SQL001–007、spec/review 未改变；合同与字典保持原字节前缀，AGENTS 更新对应授权范围 |
| 上轮 R2-A 材料 | 26 个私有 artifact、原公开 report/manifest、candidate/proposal hashes 保持一致 |
| 本轮修复材料 | 17 个 indexed artifact 的 size/hash 有效，final handoff 的 report/manifest/CI-log hashes 匹配 |
| 候选 source scope | 再次验证 423,702 次原 raw 观测引用；这是可重叠引用次数，不是唯一异常数量 |
| 审批生效 | 真实新 bindings/generations 0；approved_case_set/hash 仍为 null |

原库 SHA256 验证前后保持：

```text
2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba
```

Frozen identity：`83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c`。
Strict receipt evidence：`0992ccac745f6e5299615caaf7a68e4aabf9fb4d90c49e1d1c742716bf4e3597`。

作者 decoded/current-credential/credential-pattern 扫描记录为 PASS，并由保留的哈希索引约束；本次独立检查没有加载当前凭据。公开修复差异为 source/design/tests/review 文件，没有提交 .env、数据库、WAL 或真实 dataset。

## 5. 工程批准对象与历史审批边界

**Engineering exact SHA、修订后的 policy/design/context/publication 模型及所列源码/SQL hashes 获独立批准。** 可核对的完整工程批准对象记录在 [Engineering approval manifest](Phase1C1_R2_A_Engineering_Approval_Manifest.json)。

| 关键 artifact | 批准 hash |
|---|---|
| DQ policy `r2-v1.json` | `f2c3267ddbd8eecc55d29c3ebac4eae971442e77d78181b5757676e37e9bfe03` |
| Design v1 | `2093b9511f263bd128f0f9c396916b8c69960202eed8a604186a41374b37b3d5` |
| Addendum 1 | `2e5cfeb6bd8cfc793eaa29e999cf0d733d8ac87d9683d96e0c94c2fe23871553` |
| Addendum 2 | `1566336f7f6f15efa0b22e45e14a88b1b7da7c830672dd35780ab4f3fa7f34a3` |
| **Addendum 3** | **`8d4e77c29c8a56e70fc3a4cb2ac8746a049c8cfc3a6e7d992defe9af7062f069`** |
| SQL009（未部署） | `d8fc4ae38d86239e14939d8beabc132d2aa790affe3b849651310d1d8f604fd0` |

批准的是工程实现与固定规则。实际生产 `Approval` / `Context` 还必须具有经独立审批的 executable case_set、实际 DQ evidence、resolver/input membership、真实 knowledge/approval 时间，以及 addendum 3 hash；不能从作者 proposal 自动生成批准。现有 `derivation-context-draft-v2.json` 保持为未批准草稿，不能直接作为可执行的新 Context。

历史候选仍是原 346 个 review items、251 个 inactive model-valid drafts、5,584 个 carry-forward security scopes。观测 min/max 不能自动作为权威 listing/termination interval 或历史 universe。Venue sessions/universe、未知 limit 资产、NULL/CDR 冲突、delist 语义与旧 stock_basic omission 原因仍需证据；不把缺失事实包装成批准。

| 项目 | 本次状态 |
|---|---|
| F1/F2/F3 修复 | CLOSED |
| R2-A Engineering | **PASS** |
| R2-A Historical case / 实际 DQ evidence / 执行 context | **审批未完成** |
| approved_case_set / hash | null / null |
| R2-B | **NOT_AUTHORIZED** |
| Real-data gate | **BLOCKED** |
| Phase1C.2 | **CLOSED** |

本次 Review 不要求继续拆分工程 Gate，也不要求再做工程返工。下一步是在同一个审批材料批次中完成历史 case 的明确可执行 scope/证据裁定、DQ evidence 和更新后的 Context proposal；未证实部分继续保留 EVIDENCE_REQUIRED/CONFLICT/quarantine。待这些对象获独立批准并由用户明确授权后，才进入 R2-B 的 existing-raw 离线派生/双重重建。不得重新请求 133 个市场请求。

独立证据：[原库保护](R2A_Fixes_Independent_Preservation.json)、[三项修复复现](R2A_Fixes_Independent_Repros.json)、[数学对照](R2A_Fixes_Math_Equivalence.json)、[合成复现脚本](R2A_Fixes_Independent_Regression_Repros.py)。原 CHANGES_REQUIRED 报告保持不变。
