# Research：近期采集计划、正常试错及不可变消费

2026-10-13。默认仍dry-run；机器proposal不是运行许可。
原39成员获批后首次UNKNOWN现场已保留。用户随后明确批准本批正常试错采集，
覆盖原首错停止及本批重试限制；新尝试采用新的精确plan/HUMAN批准/implementation/目的地，
不清除或复用旧消费。原窗口、证券、接口及用途不扩大，不涉及旧Phase1重放。
累计106尝试：39 COMPLETE、66 FAILED、1 UNKNOWN，39逻辑成员均已有成功来源。
正常诊断/修复细节及各批执行版本见[REVIEW](REVIEW.md)。所有市场请求现已结束。

旧批准不含continue_on_error时仍首错停；新批准的可选实际bool允许成员错误继续，
秘密/时钟/不可变写入等错误仍停止。HTTP不自动重试，每批每成员只消费一次。
需要正常重试时必须有当前用户授权，新账本另行保留且指明来源，不 reset 历史结果。
失败Raw如完整有界且无秘密可保留，但不得升格或导入；成功來源须完整COMPLETE证据。
CLI capture-import可重复--include-capture，仅合并相同研究范围中不重复的成功成员。

响应允许类型受控detail/count metadata，不以count认定覆盖；实际覆盖由返回日期/行及日历核验。
传输明确Accept-Encoding: identity，压缩响应仍拒绝，TLS/尺寸/秘密检查不降级。
当前成功bundle的39来源为LOCAL_CAPTURE_BOUND本地链绑定，不是供应商独立签名。

以下是原批准39请求的准确计划及默认工程边界；首错停/39总尝试/单一目的地条款
在本次新用户授权覆盖的正常试错批次内已被上述规则替代，原39版本记录不被改写。
新批有限预算及目的地逐一随实际plan/批准保存在私有目录，不能把文件当未来运行许可。

## 一次批准的准确范围

机器清单：[acquisition-proposal.json](../config/research/acquisition-proposal.json)。

- 用途：CURRENT_OBSERVATION，仅观察研究，不用于当时已知的历史回测或自动交易。
- 股票：000001.SZ、000002.SZ、000333.SZ、002415.SZ、300750.SZ、600000.SH、
  600036.SH、600519.SH、601318.SH、601899.SH。
- 基准：000300.SH、000905.SH；必须由index_basic精确返回身份，不把.SH/CSI代码视为别名。000905.SH仍需当次精确返回证实，不能以另一指数推断。
  已有真实保留响应证实000300.SH的market=SSE；两指数提案请求SSE市场并精确核验，保留publisher/market；研究采用显式SSE日历且要求沪深日历一致，不能据后缀推断交易所。
- 日期：2026-04-01至2026-10-12。按官方2026休市表计算128交易日，旧截至10-09为127日；
  实际完整性以返回的沪深自然日日历和每股连续尾窗验收，不把理论天数当已取得行情。
- 最早执行：2026-10-13 09:30北京时间。当前10-12交易已收盘；供应商更新窗口不等于已完成证明。
  若实际缺末日，保留缺口，不能自动扩大日期、重试或以前日冒充末日。
- 固定HTTPS POST https://api.tushare.pro；证书验证、trust_env=false、重定向0、重试0、间隔至少1.25秒。
- 最多39请求/39尝试：stock_basic 10、index_basic 2、trade_cal 2、daily 1、adj_factor 10、
  stk_limit 10、suspend_d 1、stock_st 1、index_daily 2。
- 单响应2MiB；累计响应保守计费最多78MiB；新增磁盘256MiB。失败/未知按整单2MiB预留，不能退款换请求。
  Raw保留副本与DB/临时文件峰值纳入预算；导入先预留累计响应+32MiB，不复制旧库。
- 唯一目的地：data/private/research-v1/capture-20261012-v1-1；其中plan、claim、result、原响应、
  bundle、独立research.duckdb/raw和报告均私有。其他日期/路径/代码需要新的完整提案与批准。

