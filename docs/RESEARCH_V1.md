# Research V1：实际业务入口

2026-10-12。已实现离线主路径：真实文件 → 独立 Research Store → Market Regime /
Screening → 私有候选观察报告。用途固定 CURRENT_OBSERVATION，输出 OBSERVATION_ONLY。
不启动全历史 Phase1，不连接券商、不产生订单，不擅自设置交易风险参数。

## 立即运行

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen astock research --help
uv run --offline --frozen astock research import --bundle 私有输入bundle.json
uv run --offline --frozen astock research report \
  --bundle 上一步输出的bundleID --as-of 2026-10-12T00:00:00+08:00 \
  --watch 000001.SZ
~~~

默认store：data/private/research-v1/research.duckdb；原字节/来源证据：其旁raw/；
默认输出：reports/private/research-v1/，文件名由计算快照hash确定。
`market`、`screen`使用相同bundle/as-of/参数，CLI只显示脱敏计数；详情进入私有报告。
`--parameters`可指定版本JSON，默认config/research/observation-v1.json：20日收益、60日均线、
20日前高/成交窗口和观察筛选门槛。它们是待验证的研究参数，风险预算固定null，策略未验证。
不足窗口保持UNKNOWN，不用离散日期伪造连续收益；允许没有候选。

本地已实际运行5只股票的保留来源：2026-09-28至09-30连续3个交易日。
默认筛选为0，人工观察5张；报告明确行情陈旧、长窗口指标、基准/状态/基本面缺失。
这是第一份可复现的真实历史样本观察报告，不是2026-10-12最新选股或完整120日研究。
可从保留来源重新生成明确范围的输入：

~~~bash
uv run --offline --frozen astock research legacy-bundle \
  --start 2026-09-28 --end 2026-09-30 \
  --code 000001.SZ --code 000002.SZ --code 600000.SH \
  --code 600519.SH --code 601318.SH \
  --output data/private/research-v1/另一个未存在目录/bundle.json
~~~

此adapter复用受管旧库只读连接、validate_raw_run和物理来源/冻结版本校验；
只读验证旧来源，向新store建立CURRENT_OBSERVATION，不调用pipeline.build、不写p1_fact，
也不改变旧RAW_ONLY用途结论。无匹配真实来源时失败，不自动下载或补全身份。

## 用户真实文件的输入契约

bundle JSON指定protocol=RESEARCH_INPUT_V1、purpose=CURRENT_OBSERVATION、window_start/end、
universe、benchmarks、universe_scope（WATCHLIST或PROVIDER_SAMPLE）和files。
每个file列path、sha256、dataset、format（csv/parquet；原响应用json）、source、retrieved_at、available_at、
adapter（native-v1/tushare-v1/tushare-response-v1）、明确成交单位，以及可选evidence原文件/hash。
输入路径相对bundle目录或绝对路径；原字节校验后保留，重复主键/冲突拒绝，不悄悄合并。
retrieved_at是实际来源观察时间；available_at不能早于它。未知发布时间不补成历史可用时间。

| dataset | native-v1列 | 语义 |
|---|---|---|
| instruments | code,name,exchange,kind | 精确原生身份；exchange=SSE/SZSE/BSE/UNKNOWN；kind=STOCK/INDEX；不从后缀推断 |
| calendar | date,exchange,is_open | 每个相关交易所完整自然日窗口，0/1明确闭市/开市；不把工作日当交易日 |
| daily/index_daily | code,date,open,high,low,close,pre_close,volume,amount | OHLC、正价、有限值/非负成交；明确volume_unit=shares/lots100、amount_unit=CNY/thousand_CNY；pre_close可空 |
| adj_factor | code,date,adj_factor | 正数；股票收益/趋势需要涉及各日因子，缺失不计算；指数是价格指数 |
| status | code,date,st,suspended,up_limit,down_limit | YES/NO/UNKNOWN，限价可空；不存在的行保持UNKNOWN，不能把稀疏响应的缺席当正常 |

Tushare adapter使用真实ts_code/trade_date/cal_date/vol字段，按现有契约严格转换手→股、
千元→元。证券文件默认STOCK；INDEX须有显式种类证据，不能靠声明股票为基准来改变身份。
所有输入仅是当前观察，不是完整历史证券全集或PIT回测许可。
source说明由文件提供者负责真实性；自报hash只能证明字节一致，不能独立证明提供者/发布时间。
legacy adapter额外验证实际侧文件、DB登记及原始HTTP绑定。导入不等于所有研究用途合格。

## 业务输出与复现

5表store管理版本、输入bundle、标准化观察、计算快照和人工日志；锁先于连接，导入SQL事务原子。
原字节与侧证据按hash保存；文件先经临时写/校验/fsync再无覆盖原子发布；每次分析从保留原字节独立重推导并比对DB观察，检测来源/事实篡改。
无新框架、服务或依赖。报告不依赖原输入路径仍存在，可恢复/迁移私有store及raw整组。

Market Regime输出观察池趋势/涨跌/均线宽度、成交活跃比、波动、基准向量和有效分母。
当前池不是全市场；缺市值/风格证据时风格UNKNOWN，不把成交金额解释为资金流入。
Screening按连续窗口质量、价格收益/均线、平均成交额和时效过滤，逐只给出排除原因；
按窗口收益透明排序，无复合黑盒评分。相对基准只比较同一实际日期窗口。

每张候选或人工观察卡有来源、指标、入选依据、反面证据、入场观察条件、逻辑失效、
不交易条件、待验证退出逻辑。缺ST/停牌/涨跌停、基本面/公告/行业主题、可成交性或
用户批准计划时，不声明可交易；trade_eligible恒false，不设仓位或成本价止损规则。

