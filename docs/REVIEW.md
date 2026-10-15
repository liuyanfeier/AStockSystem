# 当前交付与验证：日常入口、测试产物生命周期与清理提案 M0

2026-10-15用户确认整体计划后开始实施。当前分支为`codex/daily-workflow-foundation`，基线为`83a9c8819baa2c8986c74116ddd0c4aff8cd140a`。整体架构、资产取舍及预计日期见[SYSTEM_DESIGN](SYSTEM_DESIGN.md)，当前任务状态见[CURRENT_STATE](CURRENT_STATE.md)。

用户已改为由Codex自主负责普通研发、修复、验证和推进，GPT只在用户认为需要时介入。本文件是交付证据入口，不是新增人工Gate。本批不授权或执行新真实市场请求、私有破坏性删除、真钱风险参数或交易。

## 本批结果

已有收盘命令需要重复输入多个路径和来源参数。本批增加`research daily --profile`，把参数放入一个严格版本配置，直接调用原`decision-close`；没有复制决策、持仓或来源计算路径。

- 相对路径统一以项目根解析，拒绝越界、父级跳转和符号链接。
- 模拟/真实Journal目录及账户模式分开；来源库与Journal同路径或硬链接会拒绝。
- 观察时间来自显式run输入，不自动改为现在；拒绝未来真实观察。
- `--check`只读配置和路径，不打开数据库或创建Journal/报告；通过不代表行情内容已验证。
- 只输出私有报告，不因配置夹带字段自动取得API或公开发布权限。无账户仍UNKNOWN，不推断空仓。
- 新增配置固定重查旧10月14日研究、10月12日行情，生成新小型私有Journal和报告，不覆盖冻结交付。

新增`managed_pytest.py`记录每次本地合成回归的来源指纹、命令、预算、日志、JUnit和结果；固定独立新basetemp，避免默认轮转删除旧受保护临时根。7GB受管预算、6GB预计峰值、1GB可用磁盘余量，通过7天后仅列候选；失败/来源变化/未知保留。预算是前置检查，不是硬配额或全项目自动监控；没有删除命令。AGENTS/README统一指向受管本地测试入口。

## 已完成验证

首批入口实现`8f13a48310fa6b0509bbb8bcc9c37b13c68badd3`相关57项通过，1.71秒。新增生命周期14项与公司/日常/决策/增量/CLI组共81项通过；最初一次磁盘边界断言写错，修正后通过，原失败产物保留。

本批实现`3ddd5172a2190e3f53ccb6306411169218f7ac85`受管完整回归：**1264 passed、失败0、跳过0、1项macOS fork弃用警告，1436.61秒**。源码/测试/配置/schema/锁综合指纹前后一致，日志与JUnit Hash随[本批结果](research/results/2026-10-15-storage-lifecycle/VALIDATION.json)公开。测试使用合成数据并禁止网络；入口贯通测试以合成快照替换市场边界，实际执行来源文档校验、决策、Journal和报告路径。

```bash
PATH="$PWD/scripts:$PATH" uv run --offline --frozen python scripts/managed_pytest.py
.venv/bin/python scripts/managed_pytest.py --status
.venv/bin/astock doctor
.venv/bin/astock data contracts
.venv/bin/astock data contracts --catalog v2
.venv/bin/astock research daily --profile config/daily/retained-evidence.json --check
.venv/bin/astock research daily --profile config/daily/retained-evidence.json
```

Doctor PASS；原12与v2九合同PASS。真实旧来源配置检查与收盘入口均成功；运行前后原Store及31份PDF的SHA256不变。新市场请求0、删除0、订单0。日期/真实变化与Hash见[本批验证](research/results/2026-10-15-daily-foundation/README.md)。这是保留来源重查，不是新市场日或新公告研究。

上述是本地受测实现SHA；后续只提交状态/证据文档。新分支远端CI尚未核验，不沿用PR #9旧CI宣称本批通过。最终版本从分支HEAD读取，不在正文制造自引用SHA；[该分支CI入口](https://github.com/liuyanfeier/AStockSystem/actions?query=branch%3Acodex%2Fdaily-workflow-foundation)需核对实际checkout和结果。

## 范围、保全和剩余工作

原15根41.798GB是11:22—11:23快照。完整回归后12:57:45—12:58:21的17根快照为47.816GB逻辑长度、49.065GB去重inode文件blocks，complete=true、错误0；包括本轮5.921GB受管完整回归目录。范围和时点局限见[容量与清理核验](research/results/2026-10-15-storage-lifecycle/README.md)。

首批提案只含旧pytest-278/279/280中的1626个合成测试子目录及707个关联别名，普通文件11,078,189,085逻辑字节。完整生成器回放通过；中断旧根、共享夹具和历史失败家族382个目录约2.188GB保留，历史失败缓存原字节保留，真实源/消费/个人记录不在范围。精确清单Hash为`78c785ec7b751d79af91d78fae9e96019f12db7c428ec488d38ab216c68b93fb`，待用户确认。执行前须重新核对根inode/逐文件元数据、进程和保护引用；合成语义重放不承诺历史随机ID/数据库字节相同。实际删除0；条件执行后约36.738GB，不是已释放空间或APFS物理释放保证。

M0工程、受管测试生命周期和首批清理提案已交付，私有实际删除等待明确确认。接下来M1推进统一应用接口、中文录入和首轮策略合同；待确认删除或新数据许可不阻断其他普通业务开发。九个旧演示根、旧演练与仓库外历史工作区继续保留分类，不扩展全历史治理。

CLI源码变化会影响采集implementation hash，旧49请求未授权提案不能直接用于新实现；实际请求前重新准备准确计划与匹配实现。既有Raw、消费/失败/UNKNOWN、旧Store及真实记录不重置。用户原有六项文件删除和五份未跟踪蓝图保留在工作树，不包含在本批提交。

[Decision Loop V0固定版Review](https://github.com/liuyanfeier/AStockSystem/blob/8fb35e9eeb69e5d63c30ac07969d45ec90976277/docs/REVIEW.md)保留其当时范围和验证事实；[交接](handoffs/2026-10-15-project-and-decision-loop-handoff.md)记录后续CI及停止现场，不改写历史。
