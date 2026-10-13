# 项目方向重置与渐进清理记录

2026-10-11；开发分支 codex/project-reset-research-v1。
开始基线 c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db；不改写 Git 历史。

## 本批交付

完整 [长期宪章V2](PROJECT_CHARTER.md) 保持原字节，SHA256
c4aa2e47d95d89e8253f5baea1d7684a731288c6ee6b221ce3b2bd6255f0100a。
根目录用户原文归并至这个单一入口，私有原文备份另保留。
更新 README/AGENTS，不再堆叠 Active Phase1 任务；建立 CURRENT_STATE、ROADMAP、ARCHITECTURE、
RESEARCH_V1、CODE_MIGRATION、STORAGE_GOVERNANCE、HISTORY。原小写 architecture.md
统一为大写新架构入口，原 Phase0 内容在开始基线可恢复。

读取实际源码/测试/配置/近期提交和文档，使用受管只读连接审计4个主要DB。
新增 scripts/repository_inventory.py 作为离线只读容量工具，无新依赖、不打开数据库、不联网。
未修改既有 src/、tests/、config/、sql/、compat/ 及CI工作流；新增容量工具3条边界回归，
不改冻结实现/审批事实。

## 删除/归并与恢复

以下5份已跟踪文档共43,172逻辑字节，从当前工作树移除；不是清空历史数据。
删除前核验工作树原文与基线Git原字节一致，查代码/配置/文档引用，并排除171固定项。
完整SHA256与Git blob记录在私有 deletions.json；下表链接对应原提交内容。

| 原路径（点击查看历史原文） | 字节 | 原因 | 恢复blob |
|---|---:|---|---|
| [Codex_Phase1B_Small_Real_Data_Probe_Prompt_v1.0.md](https://github.com/liuyanfeier/AStockSystem/blob/c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db/Codex_Phase1B_Small_Real_Data_Probe_Prompt_v1.0.md) | 11,225 | 无代码/测试/现存文档引用，固定旧阶段实施指令已结束 | 008285cc76ee7282d4f5c86861a1378f7fbf372b |
| [Codex_Phase1C0_Identity_Bootstrap_Prompt_v1.0.md](https://github.com/liuyanfeier/AStockSystem/blob/c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db/Codex_Phase1C0_Identity_Bootstrap_Prompt_v1.0.md) | 10,943 | 无代码/测试/现存文档引用，固定旧阶段实施指令已结束 | 638fe16b7c23600db65f2422b015cc0f619f3403 |
| [Codex_Phase1C1_Implementation_Prompt_v1.0.md](https://github.com/liuyanfeier/AStockSystem/blob/c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db/Codex_Phase1C1_Implementation_Prompt_v1.0.md) | 1,547 | 无代码/测试/现存文档引用，固定旧阶段实施指令已结束 | a9cafb6643319ef8ab8df36894891e6ad8c44303 |
| [docs/reviews/2026-10-02-phase1c1-r1-g1-review.md](https://github.com/liuyanfeier/AStockSystem/blob/c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db/docs/reviews/2026-10-02-phase1c1-r1-g1-review.md) | 10,403 | 无现存引用的作者中间报告；独立修复与最终审查已保留 | f08bd4552bfeede78a31157268d6965b2c488faa |
| [docs/reviews/2026-10-02-phase1c1-r1-g2-review.md](https://github.com/liuyanfeier/AStockSystem/blob/c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db/docs/reviews/2026-10-02-phase1c1-r1-g2-review.md) | 9,054 | 无现存引用的作者中间报告；独立修复与最终审查已保留 | e0bbf6288229429556ae61b235ee6f941f193ae2 |

恢复某一原文可使用以下模板（这是恢复说明，本批无需执行）：

~~~bash
git show c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db:原路径 > 原路径
~~~

不新建历史 archive 树。重要授权、实际审查/来源及冻结设计保持原路径；
根目录剩余旧设计/Prompt通过 HISTORY解释用途。既有未提交 handoff原文保留并纳入历史索引。
旧 AGENTS/README/architecture/reviews README 的完整内容仍可从开始基线恢复。

## 代码与数据边界

本批源码/配置/回归删除0；实用原语 REUSE、旧工作流 DEPRECATE、耦合实现 MIGRATE、
业务空包 NEEDS_VERIFICATION，逐文件组与退出条件见 [代码迁移清单](CODE_MIGRATION.md)。
未替换数据业务代码，因此不伪称已完成代码迁移或旧入口已被运行时禁用。

真实市场API/文献/诊断请求0，真实fact导入/原库升级/写入0，私有数据破坏性删除0。
只读数据库查询前后hash一致且无WAL。旧消费、失败/未知、原始证据与源版本不变。
GitHub CI只读查询不属于市场API。所有私有清理提案字段仍 delete_authorized=false。

## 验证记录

- 既有全套回归：1005 passed、1个既有多线程fork弃用警告，1217.32秒；未skip、未删断言。
- 新增容量工具3条回归：3 passed，覆盖inode去重、符号链接/外部私有文件隔离、
  输出位置约束与快照不可覆盖。两组加总1008项通过，不把分开运行写成一次新全套运行。
- doctor、v1/v2 contracts、identity/slice specs、probe/slice plan、统一23契约 specs 均通过，
  均为离线只读检查。
- 既有155,655数据文件起止全hash一致；146,656历史保护路径本轮未变；171固定pin、23运行pin、
  V1/V2-5672 archive验证通过。旧capture在旧启动snapshot与已授权部署后的hash差异是历史事实，
  本轮核对的是实际停止交付hash，没有把旧snapshot差异误记为本轮数据修改。
- 四个主要DB读取前后hash不变，无WAL；当前仓库du口径约19.32GB，治理证据约100MB。
- 12份当前入口文档本地链接通过；公开变更与明文/编码/解码凭据检查通过，无私有数据路径暂存。
- 方向与清理提交7a27b53；验证记录另提交。最终HEAD通过git rev-parse HEAD读取，
  避免在文档中制造自引用SHA。基线CI已实时核实success；新分支GitHub CI需按实际HEAD查询，
  不将基线CI冒充新提交认证。

## 下一批入口

可直接开始 [Research V1](RESEARCH_V1.md) 离线实现，无需再次发起全历史基础设施任务。
最新真实股票报告还需已授权近期真实来源、Research Store和分析/报告模块。
本批完成的是方向、真实状态、迁移/容量治理与可实施入口，没有生成股票推荐、交易信号或订单。