快照记录bundle、来源/hash/时间/单位、代码hash、参数/hash、as-of和日志hash；
同一输入/代码/参数/as-of/人工记录重复运行快照及Markdown相同。CLI不打印私密报告/持仓。
来源原文件不变；后续新窗口产生新的bundle/报告，不覆盖旧研究卡。

## 私有持仓与日志最小能力

~~~bash
uv run --offline --frozen astock research journal-add --event 私有事件.json
~~~

事件包含event_id、kind（PLAN/POSITION/EXECUTION/EXIT/REVIEW）、code、event_at、recorded_at、
可选thesis、invalidation、exit_conditions、research_report_id、shares、price_cny、review_due、
risk_plan（用户文本，非执行参数）、confirmed（默认false）、notes、correction_of；缺逻辑/计划会产生提醒。POSITION必须有人工shares，零表示人工确认平仓快照。
事件ID相同内容可重复提交，冲突拒绝；更正另追加并绑定旧事件，不改旧记录。
recorded_at不得早于事件发生；报告按两个时间过滤，显示最初持仓逻辑/研究版本、原研究陈旧、退出条件待核实、复盘到期、人工未确认及行情缺口。
这些是人工提供记录，不是券商核对结果；EXECUTION/EXIT不自动推算当前仓位、现金、T+1可卖数量。
未导入记录不等于用户没有持仓。组合预算/真实退出管理/业绩归因仍待后续实现。

## 获取近期连续行情

[39请求预算](RESEARCH_ACQUISITION.md)和config/research/acquisition-proposal.json列出精确股票/指数、
窗口、字段、端点、尝试/容量上限与停止条件；execution_authorized=false。
本批市场API调用0。当前CLI已实现默认dry-run采集和九接口状态适配；真实执行仍需用户匹配批准，
无需复制Phase1审批体系，也不得沿用旧许可证或重放旧失败/未知消费。
容量纳入仓库及已确认项目外历史工作目录，见[存储治理](STORAGE_GOVERNANCE.md)。

## 验证与下一步

合成回归覆盖完整导入/重开/报告、as-of未来信息、单位、未知身份、假指数、重复/冲突、
断档、末日缺失、公司行为因子、零成交、闭市/假日、ST/停牌/限价、事务中途故障、
原库拒绝迁移、来源/DB/报告篡改、私有路径/符号链接和人工日志追加/更正/复盘。
旧重要回归与网络禁止保留；CLI清单测试因新增research入口作等价更新，不删安全断言。

下一步补最新连续120日及两个指数，再生成满足默认观察配置的真实候选报告；
随后核实候选公司/催化，完善持仓退出与复盘。暂不宣称完成完整Market Regime、策略或回测。


## Research V1.1：原响应直接入库

~~~bash
uv run --offline --frozen astock research capture
uv run --offline --frozen astock research capture-status --capture-dir data/private/research-v1/捕获目录
uv run --offline --frozen astock research capture-import --capture-dir data/private/research-v1/捕获目录
uv run --offline --frozen astock research report --store data/private/research-v1/捕获目录/research.duckdb \
  --bundle 导入输出的bundleID --as-of 实际研究可知截止 --output reports/private/research-v1/当次观察
~~~

capture默认仅列计划/hash/预算，零HTTP、零消费文件。--live必须匹配私有人工批准、干净Git、
当前implementation_hash、有效时间、绝对目的地和准确未尝试成员；无匹配批准不读凭据发请求。
详情及一次可批准提案见[采集说明](RESEARCH_ACQUISITION.md)。status只读永久消费状态，
UNKNOWN含无terminal的stranded claim；恢复不是重发，旧失败/未知不动。

capture-import自动验证COMPLETE响应/回执/请求、生成bundle并导入同目录独立Store，
不要求人工转CSV/Parquet。九类原JSON仅留必要原响应、谱系与DB观察；不再建Curated层。
响应SourceFile新增request、calendar_exchange、evidence_grade；请求字段/单位按新研究合同验证。
CSV/Parquet旧adapter仍兼容，未修改冻结Phase1合同。现存旧bundle/报告/日志不迁移或覆盖；
新增manifest默认元数据可能产生新bundleID，原ID仍按原manifest读取核验。

index_basic身份是INDEX、交易所UNKNOWN，保留provider_market/publisher；研究交易日历须另显式
绑定且沪深自然日表一致。同日不同S/R/日内时间分开保留，重复事件拒绝；S/R与ST保留当日观察，绝不从稀疏缺席填NO；多个状态来源分别
保留再按as-of合并，矛盾拒绝。完整来源重推导仍为每次查询默认，含DB主键一致性核验。
USER_DECLARED只表示用户文件声明，LOCAL_CAPTURE_BOUND表示本地TLS采集和消费链绑定，
非独立供应商数字签名；SYNTHETIC不能当真实行情。输入限当前观察用途。

默认20/60配置在10股/2指数、128交易日合成供应商形状上验证，含拆分、假日、ST、停牌断档、
新股30日、因子缺末日、零成交、晚到as-of/陈旧和筛选排除。指标有独立期望，不只验证重复性。
候选增加Breakout/Pullback待研究Setup的状态/参考、相对落后或活跃下降反证；没有实盘入场价/
仓位/止损。报告输出下一研究日跟踪、持仓原始研究与退出待核实，不擅自决定卖出。

性能可用scripts/profile_research.py分别量导入、完整来源校验、特征、含校验分析、报告；
支持10/100股合成输入，只写指定私有目录。RSS是进程累计峰值，Python峰值不含原生分配。
没有测得需要Store重写的瓶颈；没有新增缓存/查询旁路或依赖。