旧daily十单合并成一单，suspend_d十单合并成一单（官方支持多代码）；
stock_basic改十个精确身份请求，避免全表增长触顶，也避免手工过滤掩盖缺身份。
不采集盘后成交可选字段，避免把2026-07-06之后的字段强制用于此前历史。
stock_st只取末日全名单，故此前ST仍UNKNOWN；停复牌不完整的状态同样不能外推。
默认研究未依靠NO状态产生交易资格，所有卡trade_eligible=false。

## 官方接口核对与新研究合同

核对日期2026-10-12；新纯响应合同在research/tushare.py，旧Phase1合同不改。
字段及参数以机器清单为准。所有响应达到上限或has_more=true都拒绝，不能宣称完整。
官方未公布数值上限的接口采用明确的本地保守上限，不称其为供应商上限。

| API → Research数据集 | 官方语义、权限、行限 | 本轮处理 |
|---|---|---|
| daily → daily | 未复权；停牌不提供行情；6000行；基础权限。盘后成交字段有起始日期 | 手×100、千元×1000；字段只取必要核心；断档保持缺口 |
| adj_factor → adj_factor | 2000积分；独立因子；盘前更新；该页面未给行限 | 本地2000行上限；各价格日需因子，不能跨缺失计算 |
| stk_limit → status | 2000积分、5800行；覆盖A/B股和基金；盘前限价 | 保留限价；缺失为null；不同来源矛盾拒绝；不保证成交 |
| suspend_d → status | 2000积分、5000行；S/R事件、日内时间；更新不定期 | S为停牌观察；R仅保留复牌事件，不视为整日NO；缺席UNKNOWN |
| stock_st → status | 3000积分、1000行；按日名单、9:20更新 | ST行YES；空/未入名单仍UNKNOWN；不外推历史 |
| stock_basic → instruments | 2000积分、6000行、50次/分钟 | 原生代码/明确exchange及上市日期；精确逐股验证，不制造身份 |
| index_basic → instruments | 2000积分、8000行、18点更新 | INDEX及market/publisher依据；交易所UNKNOWN、另证研究日历 |
| trade_cal → calendar | 2000积分；自然日0/1；页面未给行限 | 本地2000行上限；不传is_open过滤；完整沪深自然日与节假日 |
| index_daily → index_daily | 2000积分；点位、手、千元；页面未给行限；价格和成交覆盖可能不同于行情软件 | 本地2000行上限；不解释为全市场成交，不推断资金流 |

