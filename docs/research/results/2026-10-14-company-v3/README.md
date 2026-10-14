# Research V3 真实公司研究交付

价格固定于2026-10-12；公司研究as-of为2026-10-14T07:17:45.808876+00:00。
[先读简明决策摘要](DECISION_BRIEF.md)，然后查看公司卡。研究优先级不是买入评级，没有订单。

|公司|交易所/板块|行业|状态|
|---|---|---|---|
|[新华文轩](601811.SH.md)|SSE主板|传媒|风险观察|
|[善水科技](301190.SZ.md)|SZSE创业板|基础化工|风险观察|
|[近岸蛋白](688137.SH.md)|SSE科创板|医药生物|风险观察|
|[澳弘电子](605058.SH.md)|SSE主板|电子|风险观察|
|[招商银行](600036.SH.md)|SSE主板|银行|继续重点研究|
|[万科A](000002.SZ.md)|SZSE主板|房地产|风险观察|
|[武汉蓝电](920779.BJ.md)|BSE|电力设备|普通跟踪|
|[招商轮船](601872.SH.md)|SSE主板|交通运输|继续重点研究|

[复现代码/输入/结果Hash](REPRODUCTION.json)随文件提交。
[完整JSON](research.json)保存101项财务指标、时点、来源、事实/推断/假设/未知和每卡条件化决策草案；
[16只短名单/5574只资格与容量分配审计](SHORTLIST.json)保留未入选、行业集中度降级、ST/质量争议原因。
原20/60参数不变，1347资格与研究分配区别明确，行业上限3。
[数值/单位/来源页码复核](NUMERICAL_CHECK.json)和[单日更新未授权方案](INCREMENT_PROPOSAL.json)可直接审查。

## 验证与真实局限

31份保留PDF包括12份直接披露平台与19份第三方原始文档镜像；8家公司均有2025年报、2026一季报和半年报来源。
每个关键数字记录原单位、期间、比较期间和原表定位。CNY=人民币元，CNY_MILLION=人民币百万元，
PERCENT=百分数值（变化是百分点），CNY_PER_SHARE=人民币元/股。
101项指标的本期/比较值、单位及正基数同比独立复核；pypdf逐页复核数值，与手工转录使用的pdftotext分开。
招行年报中文映射异常，单位另由pdftotext和原表视觉复核；澳弘负债表续页单位来自同一表的47页表头。
8家公司半年报主要财务表及招行年度单位页已逐页视觉核对。数值同页存在检查不能单独证明行归属，
视觉与人工行定位补足该局限；这不是独立会计师审计。

原始风险公告与半年报交叉核验了文轩/澳弘的经营与价格背离、近岸亏损和AI/RNA收入占比限制；
万科年报明确有持续经营重大不确定性段落，不能因无保留意见或展期就宣称风险消失。
竞争地位、客户/竞品、部分完整债务附注、最新未穷尽公告及估值复算仍UNKNOWN。
公司披露的业务原因是管理层声明，不等同于独立产业证明；不把涨价解释为公司催化。
原市场窗口不是实时行情，定期财报不是完整交易执行验证；所有交易参数留空。

镜像的显示公告日保守使用，原站精确发布时间未核实。Hash只证明本地字节保留，不是提供方认证。
原始PDF/失败连接记录/原表/个人Journal与许可不入Git；Reviewer可以打开公开URL核查必要事实，
没有私有来源访问权时不能据作者摘要独立证明下载真实性。不存在新Tushare/付费API请求。

## 离线复现

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen astock research company \
  --market docs/research/results/2026-10-14-real-market-v2/0d235e75a112e3e3a03da497c51fd550ea3551e9c80d3f247dd92a5e363db9ef.json \
  --store data/private/research-v1/market-v2-20261013-002/research.duckdb \
  --catalog config/research/company-evidence-20261014.json \
  --documents data/private/research-v3/2026-10-14-documents \
  --output docs/research/results/2026-10-14-company-v3
~~~

先从保留Raw/Store复算完整V2公有投影，匹配后才读行业归属，非自报Hash。
本批V2所有业务字段及code hash原值一致；重复本批公司报告字节一致，不写旧Store或保存新V2报告。
输出不可覆盖；来源/研究更正需新版本目录。

独立PDF复核助手（不采集）为`scripts/research/check_company_sources.py`，需要pypdf与Poppler。
本机使用已提供的文档运行时，项目依赖未增加；CI运行封闭合成反例，不持有私有PDF。
使用可用Python执行：

~~~bash
python scripts/research/check_company_sources.py \
  --catalog config/research/company-evidence-20261014.json \
  --documents data/private/research-v3/2026-10-14-documents \
  --output /tmp/company-source-check.json
~~~

本地全量回归、CI、保全与容量实际记录见[VALIDATION](VALIDATION.md)和[当前Review](../../../REVIEW.md)。
下一步价值：对招行/航运补外部产业和信用证据，对极端上涨与困境样本先解决反面风险，再由用户审核条件化计划；
不增加大规模全历史采集。
