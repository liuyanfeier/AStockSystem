# Phase 1C.1 R2-A Independent Review

审查日期：2026-10-03（Asia/Shanghai）。结论：**CHANGES_REQUIRED，1 项 P1、2 项 P2，均已独立复现。**

R2-A 工程暂不通过；R2-B 不放行。Real-data gate 继续 BLOCKED，Phase 1C.2 继续 CLOSED。本次仅 Review，没有修改项目源码、部署迁移、批准真实映射、运行新真实 generation，或请求市场数据。

## 1. 精确审查范围与依据

| 项目 | 精确版本 |
|---|---|
| 已批准 R1 FINAL baseline | `cc458ce2e8229dcc914e9a45ae2ac6186f48c45c` |
| R2-A 冻结设计 commit | `1f4d983d460c5dbf6c1f388397b33ad316bd60a7` |
| R2-A 实现 commit | `39be745e4aa62a7d07102b8d4e82fbbf4e4f30b4` |
| 本次最终交付 / 审查 SHA | `68b62ca6fb65e28b4ea059ca8c197c244b5a2253` |
| 精确 SHA CI | [GitHub Actions 37022889305](https://github.com/liuyanfeier/AStockSystem/actions/runs/37022889305)，job `110890137888`，SUCCESS |

从 baseline 到最终 SHA 整体审查：三个新增 Python 模块、三份新增 SQL、三组测试、DQ policy、冻结设计及两个 addenda、operation contract、proposal/context draft、私有证据索引与原库保护材料。最终交付与实现 commit 的差异仅为 `r2-a-review.md` 和 `r2-a-manifest.json`。

本次使用授权的 v1.1 两批流程。R2-A 的设计、实现、合成验证与候选准备均在同一批次 Review；不会恢复 G0/G1/G3/G4 的逐步停顿。

## 2. 必须修复的发现

### R2A-F1 — P1：单根或分段首根行情缺少 factor，DQ 仍返回 PASS

位置：[reconstruction_dq.py:230](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction_dq.py:230)、[reconstruction_dq.py:272](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction_dq.py:272)。

当前检查会验证实际存在的 factor 是否非正，并在相邻行情配对时统计 `missing_factor_pairs`，但没有逐根检查 daily 所需的 factor 是否存在。没有相邻 pair 时，这两项无法发现缺失。

独立复现使用完整的六个市场 dataset 输出、已批准的合成 SZSE episode/bindings、认证 session、无 quarantine；daily 有一根合法行情，adj_factor 是合法的 typed empty partition。完整 publication 已通过。随后：

```text
daily resolved rows = 1
adj_factor source rows = 0
audit findings = 0
local_status = PASS
batch_gate_status = PASS
```

这会把缺少独立复权校验输入的输出放行。旧 DQ 在 [slice_dq.py:147](/Users/yanliu/Documents/AStockSystem/src/astock/data/slice_dq.py:147) 对每根 daily 检查 `daily_missing_factor`；新 runner 遗漏了该项。存在数据间隔或缺少认证前序 session 时，也不能以“没有 pair”替代每根 factor 完整性检查。

修复要求：对每个已解析 daily 的 security/episode/event 独立检查 factor 的存在及数值有效性，缺失或无效应产生 blocking finding，指向实际 source row/date。保留现有 pair 校验与固定容差，禁止填补或重新请求 factor。增加孤立行情、分段首根以及有效 factor 的正负例。

### R2A-F2 — P2：收益异常被记到 episode 最后一天，逐输出质量结论错误

位置：[reconstruction_dq.py:270](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction_dq.py:270)、[reconstruction_dq.py:315](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction_dq.py:315)。

当前 runner 用 episode 聚合的 mismatch 数量生成 finding，并统一把 `event_date` 设为整组行情的最大日期。随后 per-output quality 又按 dataset/date 分配 finding。

独立复现构造连续认证的三天行情：2025-05-06 正常；2025-05-07 的 close/pre_close 表示 10% 收益，而 pct_chg 为 0，causal/factor 各有一项 mismatch；2025-05-08 的对应 pair 正常。结果：

```text
实际异常 pair 日期：2025-05-07
CAUSAL_RETURN_MISMATCH 日期：2025-05-08
FACTOR_RETURN_MISMATCH 日期：2025-05-08
2025-05-07 daily quality：PASS
2025-05-08 daily quality：BLOCKED
```

Batch gate 虽然仍 BLOCKED，但异常输出被标为 PASS，正确输出被错误阻断。追加正常的后续行情还会移动 finding key，使旧异常看似消失并生成新的异常，影响 append-only 处置台账的可解释性。

修复要求：逐个实际异常 pair 产生 finding，记录 current/previous 的真实 event、source row 与 episode 关联；聚合计数单独保留。逐输出质量必须根据实际异常 scope 分配。测试追加正常后续行情不改变原异常定位和稳定 key，且原异常日 BLOCKED、正常日 PASS。保持原因果与 factor 公式、单位和容差。

### R2A-F3 — P2：追加合法 binding 版本使已冻结的旧 context 失效

位置：[reconstruction.py:320](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction.py:320)，关联 [reconstruction.py:160](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction.py:160)。

Context 保存 resolver hash，但 `validate_context()` 将它与当前全库 resolver hash 比较。没有保存可以独立加载的 context resolver membership/snapshot。只要合法追加 binding、episode 或 code，新全库 hash 就变化，旧 context 会被拒绝。

独立复现先发布一个完整合成 generation，再通过 `import_approved_cases()` 追加更晚批准、可见时间更晚的 v2 binding。没有修改原 binding、raw、context 或输出。按旧 `knowledge_as_of` 调用 resolver 仍正确返回 v1；然而选择旧的明确 COMPLETE context/generation 返回：

```text
old knowledge resolves original binding = true
select_complete(old context, old generation)
→ ValueError: Design/resolver snapshot changed
```

旧 R1 机制保持不变，但新 R2 context 的长期可选择、审计和重建能力依赖于全库永远不再追加知识，违背版本化映射与冻结 context 的用途。同一 context 的第二次 rebuild 也会被这个入口拒绝。

修复要求：持久化并验证 context 专属的不可变 resolver snapshot/membership，读取、DQ、重建均使用已固定的那一版。后续合法追加不得使旧 context 失效；对旧 context 实际引用记录的篡改仍必须拒绝。不能简单删除 hash 检查。补充“旧 context COMPLETE → 追加新版本/新 context → 两者均可明确选择、旧 context 再构建一致”的集成回归，以及篡改 pinned 内容的负例。

## 3. 独立验证与已通过部分

精确最终 SHA 的远端 CI：**563 passed，4 warnings，805.95s**，offline diagnostics/contract/spec/plan 检查通过。本地独立运行新增三组测试：**83 passed，119.13s**。额外三个合成 probe 均确认以上错误行为；现有测试通过不能覆盖这些缺口。

本地测试命令使用项目 `.venv`，关闭 bytecode，并把 pytest cache/basetemp 指向本 Review 工作目录。额外 probe 只在临时合成 root/in-memory DuckDB 中迁移和出版。provider/http/socket 入口被阻断，调用计数为零。

以下保护与对账已独立核验：

| 项目 | 结果 |
|---|---|
| 原库 schema / 表内容 | 001–007、19 张表逐表内容摘要一致，未应用 R2 schema |
| 原始 raw | 181 个对象按 raw manifest/run 验证有效 |
| R1 receipt | 133 条，VALID / EXACT，failure 0；completion bindings 与 upgrade audits 各 133 |
| 旧 generation1 | 126 输出；402,246 source rows = 394,580 resolved + 7,666 quarantine，逐 source ordinal 守恒 |
| 历史受保护文件 | 1,102 个路径/大小/哈希与 R1-G0 inventory 一致；包含旧 raw、252 curated/lineage 和旧私有演练材料 |
| 历史跟踪文件 | 仅 AGENTS 与合同/字典有授权变更；合同/字典保留原字节前缀；旧 source、SQL001–007、specs/reviews 未改 |
| 私有证据索引 | 26 项 artifact 的 size/hash 一致；公开 manifest 的 source/policy/design/candidate hash 一致 |
| 旧异常台账 | 15,756 唯一 finding keys，2,512 ERROR / 13,244 REVIEW；其中 unexplained-missing coverage 1,226 |
| Quarantine | 5,008 interval / 1,374 PRE_BSE_LEGACY / 1,284 NO_MAPPING，与原 lineage source refs 一致 |
| BSE / candidate source scope | 16,996 BSE 观测；候选及 carry-forward 的 dataset/native/event/retrieval/source-hash 与实际 raw 对应 |
| 原 resolved 显式 carry-forward | 386,309 + 8,271 = 394,580 个 source rows，不重叠且覆盖原 resolved 集合 |
| 批准与生效状态 | approved_case_set/hash 仍为 null；没有真实新 bindings 或 generations |

合计核对 423,702 次观测引用；其中存在跨材料重复引用，不是新增数据量或唯一异常量。

原数据库本次验证前后 SHA256 均为：

```text
2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba
```

原 identity hash 仍为：

```text
83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c
```

Strict receipt aggregate evidence hash 仍为：

```text
0992ccac745f6e5299615caaf7a68e4aabf9fb4d90c49e1d1c742716bf4e3597
```

现有模型对 endpoint/capture/row/knowledge 的显式 scope、独立官方 code interval、partial generation 拒绝、受保护文件、不覆盖 orphan、source conservation、append-only audit 等主体方向合理。上述结论支持保留当前方案并集中修复，不要求推倒重做。

## 4. 历史候选与政策审批结论

346 个候选 review items 中，251 个有 model-valid inactive drafts；另有 5,584 个原 resolved security scopes 的显式 carry-forward 候选。**这些数量和代码合法性不构成历史事实批准。** Observation envelope 的 min/max 不能自动成为权威 listing/termination interval 或完整历史 universe。

本次重读三份官方实施公告，确认以下文书事实：

| 候选 | 文书事实与独立复核范围 |
|---|---|
| 000022.SZ → 001872.SZ | 实施日 2018-12-26，公告说明上市主体/股份延续。[实施公告](https://static.cninfo.com.cn/finalpage/2018-12-26/1205690369.PDF) |
| 000043.SZ → 001914.SZ | 实施日 2019-12-16，公告说明上市主体/股份延续。[实施公告](https://disc.static.szse.cn/download/disc/disk02/finalpage/2019-12-16/a5a3d55e-cc2e-42e6-91c1-ea98235594fb.PDF) |
| 300114.SZ → 302132.SZ | 实施日 2025-02-17，公告说明上市主体/股份延续。[实施公告](https://disc.static.szse.cn/disc/disk03/finalpage/2025-02-15/cedb693a-f5ee-4463-9682-ea33d406b569.PDF) |
| 689009.SH | SSE 公告确认其为存托凭证，2020-10-29 上市；不能据此解释特定 stk_limit NULL 或批准填补/豁免。[上交所公告](https://www.sse.com.cn/disclosure/announcement/listing/c/c_20201027_5242851.shtml) |

BSE 248 对官方旧证据沿用既有批准材料，其 preserved authority artifact 哈希已复核；本次没有重新获取 mapping list，也没有据此批准全部 248 个 episode/provider scopes。旧代码在当前 stock_basic 中缺失的原因、未知 limit instrument 资产类别、NULL/CDR 冲突、历史 universe、各 venue session 和 delist 元数据语义仍不能自动确认。

本次审批状态：

| 审批项 | 判定 |
|---|---|
| Engineering exact SHA | CHANGES_REQUIRED |
| 冻结 policy/design/addenda/context/publication | 当前 hash 已核对；审批暂不授予，需包含三项修复后统一 Review |
| Historical case set | 未批准；`approved_case_set = null`，`approved_case_set_hash = null` |
| R2-A | 尚未通过 |
| R2-B | NOT_AUTHORIZED |
| Real-data gate | BLOCKED |
| Phase 1C.2 | CLOSED |

缺失的真实历史证据可以继续保留 EVIDENCE_REQUIRED/CONFLICT/quarantine；不得为通过 Review 放宽容差、填补 NULL、猜测 alias/继承身份、缩短 universe 或 backdate knowledge。

## 5. 下一步：一次集中修复，一次统一复审

将 F1/F2/F3 放在同一个 R2-A 修复批次。冻结 design v1 保持原字节，需要改变设计时追加 addendum 并更新 hash；新增 R2 schema 尚未部署，其调整与实现一起提交复审，SQL001–007 保持原样。先完成三个针对性集成回归，再跑一次最终完整 offline suite/diagnostics/secret scan，推送后核验最终精确 SHA CI。

原 evidence/candidate 材料保留；仅更新修复所需设计、source hashes、测试和交付证据。再次提交最终 SHA、CI 和统一 Review package 后停在 R2_A_REVIEW_READY。此 Review 没有授权 R2-B，也没有授权任何新的真实市场请求。

可直接使用：[R2-A 集中修复 prompt](Codex_Phase1C1_R2_A_Consolidated_Fix_Prompt.md)。独立证明：[缺陷复现结果](R2A_Independent_Repros.json)、[原库与证据保护结果](R2A_Independent_Preservation.json)、[合成复现脚本](R2A_Independent_Regression_Repros.py)。
