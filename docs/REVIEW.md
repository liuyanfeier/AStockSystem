# 当前 Review：Research Level B首次采集已UNKNOWN停止

## 当前结论与授权范围

2026-10-13。用户提供的独立结论接受Level A及P1，固定c9eb868344ce990ed96d9fdf900bb636e6931880，
CI1099 passed、6 warnings。按本次明确授权，核对main旧c1a9ef7、PR #1固定head/成功checks/无冲突后，
采用普通Merge合入main：95f49467133e89ca78ab0cb5ccbf6c6f7b0a1693。
两个parent分别是旧main与接受的c9eb868，合并文件树与c9eb868完全相同，
重置a00c7dd、Research V1、V1.1、P1及PR #2合并b4e9caa历史完整；不squash/rebase/reset。
[新main CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38336577698)成功：
1099 passed、6 warnings、2261.55s；doctor及后续合同/规格步骤均成功。

用户另行回复“批准这批39次真实采集”，准确批准上一条预检固定清单及两小时有效期。
私有RESEARCH_CAPTURE_APPROVAL_V1_1绑定HUMAN/fixture_only=false/实际记录时间、目的地、39个顺序成员及：

- plan_hash：cd2a28d7aa497a3b6991ba2881912181da65e4021bed3c15ae3965d051489db7。
- implementation_hash：9421f665ebfd15ee6783706cea583ab577cf0a497f87ec37f22ee6d618b2056b。
- 执行Git SHA：95f49467133e89ca78ab0cb5ccbf6c6f7b0a1693，工作树干净。

计划不改：10股/2指数、2026-04-01至10-12、CURRENT_OBSERVATION；39请求/39尝试，
单响应2MiB、总78MiB、新磁盘256MiB、间隔>=1.25s，重试/重定向0、首错停。
唯一目的地data/private/research-v1/capture-20261012-v1-1，执行前不存在、消费0。
本机凭据YES，实际积分/代码权限未通过额外探针确认。
只读官方文档核对盘后及次日盘前更新时间，未改日期，不把更新窗口当真实覆盖。

## 真实执行结果与业务阻断

既有capture --live入口执行一次，永久claim先于传输。第1成员
stock_basic(ts_code=000001.SZ,list_status=L)终态UNKNOWN，error=TRANSPORT_UNCERTAIN。
COMPLETE=0、FAILED=0、UNKNOWN=1、UNATTEMPTED=38；已消费尝试1，计费预留2MiB，
真实响应文件0、可验证COMPLETE回执0。UNKNOWN不证明供应商收到请求或拒绝权限；
HTTPS_TLS是本次选用transport标识，无COMPLETE不能据此宣称TLS连接或采集成功。
执行代码只记录统一传输错误、不保留原生异常类型/文本，不能事后认定DNS、连接、TLS或超时原因。

首错停止后未重发、重命名/清除消费、换路径复用许可、追加诊断网络请求或续发38成员。
现有许可不能用于停止后续跑；剩余成员必须新授权，已消费UNKNOWN永不重发。
离线CA文件/TLS上下文及构造请求检查通过（未发送，仅占位凭据）；这不验证真实主机连通或API权限。
capture-status复核批准/plan/claim/result绑定；capture-import正常拒绝无COMPLETE来源，
无bundle、新Research Store或报告。该失败是数据缺失的正确拒绝，不绕过契约或填合成行情。

| Level B业务项 | 当前证据 |
|---|---|
| 10股/2指数身份、实际交易日历 | 未取得本批完整来源；不能确认128日期望或精确指数身份 |
| 行情、因子、成交和状态质量 | 无COMPLETE响应，逐证券有效日/连续尾窗/末日/覆盖仍无法验收 |
| 默认20/60真实分析、候选/排除、指标抽样复核 | 本批未生成，不能用合成或旧5股3日代替 |
| Store保留Raw重建、两次报告一致 | 尚无可合法导入输入，未执行真实验收 |
| 用户真实持仓/成交 | 未取得实际持仓数据，不推断空仓、不制作示例持仓 |

