# AStockSystem 全A股市场与行业雷达：首次采集停止记录

**本批首个连接失败，未取得行情；这不是已完成的全市场与31行业研究报告。**

2026-10-13，本轮直接用户消息批准固定299请求方案及GPT提供的审批结论。
实际执行版本为PR #5普通合并后的main `8ab3a7c6e84a25d645e29085fd9757dbfabc12c4`。
执行前干净Git、新目的地无历史消费、令牌存在，plan/implementation hash精确匹配批准值；
2026-04-01—2026-10-12、SSE/SZSE/BSE、SW2021一级31行业及两指数范围不变。

| 实际事实 | 结果 |
|---|---|
| 新采集尝试 | 1：stock_basic，exchange=SSE，list_status=L |
| COMPLETE / FAILED / UNKNOWN / 未尝试 | 0 / 0 / 1 / 298 |
| 错误 | TRANSPORT_CONNECT_ERROR；未取得HTTP响应 |
| Raw / 可用回执 | 0 / 0 |
| 本批接收股票/行业/行情/日期记录 | 全部0；未取得来源，不是市场数量为零 |
| 实际当前A股证券池分母 | UNKNOWN；三市场身份分区尚未取得 |
| Market Regime、MA20/60、行业强弱、筛选 | NOT_RUN，指标和候选数量保持null |
| 跨交易所/行业独立股票数值抽查 | 不适用，无Raw可抽查 |
| 新Research Store导入/重建 | NOT_RUN，无可准入bundle |
| 新采集目的地实际大小 | 78,521字节；全部为计划、许可、claim/result及锁等元数据 |

授权停止策略为continue_on_error=false。已首错停止，保留不可变claim与UNKNOWN，未自动重发、
清空目录、追加诊断HTTP或购买权限。安全分类不能区分DNS、连接或TLS根因，也不能据此宣称
Tushare权限不足、字段合同错误或供应商系统异常。stock_basic、index_classify和index_member_all
首次真实返回格式/权限/覆盖验收仍待完成；严格版本、秘密、预算、TLS与消费保护保持。

[结构化公开投影](snapshot.json)使用既有public_snapshot白名单；没有Raw、许可内容、个人路径、
Journal、持仓、成交或人工观察清单。原始许可、当前用户授权引文与完整本地执行事实私有保留。
公开hash用于本地来源绑定，不能替代供应商响应、签名或私有证据访问。

原106消费（39 COMPLETE、66 FAILED、1 UNKNOWN）和391相关文件hash不变；
155655历史保护文件changed=0、missing=0。旧10股真实研究及4候选保留，它们不作为本批全市场验收。
软件回归/CI成功与真实业务未完成分别报告，见[验证摘要](VALIDATION.md)。

下一步先确认具备联网权限的执行环境。已准备一个仅更换目的地的299请求新批次提案，
明确包含原UNKNOWN成员重新请求；原001消费保持。该提案未获授权，详见[当前REVIEW](../../../REVIEW.md)。
取得足够来源后复用现有Store/radar，产出真实业务报告与数值抽查；随后进入公司基本面、公告催化及退出计划。
