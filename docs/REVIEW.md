# 当前交付与验证：M2三组规则与统一合成执行

分支`codex/daily-workflow-foundation`；本批基线`e22a31935b7eb018eda71784d8f41c2a7b2f2272`。用户已授权按整体目标自主完成普通实现/修复/验证和提交，GPT仅按需介入。本批没有新真实市场请求、真实PAPER成交、用户订单或私有破坏性清理。

## 验收范围与结果

P0趋势回踩恢复、B0突破、T0简单趋势由同一`evaluate_strategy`判定，窗口、复权、相对基准与首次满足均绑定来源/参数/代码Hash。共享连续窗口/调整价原语，保持旧市场数值和精确基线核验。未知窗口/资格不赋零，满足形态与执行资格分别表达，所有符合形态的记录保留。

新`research setups`只读来源，不依赖公司目录/账户；日常profile可启用`strategy_parameters`，在同一中文简报显示摘要，完整观察留私有JSON。冻结前的旧观察显示未启用该参数版本。策略观察不自动写人工计划、账户或订单，公开公司投影仍不包含私人队列/事实。

旧`decision.paper.simulate`执行循环已移除，只保留旧协议适配。三组与V0共用一个执行内核：同开盘先卖后买、代码顺序用现金，次日开盘/资格/限价/股数约束、T+1、退出受阻保留持仓、同一20日退出和5/10日复核。净费用、滑点偏差、MFE/MAE、收盘估值与双倍成本全保留；缺报价或公司行为未模型化时不宣称完整估值/回撤。没有部分成交/订单簿模型，费用是合成假设。

真实日常重跑暴露四个同截止报告的跨版本接续问题：公司判断完全相同，仅市场执行Hash等元数据不同，却触发歧义。修复仅在完整公司卡与目录Hash相等时选择稳定引用，同时记录全部等价报告ID；内容或目录冲突仍拒绝，旧报告Hash先核验，不改旧记录。失败回执保留，新运行不冒充同版本resume。

## 版本、测试与CI

|版本|实际证据|适用边界|
|---|---|---|
|M1 `0c29534` / 最终文档 `e22a319`|[前者CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38699499993)、[后者CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38701159651)均1298 passed、5 warnings|前批完整通过|
|规则核心 `e13da60a3485373ed1b7eed0c63b426fc7b74d9e`|[完整CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38704596325)1315 passed、5 warnings、1871.08秒|尚不含后续合成内核/日报整合|
|整合 `7635522106d389f467c547a07f2cf66440fcf93a`|83项相关回归通过，提交后指纹核对相等；[完整CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38708295648)执行中|不含同截止接续修复|
|最终运行 `f68228e42ea9a4e0f2323bc64ebca5aedfd6770d`|45项机制/原生回归通过；3项等价/判断冲突/目录冲突针对反例通过|[完整CI执行中](https://github.com/liuyanfeier/AStockSystem/actions/runs/38709036035)；最终文档HEAD另核对|

[VALIDATION.json](research/results/2026-10-15-strategy-v1/VALIDATION.json)记录准确源码指纹、受测HEAD、测试选择、日志/JUnit Hash、失败保留、真实来源/参数与CI快照。48项运行中三项新增fixture忘记初始化合成Store，修正后3/3通过；其余45项在该运行通过。此前原生fixture未标明合成来源，未来日期被真实观察保护拒绝，改为明确SYNTHETIC后通过；未关闭保护或跳过用例。早先策略fixture前提覆盖错误也保留失败现场。

最终HEAD从`git rev-parse HEAD`或分支获取；[实际HEAD Actions](https://github.com/liuyanfeier/AStockSystem/actions?query=branch%3Acodex%2Fdaily-workflow-foundation)须单独核验。以上是作者实际diff自查与验证，不是独立审计，也不将上一SHA成功当最终PASS。

```bash
.venv/bin/python scripts/managed_pytest.py tests/test_strategy_lab.py \
  tests/test_decision_paper.py tests/test_strategy_rules.py \
  tests/test_manual_workflow.py::test_native_source_to_manual_input_to_next_brief \
  tests/test_daily_workflow_controls.py tests/test_daily_profile.py tests/test_cli.py \
  --expected-peak-bytes 50000000
.venv/bin/astock doctor
.venv/bin/astock data contracts
.venv/bin/astock data contracts --catalog v2
.venv/bin/astock research paper-demo
.venv/bin/astock research daily --profile config/daily/retained-evidence.json \
  --observe-now --market-date 2026-10-14
```

复现测试必须先看受管容量余量；本机接近7GB测试预算，不能直接重复上述组或本地全套，优先使用远端CI或另行核验精确候选后清理。测试禁止网络并使用合成输入。没有新增依赖、数据库schema或第二套市场/执行业务路径。

## 真实与合成证据

[完整业务输出](research/results/2026-10-15-strategy-v1/README.md)：真实5574池、截至10月12日的形态计数及全部340条符合形态记录；真实执行资格0。合成80日场景中三组均亏损、较高费用更差，展示跳空/退出受阻；这不是历史PIT、真实前瞻或策略优势。真实/合成分文件，Raw、DB/WAL、实际许可、私人路径/账户记录不公开。

原行情库及31PDF共32文件与保护Hash一致，核验摘要/Hash保留，私有完整映射不公开。无私有访问的reviewer可检查公开算法、方法和结果，不能据摘要宣称独立完整验收Raw。代码、报告和凭据明文/编码/解码字面量检查随提交执行；保留原通用禁止路径前缀guard。

## 容量、恢复与未完成项

最新10月15日16:59:50—17:00:21只读盘点沿用17个已确认项目根，完整、错误0：37,779,428,188逻辑字节（37.779GB），去重inode文件blocks 38,948,253,696字节。[机器容量](research/results/2026-10-15-strategy-v1/CAPACITY.json)计入保留测试、真实/合成报告、代码与本批辅助脚本；随后的小量文档/Git写入在快照之外。受管测试6,985,132,289字节/7GB，余量约14.9MB；本机不再重复大型测试。文件blocks不解析APFS共享，不等于物理释放量。

同截止修复只追加后续观察；保留失败回执、所有旧来源/消费/报告。代码可按聚焦提交回滚；含新事件和回执的工作区要保留对应读取器或另建副本。Git不能恢复私人事实，不通过reset/retry重写旧状态。compat/phase1继续冻结保留。

M2软件机制已实现，最终CI、真实更新、完整交易/费用规则、持仓/现金、行业/市场执行分层、严格PIT和样本外/前瞻策略效果仍未完成。任意新公司接入、跨基线计划迁移、更正问答与后台提醒继续按路线逐步建设。49请求提案未获许可，运行前须重绑最终采集实现和准确新范围；本批不扩大旧FAILED/UNKNOWN重试。

前批[M1 Review](https://github.com/liuyanfeier/AStockSystem/blob/e22a31935b7eb018eda71784d8f41c2a7b2f2272/docs/REVIEW.md)与[历史交接](handoffs/2026-10-15-project-and-decision-loop-handoff.md)保留当时事实。
