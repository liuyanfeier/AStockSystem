# Decision Loop V0

本批把已有公司研究用于持续判断，优先补持仓、退出与复盘；不扩大研究公司数量。
初始案例为招商银行、万科A、招商轮船，沿用Research V3真实披露与10月12日价格。
[业务结果](research/results/2026-10-14-decision-loop-v0/README.md)。

## 一条可重复的收盘路径

真实Raw/Store只读复算 → 上次与最新公司证据目录 → 初始研究计划检查 → 四类观察状态
→ 私有持仓风险 → PLAN/REVIEW/EXIT追加记录 → 简明中文报告。

`research decision-close`是零HTTP收盘命令；新市场来源必须先获得准确清单的单独授权。
只复用Research Store五表、Journal和原features/radar/compose，不修改旧Raw/消费或部署旧库。
新的决策记录使用专用小型五表Store，不复制行情；真实证据与模拟事件分别放real/simulated私有目录。
公司证据目录及原始PDF继续走Research V3的来源、实体、可知时间和字节校验。

~~~bash
.venv/bin/astock research decision-close \
  --run config/decision-loop/real-run.json \
  --previous config/research/company-evidence-20261014.json \
  --latest config/decision-loop/rechecked-catalog.json \
  --documents data/private/research-v3/2026-10-14-documents \
  --baseline-market docs/research/results/2026-10-14-real-market-v2/0d235e75a112e3e3a03da497c51fd550ea3551e9c80d3f247dd92a5e363db9ef.json \
  --bundle 64f88be1c6058c7fae56585c2f6ce2cfe417b78051065b74645714d1c35ecf53 \
  --store data/private/research-v1/market-v2-20261013-002/research.duckdb \
  --journal-store data/private/research-v1/decision-loop-v0/real/close-command/journal.duckdb \
  --output reports/private/research-v1/decision-loop-v0/close-command
~~~

新一次观察需要新run/证据版本和真实截止，不改写冻结输入。新delta导入自己的Store后使用
`--store 新Store --bundle 新bundle --component 旧bundle --component-store 旧Store`，冲突另给`--revisions`。
`--position-scope`只读取私有声明，不读取券商；`--public-output`只发布受控三家公司证据，不发布组合。

研究计划的创建时间是本批实际起点，不补造过去判断。下一复核日期由程序提出，供人工采用；
它不是已批准的交易时间退出参数。保留原计划/市场/证据Hash，后续可追溯到上次程序观察。
同口径指标变化可触发支持/挑战/失效复核；流量指标不同财季不可直接比较。
到期表示研究复核需刷新，不宣称原始财报事实过期作废。原始证据仍保留。
语义性的公告/债务判断仍须人工核验；程序不声称自动理解所有公告。

四种状态：继续观察、暂停新交易等待证据、逻辑失效复核、研究结束/退出观察。
未决检查不会因下一次输入省略事件而自动解除；失效复核须明确复核，观察结束在同一计划内持续，
重启需要新计划。不能用原创建时间改写初始计划。退出观察不取消仍有持仓对象的风险检查。
继续观察不等于可以交易；逻辑失效复核不产生卖单。观察退出需要明确人工动作或明确模拟动作。
PLAN为程序研究草案，REVIEW为程序提醒，用户确认与实际执行分别记录；不伪造用户确认。

## 私有组合边界

POSITION继续使用人工快照。范围声明须明确USER_MANUAL或SIMULATED、快照时间、条目ID、完整性、现金和确认状态。
无声明时持仓UNKNOWN，不推断空仓。缺价格不对剩余持仓重新归一化；未确认完整持仓、现金未知、
报价陈旧时账户总资产/权重UNKNOWN。已报持仓及行业占比只表示该快照和报价日，不代表完整账户。
行业归属来自复算后的Store来源。阈值、风险预算、最大仓位均未授权，不自动判定超限或同步券商。
实际用户尚未提供持仓；USER_MANUAL接口只经过合成反例测试，不宣称接入真实账户。

## 日更与容量

LinkedResearchStore按明确bundle→Store路径只读引用组件；复用原compose的日历、来源、冲突选择验证。
实际128日基底+显式合成两日增量已验证，原706095条日行情保留，三个案例连续窗口达到130日。
这不是已取得10月13/14日真实来源，也不是新的全市场真实覆盖。

本批唯一有效采集提案：[13–14日49请求](../config/research/decision-market-20261013-14-proposal.json)。
日期按本批准备时已过收盘的完整日固定，不自动延长。3身份、2日历、32行业、2指数身份、
2指数区间行情、两日行情/因子/停牌/ST各2。单响应2MiB、总98MiB、目的地新增384MiB；
目的地`data/private/research-v1/decision-market-20261013-14-proposal-001`未创建。
日历须确认预期两日开市，否则停止定位；不能把计划日期当作已验证交易日。
无购买/重试/范围扩张；有限失败继续、连续3次传输或同类HTTP故障熔断，401/403/429立即停，
秘密、时钟、I/O、截断、行限及容量立即停。新实施Hash须匹配用户授权。

旧45请求仅覆盖13日，现为未执行历史提案，不能同时当作活动授权方案。
当前49请求保持原完整池合同；32个行业请求与身份不是长期每天必须重复的业务需求。
后续若采用缓存，应保留独立元数据时间、刷新/失效条件、新上市及未知归属，另验证合同；本批不偷偷减少成员。
先消除旧窗口约436MB的重复数据库复制，384MiB预算只计新delta与其来源/Store。

## 一个有限策略实验

[固定Breakout协议](../config/decision-loop/breakout-forward-protocol.json)是实验参数，不是用户风控。
主板收盘价突破此前20日高点且在MA60上方、市场允许时进入观察；下一开盘才模拟成交。
ST/停牌/流动性/限价未知、触及价格边界或模拟资金不足取消入场；不假设涨停可以买、跌停可卖。
退出备选：前20日低点被收盘跌破、MA20趋势反转、持有5交易日到期复核，均于后续可执行开盘模拟。
T+1、跳空、固定双边费率和滑点进入模拟账；费率不是已核实券商合同，不保证触发价成交。
涨跌停或停牌阻断退出时保持未平仓；按实际可模拟开盘记偏差。

已执行的实验是显式合成流程验证，统计胜率、平均净盈亏、实验盯市回撤与成交偏差，不能作为策略盈利证据。
真实前瞻阶段在参数冻结后逐收盘留档，再核对次日执行约束；不把128日当前上市池当无幸存者偏差回测。
真实验证前还需完整交易日历、公司行为、费用最低额/税费/有效规则、可成交与样本外资料。
真实账户损益UNKNOWN，无实际订单。
