# 当前交付与验证：M3日报提速与已核验输入复用

分支`codex/daily-workflow-foundation`；本批基线`a41168b5ff69166b792ea6d1483a87fab5a5cdd6`。用户已授权沿整体目标自主完成普通开发、修复、验证及推送，GPT仅按需介入。本批没有真实API、实际/PAPER订单、源库升级或私有破坏性清理。

## 问题与最终行为

真实日报原先在市场/行业、策略及旧基线阶段反复读取相同来源。实际性能采样发现5次完整快照核验、1495次来源文件规范化；当前体量超过原256MiB expectation缓存界限，重复调用成本直接进入每次报告。

`analyze`保留完整来源/SQL/as-of核验与原业务计算，末尾增加本次内部输入消费者；市场上下文从该输入提取行业成员，三组规则消费同一份当前快照，旧基线核验从自己的那次计算提取成员。独立`research setups`与日报都调用同一观察函数，没有两套公式或SQL读回分支。

每次日报当前与旧基线各核验一次，调用结束释放输入，下一任务重新验证；未增加跨任务缓存，没有改变ResearchStore.snapshot、compose、旧解码或来源准入。来源/增量冲突和消费者失败继续中止，不发布部分成功。策略参数、风险授权和执行逻辑未改变。

## 验收证据与受测版本

|版本|证据|边界|
|---|---|---|
|前批最终`a41168b5ff69166b792ea6d1483a87fab5a5cdd6`|[完整CI成功](https://github.com/liuyanfeier/AStockSystem/actions/runs/38710099050)：1335 passed、5 warnings、1954.43秒|前批完整通过|
|本批运行`f93ceb06cb18343e7241bc207c3b9dd127c7ac04`|24项相关测试通过，提交后源码指纹核对相同；真实相同截止前后业务等价、原32文件不变|[完整CI执行中](https://github.com/liuyanfeier/AStockSystem/actions/runs/38741671906)，最终HEAD另核对|

测试运行`70770f7e804e44a68fcc22bbd867a89e`，新增4个纯反例覆盖单次共享/与独立扫描等价、下一任务失败不复用成功、增量冲突拒绝、消费者异常传播；原生来源/基线及完整六次观察/录入/持仓/研究计划接续通过，原生断言12次来源读回（每次当前/基线各一份）。测试禁止网络，使用合成数据，没有删用例、跳过失败或关闭保护。

[机器验证](research/results/2026-10-15-daily-performance/VALIDATION.json)记录准确测试HEAD、源码指纹、日志/JUnit Hash、测量、受控元数据排除、来源Hash、CI和局限。Doctor与v2九合同PASS。最终HEAD由分支/`git rev-parse HEAD`获取；[该HEAD CI](https://github.com/liuyanfeier/AStockSystem/actions?query=branch%3Acodex%2Fdaily-workflow-foundation)必须单独核验，不借前一SHA成功。以上为作者实际diff自查与验证，不是独立审计。

```bash
.venv/bin/python scripts/managed_pytest.py tests/test_shared_market_inputs.py \
  tests/test_native_market_context.py \
  tests/test_manual_workflow.py::test_native_source_to_manual_input_to_next_brief \
  tests/test_strategy_rules.py --expected-peak-bytes 13000000
.venv/bin/astock doctor
.venv/bin/astock data contracts --catalog v2
.venv/bin/astock research daily --profile config/daily/retained-evidence.json \
  --observed-at 2026-10-15T13:09:43.017224+00:00 --market-date 2026-10-14
```

本机目前测试预算不足以重跑上述组；复现先检查受管余量，使用远端完整CI，不能自动扩大7GB或轮换删除旧保护根。测试日志/结果/工作目录全部保留。

## 真实结果与容量

[业务输出与实测](research/results/2026-10-15-daily-performance/README.md)：相同as-of/配置/来源、相同cProfile下，273.068→137.624秒，降49.6%；普通运行69.390秒。普通146.739秒仅是前批历史参考，不能将不同采样方式直接比较。公开展示方法、测量及脱敏公司日报，完整私有原报告/来源仍留本机。

优化前后完整日报只有`market_snapshot_hash`与`baseline_verification.current_code_hash`不同；只排除这两条后全部业务Hash一致。普通重跑与优化后的采样运行得到同一报告ID，验证幂等。真实行情仍截至10月12日，PAPER/真实订单0，策略效果未验证；同资料重算不是新交易日或真实前瞻积累。

10月15日21:30:20—21:30:50只读盘点：原17根中13个仍在原位置，现存根小计35,604,663,902逻辑字节（35.605GB），去重inode文件blocks 36,737,130,496字节；现存根扫描无错误。另4个历史pytest根lstat为FileNotFoundError，整体范围complete=false，未把缺失当零或声称本批释放空间。[当前容量及缺失登记](research/results/2026-10-15-daily-performance/CAPACITY.json)；上一次完整17根37.779GB仍作为历史快照保留。受管测试6,996,250,341字节/7GB，余量约3.75MB，没有扩预算。

原行情库和31份PDF与保护Hash一致；Raw、DB/WAL、实际许可、私人账户与路径不公开，凭据明文/编码/解码字面量检查执行后提交。缺少私有访问的reviewer只能核验公开方法、结果和代码，不能宣称独立完整验收Raw。

## 恢复与下一步

源码可按聚焦提交回滚；旧报告和原始消费没有覆盖或重置。新/旧运行都追加独立任务回执，相同输入/版本报告幂等；版本改变不冒充旧任务resume。Git不能恢复私有来源或真实事实，保留对应读取器与独立备份边界。

M3稳定试用尚未完成：真实新数据、完整执行/费用规则、PIT/样本外与前瞻策略效果仍缺。旧49请求提案未授权，其中37个身份/行业快照请求并非都适合每日重复；接下来先收敛可复用来源与更小增量的合同，再准备精确成员、日期、预算、新目的地和最终实现绑定后请求真实API授权。尚未实现的新方案不当作当前采集入口。

前批[M2 Review](https://github.com/liuyanfeier/AStockSystem/blob/a41168b5ff69166b792ea6d1483a87fab5a5cdd6/docs/REVIEW.md)、[整体路线](ROADMAP.md)和[历史索引](HISTORY.md)保留设计与交付事实。
