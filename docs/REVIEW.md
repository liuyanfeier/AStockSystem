# 当前交付与验证：M1研究计划、合并待办与离线恢复

分支`codex/daily-workflow-foundation`；本批基线`b361e0abd7b2bd135b6c05997305f00ea8e1a803`，运行实现`0c2953442b902e14913008ff0786f80cef450a33`。
[当前状态](CURRENT_STATE.md)、[日常使用](DAILY_WORKFLOW.md)、[整体方案](SYSTEM_DESIGN.md)、[策略研究合同](STRATEGY_RESEARCH_V1.md)。

用户授权沿整体目标自主继续普通实现、修复、验证与向本分支推送；GPT只按用户要求介入。本批未执行新真实市场API、私有删除、风险参数批准或真实交易。原用户六个文件删除和五份未跟踪蓝图保留，不纳入提交。

## 结果与实际变更

原日常任务只能运行固定研究计划；本批新增中文`research plan`，通过唯一计划解析服务新增/结束/重开研究计划或明确复核当前证据。操作在工作Journal的RESEARCH_INPUT类型内追加，绑定预览Hash、目录/原市场锚点与计划版本；幂等请求冲突和事务故障均拒绝部分写入。创建时间采用实际录入时间，冻结配置/旧计划不改写，真实与模拟模式隔离。

同一配置/基线最多20对象，当前两份真实公司目录均有8家公司；指标必须已有来源，问答首版录一个指标，类型化服务可多指标。结束观察不代表卖出，有已报持仓时保留优先风险待办；重开新版本不改持仓原始逻辑。明确复核绑定整份当时目录及来源Hash，目录变化不继承旧复核。缺少本轮复核目录时保持原来源时间并降级UNKNOWN，不制造当日已复核。

私有报告开头按对象合并对账、时效、反证、到期和证据变化；已阅不关闭问题，超出8项仍在私有JSON保留。上次未决研究判断在组合计算前接续，避免最终判断与持仓风险采用不同状态；persist继续原路径并不重复接续。未增加依赖、数据库表或第二套研究/组合计算。

`daily-status`只读查看启动/终态回执；只有启动回执时保持运行中或已中断。`daily --resume`新建一次离线尝试，绑定原观察时间/行情要求、代码、配置与当时可见的人工事实。正常录入在旧截止之后不会回填；旧入口补写过去时间的事实也会阻止冒充原任务恢复。部分观察持久化/报告发布可同版本幂等补齐，既有字节与事件保留；不重置消费或重发市场API。原始异常文本不写回执，回执写入失败如实提示。

## 受测版本与CI

|版本|证据|边界|
|---|---|---|
|前批最终`b361e0abd7b2bd135b6c05997305f00ea8e1a803`|[完整CI成功](https://github.com/liuyanfeier/AStockSystem/actions/runs/38696541371)：1284 passed、5 warnings、1651.97秒；实际checkout匹配|仅覆盖前批|
|本批最终运行`0c2953442b902e14913008ff0786f80cef450a33`|提交前111项相关回归通过，综合源码指纹与该SHA相同；提交后34项核心控制/原生闭环通过，指纹前后一致|[完整CI执行中](https://github.com/liuyanfeier/AStockSystem/actions/runs/38699499993)，尚无本批全套PASS结论|

[机器验证](research/results/2026-10-15-plans-and-recovery/VALIDATION.json)记录准确测试运行ID、源码指纹、日志/JUnit Hash、参数、来源/as-of、容量及CI快照。最终HEAD从分支`git rev-parse HEAD`读取；后续文档提交不自引用，须核对[该HEAD CI](https://github.com/liuyanfeier/AStockSystem/actions?query=branch%3Acodex%2Fdaily-workflow-foundation)。前一SHA成功不能替代最终HEAD结果。以上是作者实际diff自查与验证，不是独立审计。

```bash
.venv/bin/python scripts/managed_pytest.py tests/test_daily_workflow_controls.py \
  tests/test_manual_workflow.py tests/test_native_market_context.py \
  tests/test_daily_profile.py tests/test_decision_loop.py tests/test_decision_increment.py \
  tests/test_decision_paper.py tests/test_cli.py tests/test_company_research.py \
  --expected-peak-bytes 100000000
.venv/bin/astock doctor
.venv/bin/astock data contracts
.venv/bin/astock data contracts --catalog v2
.venv/bin/astock research daily --profile config/daily/retained-evidence.json
.venv/bin/astock research daily-status --profile config/daily/retained-evidence.json
```

测试禁止网络并使用合成数据。新增14个反例覆盖幂等/过时预览/原子回滚、结束仍有持仓、重开、目录版本复核、缺复核降级、输入/代码/历史事实变化拒绝恢复、回执篡改/软链接、只读状态和发布/持久化中断。完整原生用例未替换市场/公司服务，仅注入合成时钟，实际验证原来源导入与精确锚点后运行五次观察。

首次新复核测试因固定初始观察早于合成事件被时点校验拒绝，修正测试helper使显式观察贯穿配置读取与运行后通过；原失败日志/工作目录保留，没有关闭或跳过检查。凭据/编码/解码字面量与私人路径检查通过；原有通用禁止路径前缀guard逐行核验并保留。

Doctor及原12/v2九合同PASS。新真实接口重查成功，仍为10月14日固定观察、10月12日行情；原行情库和31份PDF与此前保护Hash一致。没有真实个人输入或研究操作，持仓UNKNOWN、订单0；[真实脱敏报告与合成演示](research/results/2026-10-15-plans-and-recovery/README.md)分开。缺私有访问的reviewer可核对公开方法、结果和代码，不能宣称独立完整核验Raw。

## 容量、恢复与剩余工作

延续17个已确认项目根口径；[本批容量](research/results/2026-10-15-plans-and-recovery/CAPACITY.json)计入全部保留测试、报告与代码，单列受管测试7GB预算。未重复本地约6GB完整回归，远端运行完整CI；测试预算不自动扩大，失败/未知继续保留。50GB目标、100GB上限不变，逻辑文件长度不等于APFS物理占用。

本批无删除。上批获准的1626子目录/707别名、11.078GB逻辑文件移除见[原执行回执](research/results/2026-10-15-storage-lifecycle/CLEANUP_RECEIPT.json)；不扩展其他历史清理范围。代码可按提交回滚，已包含新事件/回执的工作区须保留当前读取器或另建工作副本；Git不能恢复私有事实，不能通过reset/retry改写历史消费。

M1软件交互已落地，完整CI和真实连续使用仍分别验收。接下来按合同推进M2回踩/突破/简单趋势规则与统一PAPER；样本外、真实费用/可成交与前瞻证据尚缺，不宣称策略有效。任意新公司接入、跨基线计划迁移、持仓更正问答和长期提醒仍待后续。

当前49请求提案未获真实运行许可；新采集须绑定最终实现、准确日期/成员、预算及新目的地，不随本次软件授权扩大。前批[M1首段Review](https://github.com/liuyanfeier/AStockSystem/blob/b361e0abd7b2bd135b6c05997305f00ea8e1a803/docs/REVIEW.md)及[历史交接](handoffs/2026-10-15-project-and-decision-loop-handoff.md)保留当时事实。
