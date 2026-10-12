# 当前状态

2026-10-12。重置及统一Review批次已按用户提供的独立结论关闭：
a00c7dd544a331fe42c319a1c8ab9826027b988d，对应CI成功、1008 passed。
Research V1已按用户独立结论ACCEPT：1a81338、CI1032 passed；V1.1在020672b独立Level A有条件通过。
PR #2已合入codex/research-v1（b4e9caa），main仍c1a9ef7；当前在该专用开发线修复唯一前置P1，
将PR #1调整为main的完整累计交付，待独立Review和合并授权；不重开文档治理或全历史Phase1。
当前整批版本、验收与验证见[REVIEW](REVIEW.md)。

## 实际可运行能力

| 能力 | 当前实现与证据 | 实际限制 |
|---|---|---|
| Research Store | 独立5表；原字节/侧证据、hash、捕获/可知时间、单位、原子导入、受管锁、快照 | 当前观察用途；不迁移/写旧库，不是PIT回测store |
| 输入与用途 | CSV/Parquet明确schema及Tushare原生字段adapter；完整自然日日历、身份/单位/主键/时间校验 | 用户文件自报来源不等于独立认证；缺失保持UNKNOWN |
| 保留真实来源复用 | legacy-bundle只读核验raw/sidecar/DB登记及真实日历HTTP来源/冻结decoder | 不采用旧事实构建/全历史许可；仅为新用途验证输入 |
| Features / Market Regime | 连续交易日尾窗、因子价格收益、均线/前高、成交活跃/波动、池内宽度及分母、基准 | 局部池不是全市场；风格代理UNKNOWN；无仓位指示 |
| Screening / 候选报告 | 流动性/价格趋势/时效筛选、透明排序和排除理由、可复现私有Markdown/JSON | 未验证策略；候选卡含失效/不交易条件，trade_eligible恒false |
| 私有日志与持仓 | PLAN/POSITION/EXECUTION/EXIT/REVIEW追加事件、更正、as-of过滤、人工持仓/退出逻辑/复盘到期 | 不与券商同步，不自动由成交推仓位/现金/可卖数量；无自动退出/风险参数 |
| 旧可靠基础 | 原契约、身份/时点、受管数据库、冻结来源兼容、历史审计/重建及回归保留 | 旧机制软件通过不代表完整真实研究覆盖，失败/未知消费不重跑 |
| 仍未实现 | 行业/动态主题/催化核实、公司基本面业务、正式入场退出、组合风控、回测/业绩归因、告警 | 后续按具体业务补齐；不得根据涨幅虚构催化或风险预算 |

CLI已支持`astock research import / legacy-bundle / market / screen / report / journal-add`。
受限采集默认dry-run，live须匹配当前用户批准；无券商命令；运行和输入契约见[RESEARCH_V1](RESEARCH_V1.md)。
原占位features/regime/screening/reports包已添加实际模块，不另建同名系统。
旧risk/regime/universe/data_sources顶层YAML仍disabled，新观察参数仅在config/research/版本化。

## 本批真实业务结果

从原库保留来源只读生成10文件bundle：5股、2026-09-28至09-30连续3个交易日，
包含证券身份、行情/因子和已验证交易日历；实际观察时间按来源保留，没有回填旧历史可用时间。
在研究可知截止2026-10-12T00:00:00+08:00生成：

- 默认20/60日配置：程序筛选0，人工观察5；不足窗口及12自然日陈旧明确披露。
- 三日探索配置：程序观察候选5，非默认/未验证研究参数；不冒充120日或最新行情筛选。
- 两种报告均为OBSERVATION_ONLY，ST/停牌/限价、基准/基本面/公告/主题证据不足写UNKNOWN。
- 反复运行同样输入/代码/参数/as-of/日志，快照及报告字节相同；从保留原字节重推导与DB比对。
- 没有导入用户真实持仓/成交。日志能力由合成回归验证，不能据此宣称已接入真实账户。

