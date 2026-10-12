# 当前 Review：Research V1.1

基线为已独立ACCEPT的Research V1：`1a81338ada05888d9c9727e0bb5d3da9714cb57f`，
[PR #1](https://github.com/liuyanfeier/AStockSystem/pull/1)固定HEAD的
[CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38199136159)已成功、1032 passed。
2026-10-12核对PR仍open/draft、未合并，工作区干净；新分支codex/research-v1-1。
[PR #2](https://github.com/liuyanfeier/AStockSystem/pull/2) base=codex/research-v1，head=codex/research-v1-1，审查本批只比较上述固定基线到新head。
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

## 作者验证与CI

固定功能源码`89b2bc750c49d30afc037f2ba80e5f6b9219df09`本机完整回归：
**1071 passed、1 warning、1267.50s**；Python 3.12.14。聚焦回归72 passed。
警告来自既有warehouse_ownership多线程fork测试；未关闭警告或改变该回归。
doctor、v1/v2 contracts、probe plan、identity specs、slice plan/specs及phase1 specs均通过。
本批功能版[CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38236902529)对应上述完整SHA；
随后仅提交Review/状态/容量文档，功能、配置、依赖和测试均未再改变。
交付文档HEAD同样触发完整CI，最终准确结论/运行链接记录于本[PR #2正文及checks](https://github.com/liuyanfeier/AStockSystem/pull/2)。
本机通过不替代CI；不将进行中/失败标为成功。
上批1032只是基线，不代表本批通过。旧重要回归未删/skip/减弱，网络禁止保留。
CI以本PR head checks及准确日志为准；公开审查须读取实际改动/依赖/测试，不能据作者摘要独立PASS。

完整供应商形状合成：10股/2指数、128交易日、沪深自然日/假日、涨跌平、拆分、
停牌/断档、ST/限价、同日S/R日内事件、新上市30日、因子缺末日、零成交、迟到as-of及陈旧过滤。
独立验算收益/60日均线/排除当日前高/同期基准/单位；单独重建snapshot和报告一致。
HTTP/权限/重定向/超时/响应大小/字段/重复/未来日期/价格/秘密/截断、
批准不匹配零调用、停止后未尝试恢复、stranded claim不重发均闭合Mock测试。

固定功能源码`89b2bc750c49d30afc037f2ba80e5f6b9219df09`实测（tracemalloc启用，合成128日，非供应商延迟）：

| 股票数 | 导入 | 来源完整重推导+读取 | 特征 | 含完整核验分析 | 报告发布 | Python分析峰值 / 进程累计RSS峰值 |
|---|---:|---:|---:|---:|---:|---:|
| 10 | 1.1946s | 0.5347s | 0.0194s | 0.6014s | 0.0072s | 10.47MB / 194.12MB |
| 100 | 10.8666s | 5.3093s | 0.4042s | 5.9640s | 0.0415s | 99.83MB / 480.51MB |

10/100股各自私有profile输出约3.42/16.17MB逻辑长度，包含原响应、manifest、Store和报告；
不将100股性能或外推空间视为全市场实测。代码hash为
`f8935d6f54751a4a0798a7b3c90480030771a699766efe61049f9be788e87c52`。

CLI实测在同一固定功能版本上完成：39个Mock响应全COMPLETE，经capture-status、capture-import、
market、screen、report直接运行；默认20/60、观察池10股/2基准、4合成候选/6排除，
报告重复发布与独立Store重建snapshot一致。合成人工POSITION经journal-add保存并关联该研究，
后续报告显示原研究陈旧、复盘到期、缺风险计划、未确认及退出待核实；无真实用户持仓。
旧真实5股3日bundle在独立验证Store用默认配置生成0筛选/5人工观察，原Research Store hash不变。
本机私有报告可读；旧来源和模拟结果分别标识，未产生最新真实128日报告。

同时修复旧日志新增默认字段的幂等兼容、关联报告hash核验、采集时钟回退下一请求前停止；各有回归；真实transport不接受测试时钟/节拍注入，人工零股后重开持仓重新关联原始逻辑。

100股尚非日常瓶颈，故保留每次完整来源一致性核验，不引入缓存/双查询路径或重写Store。
tracemalloc仅计Python分配；RSS包含原生DuckDB/Arrow且是进程累计峰值，不等于某阶段独立新增占用。
私有来源/容量/恢复核验不能由公开Git独立验证；提供脱敏结果和方法，原字节、DB/日志/报告不提交。

## 保留、迁移及下一步

[CODE_MIGRATION](CODE_MIGRATION.md)记录复用原语及删除Research直接最终文件写入旧实现；
旧Phase1/compat、消费账本、来源pin、原DB不改，不删除旧回归。
新目录的临时.pending文件可能因kill遗留，不能成为最终原始对象或阻碍同字节恢复；
本批不清理真实私有临时/历史数据。50GB目标、100GB上限及外部历史根盘点保留。

下一步仅需要批准明确近期清单或提供可验证真实连续文件，开展Level B默认研究报告，
再核实重点公司/催化和用户持仓逻辑。行业/主题、正式交易风险、策略样本外/成交验证、
组合与业绩归因仍缺，不假称已完成闭环。人工事件文字风险计划不是启用风险参数。


基准清单复查采用已保留且经physical_validate再次核验的000300.SH/market=SSE来源；
新提案仍需精确验证000905.SH，不自动换成.CSI别名。同日不同S/R及日内时间事件分别保留，
完全重复事件拒绝；YES表示当日停牌观察，不表示全天停牌或收盘后交易资格。
修复/更正期间先前完整运行已被取代，其日志留存，不当最终验收；最终固定源码重跑全套1071通过。
其中人为停止旧运行时触发了旧中断恢复测试失败，该运行不作为PASS，也不删除回归规避。

## 本批保全与实际容量

本机逐文件SHA256复核原盘点155,655个data文件：改变0、缺失0；原四库及基线历史库文件均同字节。
旧data/phase1/compat/SQL及uv.lock相对本批基线无diff；公开改动凭据明文、编码及JSON解码检查无匹配。
真实市场请求0、旧库SQL写入0、私有破坏性删除0、风险参数启用0、自动订单0。
公开Git没有实际行情/持仓/个人报告/授权令牌；上述私有结果须有本机访问权才可独立复核。

本机最终容量快照见[STORAGE_GOVERNANCE](STORAGE_GOVERNANCE.md)：6个确认根，
329,006普通文件、1,882数据库；32,386,899,566逻辑字节、33,342,554,112去重inode文件blocks。
包含旧项目外部工作目录8.20GB及本批保留pytest目录5.27GB逻辑，complete=true、错误0。
blocks不解析APFS clone共享或目录开销，未确认外置/远端备份不当零；整体50GB目标/100GB上限。
可再生测试目录仅列建议：日志/版本/失败现场保留、无进程持锁及精确批准后才清理。
本批未执行私有删除，不能承诺已经释放空间。
