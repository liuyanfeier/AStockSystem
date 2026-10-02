# Phase 1C.1-R1 — Engineering Integrity Remediation

规格 v1.0 · 2026-10-02 · 状态：DESIGN READY / EXECUTION NOT STARTED。

依据：[完整演练证据](https://github.com/liuyanfeier/AStockSystem/blob/2aba10fc143a8b1975b00b7a2a965cd1465942a7/docs/reviews/2026-10-01-phase1c1-review.md)、[migration006](https://github.com/liuyanfeier/AStockSystem/blob/2aba10fc143a8b1975b00b7a2a965cd1465942a7/sql/006_bounded_slice_lifecycle.sql)、[raw verifier](https://github.com/liuyanfeier/AStockSystem/blob/2aba10fc143a8b1975b00b7a2a965cd1465942a7/src/astock/data/raw_writer.py)，以及引用对话的全量 REVIEW。真实私有对象尚未在本次重新验算；本规格中的真实计数为该公开报告基线。

## 1. 目标和边界

先修复“系统如何证明一次请求真的完成”。在现有 Phase1C.1 上追加修复，不重做演练。审查基线是 `2aba10fc143a8b1975b00b7a2a965cd1465942a7`；执行前读取实际 HEAD 并记录差异。存在后续未审变更时不得 reset、覆盖或假定它们获批。

真实 batch：`1d34d71f-c711-4893-9729-0b719bbba6dd`。冻结计划：7 slices、21 market dates、7 SSE calendar requests、6 market datasets/date，共 133 requests。此前公开报告：133 HTTP attempts、133 raw objects；加早期 48 objects 共 181；旧 curated generation 0/1 各 126 objects。

本轮新增市场请求预算为 **0**，包括 calendar、identity metadata 和旧 probe。只允许离线读取已有私有证据，以及代码/规格/测试/CI。禁止调用真实 capture/resume CLI 来验证修复；该路径既要求 live/token，又检查 capture code_commit，不能作为离线审计入口。

R1 不改变 identity、venue、DQ 容差、coverage policy 或 curated 结果。保持 raw/历史 receipts/attempts/started_at/旧审计内容。新增 schema 和审计记录可以追加；不为消除错误修补历史成功事实。

## 2. 已确认的漏洞

`sql/006_bounded_slice_lifecycle.sql` 只对 `slice_request.object_id` 施加 UNIQUE，没有 raw manifest FK。`resume_batch()` 忽略 COMPLETE 的 raw 证明；capture 对 COMPLETE 仅调用按 run 验证的 `verify_batch()`。`verify_batch()` 对空 run 列表或某个 run 的零 manifest 仍返回 True。`_object_table()` 校验一条 raw/run、dataset/params，却没有证明 raw.object_id 等于 COMPLETE receipt.object_id。

因此修复不能只新增 FK 或只把 `verify_batch` 改为非空：必须覆盖所有承认 COMPLETE、跳过请求、完成本地恢复、进入 curation/DQ 和标记 CAPTURED 的入口。

## 3. 核心不变量

对于冻结计划中每条 COMPLETE request r，必须同时满足：

```text
计划中恰有一个 r.request_id / ordinal，receipt 与冻结 request 相同
r.attempts == 1
ingestion_run(r.run_id) 恰有一个，source/dataset/mode 与原契约一致
raw_object_manifest WHERE run_id=r.run_id 恰有一个对象 m
m.object_id == r.object_id
m.run_id == r.run_id
m.dataset == r.dataset
typed_canonical(m.request_params) == typed_canonical(r.request_params)
contract catalog/version/hash 与冻结契约、capture-contract.json 一致
raw 路径安全、文件存在、物理 checksum/row_count/schema_hash 均成立
manifest.json 与 capture-contract.json 指向同一个精确对象且字段一致
ingestion_run 的终态与 COMPLETE 相容，冻结输入未变
```

run 恰一 object 是 slice 契约，不能误扩展到允许多 part 的通用 raw writer。合法零行 Parquet 与零 manifest 区别明确：前者有一个对象且通过 schema/null/endpoint policy 可合法，后者永远不是完成。

raw file/sidecar/capture metadata 均禁止 symlink，路径 resolve 后位于允许的项目 data/raw 内；禁止外部路径、路径穿越和 sidecar 偷换对象。checksum 从实际文件计算。sidecar 的对象集合与该 run 的 manifest 集合精确相符，不能只做 `any(...)` 命中一条。

JSON 比较使用项目现有 RequestParams/日期序列化规则：键顺序不影响；日期规范相同；不得把字符串、数字、null、缺失值互换；重复键/未知字段按现有 contract 拒绝。不得更改旧 request_id 的 digest 定义。

R1 只是重新检查历史证明。verification_code_commit 和审计时间单独记录，不得改 capture code_commit、retrieved_at、available_at 或 batch knowledge_as_of 来适应新代码。

## 4. Validator 与入口契约

建议统一实现 `validate_slice_receipt(root, db, request, frozen_plan, contracts)`，名称可随仓库风格调整。返回结构化结果：pass、reason_code、request_id、run_id、object_id、expected/observed 基数和已检查项；公开报告只输出脱敏计数。调用方不能捕获失败后默认 True。

通用 `verify_batch`：run_ids 非空；每个指定 run 至少一个 raw manifest；所有对象全部通过；不存在 run、manifest 为空、任一损坏/缺失/解析异常均 False。是否允许多个 part 继承既有用途，不硬锁成 slice 基数；slice validator 再强制一 object/run。严格 batch validator 拒绝重复/遗漏 run、receipt、ordinal 和 request ID。

| 入口 | 必须行为 |
|---|---|
| resume 判断哪些请求可跳过 | 先检查全部 COMPLETE exact receipts，失败则阻断；不返回“可执行 pending” |
| capture preflight / COMPLETE 分支 | 同一 validator；失败发生在 client fetch 前 |
| finalize_receipt | 先校验 local raw 候选与计划，事务内再检查状态，再完成 receipt |
| CAPTURED promotion | 验证完整 133-request 集合及每条 exact receipt；不能只数 133/133/133 |
| curate 与 DQ preflight | 调用相同严格检查；不能只信 COMPLETE、run 验证或 `_object_table` |
| 离线 audit 命令 | 不初始化 provider client、不要求 token、不执行 claim、不更新历史状态 |

离线 audit 失败：nonzero exit、返回 BLOCKED 的新审计记录，历史 batch 原字段保留。实际执行路径遭遇非法 COMPLETE 时可将操作/batch gate 阻断，但不把历史 COMPLETE 改成 FAILED 或重置 PENDING；保存原始矛盾证据。R1-G3 禁止执行这些真实写状态路径。

## 5. 新 migration 的要求

不得编辑 migrations 001–006。若 007 未被后续 commit 占用，使用新增 007；若已占用，登记并用下一个序号，不能覆盖。以仓库锁定 DuckDB 版本实际验证 ALTER/FK 能力，不能写未经测试的数据库语法。

首选可安全迁移的 FK/完整性约束。普通 object FK 只能证明存在，不能证明 run/dataset/params 匹配，应用层 exact validator 始终必需。若 DuckDB 不支持所需原地加约束，允许新增 receipt-integrity binding ledger：

```text
request key / batch key → 既有 slice_request 的可引用唯一键
object_id → raw_object_manifest(object_id)
run_id → ingestion_run(run_id)
唯一的 accepted completion binding + 验证版本/时间/证据摘要
```

binding 只能由严格 validator 后事务插入，receipt 未获 binding 或 binding 不精确时拒绝验收。append-only validation history 与唯一 accepted binding 分开，重复运行审计不得制造重复完成。schema 要报告哪些关系被 DB 保证，哪些由应用层保证，禁止声称“有 FK 就全解决”。如果必须重建表以新增 FK，R1-G0 先设计并 Review；不得边实现边删除/重建生产历史表。

迁移流程：备份 DB/校验备份 → 在隔离副本预检查 → 全量 strict validation → 事务迁移/登记 → 重跑检查 → 元数据不变性比较。历史非法 receipt 导致中止并输出诊断；禁止自动换 object_id、补 manifest、补 sidecar、删除多余 raw 或改 attempt。DDL/DML 失败不能留下半应用 schema_version。验证 fresh DB、从006升级、重复迁移和失败回滚。

## 6. 进程锁与原子 claim

采用本机 macOS 可用的 OS advisory exclusive lock；稳定 lock inode，不靠 `exists(lockfile)`、mtime、PID 是否活着来获取/偷取；不在释放时 unlink 造成多个 inode。锁键是规范化真实 warehouse DB 路径，覆盖同一 DB 的 capture、migration、curation、DQ 写入和 identity/bootstrap 写入。离线只读审计也在一致快照内进行；需要写新审计时遵守同一锁。

范围：打开写连接前拿锁，验证冻结输入和 preflight，事务 claim/恢复/写入，最后释放；异常、退出、进程死亡由 OS 释放。第二 writer 可拒绝或有界等待，必须返回 LOCKED/BUSY，不能消耗 attempt。锁不把损坏/uncertain 变成可重试。DB 原生锁冲突同样 fail closed。

`claim_request` 中 PENDING→IN_FLIGHT、attempt=1、ingestion_run.request_count=1 置于同一事务，并检查 RETURNING 行数为1。无成功 commit 不得调用 transport。finalize 用期望状态/attempt 条件，重复 finalize 只能在既有 exact completion 相同的情况下幂等，不接受另一个对象。

故障处置：claim 前崩溃保持 pending；claim 已提交但未证实 HTTP 是否发生时 uncertain，不重发；manifest 注册后 receipt 未完成时仅本地验证并恢复；raw 文件存在但未注册、多个候选、sidecar/contract 缺失均保持阻断，不靠文件存在补成功。本轮 audit 只检查，不实施历史恢复。

## 7. 生命周期与其余工程发现

保持旧 batch 的 ingestion_run.status/started_at。文档明确：历史 RUNNING/started_at 是预创建治理记录语义，不是精确 HTTP 起点；不得构造假的 network timestamp。

为将来设计 PLANNED→RUNNING→终态，或 claim 时创建 ingestion_run，单列 created_at/claimed_at/http_attempt_started_at/finished_at 语义。将“准确 lifecycle 实现”登记为 Phase1C.2 开启前必过项，本轮只设计，不开新批次、不建全量回填执行器。

partial generation、quarantine 精确行 FK、append-only local/batch audit 由 R2-G1/G3/G4 为本轮派生工作落地。全规模 dataset-year 恢复、SSE/SZSE/BSE session calendar 的普遍认证仍列在 Phase1C.2 前置清单，R1 不暗示已经完成。

## 8. 测试矩阵

全部 synthetic、无 token、transport spy/网络拒绝。必要时构造 legacy006 测试库来复现非法 SQL receipt；新 FK 阻止构造也应计为 DB 通过，但仍需测试应用层 legacy/损坏输入。

| 用例 | 预期 |
|---|---|
| COMPLETE + random UUID + 零 manifest | DB 拒绝或 validator BLOCKED；fetch=0 |
| COMPLETE + 另一 run 的合法对象 | BLOCKED；不得因 run 内别的对象正常而通过 |
| wrong dataset / params / contract hash | 分别 BLOCKED |
| receipt.object_id 与同 run manifest 不一致 | BLOCKED |
| slice run 0 或2 objects | BLOCKED；通用多 part 按原契约验证 |
| empty run_ids / 不存在 run / 某 run 零 objects | verify_batch False |
| 一个合法零行对象 | 按 endpoint 空表 policy 判定，不因行数0拒绝 |
| valid exact COMPLETE | 离线审计通过，resume 可跳过，fetch=0 |
| 文件缺失/改 bytes/schema/count；坏 sidecar/contract | BLOCKED |
| symlink/越界路径/sidecar对象集合偷换 | BLOCKED |
| JSON键顺序不同但内容同；typed内容不同 | 前者通过，后者阻断 |
| duplicate/missing request、改 ordinal/plan | BLOCKED |
| claim 事务第二写入失败 | 全部 rollback；fetch=0 |
| 两真实子进程操作同一测试 DB | 最多一个 claim；另一 BUSY；无重复出版 |
| writer kill/异常、锁释放、锁路径别名 | 不双持锁；恢复遵守 receipt 不变量 |
| manifest 后故障 / uncertain / repeated finalize | 只恢复 exact local evidence；不重发 |
| fresh/upgrade/repeat/failing migration | schema_version、FK、数据保留均正确 |
| 任一坏 COMPLETE 同时有 pending | 整个 resume preflight 阻断，pending fetch=0 |

全套 pytest、doctor、contracts v1/v2、slice plan/specs 和已有 secret scan regression 仍通过。CI 必须关联本 Gate exact SHA；前一 SHA 的绿灯不是本次证据。无需真实数据进入 CI。

## 9. 分 Gate 交付

| Gate | 单次范围 | 必交付 | 放行条件 |
|---|---|---|---|
| R1-G0 | 只读库存与具体设计 | HEAD差异、私有证据可用性、schema方案、validator入口表、测试计划、冻结库存摘要 | 独立 DESIGN REVIEW PASS |
| R1-G1 | exact validator、非空verify、schema与全部入口 | migration、负向测试、fresh/upgrade/rollback测试、脱敏review | exact SHA Review PASS + CI PASS |
| R1-G2 | DB进程锁、claim事务、未来生命周期政策 | 多进程/故障测试、历史保留检查、未来前置清单 | exact SHA Review PASS + CI PASS |
| R1-G3 | 现有真实证据离线验收与最终包 | 133逐receipt检查、181raw复核、旧curated不变、零新请求证据、最终review包 | R1 FINAL REVIEW PASS；缺私有证据不能放行 |

每 Gate 一个聚焦交付 commit；需要修正同一 Gate 时允许后续修正 commit，但重审新的 exact SHA。停止时明确 NEXT_GATE_NOT_AUTHORIZED。不得自动进入下一个 Gate，包括文档 Gate。独立 reviewer 的 PASS 记录含 Gate、SHA、CI URL/状态、判定、阻断项与明确下一 Gate 授权；作者不能生成自己的批准记录。

## 10. R1-G3 私有验证与最终验收

读取真实 batch 的 immutable request manifest、capture contracts、DB副本与raw。严禁重新生成 batch。migration 先在隔离副本跑；只在方案获批且检查通过后向既有 DB 追加 schema/binding/audit，不能改成功事实。

必须验证：133/133 planned receipts COMPLETE 且 exact；133 distinct request/run/object；attempt sum 保持133；同 batch raw 精确133；所有181既有raw 文件与校验元数据不变；旧252 curated 与 lineage/manifest 不变；frozen identity hash 保持 `83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c`。计数不同先调查，不能按“预期数字”修 DB。

新增市场调用=0必须有执行证据：audit 不构造client；网络入口被拒绝或spy统计；代码调用路径检查；前后 request/attempt/raw库存摘要。attempt计数不变只能证明 DB 未记录新增 attempt，不能单独证明没有网络。依赖安装/CI/GitHub通信与市场数据 transport 分开描述。

公开 artifact 建议 `docs/reviews/YYYY-MM-DD-phase1c1-r1-g3-review.md`：基线SHA、被测实现SHA、交付文档SHA或其获取方式、schema版本、测试/CI、133验收汇总、181保留、旧curated保留、失败数、网络证据、限制。不包含token、raw行、完整代码列表或私有路径细节。私有逐条结果保存在 ignored data/private。

自引用 SHA 不写成虚构值：报告被测实现SHA，提交文档后 final handoff 给当前 artifact SHA与对应CI；两者若不同要明确。真实审计后的文档 commit 同样要 Review，不能借“补报告”开始下个 Gate。

R1 PASS 的必要条件：所有必需离线/CI/真实验证通过，P0 receipt漏洞关闭，并发/事务保障通过，零新市场调用，历史不可变。仍显示 Phase1C.1 real-data gate BLOCKED；R2 未启动；Phase1C.2 CLOSED。真实证据不齐时 R1 状态是 IMPLEMENTATION_READY / REAL_VALIDATION_BLOCKED，不能 R1 FINAL PASS。