Level B没有完成，不宣称策略、真实市场覆盖或数据准入通过。最小下一步是对同一provider主机
另行批准不含HTTP/凭据的有限DNS/连接/TLS诊断，或提供可验证的连续真实文件。
不能直接重跑原命令；解决连通性后也需要处理已消费成员缺身份及剩余38的新授权。
旧已保留5股3日可继续有限历史观察，但不能满足此次默认20/60业务目标。
已离线重新验证旧bundle，含000001.SZ/SZSE/STOCK身份，等级USER_DECLARED；
后续是否能作为组合输入须核对旧时点/用途及冲突，不提升等级或补造此次stock_basic成功回执。
后续采集应只记安全的异常类别以改善诊断，不能泄漏异常正文/凭据；本批未改已授权运行实现。

## 离线验证、保全与交付边界

main代码上关键回归100 passed、48.14s；Python3.12.14/uv0.12.21、doctor PASS、12合同PASS。
旧重要回归未删/skip/减弱。没有源码、测试、依赖、配置或schema变更；本批后续diff仅必要状态文档。
main精确SHA完整CI结论见上方链接；后续文档HEAD checks独立核对，不能冒用前一SHA成功。

容量覆盖仓库、已确认仓库外历史工作目录及项目测试根，共6根、无盘点错误：
32,255,763,156逻辑字节，33,143,857,152去重inode文件blocks；执行前可用磁盘170,981,777,408字节。
文件blocks不解析APFS clone共享或目录开销；未知远端/外置备份不当零。整体50GB目标/100GB上限保留。
停止现场11,217字节，claim/result/许可均私有，无完整Raw。逐文件SHA256复核原盘点155,655文件，
改变0、缺失0；停止现场5个文件另保存hash，后续文档更新不得改写消费事实。
旧库写入、私有破坏性删除、风险参数启用与订单均0。原UNKNOWN真实事实不可改写。

复核命令（全部离线，不包含live重跑）：

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen astock research capture-status --capture-dir data/private/research-v1/capture-20261012-v1-1
uv run --offline --frozen astock research capture-import --capture-dir data/private/research-v1/capture-20261012-v1-1
# import预期失败：本批无COMPLETE来源；不产生新store。
uv run --offline --frozen pytest tests/test_research_capture_evidence.py tests/test_research_v1_1.py tests/test_research_v1.py tests/test_research_publication.py tests/test_cli.py
uv run --offline --frozen astock doctor
uv run --offline --frozen astock data contracts
git diff --stat 95f49467133e89ca78ab0cb5ccbf6c6f7b0a1693..HEAD
~~~

私有preflight/实际授权/终态/诊断/保全和准备报告在data/private/repository-governance/2026-10-13/research-level-b/；
公开Git不提交真实来源、授权JSON、凭据或个人记录。公开reviewer可核对代码/diff/CI与脱敏状态，
没有本机权限不能据作者摘要独立核实私有消费或宣布Level B通过。
无软件变更不另建重复PR，交付固定文档HEAD；执行SHA与后续状态SHA分别记录。

## 已接受的Level A修复记录（2026-10-12，以下为历史范围）

用户提供的独立审查针对`020672b448675cb519786edff9723dea7816d10c`：
Level A有条件通过，CI1071 passed/6 warnings/0 failures；唯一进入Level B前的P1是来源等级防伪。
本批仅修复该P1、补相关回归、同步必要状态并整理现有PR；保留架构，不扩展历史审批框架。
真实采集39请求仍未授权；真实市场API、破坏性私有删除、交易风险参数及订单均0。

## 分支关系与累计审查范围

