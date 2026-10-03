# Phase1C.1-R2-B blocker 独立 REVIEW

审查最终 SHA：`63a166b89f44850dd9fa2efa8ab06c0e49a8bfd5`；实际执行 SHA：`f597671fd553e2240b3793ac342bd3b7201096cc`。上次工程 SHA：`2f2592968a7f8e2500ee5e0bd3772a15a5c621f5`；实现 commit：`5108731af43bc0738144b6e835c5b65f5f5fc37f`。

**结论：阻断已独立确认，R2-B / R2 FINAL 为 BLOCKED，工程需要一项 P1 修复。作者在隔离预演失败后停止原库部署符合批准指令。原历史案例有限裁定继续保留，当前 resolver / Context v1 暂停执行；没有 R2 FINAL PASS，Phase1C.2 继续 CLOSED。**

本次不是缺少另一次市场请求。原 3 个案例、192 条精确源记录的历史证据没有改变。问题位于 Python 模型、TIMESTAMPTZ 存储和 snapshot 完整性检查之间，必须统一规范时间表示并验证实际 SQL 读回。

## P1：resolver 完整性使用时间字符串，而非稳定的时间点表示

位置：[ProviderResolver.snapshot_hash](/Users/yanliu/Documents/AStockSystem/src/astock/data/provider_identity.py:186)、[resolver_payload](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction.py:172)。

