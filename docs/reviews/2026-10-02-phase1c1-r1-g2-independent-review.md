# Phase 1C.1-R1-G2 Independent Review

日期：2026-10-02，Asia/Shanghai。

**判定：CHANGES_REQUIRED。两项 P2 阻断发现；R1-G3 不放行。**

审查 exact SHA：`26004ac573d6f66fe14cc63bb87b37543109cf22`。Base / 已审 G1：`1a769b7acd0ed5c0bd41b2cc232571584be9babe`。本地 HEAD 和 GitHub main 均为被审 SHA；工作树干净。

本判定只覆盖 G2 的 writer ownership、原子 claim、故障行为及其政策/测试，不改变 G1 PASS。没有发现新的 P0/P1；下述两个所有权边界尚不能满足当前 G2 的交付保证。

## 1. [P2] 路径锁被当作连接托管证明，先连接后拿锁仍能写入

位置：[warehouse_lock.py L122–128](https://github.com/liuyanfeier/AStockSystem/blob/26004ac573d6f66fe14cc63bb87b37543109cf22/src/astock/data/warehouse_lock.py#L122-L128)。相关：[连接 owner L108–119](https://github.com/liuyanfeier/AStockSystem/blob/26004ac573d6f66fe14cc63bb87b37543109cf22/src/astock/data/warehouse_lock.py#L108-L119)、[unmanaged helper 测试](https://github.com/liuyanfeier/AStockSystem/blob/26004ac573d6f66fe14cc63bb87b37543109cf22/tests/test_claim_lifecycle.py#L232-L251)。

`require_writer(db)` 从 `PRAGMA database_list` 取路径，再检查当前 context 是否持有该路径的独占 guard。它没有验证该连接是否由 `warehouse_connection()` 在拿锁后创建，也没有绑定该连接的生命周期。只要调用时恰有同路径 guard，先前打开的任意 native connection 都会被当作合格 owner 的连接。

独立复现仅使用临时合成库：

1. 正常初始化一个 batch，然后关闭托管连接。
2. **先**执行 `unmanaged = duckdb.connect(path)`。
3. **后**进入 `with warehouse_lock(path)`，调用 `require_writer(unmanaged)` 和 `claim_request(unmanaged, batch, 0)`。
4. 两个调用均成功；receipt 变为 `IN_FLIGHT / attempts=1`，对应 ingestion run 的 `request_count=1`。

这与 helper docstring、lifecycle policy 和交付报告的“unmanaged/late acquisition 会被拒绝”不符。现有测试虽然注释声称验证 late acquisition，实际只测试了**完全没有 guard** 的情况，没有执行步骤3，因此不能证明这个保证。

主要顶层入口已经正确使用 lock-before-connect。本发现针对仍可直接调用的 disk mutation helper：它承认一个未托管连接，且连接可继续活到 guard 释放后。G3 的隔离副本迁移/登记也需要可信的连接 owner，不能依赖调用者碰巧遵守创建/关闭顺序。

修复要求：为托管 disk connection 绑定可验证的 owner 和有效生命周期，或采用等效机制；helper 同时验证连接归属、当前 exclusive guard、进程/线程和有效连接 scope，不能只凭路径锁授予写权限。owner 应覆盖连接 close。保留明确的内存合成/reference 用法及必要故障代理支持，不能用通用 proxy/memory fallback 重新绕过 disk guard。

新增负向回归必须实际先打开 unmanaged connection、再拿同路径锁；在 `require_writer` 与代表性 mutation helper 前拒绝，旧 rows/files 不变。还需覆盖连接 scope 已结束的情况，并保留合法托管连接与故障代理的正向/回滚测试。

## 2. [P2] fork 清理只看当前 ContextVar，另一线程的锁描述符会遗留到子进程

位置：[warehouse_lock.py L32–43](https://github.com/liuyanfeier/AStockSystem/blob/26004ac573d6f66fe14cc63bb87b37543109cf22/src/astock/data/warehouse_lock.py#L32-L43)。

`_after_fork()` 只遍历 `_held.get()`。ContextVar 是当前执行 context 的值；线程A持锁、线程B调用 fork 时，B 的 `_held` 可以为空。然而 fork 会继承进程打开的描述符，包括A的 lock descriptor。`O_CLOEXEC` 只在 exec 时关闭，不会替这个 fork child 清理描述符。

独立合成复现使用两个父进程线程与一个只做 pipe 同步的 fork child：

1. A线程进入 `warehouse_lock(path)`；B线程此时没有 guard，执行 fork。
2. child 保持存活，等待 pipe 通知；不调用 DuckDB 或 provider。
3. A线程退出 lock context，父进程确认A已经结束，再尝试获取同路径锁。
4. 结果仍为 **`WAREHOUSE_BUSY`**。只有通知 child 退出后，再次获取才成功。

原因是 child 保留了共享同一 open-file-description 的 fd，导致原 owner 正常释放后锁仍有效。这是锁释放/可用性问题，不是本次已观察到的双 claim。当前测试只覆盖持锁 context 自己 fork，不能覆盖另一线程/context 的 owner。对于实现已经宣称的线程 owner 与 fork 清理保证，这个组合仍有缺口。

修复要求：fork child 清理必须覆盖父进程中所有相关 lock descriptors，而非仅 fork 线程的 ContextVar；建立适当的进程级登记和 fork 同步/清理，或等效机制。child 仅关闭继承副本，不得用 `LOCK_UN` 提前释放父进程的所有权。正常 context 的 owner reuse 仍应限制到正确进程/线程，不能把全局登记当作任意线程可复用的 guard。

新增组合回归：线程A持锁、线程B fork；父 owner 存活期间 competitor 必须 BUSY，A释放后即使 child 仍存活，新的合法 owner 也必须能拿锁；child 不得继承使用父 guard。保留已有 fork、kill、exception、stable inode、alias、shared reader 测试。

## 3. 本次已确认的有效实现

- `claim_request()` 将 PENDING reread/未执行校验、receipt IN_FLIGHT/attempt1、精确 ingestion run request_count1 放入同一事务；检查两次 affected-row 结果，COMMIT 成功返回后才进入 fetch。异常、零更新和 commit 前死亡回滚两个事实。使用 DuckDB affected-count 避开 referenced-parent RETURNING 限制，没有重建表或减弱 FK。
- capture、curation、DQ、bootstrap、probe 主要入口在 disk connection 和 preflight 前获取统一 owner，并保持到 publication/finalization/连接关闭。raw、migration、identity 等 helper 加入 guard 检查；发现1要求补强其连接归属证明。
- lock 使用 canonical DB path、稳定 sibling inode 和 OS flock；没有 PID/mtime 偷锁或 unlink。默认竞争立即 BUSY，显式等待有界；symlink/nonregular/multiply-linked lock path 被拒绝，普通路径别名统一。
- actual capture 和 raw publication 的跨进程竞争测试确认唯一 owner；第二 writer 在 provider/preflight/claim/publication 前被阻断，attempt 不增加。native DuckDB 冲突也失败关闭。
- 离线 audit 在 shared lock 后打开 read-only connection，并在一致事务内读；shared-to-exclusive upgrade 被拒绝。source DB/data 仍只读，初次协调可以创建稳定空 lock file。
- uncertain committed claim 不重发；orphan/extra/incomplete evidence 阻断；完整 exact metadata 只本地恢复。finalize 在各写入和 COMMIT 故障窗口保持原子性与幂等，单一 binding/history 与原终态时间得到验证。
- lifecycle policy 保留历史 RUNNING/started_at 的预创建语义；未来准确 timing/lifecycle、partial generations、quarantine row FK、append-only audit 等按规格登记，没有提前实现 Phase1C.2 或 R2。

这些已通过的设计与行为应保留。两项发现需要补强 G2 的 owner/lifetime 边界，不要求重做全部锁和 claim 实现。

## 4. 测试与 CI

- 独立运行两个新增 G2 测试模块：**60 passed in 31.12s**。包含真实 spawned subprocess 的竞争、异常/kill/fork/native 冲突，以及 claim/finalize 崩溃窗口。执行均使用临时合成数据；父/子测试路径拒绝网络。
- 独立补充两个上述未覆盖场景，分别实际确认 late unmanaged connection 被接受和非持锁线程 fork 导致锁延迟释放。新增测试60项通过不能覆盖这些已复现缺口。
- 独立核验 [CI run 36974976385](https://github.com/liuyanfeier/AStockSystem/actions/runs/36974976385)：push、completed/success；head_sha 精确等于 `26004ac573d6f66fe14cc63bb87b37543109cf22`。实际 job 日志：**442 collected / 442 passed, 1 warning in 413.30s**；doctor Overall PASS，Tushare token configured NO；contracts/plans/specs 步骤均成功。
- 本次未重复本地全套442测试；全套结果来自核验后的 exact-SHA CI，独立本地结果为上述60项和补充故障复验。作者本地442 passed/229.86s不记为独立运行。
- 阅读26个变更文件及写入口调用关系；SQL001–007、config/catalog、已有 reviews 与已审 G1 的字节差异为0。工作树干净，diff whitespace 检查通过。

## 5. 历史证据保留

独立重算 G0 inventory 所列 **1,102 个既有文件**的大小/哈希，差异0。原 DB SHA256：

`924bf429b25c4ac2fafc557bdbc67667b39de902b3175a7d7828461207fd4617`

与 G0 一致；G0 inventory artifact SHA256 仍为：

`f5c30de4f0e0ccb7f526914f047fcccfe65e52d3100784744039dbc158848e9c`

原库只读一致事务检查：schema仍1–6，007两张表不存在；133 COMPLETE、attempt sum133、distinct request/run/object各133；181 raw、252旧curated；frozen identity hash仍为 `83d8f02609b2e763dc9241738e37d4cd79d401c82902be54f7da5e2d97361b3c`。真实 warehouse 没有创建 `.lock` 文件。

Review 新增真实市场请求为 **0**；没有真实 capture/resume、迁移、curation/DQ，也没有修改原 DB 或历史证据。新增两个复现仅用临时合成存储，其中 fork probe 不打开数据库。这是保留性复核，不是 G3 strict real acceptance。

## 6. 修复与重审边界

继续停在 **R1-G2**，补上述两项 owner/lifetime 修复与回归，更新交付保证，完成必要全套检查并推送新 exact SHA，再次独立 Review。不得把本反馈当作 G3 执行授权。

真实证据离线验收、原007部署与R1最终包仍属于尚未授权的G3。R2须等R1 FINAL Review PASS后才能开始，Phase1C.2继续关闭，不得重跑133个真实市场请求。

```text
gate_id: R1-G2
reviewed_exact_sha: 26004ac573d6f66fe14cc63bb87b37543109cf22
review_base_sha: 1a769b7acd0ed5c0bd41b2cc232571584be9babe
ci_url: https://github.com/liuyanfeier/AStockSystem/actions/runs/36974976385
ci_result: SUCCESS; 442 passed; doctor/contracts/plan/specs PASS
independent_local_regressions: 60 passed; two additional reproduced gaps
reviewer: 此会话 Codex，独立于实现会话
review_date: 2026-10-02 Asia/Shanghai
verdict: CHANGES_REQUIRED
blocking_findings: P2 unmanaged-connection-owner; P2 fork-descriptor-leak-across-contexts
next_action: FIX_WITHIN_R1_G2_AND_REVIEW_NEW_EXACT_SHA
r1_g3_execution_authorization: NOT_GRANTED
r1_final_review: NOT_READY
r2: LOCKED
phase1c1_real_data_gate: BLOCKED
phase1c2_authorization: CLOSED
review_new_real_market_requests: 0
```