2026-10-12实际核对：[PR #2](https://github.com/liuyanfeier/AStockSystem/pull/2)已由用户合入
`codex/research-v1`，合并提交`b4e9caa40a1b98571b7872d2c7f60cedf626109c`。
main仍为`c1a9ef7`；这次合并没有改变main，无需撤销或重放PR #2。
修复继续在现有专用开发线，保留重置、V1、V1.1及PR #2的合并历史。
[PR #1](https://github.com/liuyanfeier/AStockSystem/pull/1)改为base=main、head=codex/research-v1，
统一呈现完整开发线；不另建重复整合PR。本批只准备合并，未自动合入main。

审查须同时看：`020672b..HEAD`的P1修复，以及`origin/main...HEAD`的实际累计Diff。
已接受重置基线`a00c7dd544a331fe42c319a1c8ab9826027b988d`与V1基线`1a81338`仍可复核；
旧PR #2和独立审查固定SHA仍保留。最终准确HEAD、完整本机回归结果及对应CI链接从
PR #1正文/head/checks读取；下述旧1071结果不是本次最终HEAD验收。

## P1实现及验证入口

新增小型`research/evidence.py`，共用既有strict_json、CapturePlan、hash和时间原语。
LOCAL_CAPTURE_BOUND只能用于响应adapter，必须保留完整plan、claim、批准、COMPLETE回执和原JSON。
校验四类旁证角色/字节、计划hash、精确成员、批准消费绑定、授权类型/有效时间/历史目的地、
transport、claim hash、原对象/原JSON hash、抓取时间、保守可用时间、研究池/窗口及基准日历。
Mock批准与transport只能赋予SYNTHETIC；用户自报hash或来源文本不能提升等级。
直接records、导入以及Store保留字节重建走同一校验；as-of之前暂不可见来源也先检查谱系。
原始路径迁移后按Store保留对象核验，不依赖原capture目录继续存在。
USER_DECLARED和无采集证据的SYNTHETIC输入继续兼容；旧原库、schema、旧报告不改写。
不合格旧LOCAL声明会拒绝，不能静默改成已验证；可核实后以USER_DECLARED新bundle重新导入。

本地无签名JSON链可被拥有全部字节写入权的人整体伪造：此等级只表示本地链内部绑定，
不等于不可伪造的供应商/独立认证。没有新增签名系统，也不以格式正确的合成TLS形状冒充真实采集。

`tests/test_research_capture_evidence.py`覆盖自报等级/任意hash、缺四类旁证、Mock升格、
重算hash后的回执/授权/时间/请求/来源/范围篡改、保留旁证损坏、重算Store manifest ID后的伪造，
以及合法闭合生产形状链、原路径搬移后重建；全部为明确标注合成测试。
既有冲突/日历不一致/同日S-R回归继续检验原业务失败条件：仅把刻意改变的合成fixture旁证同步，
或明确降为用户声明，不删除、跳过或放宽这些断言。
聚焦回归已完成：100 passed（新增28项），46.57s；无新增依赖或旧回归删除。

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen pytest tests/test_research_capture_evidence.py tests/test_research_v1_1.py tests/test_research_v1.py tests/test_research_publication.py tests/test_cli.py
uv run --offline --frozen pytest
uv run --offline --frozen astock doctor
uv run --offline --frozen astock data contracts
git diff --stat origin/main...HEAD
git diff 020672b448675cb519786edff9723dea7816d10c..HEAD
~~~

Level B须本P1独立Review及用户明确批准最终请求清单后开展；本批未制造真实最新默认20/60观察报告。

## 已接受V1.1工程与历史证据

基线为已独立ACCEPT的Research V1：`1a81338ada05888d9c9727e0bb5d3da9714cb57f`，
[PR #1](https://github.com/liuyanfeier/AStockSystem/pull/1)固定HEAD的
[CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38199136159)已成功、1032 passed。
当时PR #1仍open/draft，本V1.1分支为codex/research-v1-1，PR #2以codex/research-v1为base。
该历史工程批次比较上述V1固定基线；最新合并关系和当前整批范围见本文开头。
最终固定SHA从PR head或git rev-parse HEAD读取，避免文档自引用。

## 用户授权与验收

直接任务是Research V1.1连续业务开发，普通实现/修复/测试/提交/CI无需逐步审批。
核心：九API真实格式响应自动进入独立Store；连续窗口与来源/用途；Market Regime/筛选/候选卡；
持仓原始逻辑、退出待核实及复盘；默认dry-run的受限采集；性能/空间实测。
不做全历史Phase1重建、新闻平台、分钟行情、机器学习、会计/券商引擎或文档治理重开。
新真实市场API、破坏性私有删除、风险参数生效及订单均未授权，本批均0。
官方文档只读核对已授权，不把浏览网页或MockTransport当行情API成功。

Level A离线软件：逐API转换、完整20/60合成窗口独立期望、错误/时间/冲突/缺失、文件和SQL故障恢复、
单一计算路径、持仓日志、统一CLI、旧回归及来源保护。用户提供独立结论为有条件通过；P1修复待新Review。
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