模型 JSON 保留 aware datetime 的 offset 拼写。审批 payload 混用 UTC/Z 和 +08:00；SQL TIMESTAMPTZ 读回由会话时区决定表达。同一 instant 因此产生不同 JSON 和 digest。[DuckDB 官方说明](https://duckdb.org/docs/current/sql/data_types/timestamp.html) 明确 TIMESTAMPTZ 保存绝对时间点，不保存原时区信息；其格式化受配置时区影响。独立实测也确认该行为。

批准 resolver hash 为 `5ed2a9d8831ca37efd4f50f754812903b5e52ea54bd34c56c5241ae720c92772`。在作者保留的实际隔离库上，独立只读载入获批成员，结果如下：

| 会话时区 | 原实现 readback hash | 只有 offset 表示不同的字段数 |
|---|---|---:|
| Asia/Shanghai | `df9325a0875c6e64c7354762be1b716dcae91e96522795b7c9d210227eeaa222` | 33 |
| UTC | `408a3a328da5858a2e400c09675bedb2623f8afb6ff00d2a501854608454dbe3` | 12 |
| America/New_York | `2b27ed78abbc47a25b782bd7bf7660c0c3500ec8110796c97e0c5f6f4916d94c` | 45 |
| Asia/Kathmandu | `8f7b25b7e22d8bc55508dbd13ae0838b98dc49c948dcff49f01022bfa4675b86` | 45 |

四种会话下按 immutable ID 对齐后，episodes/codes/bindings 模型语义全部相等，观察集合和顺序、其他字段均不变。对应注册前检查全部拒绝原 Context：`Resolver snapshot changed`。作者的 synthetic in-memory SQL 复现也独立运行通过。

仅设置 UTC 不会保留原 payload 内 12 个 +08:00 的 first_observed_at 拼写；不能当作修复。直接改成某次 readback hash、修改批准文件、重新填写过去的 approval 时间或关闭检查，均不解决完整性协议。

### 同一缺陷还影响已固定 snapshot 的成员校验

位置：[load_context_resolver 的成员比较](/Users/yanliu/Documents/AStockSystem/src/astock/data/reconstruction.py:200)。

`members` 与 pinned member 都用 `model_dump(mode='json')` 比较。同一 instant 的不同 offset 字符串也被当作成员篡改。这意味着仅修复 snapshot_hash / resolver_payload，后续在另一个时区读取已注册 Context 仍可能失败。

独立诊断对实际隔离库保持只读，以内存模拟的 snapshot 查询结果进入既存 Context 分支：提供 UTC payload 与其一致的旧 digest，实际成员仍从 Asia/Shanghai 会话读取。payload checksum 与 ProviderResolver hash 校验均通过，最终成员比较抛出 `Pinned resolver member changed/missing`。模拟没有生产 Approval，没有插入或注册 Context。

这属于同一 P1 根因的第二个入口，应在一次修复中同时覆盖，不能删除 pinned-member、checksum、missing/tamper 检查。

## 可审查的修复规则与验证边界

候选规则：仅对 resolver 明确的 aware datetime 字段按同一 instant 转成 UTC，固定六位微秒和 Z；published_at=null 保持 null。日期字段、native、IDs、scope、evidence、批准引用与顺序保留原语义。共用同一实现生成 snapshot payload、digest 和 pinned/live member 比较值。禁止 `.replace(tzinfo=UTC)` 把当地时刻重新解释为另一个时间点。

字段包括 episode 的 published_at/retrieved_at/available_at、code 的 available_at、binding 的 first_observed_at/decision_at/available_at。不能通过全局改写 receipt_integrity.serial、历史 raw 或旧 frozen identity 来修复 R2。

该候选规则在本轮纯诊断中对四种真实 readback 和原批准 payload 得到完全相同的规范结果，且幂等。时间点增加 1 微秒、native、security_id、official code start、approval_ref、source ordinal 六类实质变化仍改变 digest。候选规范 digest 恰为上述 UTC readback digest，但 **它不是新批准 hash**；获批实现未修复，其他调用路径也尚未验证，不得据此替换 v1 批准。

工程修复须包括实际 SQL 008–010/import/register/reopen/load/rebuild 的合成回归，并保留 F1–F3 的缺 factor、逐日 causal status、追加 resolver 成员后旧 Context 稳定性和 pinned 篡改拒绝回归。规范化协议要以新的冻结 design addendum 明确；旧设计/批准文件不重写。

## 原库、备份、历史与隔离证据

`f2df32…→63a166…` 只有 7 个新增文档/合成复现文件，生产实现、旧文件、AGENTS、schema 和政策未改变；Git clean。新 private index 24 个 artifact 字节 hash 全部匹配；blocker ZIP 29 个唯一成员 CRC 和解压字节均匹配，不含数据库、完整 raw/curated 文件或 .env。新独立批准目录的 11 个文件逐字节等于 reviewer 原包，未改变批准 scope/time/hash。

原 DB 与 verified backup 均为 `2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`。共享协调锁下独立只读检查二者均可读，schema001–007、19 张表内容与原基线一致。原库无 WAL。181 个 raw bytes/schema/manifests 通过；旧252curated/lineage、原1102保护文件及隔离复制的1102保护文件均未变化；旧26项与修复17项证据保持不变。

原133 strict receipts：VALID / EXACT，0 failures；evidence hash 仍为 `0992ccac745f6e5299615caaf7a68e4aabf9fb4d90c49e1d1c742716bf4e3597`。

本轮在内存独立重建旧 frozen Context 的全部126个输出：126/126 logical hashes 与旧DB/lineage一致，quarantine精确相同；394580resolved+7666quarantine=402246源行。没有发布重建文件或写入DB。

隔离 DB 的旧19张表内容（schema_version按原001–007子集）保持原基线。隔离 schema 为001–010，恰有3episodes、3codes、12bindings、192observations。derivation_context/generation/input/output/snapshot/quarantine 均为0，隔离 DB 的文件 hash 也保持作者交付值。不存在原库 R2 deployment；不用原库 rollback。

所有未执行项目保持 NOT_EXECUTED：原库008–010部署、真实 Context 注册、两个 COMPLETE 新代、实际 DQ 和新 finding/source-disposition 账本。192resolved+402054quarantine仍是有限集合的预期，并非执行结果。旧15756finding不会被缺少的新结果关闭。

## CI、批准状态与后续

已独立从 GitHub 读取最终 SHA 的 run/jobs/logs：[37096692371](https://github.com/liuyanfeier/AStockSystem/actions/runs/37096692371)，job111127959810全部步骤success，589passed、4warnings、642.38s。作者 local589passed、1warning记录与冻结日志一致。CI绿色不覆盖本次 SQL roundtrip 缺陷；本轮没有对未改动的实现重复完整suite。

| 状态 | 独立裁定 |
|---|---|
| R1 final / 历史保全 | PASS，未改变 |
| 本次 blocker 报告与安全停止 | VERIFIED，符合执行指令 |
| R2 工程准入 | CHANGES_REQUIRED：一项P1，两个入口 |
| 原有限历史case / DQ事实裁定 | 保留；不要求重新调查或批准扩大范围 |
| resolver / 实际Context v1 执行 | SUSPENDED_PENDING_ENGINEERING_FIX_AND_MATCHED_REAPPROVAL |
| R2-B / R2 FINAL | BLOCKED / NOT_READY |
| historical completeness / real-data admission | BLOCKED |
| Phase1C.2 | CLOSED |

上一轮 reviewer 校验覆盖模型、JSON和精确raw scope，未覆盖真实SQL导入读回，是该次工程验证的缺口。本次确认后，旧审批记录仍保留原状，v1执行暂缓；修复SHA通过统一复审后，再由reviewer生成匹配的新版本执行批准。不能把旧SHA/Context重新标记为修复后版本，也不能由作者重签生产Approval。

下一步无需重做历史调查。实现Codex应一次完成两处规范化、SQL roundtrip/reopen/tamper回归、Context候选影响清单和final-SHA CI，再交一次修复审查；通过后更新执行批准并续跑已有有限B。实际实现及批准 hash 的改变构成必要审查边界，不再增加逐内部Gate停顿。

交付：[修复指令](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_R2_B_Time_Integrity_Fix_Prompt.md)、[独立验证JSON](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/R2B_Blocker_Independent_Validation.json)、[本轮状态Manifest](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C1_R2_B_Blocker_Review_Manifest.json)。