官方依据：[日线](https://tushare.pro/document/2?doc_id=27)、
[因子](https://tushare.pro/document/2?doc_id=28)、[限价](https://tushare.pro/document/2?doc_id=183)、
[停复牌](https://tushare.pro/document/2?doc_id=214)、[ST](https://tushare.pro/document/2?doc_id=397)、
[证券](https://tushare.pro/document/2?doc_id=25)、[指数身份](https://tushare.pro/document/2?doc_id=94)、
[日历](https://tushare.pro/document/2?doc_id=26)、[指数行情](https://tushare.pro/document/1?doc_id=95)、
[更新与权限汇总](https://tushare.pro/document/1?doc_id=108)、
[上交所休市表](https://www.sse.com.cn/disclosure/dealinstruc/closed/c/c_20251222_10802510.shtml)。
日线详情写15～16点，汇总写15～17点；以较晚窗口留余量，仍逐份检查实际返回。
账户是否满足积分、查询代码是否存在以及当天数据是否完整，未通过任何真实探针确认；
权限失败/身份空返回停止，不能新增诊断请求。

## 命令、许可和消费恢复

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen astock research capture
# 得到当前plan_hash、完整成员、字段与预算；不读取凭据、不创建消费状态。
# 仅在用户明确批准之后，保留私有真实批准记录，再运行：
uv run --offline --frozen astock research capture --live --approval 私有批准.json
uv run --offline --frozen astock research capture-status --capture-dir data/private/research-v1/capture-20261012-v1-1
uv run --offline --frozen astock research capture-import --capture-dir data/private/research-v1/capture-20261012-v1-1
# import输出bundleID；随后用相同目录的research.duckdb调用research report。
~~~

真实批准JSON仅在明确授权后填写：protocol=RESEARCH_CAPTURE_APPROVAL_V1_1、plan_hash、
绝对destination、implementation_hash、authorized_by=HUMAN、approved_at、expires_at、
按顺序member_ids、fixture_only=false、execution_authorized=true。implementation_hash绑定
研究计算/采集源码；真实执行还要求干净Git。批准由本地人工记录保存，不是密码学签名，
作者不能据软件测试制造用户授权或独立审查结论。测试批准只能SYNTHETIC_TEST+MockTransport。

claim原子落盘在HTTP之前，代表请求已消费且暂UNKNOWN；COMPLETE有完整响应/hash/时间；
HTTP/权限/结构/日期/单位/大小/秘密错误FAILED，传输/本地中断不确定UNKNOWN。
任何异常首次停止；KeyboardInterrupt/进程被杀留下claim，不能重发。原响应不泄露token。
失败/未知不被清除、退款或重命名。后续只在**新的匹配人工批准**下恢复未claim成员，
新批准member_ids必须准确等于剩余清单，预算仍是原批总预算。旧停止任务入口从未调用。
不同内容同名对象拒绝；SQL失败可留下完整未引用raw，重跑离线导入复用同字节，不重采集。

capture-import仅读取COMPLETE；身份/日历缺失则尚不能导入，行情/状态缺失则明确披露。
完整规范化由原JSON现场推导，无人工CSV拼装；Store保留原JSON、计划/claim/批准/回执证据。
证据等级区分USER_DECLARED、LOCAL_CAPTURE_BOUND和SYNTHETIC；本地TLS绑定不是供应商数字签名。
等级授予须完整计划/批准/claim/COMPLETE回执/原JSON语义一致，不能只校验manifest自报hash。
Store重建从保留对象复核同一链，Mock固定SYNTHETIC。P1独立修复Review与用户最终清单批准
已实际完成，后续用户正常试错授权已执行，原停止消费不改写；PR合并及Level A工程通过不自动授予未来运行许可。

## 全A股日常增量：下一步可落地方案

10股是连续研究试点，最终覆盖主板、创业板、科创板、北交所；此提案不是永久universe。

| 方式 | 请求规模/成本 | 恢复与覆盖风险 |
|---|---|---|
| 逐证券窗口 | N股×所需接口；本轮因子/限价各10单；扩展N=6000时历史序列两域约12000单 | 单股失败隔离容易，日常仍逐股浪费；不能推断退市/PIT身份 |
| 按交易日批量 | 128日daily约128单，之后每交易日daily/因子各1单；状态及元数据另计 | 官方建议daily按日；总行数接近6000时必须分区/分页且明确总覆盖；不能自动续页扩大本批准 |

全市场增量先建立版本化证券池（含BSE及上市/退市变动），根据当日行限按确证分区设计明确请求。
限价5800还含B股/基金，不能套daily全A股单次完整性；ST1000、停复牌5000独立检查。
BSE官方日历说明可参照沪深，但须显式来源/映射和规则验证，不偷偷标成SSE证券身份。
每个请求有永久逻辑成员与消费记录，未尝试分区可以后续批准恢复，失败/未知保持终态。
新增日归并旧连续来源时核对重叠内容与更正、因子变化/as-of，保留旧报告，不只替换最新版。

粗预算（容量估计，不是实测）：6000股×128日，JSON约200～400B/日行，单域154～307MB；
日线/因子/状态及DB约0.5～1.5GB初始峰值，日常原JSON若干MB到十余MB，需实测校准。
按日批量不等于全历史下载；达到50GB目标预警、100GB上限前先做可恢复清理申请。
本轮100股128日合成路径约16MB，不据此冒充全市场供应商真实尺寸。
