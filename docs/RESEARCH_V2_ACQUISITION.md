# Research V2 首批真实采集方案（已授权，首个UNKNOWN后停止）

机器可执行的固定请求：[market-v2-proposal.json](../config/research/market-v2-proposal.json)。
CURRENT_OBSERVATION；本轮直接用户消息明确授权本固定299方案及首错停。
执行main 8ab3a7c、干净Git、两个批准hash精确匹配；首个SSE stock_basic连接错误，
1 UNKNOWN、298未尝试、0 Raw/回执，本批停止。旧Level B的106次消费不变。
许可来源和实际结果见[本批Review](REVIEW.md)；供应商行情/行业权限与返回格式尚未真实验证。

## 精确范围与预算

| 接口/分区 | 请求数 | 固定范围 | 行数/完整性 |
|---|---:|---|---|
| stock_basic | 3 | exchange=SSE/SZSE/BSE，list_status=L；原生身份+CNY | 每分区<6000；非空、身份/日期/market/状态/币种校验 |
| trade_cal | 2 | SSE/SZSE，20260401—20261012 | 每份<2000；195自然日显式开闭、沪深一致 |
| index_classify | 1 | level=L1，src=SW2021 | 本地<1000；固定31代码集合一致 |
| index_member_all | 31 | 31个申万2021一级l1_code，is_new=Y | 每行业<2000；不重叠，所属分类/当前成员验证 |
| index_basic/index_daily | 4 | 000300.SH、000905.SH；身份market=CSI，行情同窗口 | 身份<8000、行情本地<2000；同窗同日期比较 |
| daily | 128 | 128个实际交易日逐日批量，全返回池再按身份核对 | <6000；响应行数不是应有股票数 |
| adj_factor | 128 | 同128日逐日批量 | 本地<10000；按股票/日期核对缺因子 |
| suspend_d/stock_st | 2 | trade_date=20261012，稀疏事件 | <5000/<1000；空结果不证明正常 |
| **总计** | **299** | 明细逐项固定于JSON | **最多299尝试；HTTP自动重试0、重定向0** |

窗口来自已保留、已验证的真实沪深日历，128个开市日，截止2026-10-12。
此方案保证日期明确，不能将其称作批准执行当天最新窗口；若批准时已超过7自然日时效或用户要延长到
最新收盘日，应在执行前更新一次具体日期/明细并重新提交整批确认，不暗中扩大范围。

单响应最多2MiB；按所有尝试最大体积预留598MiB=627,048,448字节。
新目的地`data/private/research-v1/market-v2-20261013-001`，总新增磁盘上限2GiB=2,147,483,648字节，
覆盖捕获Raw、保留对象副本、独立DB及元数据。1000股合成完整目的地约90.24MB；6000股容量按此量级
估算约0.54GB，估算不是实际供应商字节或峰值保证。预算不足停止新增，不删Raw换空间。
预计成功业务是当前A股池宽度、板块/申万一级行业雷达、默认20/60候选和中文MD/JSON；
BSE行情/因子/行业覆盖实测后单独披露，缺域仍UNKNOWN。

## 权限、失败与恢复

