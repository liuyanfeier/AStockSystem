# 当前 Review：Research V1.1

基线为已独立ACCEPT的Research V1：`1a81338ada05888d9c9727e0bb5d3da9714cb57f`，
[PR #1](https://github.com/liuyanfeier/AStockSystem/pull/1)固定HEAD的
[CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38199136159)已成功、1032 passed。
2026-10-12核对PR仍open/draft、未合并，工作区干净；新分支codex/research-v1-1。
新PR base=codex/research-v1，head=codex/research-v1-1，审查本批只比较上述固定基线到新head。
最终并入main顺序：已接受重置分支 → PR #1 → 本批；本次没有自动合并任何分支。
最终固定SHA从PR head或git rev-parse HEAD读取，避免文档自引用。

## 用户授权与验收

直接任务是Research V1.1连续业务开发，普通实现/修复/测试/提交/CI无需逐步审批。
核心：九API真实格式响应自动进入独立Store；连续窗口与来源/用途；Market Regime/筛选/候选卡；
持仓原始逻辑、退出待核实及复盘；默认dry-run的受限采集；性能/空间实测。
不做全历史Phase1重建、新闻平台、分钟行情、机器学习、会计/券商引擎或文档治理重开。
新真实市场API、破坏性私有删除、风险参数生效及订单均未授权，本批均0。
官方文档只读核对已授权，不把浏览网页或MockTransport当行情API成功。

Level A离线软件：逐API转换、完整20/60合成窗口独立期望、错误/时间/冲突/缺失、文件和SQL故障恢复、
单一计算路径、持仓日志、统一CLI、旧回归及来源保护。作者结果是工程自测，待独立Review。
Level B最新真实研究：仍未开展，没有新的采集授权；此前5股连续3日有限真实证据仍保留，
不能冒充128日或最新默认配置验证。未导入用户实际账户/持仓/成交。

## 实际实现与可运行入口

- research/publication复用data.raw_writer.atomic_new_file：临时写/校验/fsync/硬链接无覆盖发布。
  SQL回滚只留下完整未引用对象；报告双文件中断可同输入恢复；同名异内容拒绝。
- research/tushare纯响应合同覆盖全部9接口，原JSON直接推导6类观察，不增加Curated副本；
  身份、请求范围、时间、单位、完整日历、上市日期、上限、重复/冲突检查。
  stock_basic明确exchange；index_basic保留market/publisher，日历另证，后缀不推断身份。
- 稀疏ST/停复牌/限价证据按as-of合并；R不扩展为每日正常，未知不填NO。
  原JSON/plan/claim/批准/结果/hash保留，来源等级区分声明、LOCAL_CAPTURE_BOUND、SYNTHETIC。
- research/acquisition独立39请求计划，默认dry-run，不访问旧执行入口；永久claim先于HTTP，
  首错停止、FAILED/UNKNOWN不重发；新批准只恢复未claim成员。TLS、无代理/重定向/重试、流式大小/磁盘预留。
- features/regime/screening/report仍共用service；价格/因子/日历/身份来源纳入特征证据。
  Breakout/Pullback为待研究Setup，有参考价/状态、反证、不交易与失效条件，无策略有效或买卖声明。
- journal追加人工快照/更正，保留最初逻辑和研究版本，as-of防迟到更正泄漏；
  缺逻辑/风险计划、原研究陈旧、复盘到期、人工待确认、用户退出条件PENDING_VERIFICATION。
  缺持仓输入不推断空仓；不从成交推账户或按成本设止损。
- 报告增加活跃/波动、Setup、持仓复盘与下一研究日跟踪，仍私有可复现。

运行命令和规范：[RESEARCH_V1](RESEARCH_V1.md)；
一次可批准的范围/官方依据/恢复及全市场增量：[RESEARCH_ACQUISITION](RESEARCH_ACQUISITION.md)。

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen astock research capture
uv run --offline --frozen pytest tests/test_research_publication.py tests/test_research_v1_1.py tests/test_research_v1.py tests/test_cli.py
uv run --offline --frozen pytest
uv run --offline --frozen astock doctor
uv run --offline --frozen astock data contracts
uv run --offline --frozen python scripts/profile_research.py --size 10 --output data/private/research-v1/新目录10
uv run --offline --frozen python scripts/profile_research.py --size 100 --output data/private/research-v1/新目录100
~~~

## 作者验证与CI（随实际结果更新）

聚焦回归当前66 passed；整套本批回归与新HEAD CI正在准备，**尚未标记通过**。
上批1032只是基线，不代表本批通过。旧重要回归未删/skip/减弱，网络禁止保留。
CI以本PR head checks及准确日志为准；公开审查须读取实际改动/依赖/测试，不能据作者摘要独立PASS。

完整供应商形状合成：10股/2指数、128交易日、沪深自然日/假日、涨跌平、拆分、
停牌/断档、ST/限价、新上市30日、因子缺末日、零成交、迟到as-of及陈旧过滤。
独立验算收益/60日均线/排除当日前高/同期基准/单位；单独重建snapshot和报告一致。
HTTP/权限/重定向/超时/响应大小/字段/重复/未来日期/价格/秘密/截断、
批准不匹配零调用、停止后未尝试恢复、stranded claim不重发均闭合Mock测试。

初步性能（tracemalloc启用、合成128日，非供应商延迟）：

| 股票数 | 导入 | 来源完整重推导+读取 | 特征 | 含完整核验分析 | 报告发布 | Python峰值（分析） |
|---|---:|---:|---:|---:|---:|---:|
| 10 | 1.15s | 0.49s | 0.018s | 0.56s | 0.007s | 约10MB |
| 100 | 10.21s | 4.29s | 0.292s | 4.86s | 0.039s | 约92MB |

100股尚非日常瓶颈，故保留每次完整来源一致性核验，不引入缓存/双查询路径或重写Store。
tracemalloc不覆盖原生DuckDB/Arrow；profile脚本同时记录进程累计峰值RSS，正式实测随后补齐。
私有来源/容量/恢复核验不能由公开Git独立验证；提供脱敏结果和方法，原字节、DB/日志/报告不提交。

## 保留、迁移及下一步

[CODE_MIGRATION](CODE_MIGRATION.md)记录复用原语及删除Research直接最终文件写入旧实现；
旧Phase1/compat、消费账本、来源pin、原DB不改，不删除旧回归。
新目录的临时.pending文件可能因kill遗留，不能成为最终原始对象或阻碍同字节恢复；
本批不清理真实私有临时/历史数据。50GB目标、100GB上限及外部历史根盘点保留。

下一步仅需要批准明确近期清单或提供可验证真实连续文件，开展Level B默认研究报告，
再核实重点公司/催化和用户持仓逻辑。行业/主题、正式交易风险、策略样本外/成交验证、
组合与业绩归因仍缺，不假称已完成闭环。人工事件文字风险计划不是启用风险参数。
