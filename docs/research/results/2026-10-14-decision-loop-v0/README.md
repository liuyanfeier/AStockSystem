# Decision Loop V0：同一公司持续判断

先读[真实证据收盘命令输出](close-command/DECISION.md)，再读[变化演练](simulated/DECISION.md)。
真实行情仍止2026-10-12；本批没有新市场API、真实持仓或实际订单。
第二次真实观察重查已有披露；没有真实新事件时，用明确模拟检查状态转移，不编造公司新公告。

|案例|真实初始/重查判断|显式模拟变化|人工动作与复盘演练|
|---|---|---|---|
|招商银行600036.SH|不良率0.94%、核心一级资本14.07%，有限检查仍支持继续研究；信用质量/估值待补|指标未变化，继续观察；到期复核，不代表可以买|模拟人工核对后保留观察，不下单|
|万科A000002.SZ|H1亏损149.51亿元、现金流4.95亿元；持续经营和偿债风险未消除，等待证据|模拟重要债务/交付事件挑战现金逻辑，触发逻辑失效复核|模拟人工进入风险核验，不假造卖出|
|招商轮船601872.SH|盈利69.60亿元、CFO81.31亿元；有限正向检查支持继续研究，周期持续性未知|模拟回款信息缺失，暂停新交易|后续模拟人工结束本轮观察，保留EXIT及复盘，不是实际平仓|

[真实保留证据观察](real/DECISION.md) → [模拟初始](simulated-baseline/DECISION.md)
→ [模拟新信息](simulated/DECISION.md) → [模拟观察结束](simulated-end/DECISION.md)。
每个目录的decision.json保留指标原值/期间/来源Hash、基线/最新证据版本、上次观察、变更与到期。
[生命周期摘要](LIFECYCLES.json)记录模式与输出Hash；所有用户真实动作/订单为0。
模拟报告使用虚拟10月16/17日截止，标题与JSON都标记OFFLINE_SIMULATION，不能冒充当前真实发生。

## 持仓和组合

真实账户UNKNOWN，不据未录入推断空仓。实际用户没有提供持仓，不能宣称已接入账户。
三只模拟持仓单独保存在私有simulated Store，未确认、现金未知、报价陈旧，账户总资产/权重均UNKNOWN。
已报持仓与行业占比只描述该模拟快照及报价日，不等于完整账户暴露；不启用任何风险阈值。
USER_MANUAL输入模式、完整快照/现金/新价格才可算权重、缺报价不重新归一化等由合成反例验证。
公开投影不包含持仓、现金、Journal、私人计划 prose/人工动作理由或来源自由描述。

## 已完成的离线闭环

- 原128日Store只读复算；[合成两日增量组合](INCREMENT_REHEARSAL.json)保留706095条旧日行情，三个案例达到130连续交易日。不是已取得真实13/14日行情。
- 同一计划/证据可重复复算；PLAN/REVIEW/EXIT追加，报告不可覆盖。上次观察来自同计划、同模式、截止前的Journal绑定报告。
- 新公告/反面证据变化进入等待复核；人工确认需匹配来源Hash，不能靠一句“已检查”消除未核实风险。
- [Breakout实验](PAPER_LAB.json)仅合成流程，展示下一开盘、T+1、跳空、费用/滑点、限价与未知阻断；策略收益NOT_VALIDATED。
- [本批使用来源保全](PRESERVATION.json)验证原Store/31文档，无旧库写入、删除或消费改写，不重复全历史审计。

## 复现与下一步

~~~bash
.venv/bin/python scripts/research/rehearse_decision_loop.py
.venv/bin/python scripts/research/rehearse_decision_increment.py
~~~

需要本地保留的V2 Store与V3 PDF。冻结输入位于config/decision-loop，下一版本必须另存，不回填旧判断。
收盘CLI实例、私有路径与准确权限边界见[Decision Loop说明](../../../DECISION_LOOP_V0.md)。
[采集清单与Hash](ACQUISITION_PROPOSAL.json)仅未授权提案；真实更新及用户持仓输入仍待落实。
公开出处/原表页码见[原V3公司卡](../2026-10-14-company-v3/README.md)及各decision.json。
数字同原披露；公司披露、镜像与本地Hash的原局限继续适用，有限核查不是审计或完整公告检索。
