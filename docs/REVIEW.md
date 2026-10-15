# 当前交付与验证：日常工作流基础 M0

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

## 已完成验证

14项新入口与既有决策、增量、PAPER、CLI组共57项通过，实现SHA上1.71秒。测试使用合成数据并禁止网络；市场边界在入口贯通测试中以合成快照替代，来源文档字节检查、决策、Journal和不可变报告路径实际运行。

```bash
.venv/bin/python -m pytest tests/test_daily_profile.py tests/test_decision_loop.py tests/test_decision_increment.py tests/test_decision_paper.py tests/test_cli.py --basetemp /private/tmp/独立新目录 -q
.venv/bin/astock doctor
.venv/bin/astock data contracts
.venv/bin/astock data contracts --catalog v2
.venv/bin/astock research daily --profile config/daily/retained-evidence.json --check
.venv/bin/astock research daily --profile config/daily/retained-evidence.json
```

Doctor PASS；原12与v2九合同PASS。真实旧来源配置检查与收盘入口均成功；运行前后原Store及31份PDF的SHA256不变。新市场请求0、删除0、订单0。日期/真实变化与Hash见[本批验证](research/results/2026-10-15-daily-foundation/README.md)。这是保留来源重查，不是新市场日或新公告研究。

完整1236+回归及新HEAD的远端CI本批尚未运行；没有沿用PR #9旧CI宣称本批通过。受测实现SHA与本地验证记录在本批结果文件中绑定，不在正文制造自引用HEAD。

## 范围、保全和剩余工作

15根容量盘点41.798GB是10月15日11:22—11:23的先前快照，不是本批完成后实时总量。四个pytest根13.266GB和九个演示根0.214GB是候选，未完成完整恢复/最小失败证据核验，也没有执行删除。新定向测试使用独立basetemp，避免pytest默认轮换清掉旧临时根。新私有Journal、测试及报告增量另列于本批结果。

当前完成M0的日常入口；存储清理核验和新产物退出规则仍在推进。M1继续简单录入、统一应用接口和首轮策略合同；真实新数据需准确范围授权，不因该支线未获授权停止其他开发。

CLI源码变化会影响采集implementation hash，旧49请求未授权提案不能直接用于新实现；实际请求前重新准备准确计划与匹配实现。既有Raw、消费/失败/UNKNOWN、旧Store及真实记录不重置。用户原有六项文件删除和五份未跟踪蓝图保留在工作树，不包含在本批提交。

[Decision Loop V0固定版Review](https://github.com/liuyanfeier/AStockSystem/blob/8fb35e9eeb69e5d63c30ac07969d45ec90976277/docs/REVIEW.md)保留其当时范围和验证事实；[交接](handoffs/2026-10-15-project-and-decision-loop-handoff.md)记录后续CI及停止现场，不改写历史。