第一份真实历史样本观察报告已产生；最新连续120日候选报告尚缺近期输入。
[采集预算](RESEARCH_ACQUISITION.md)更新为39个精确请求、2指数、截至10-12窗口/字段、端点、停止条件、
78MiB总响应与256MiB新增磁盘上限，execution_authorized=false。本批市场API调用0。

## 旧数据与容量

旧真实日行情仍主要是21个离散样本日，不能当完整2013–2026序列。
旧warehouse有34表/181raw/133slice/252curated/6generations/3Context；基础三表为空。
旧metadata失败、capture失败/未知、RAW_ONLY统一catalog的47回执与0facts/generations仍保留；
旧全量研究准入缺口未被本批宣称消解。旧累计DQ观察不等同于当前独立证券/缺陷数量。
具体历史数据与执行事实见[重置记录](REPOSITORY_RESET.md)和[历史索引](HISTORY.md)。

整体容量盘点扩展到已确认AStockSystem旧Codex工作目录，而非只看当前checkout：
该目录另有约8.20GB逻辑数据/787数据库，含审查来源/证明、演练与临时副本。
两个已确认目录合计约26.97GB逻辑字节、27.72GB去重inode文件blocks；
本批三个已确认测试临时目录另有3.39GB文件blocks；最终5根汇总约31.16GB（30.28GB逻辑），
不把工程生成物遗漏，也不把其他股票项目自动算成本仓库。
[STORAGE_GOVERNANCE](STORAGE_GOVERNANCE.md)记录口径、完整性和已确认范围；
私有破坏性清理未执行，旧恢复/消费/审批数据保留。


## Research V1.1本批增量

已实现：九API原响应→六观察数据集→同一研究路径；默认dry-run/永久消费/首次异常停止，
后续批准仅恢复未尝试；Raw与报告临时校验/fsync后原子无覆盖发布；来源等级/身份/日历/单位/
稀疏状态冲突与知识时间。新CLI capture、capture-status、capture-import；旧研究入口仍可用。
默认20/60配置离线合成128交易日有独立指标验证；Breakout/Pullback仅Setup观察，
持仓保留最初逻辑/研究版本，退出待核实、陈旧/缺计划/到期及未确认提醒。
缺投资逻辑记录可以先保存为未知并提醒补录，不以强制完整性让真实记录长期无处保存。

Level A离线实现及作者本机验收完成：固定功能源码89b2bc7全套1071 passed、1 warning，
聚焦72 passed及离线diagnostics通过；最终HEAD CI和作者/独立Review边界见REVIEW及PR #2。
Level B真实最新128日仍未采集。
旧5股3日真实报告/来源保存，没有新真实持仓数据或交易风险参数生效。此次合成128日和性能
不能用于宣称最新真实选股已验收；后续批准一次近期预算即可进入实际数据业务验证。

当前P1已实现采集谱系授予/核验：plan→批准→claim→COMPLETE回执→原JSON，
导入与Store按保留旁证重建统一验证；普通manifest声明或自报hash不赋予LOCAL_CAPTURE_BOUND。
Mock始终SYNTHETIC，USER_DECLARED继续兼容。新P1回归与最终HEAD完整测试/CI见REVIEW和PR #1；
历史1071通过不能代替新修复验收。先完成P1独立审查，再由用户明确批准最终39请求清单；目前未授权。
该等级仍为本地无签名链绑定，不宣称供应商认证；合成生产形状链不是真实行情验证。

本批CLI九API全流程由39个严格Mock响应验证，生成4合成候选并独立重建一致；
人工日志与待核实持仓提醒由模拟记录验证。固定代码保留真实五股三日报告仍为0默认筛选/5人工观察。
完整来源核验下10/100股128日分析约0.60/5.96s，没有新增缓存或第二条查询路径。
2026-10-12最终6个确认根（含旧项目工作目录与本批仍保留测试目录）合计32.39GB逻辑、
33.34GB去重inode文件blocks、329,006文件/1,882数据库，complete=true。
旧31.16GB为上批时点，不代表当前占用；不可恢复来源和消费数据仍保留，私有删除0。