- 来源唯一HTTPS端点`https://api.tushare.pro`；本地token，不公开、不购买额外积分/服务。
  官方[stock_basic](https://tushare.pro/document/2?doc_id=25)、[日历](https://tushare.pro/document/2?doc_id=26)、
  [因子](https://tushare.pro/document/2?doc_id=28)、[分类](https://tushare.pro/document/2?doc_id=181)、
  [行业成员](https://tushare.pro/document/2?doc_id=335)涉及2000积分权限；因子高频档权限不同。
  账户当前行业权限未知；稀疏状态原试点曾成功，不代表新接口权限已通过。
  没有按请求现金报价，本批不承诺外部费用为零，不进行付费购买。
- 单线程，间隔至少1.25秒，约48次/分钟，低于身份文档50次/分钟；超时30秒。
  未取得用户整批授权前不做“权限探测”请求。
- 请求前不可覆盖claim；失败/未知/拒绝Raw留存，新尝试不得reset旧账本。
  实际许可可显式`continue_on_error=true`：单成员可恢复传输/提供者错误保留后继续其他请求；
  本地I/O、未知内部异常、发布/秘密/时钟/完整性错误立即停；截断/命中行限立即停；
  HTTP401/403/429立即停、无自动重试；连续三次相同HTTP错误熔断；
  连续三次连接/DNS/超时等传输错误熔断（允许类别交替）；成功重置计数。
  连续三次同类协议/提供者错误仍熔断，避免消耗整批重复拒绝；超2MiB立即停。
- 不假定支持offset/limit。满cap、has_more、日期/身份不符等不导入；不能用自报count=0当完整性。
  因子接口没有文档化数值cap，10000只是本地防护。若实际截断，先保留、离线定位，再提出具体新分区。
- 299上限中每逻辑成员只有1次，不含额外诊断、追加重试、盘中抓取、限价接口、财务/公告或订单。
  正常软件修复无需审批；重新发起已消费成员或扩大真实预算另以一个明确delta方案批准，旧失败不追改。
- 不以原始行数宣称全市场。三份身份源缺一只能有限样本；每日缺价格/因子、短上市、缺行业、
  ST/停复牌/限价不可知分别披露。上市池不是历史PIT全集，当前行业不是历史成员。
  本批未采全市场限价，候选限价未知，不产生交易计划或自动下单。

批准方式：用户明确批准上述固定299请求/日期/2GiB目的地与停止恢复策略后，
在已提交干净版本生成匹配实际许可（HUMAN、implementation hash、plan hash、成员ID、目的地、有效期），
再通过现有`capture --live --approval`执行。此文档本身不是许可，作者不签独立Review结论。

## 2026-10-13合并后最终离线核对

保留原窗口至10月12日：这是本次核对时已保留验证的完整交易日集合，申请明确采用固定窗口，
不为日期新鲜性额外请求日历/行情。整个JSON未改变；如用户希望加10月13日，应先更新单一准确方案再批准。

- plan hash：`16e127efb7d920e9df8b5eb653bf52a6f2a261174f15b51900fb5ef6b1e87855`。
- implementation hash：`d8e4b225e7e45ac0c77531ced03af8e3f4d826794e88eba1d1a0d18deaaed778`。
- dry-run通过，无网络；实际授权须绑定这些hash、299成员、目的地与有效期，不允许自动加成员。
- 代码保护：capture逐流块检查2MiB并立即停止；逐请求前保守预留目的地两份body+32MiB。
  capture-import在派生前检查已有来源+整批最大body+32MiB（含补充源），导入后检查实际目的地大小。
  预算超限抛出安全错误、停止流程；不删除Raw换空间。这是应用层检查，DB/文件系统派生峰值仍依赖保守预留，
  不是文件系统硬quota；实际容量需导入前后盘点，不将合成体积估算当真实保证。

只读官方文档核对（2026-10-13；未请求任何市场接口）：

| 合同 | 官方依据与实际计划检查 | 真实首响应需确认 |
|---|---|---|
| stock_basic | [官方25](https://tushare.pro/document/2?doc_id=25)列出SSE/SZSE/BSE、L、curr_type；3份显式字段、非空、CNY/上市日/板块验证 | 币种实际值及三市场身份/行情覆盖；不猜代码后缀 |
| daily / adj_factor | [官方27](https://tushare.pro/document/2?doc_id=27)及[28](https://tushare.pro/document/2?doc_id=28)支持逐日批量；成交单位手/千元；daily6000，因子无文档数值cap | 不将返回行数当全池分母；缺失、停牌、短上市、因子缺口分别披露 |
| index_classify | [官方181](https://tushare.pro/document/2?doc_id=181)输入src=SW2021，输出src描述“SW申万”；展示样例没有src且为旧分类 | **输出src真实格式无法据文档确定**；保留要求SW2021及31代码一致的严格检查；SW/缺值/其他版本不准入，不能制造真样本或擅自放松 |
| index_member_all | [官方335](https://tushare.pro/document/2?doc_id=335)支持l1_code/is_new，输出in_date/out_date/is_new，2000行上限 | 最新成员与有效日、空日期保留UNKNOWN；当前归属不能冒充历史PIT，BSE行业缺失披露 |

已检测身份/日历非空、日期边界、原生代码、重复/冲突、has_more和严格小于cap；provider count不替代完整性。
任何与上述合同不匹配的响应留作拒绝证据，不导入；无法真实验收的域保持UNKNOWN。正常工程修复可连续处理，
但重发已消费成员或增加接口/日期需要新的准确授权；本次已停止，不用原许可发起额外权限探测。

## 首错停止后的恢复提案（未授权）

[market-v2-recovery-proposal.json](../config/research/market-v2-recovery-proposal.json)只改变新目的地为
`data/private/research-v1/market-v2-20261013-002`；原299成员、日期、接口、预算和生产实现均不变。
它包含**1个已UNKNOWN成员的显式新批次重新请求，以及原298个未尝试成员**，不是仅298次。
原001目录及UNKNOWN不重写。新计划hash见当前REVIEW，execution_authorized=false；本轮原授权不延续。
下一轮需用户明确批准这个新方案及联网执行环境；不增加诊断HTTP、购买权限或自动重试。
