# AStockSystem：A股交易系统方案总 REVIEW v1.0

> 日期：2026-09-30  
> 定位：个人 A 股「研究 + 风控 + 交易训练 + 数据工程」系统  
> 当前阶段：V0.1 设计冻结前的方案 REVIEW  
> 核心原则：**研究可以保留有边界的主观判断，风险必须尽量客观；数据负责发现，AI 负责理解，规则负责约束，人负责最终决策。**

---

## 0. 先说结论：这套方案值得继续，但需要做 9 个重要修订

回顾前面的全部讨论，原方向总体正确：我们没有走「GPT 每天喊票」或「机械指标金叉买入」的路线，而是逐渐形成了：

**市场环境 → 行业/主题 → 催化 → 个股 → Setup → 风险收益比 → 仓位 → 退出 → 复盘**

这条链路。

经过进一步查资料和重新审视，我认为需要做以下关键修订：

1. **从“一套趋势策略”升级为“同一风险框架下的多个策略模块”**：突破、趋势回踩、催化启动必须分别统计，不能混在一起优化。
2. **Market Regime 不应只给一个离散标签**：保留标签，但底层使用连续特征向量；策略是否允许启动由各自 Gate 决定。
3. **正式加入完整的基本面分析框架**：盈利质量、现金流、资产负债表、估值、预期变化、股东行为、治理风险、行业专属指标都要进入研究层。
4. **正式加入“主题/叙事层”**：申万行业不足以描述 A 股政策与主题轮动，要把“正式行业”和“动态主题”分开管理。
5. **退出体系需要从一句“逻辑/趋势止损”升级为可回测的 Exit Engine**：初始止损、时间止损、趋势退出、逻辑失效、加仓、跳空/跌停风险分别处理。
6. **必须把 T+1 和隔夜跳空风险纳入仓位，而不只是止损**：A 股的止损价不是损失上限，尤其是事件、ST、北交所和高波动票。
7. **回测需要明确“信息何时可见、何时可下单”**：收盘后生成的信号不能按当天收盘价成交；14:50 模式和 EOD 模式必须分开。
8. **增加组合层风险和归因**：不能只管理单笔风险，还必须控制行业集中、相关性、总开放风险、Beta/风格暴露，并比较适当基准。
9. **ChatGPT 与 Codex 的关系要制度化**：ChatGPT 负责研究/策略/审查，Codex 负责实现/测试/运行；Git 仓库和数据库才是二者之间的“共同记忆”。

这 9 条应进入正式版本。

---

# 1. 我们到底在解决什么问题

过去的问题不是简单的“不会选股”，而是交易决策没有一个稳定的反馈系统：

- 热点/消息出现后冲动买入；
- 下跌时缺少明确失效条件；
- 盈利单容易过早兑现；
- 亏损单容易因为成本锚定而长期拖延；
- 市场好时风险偏好快速扩大，市场差时又回避账户；
- 查看账户频率过高，但信息利用率很低。

这和行为金融里常见的**处置效应（disposition effect）**高度一致：过早卖掉赢家、过久持有输家。2026 年一篇针对中国 A 股的研究也发现，处置效应会削弱价格延续；这类研究不能证明我们未来一定靠趋势赚钱，但它进一步支持一个行为目标：**不应让“盈利/亏损状态本身”成为卖出与持有的核心理由。**

因此，AStockSystem 的首要 KPI 不是“AI 选股准确率”，而是：

> **把每一笔交易从临场情绪行为，变成可事前定义、可事后验证的概率决策。**

---

# 2. 最终的人机协作关系

## 2.1 你：风险所有者 + 最终决策者

你不需要成为程序员，也不应该把决策责任外包给 AI。

你主要负责：

- 确认交易逻辑是否理解；
- 确认允许承担的风险；
- 最终下单；
- 如实记录是否执行了计划；
- 对系统升级拥有最终批准权。

## 2.2 ChatGPT：研究负责人 + 交易教练 + Strategy Review

ChatGPT 的主要职责应当是：

- 当前市场与行业环境研究；
- 公司/行业/政策/公告/财报深度分析；
- 催化真伪与经济传导判断；
- 帮你形成交易计划，而不是只报股票代码；
- 审查是否违反风险宪法；
- 审查 Codex 做出的回测和统计是否存在方法学错误；
- 周/月度复盘：区分策略问题、执行问题、市场环境问题；
- 提出下一轮需要验证的假设。

**ChatGPT 不应承担的角色：**

- 保证盈利；
- 随口预测第二天涨跌；
- 用一条消息替代完整研究；
- 在没有数据连接时假装能实时看到你的账户；
- 自主修改系统规则来“救”一笔亏损交易。

## 2.3 Codex：软件工程师 + 数据工程师 + 回测执行器

Codex 主要负责：

- 项目代码；
- 数据下载/清洗/存储；
- 指标与因子计算；
- Market Regime、行业雷达、候选池程序；
- 回测引擎；
- 单元测试；
- 每日报告生成；
- 以后再做通知与盘中监测。

Codex **不能自主决定“什么策略更值得你用”**。它可以发现统计现象，但策略变更必须回到研究层审查。

## 2.4 二者如何协作

推荐流程：

```text
ChatGPT
提出策略规格 / 研究假设 / 风险规则
        ↓
写入 docs/specs 或 config
        ↓
Codex
实现 + 测试 + 运行 + 输出报告
        ↓
Git + DuckDB/Parquet + reports
形成可审计结果
        ↓
ChatGPT
阅读结果 + 方法学 REVIEW + 解释
        ↓
你
批准 / 拒绝 / 小资金验证
```

所以，**未来不是你“主要去 Codex，ChatGPT 的任务就结束了”**。

更合理的是：

- 写代码、运行程序、修 bug：Codex；
- 研究市场、看股票、分析财报/公告、审核策略、讨论交易：ChatGPT；
- 两者共享事实：项目仓库 + 数据库 + 自动生成的 Markdown/CSV/Parquet 报告。

如果把 GitHub 连接给 ChatGPT，未来可以进一步减少“复制 Codex 输出到聊天”的工作量；但当前即使不连接，也不影响第一阶段建设。

---

# 3. 交易系统总体结构 v1.0

```text
                    ┌──────────────────┐
                    │ 交易所 / 巨潮公告 │
                    │ 财报 / 行业数据    │
                    │ 政策 / 新闻 / 商品 │
                    └────────┬─────────┘
                             ↓
                      Source Verification
                             ↓
行情 ──→ PIT 数据仓库 ──→ Market Regime
                             ↓
                    Industry + Theme Radar
                             ↓
                     Candidate Discovery
                             ↓
                 Fundamental / Catalyst Review
                             ↓
               Strategy-specific Setup Engine
          ┌───────────┬───────────┬───────────┐
          │ Breakout  │ Pullback  │ Catalyst  │
          └───────────┴───────────┴───────────┘
                             ↓
                   Risk / Execution Filter
                             ↓
                        Trade Plan
                             ↓
                         人工确认
                             ↓
                       券商人工执行
                             ↓
             Execution Log / Position / Review
                             ↓
            Attribution / Backtest / Improvement
```

---

# 4. 不再建立“万能策略”，而是建立三个独立策略模块

这是本次 REVIEW 最重要的修改之一。

## 4.1 Strategy A：趋势突破 Breakout

适合：

- 市场风险偏好较好；
- 行业趋势有持续性；
- 个股经过整理、波动收敛；
- 有基本面/产业/盈利支持；
- 突破不是纯单日情绪脉冲。

核心问题不是“有没有创 60 日新高”，而是：

- 突破之前是否有足够的蓄势结构；
- 行业有没有同步；
- 成交是否健康；
- 上方是否有明显筹码/估值约束；
- 突破后失败的位置在哪里。

## 4.2 Strategy B：趋势回踩 Pullback

适合：

- 原趋势已被证明存在；
- 行业/主题没有破坏；
- 回调过程成交或波动降温；
- 个股相对强度仍然较高；
- 出现重新转强确认。

它和“抄底”的根本区别：

> 抄底：因为跌得多。  
> 回踩：因为上升趋势存在，调整后重新出现买方确认。

## 4.3 Strategy C：催化启动 Catalyst

处理：

- 财报/业绩预告；
- 重大订单；
- 产品涨价；
- 供需变化；
- 正式政策；
- 新产品/技术路线；
- 重大产业事件。

它必须有独立的：

- 更严格信息源验证；
- “已经 Price-in 多少”的判断；
- 更小的初始风险预算；
- 更短的验证窗口；
- 更强的隔夜跳空风险模型。

**这三类策略不能把交易放进一个样本里直接算胜率。**

我们未来必须分别统计：

- expectancy；
- win rate；
- AvgWin / AvgLoss；
- MAE / MFE；
- holding period；
- turnover；
- regime sensitivity；
- 最大连续亏损；
- gap loss；
- liquidity/slippage。

---

# 5. Market Regime：从“标签”升级成“状态向量”

前面定义 A/B/C/D 市场环境作为思考框架是有用的，但不能过早做成一个 0~100 分的神秘总分。

第一阶段建议每天保存如下向量：

## 5.1 Trend

宽基指数：

- 沪深300；
- 中证500；
- 中证1000；
- 创业板相关指数；
- 科创相关指数；
- 北证相关指数（研究北交所时）。

计算：

- 5/20/60 日收益；
- MA20、MA60 位置和斜率；
- 高低点结构；
- 距离阶段高点。

## 5.2 Breadth

全市场与分板块：

- 高于 MA20 的比例；
- 高于 MA60 的比例；
- 20/60 日新高数量；
- 20/60 日新低数量；
- 上涨/下跌家数；
- 强势股扩散程度。

## 5.3 Liquidity

- 全市场成交额；
- 相对 20 日成交均值；
- 行业成交占比变化；
- 个股成交额分位数。

## 5.4 Volatility / Stress

建议补充：

- 宽基实现波动率；
- 横截面波动/离散度；
- 大跌家数；
- 涨停/跌停与炸板等情绪性统计（如数据可靠）；
- 极端 gap 数量。

## 5.5 Style

不能只看一个大盘指数：

- 大盘 vs 小盘；
- 价值 vs 成长；
- 高波动 vs 低波动；
- 科技/周期/消费等大类风格。

最终可以显示：

```text
Regime label: B1 轮动偏强
Trend:          +
Breadth:        neutral+
Liquidity:      +
Volatility:     neutral
Small-cap RS:   +
Growth RS:      +
Dispersion:     high
```

**标签用于人类阅读，连续特征用于策略 Gate 和后续统计。**

---

# 6. 正式加入“Industry + Theme”双层结构

只用申万行业会漏掉 A 股非常重要的一类行情：

- 人形机器人；
- AI 算力；
- 商业航天；
- 固态电池；
- 国企改革；
- 设备更新；
- 特定政策主题。

这些往往横跨多个传统行业。

因此系统里应该分开：

## Formal Industry

使用稳定的行业分类（如申万 L1/L2），用于：

- 长期统计；
- 财务同业比较；
- 相对强度；
- 行业宽度；
- 风险集中度。

## Dynamic Theme

由事件/新闻/公告生成可变主题标签，例如：

```text
theme_id
theme_name
start_date
source_event
related_stocks
confidence
economic_link
last_update
status
```

主题不能因为几个财经标题就自动成立。

必须记录：

1. 原始事件是什么；
2. 谁是直接受益者；
3. 谁只是概念映射；
4. 经济传导是否能影响收入/利润/估值；
5. 当前价格是否已经大幅提前反映；
6. 板块是否出现真实扩散。

这会显著提高我们处理“政策驱动/消息驱动/快速轮动”的能力，同时不退回“追消息”模式。

---

# 7. 常见股票分析框架：我们应该正式纳入哪些内容

原方案对“趋势 + 催化”讨论得较多，对传统公司研究覆盖不足。本次正式补足。

每个重点候选至少从下面 8 个维度分析。

## 7.1 Business

回答：

- 公司到底赚什么钱；
- 主营产品/客户/地区；
- 行业处于周期哪个位置；
- 市占率和竞争格局；
- 核心成本变量；
- 是否有明显客户集中或单一产品风险。

## 7.2 Growth

看：

- 收入同比/环比；
- 净利润与扣非净利润；
- 增速是在加速还是减速；
- 新业务占比；
- 订单/产能/销量；
- 增长是价格、数量还是并表带来的。

**增长率绝对值不是唯一重点，变化方向和预期差更重要。**

## 7.3 Earnings Quality

重点：

- 经营现金流 vs 净利润；
- 应收账款增速 vs 收入增速；
- 存货变化；
- 毛利率/净利率趋势；
- 非经常性损益；
- 政府补助、资产处置等一次性项目；
- 资本化与费用化；
- 大额商誉/减值风险。

近期研究也提示，在 A 股研究“盈利”时不能只看表面利润，需要留意非经常损益和可能的盈余管理。

## 7.4 Balance Sheet

- 现金和有息负债；
- 短债压力；
- 资产负债率；
- 利息覆盖；
- 质押/担保；
- 大额资本开支；
- 融资需求。

## 7.5 Profitability / Quality

可使用但不迷信：

- ROE；
- ROIC；
- 毛利率；
- 营业利润率；
- 现金转换。

2026 年对中国 A 股质量因子的研究显示，“质量”并非所有维度都稳定有效，其中盈利能力的证据相对更一致。这支持我们把 profitability 作为研究证据，而不是建立一个“ROE > 15% 自动买入”的筛选器。

## 7.6 Valuation

禁止统一用一个 PE 阈值。

根据行业选择：

- PE / forward PE；
- PB；
- PS；
- EV/EBITDA；
- FCF yield；
- 周期股的 mid-cycle earnings；
- 资源公司的商品价格敏感性；
- 金融公司的 PB/ROE、资产质量；
- 高成长公司的增长兑现与估值消化。

评价对象：

1. 自身历史；
2. 同业；
3. 盈利增长；
4. 当前产业周期；
5. 市场已经 Price-in 了多少。

## 7.7 Expectations / Surprise

这是原计划中遗漏较大的维度。

我们应追踪：

- 业绩预告；
- 业绩快报；
- 正式财报；
- 一致预期（未来有数据时）；
- 管理层指引；
- 分析师盈利预测修正；
- 财报后的 overnight gap。

中国市场长期存在针对业绩 surprise 后价格继续漂移（PEAD）的研究证据。它不意味着“财报超预期就一定买”，但说明：

> **“预期发生变化”应该是 Catalyst 模块中的核心变量，而不仅仅是财报同比增速。**

## 7.8 Governance / Supply

A 股还要重点检查：

- 大股东/高管减持；
- 解禁日历；
- 定增/配股/可转债；
- 股权质押；
- 回购；
- 分红；
- 监管处罚；
- 审计意见；
- 频繁更换审计机构/CFO 等异常情况。

---

# 8. 不同行业需要不同研究模板

这是此前方案中另一个明显缺口。

不能用同一套指标分析所有公司。

## 周期/资源

需要关注：

- 商品价格；
- 产量；
- 单位成本；
- 库存；
- 产能投放；
- 行业供需；
- 价格弹性。

## 制造业

- 订单；
- 产能利用率；
- 毛利率；
- 海外收入；
- 应收/存货；
- 资本开支；
- 客户集中。

## 科技成长

- R&D；
- 产品迭代；
- 渗透率；
- 订单和客户认证；
- 毛利率；
- 现金消耗；
- 竞争格局；
- 估值/成长匹配。

## 金融

普通制造业的“存货/毛利率”框架不适用，应看：

- 资产质量；
- 净息差；
- 不良率；
- 拨备；
- 资本充足率；
- ROE 等。

所以 Skill 最终应该允许加载 sector-specific checklist，而不是一张万能表。

---

# 9. Catalyst Engine：不只做“消息评级”

每个事件至少记录：

```text
source
published_at
first_seen_at
event_type
novelty
certainty
direction
affected_industries
affected_companies
economic_transmission
earnings_materiality
time_horizon
market_reaction
already_priced_in
invalidating_evidence
```

研究顺序：

**原始来源 → 事实 → 经济传导 → 受益链 → 市场确认 → 赔率**

来源优先级：

1. 交易所 / 巨潮 / 公司法定公告；
2. 政策原文 / 政府部门；
3. 权威产业数据；
4. 公司正式沟通；
5. 高质量财经媒体；
6. 券商/分析师观点；
7. 传闻/社交媒体。

低等级来源可以用于“发现”，不能单独用于“下单”。

巨潮资讯是深交所信息披露官方网站，适合作为公司公告的重要原始来源之一。

---

# 10. Entry Engine：灵活，但必须有结构

前面讨论“规则下的灵活”是对的。

最终不是：

```text
MA20 > MA60 → BUY
```

而应该是：

```text
Strategy Gate 通过
    +
Stock Thesis 通过
    +
Setup 出现
    +
执行价格仍满足 R/R
    +
组合风险允许
→ READY
```

每个 READY 交易必须在下单前有：

- Strategy；
- Thesis；
- Catalyst（如有）；
- Entry condition；
- Planned execution；
- Initial invalidation；
- Initial R；
- Position size；
- Add rule；
- Exit rule；
- Event risks；
- 最大预期正常损失；
- gap stress loss。

---

# 11. Exit Engine：必须比 Entry 更严格

过去最大的问题之一正是退出。

因此 V1 需要至少区分：

## 11.1 Initial Risk Stop

不是随便设 -5%/-8%。

基于：

- 技术结构；
- 波动率；
- 逻辑失效位置。

**买入后禁止为了避免认错而下移。**

## 11.2 Logic Exit

即使价格没跌很多，只要买入核心事实被证伪，也需要重新评估甚至退出。

## 11.3 Trend Exit

赢家不因为 “+10%” 卖出。

退出应来自：

- 趋势结构破坏；
- trailing rule；
- 行业/相对强度明显恶化。

具体参数必须回测，不能现在拍脑袋确定。

## 11.4 Time Stop

这是此前遗漏的重要机制。

如果买入理由是“即将突破/事件驱动”，但若干交易日没有任何 follow-through：

- 机会成本上升；
- 原假设可能不够强；
- 资金可以释放。

时间止损的 N 天必须按策略分别验证。

## 11.5 Add-on

只允许：

> 新的信息/价格行为进一步证明原逻辑 → 加仓。

不允许：

> 跌了 → 更便宜 → 摊低成本。

而且加仓后要重新计算：

**整个 position 的总风险，而不是只看新增仓位。**

---

# 12. A 股特有风险：止损价不等于最大亏损

A 股股票一般不能在买入后当日卖出，交易所规则也明确只有特定品种实行当日回转；因此股票策略必须显式建模 T+1。

意味着：

你 30 元买入、计划 28 元止损，

不代表最大只亏 6.7%。

第二天可能：

- 跳空低开；
- 跌停；
- 一字跌停；
- 连续无法按计划成交。

所以每笔交易需要同时保存：

```text
planned_risk
gap_stress_risk
limit_down_stress_risk
```

事件型、ST、北交所高波动标的尤其如此。

### 2026 年交易规则变化也必须做成 Point-in-Time Rule Table

截至 2026-09-30：

- 沪市主板普通股票涨跌幅一般为 10%；
- 科创板一般为 20%；
- 深市创业板一般为 20%；
- 北交所一般为 30%；
- 2026-07-06 起，沪深主板风险警示股票涨跌幅由 5% 调整为 10%。

回测不能拿“今天的规则”套 2018 年，也不能把历史 ST 规则写死。

因此建立：

```text
market_rule_history
-------------------
exchange
board
security_status
effective_from
effective_to
price_limit_pct
t_plus_n
special_ipo_rule
lot_size
after_hours_rule
```

---

# 13. 风险宪法 V0.1：建议比之前更保守一点

你的风险承受意愿较强，但你自己给“按计划止损”的执行能力只有 3/10。

这意味着第一阶段应当重点训练**执行稳定性**，而不是追求目标收益。

建议：

## Training Stage

- 新系统单独记账，不与旧仓收益混合；
- 初期真实资金只使用总资产的一小部分；
- 单笔计划风险：总账户约 **0.20%~0.25%**；
- 同时开放风险：初期不超过约 **0.75%**；
- 同时持有新系统仓位：先 1~3 个；
- 高风险/事件型交易：风险预算再打折；
- 连续出现明显纪律违规时，先降风险，不通过放大仓位“赚回来”。

当满足例如：

- 30+ 个有效交易样本；
- 止损/计划执行率稳定；
- 没有明显计划外补仓；
- 策略 expectancy 和回撤有初步可信度；

再讨论提升到之前设想的 0.3%~0.4% 单笔风险。

**这里的百分比是初始风险预算假设，不是永久真理，需要按实际滑点和回测重新校准。**

---

# 14. Portfolio Risk：此前方案还缺这一层

单笔都很安全，不等于组合安全。

例如同时持有：

- 铜；
- 铝；
- 锂；
- 黄金；
- 矿山设备；

名义上 5 只股票，实际上可能是一个宏观风险因子。

因此组合层至少记录：

```text
gross_exposure
cash
open_risk_R
sector_exposure
theme_exposure
market_cap_exposure
style_exposure
correlation_cluster
beta_estimate
```

初期可建立软约束：

- 单一股票不能无限放大；
- 单行业/同主题不能占绝大多数风险；
- 高相关仓位要按“一笔大仓位”看；
- Risk-off 时减少总开放风险，而不是只调每只股票的 stop。

遗留仓位和新系统仓位要分开归因，但**总账户风险计算不能假装遗留仓不存在**。

---

# 15. Reward/Risk 需要修正：不要用虚假的“目标价精确度”

此前用：

```text
Reward / Risk > 2 或 > 3
```

作为解释很直观，但真实市场里的 Reward 很难精确估值。

因此 V1 建议：

## 对有明确结构阻力的交易

可以计算结构性 RR。

## 对趋势交易

更重要的是：

- 下行风险是否明确；
- 历史同类 setup 的 payoff distribution；
- 是否允许 winner 形成右尾。

我们不应该为了算出 “3:1” 而拍一个目标价。

更好的统计对象：

```text
MAE
MFE
realized_R
R_capture = realized_R / MFE
```

这样可以直接验证你是否仍然存在：

> 盈利单涨一点就卖。

---

# 16. 回测方法学：必须比选股公式更严格

## 16.1 Point-in-Time

每个字段要区分：

- `period_end`
- `published_at`
- `available_at`

财报属于 9 月 30 日报告期，不代表 9 月 30 日市场知道。

## 16.2 Survivorship Bias

必须保留：

- 已退市公司；
- 历史 ST；
- 历史停牌；
- 历史行业归属；
- 历史指数成分。

## 16.3 Signal / Execution Timestamp

这是非常容易犯的错误。

### EOD 模式

如果信号使用 15:00 收盘后的完整日线：

> 最早只能下一交易日执行。

不能：

> 用 15:00 后才知道的 close 生成信号，却回测成当日 close 买入。

### Pre-close 模式

如果以后在 14:45~14:55 决策：

必须保存/使用当时真正可见的：

- partial-day price；
- partial volume；
- 实时行业状态。

不能偷偷替换成完整收盘数据。

两种模式必须是两套数据路径。

## 16.4 可成交性

建模：

- 停牌；
- 一字涨停买不到；
- 一字跌停卖不掉；
- T+1；
- board-specific price limits；
- IPO 特殊规则；
- 交易单位。

## 16.5 Costs

回测必须按时间版本保存：

- 券商佣金；
- 最低佣金规则（以你的真实账户为准）；
- 过户/经手相关费用；
- 印花税；
- slippage。

证券交易印花税当前仍为出让方征收；自 2023-08-28 起实施减半征收。历史回测不能用今天的税率覆盖过去。

## 16.6 不要随机拆分时间序列

研究流程建议：

```text
Research period
   ↓
Validation period
   ↓
Out-of-sample period
   ↓
Walk-forward
   ↓
Paper / small live
```

参数不能看到测试集后一直反复调到好看。

## 16.7 多重试验偏差

如果我们测试：

- MA10/20/30/40；
- RS 10/20/30/60；
- 突破 20/40/60/120；
- 成交量 1.2/1.5/2.0 倍；

最终总会碰巧找到漂亮组合。

所以每一次策略迭代都必须记录：

```text
hypothesis_id
why_we_test_it
parameter_range
test_date
result
decision
```

避免“数据挖矿后假装一开始就知道”。

---

# 17. 绩效评价：以后不能只看收益率

至少同时看：

## Strategy Metrics

- total return；
- CAGR；
- max drawdown；
- volatility；
- Sharpe；
- Sortino；
- Calmar；
- win rate；
- payoff ratio；
- expectancy in R；
- profit factor；
- turnover；
- exposure；
- max consecutive losses。

## Trade Diagnostics

- MAE；
- MFE；
- R capture；
- holding days；
- entry gap；
- exit slippage；
- catalyst delay；
- 是否违规。

## Attribution

收益应该拆分为：

- 市场 Beta；
- 行业/主题；
- 选股；
- timing；
- position sizing；
- execution；
- 交易成本。

同时设置多个可比较基准，而不是永远只和上证指数比较。

---

# 18. 行为训练也应该进入数据库

我们的系统不是纯量化系统，它还需要改造执行行为。

建议 `trade_plan` 和 `executions` 里增加：

```text
planned_trade           bool
stop_moved_down         bool
loss_averaging          bool
impulse_entry           bool
exit_due_to_profit_fear bool
rule_override_reason    text
```

还可以计算：

- 计划外交易次数；
- 止损遵守率；
- 盈利交易过早退出比例；
- 亏损持仓平均时间 vs 盈利持仓平均时间；
- 规则变更发生在哪些市场环境。

这可能比多加 10 个技术指标更能改善长期结果。

---

# 19. 数据源方案：当前仍然维持，但补充质量控制

## V0.1

### 主行情/财务

Tushare 5000 积分档目前约 500 元，常规数据总量权限适合第一阶段日线研究。

第一阶段够用。

### 官方验证

- 上交所；
- 深交所；
- 北交所；
- 巨潮资讯；
- 政府/监管部门原文。

### Backup / Cross-check

AKShare 可作为辅助研究和交叉验证，不建议作为唯一生产行情来源。

## V0.2 / Intraday

当我们证明：

> 日线候选确实有价值，而最主要损失来自盘中执行质量

再考虑 RQData / 券商行情。

RQData 当前官方文档提供：

- A 股历史日/分钟/tick；
- 实时 tick/分钟；
- 财务数据；
- 多品种 API。

所以它更适合第二阶段盘中检测。

**当前不需要为了“专业感”提前购买分钟/Tick。**

---

# 20. 需要补充的数据表

此前 12 张核心表方向正确，但本次 REVIEW 建议增加：

```text
security_master
trade_calendar
market_rule_history

daily_bar
minute_bar          # Phase 2
adj_factor
daily_basic

corporate_actions
security_status_history
suspension_history

industry_membership_pit
theme_membership

financial_pit
earnings_events
shareholder_events
unlock_calendar

announcements
catalyst_events

market_snapshot
sector_snapshot
candidate_snapshot

strategy_signal
trade_plan
orders             # 先记录人工下单
executions
positions

daily_nav
portfolio_exposure
trade_review
strategy_metrics
research_hypothesis
data_quality_log
```

尤其新增：

- `market_rule_history`
- `security_status_history`
- `corporate_actions`
- `earnings_events`
- `shareholder_events`
- `research_hypothesis`
- `data_quality_log`

这些都是防止未来回测“看起来很好、实盘复现不了”的关键表。

---

# 21. 工程架构：原方案基本保留

Mac 研究机：

```text
Python 3.12
uv
pandas / numpy
DuckDB
Parquet / PyArrow
Pydantic Settings
Typer
httpx
tenacity
pytest
Git
```

第一阶段不需要：

- Kafka；
- Kubernetes；
- 微服务；
- Redis 集群；
- 机器学习平台；
- TA-Lib；
- 大型回测框架。

数据量只是一人 A 股研究系统，工程复杂度本身不能成为项目。

推荐数据分层：

```text
raw/       原始不可变
curated/   清洗后的 PIT 数据
features/  可重现特征
reports/   每日/周/月快照
```

---

# 22. AGENTS.md 与 Skills：重新明确边界

## AGENTS.md

只放跨项目永久工程规则，例如：

- 禁止未来函数；
- PIT；
- survivorship；
- A 股 T+1；
- 停牌/涨跌停；
- 历史规则版本化；
- secrets 不进 Git；
- 无测试不改交易规则；
- V0.1 禁止 live order。

不要把所有买点参数塞进 AGENTS.md。

## Skill

Skill 应该放“重复研究流程”，例如：

`a-share-research`：

```text
1. 确认数据时间
2. Market / Sector context
3. 原始公告优先
4. Business/Fundamental
5. Catalyst
6. Price/RS/Setup
7. Risks
8. Invalidating evidence
9. Trade-plan readiness
```

参数：

```text
MA windows
risk budget
sector cap
ATR settings
```

应该放版本化 config，而不是 Skill。

OpenAI 当前也建议避免不断膨胀 AGENTS.md，把专项工作流拆成 Skills。

---

# 23. 券商和 Mac 架构：原结论继续成立

当前你使用：

- 东方财富；
- 平安证券；
- Mac。

东方财富的专业 EMT API 当前官方 SDK 主要支持 Windows/Linux 64 位；平安提供量盈 QMT 等专业交易解决方案，同时有 Mac 普通交易终端。

因此 V0.1：

> **Mac = Research Node**  
> **券商 App/终端 = Manual Execution Node**

是最干净的设计。

等系统跑出统计优势后，若需要程序化交易，再评估：

- Windows 小主机；
- QMT；
- EMT API；
- 合规报告和券商权限。

当前证券市场程序化交易已有明确监管和报告制度，程序自动生成/下达交易指令时必须先确认券商与交易所要求。因此“AI 自动下单”不应是早期目标。

---

# 24. 实盘工作流 v1.0

## 盘前

只做：

- 持仓公告/重大事件；
- 隔夜重要行业/政策；
- 前一日 Market Regime；
- 今日事件日历；
- 候选池。

输出：

```text
Risk mode
Focus sectors/themes
Watchlist
Existing-position alerts
```

## 盘中

原则：

> 没有触发，不看。

Phase 1 可以直接使用券商价格提醒。

Phase 2 系统才做：

- Setup 接近；
- 行业突然扩散；
- 价格进入计划区；
- 持仓风险条件。

## 14:40~14:55

只适用于未来定义好的 Pre-close 策略。

不能把它和收盘后数据策略混为一谈。

## 收盘后

程序：

1. 数据健康检查；
2. 更新日线；
3. Market Regime；
4. Industry/Theme；
5. Candidate；
6. 持仓风险；
7. Strategy signal；
8. 报告。

ChatGPT：

- 阅读真正重要的候选；
- 搜原始公告/政策；
- 做基本面/催化研究；
- 形成第二日 Trade Plan。

---

# 25. “实时性”的最终定义

我们不追求比高频资金快 100ms。

我们需要的是：

> **任何足以改变我们的交易决策的信息，在策略所需的时间尺度内被识别。**

对当前系统：

- 公司重大公告：尽快；
- 重大政策/产业事件：分钟到小时；
- 行业轮动：15 分钟到日线；
- 趋势交易：日线/收盘前；
- 风险事件：及时告警。

这比全天盯 Level-2 更适合你的实际时间约束，也更不容易把原来的高频查看账户行为重新强化。

---

# 26. 阶段路线图（建议）

## Phase 0 — Governance

先完成：

- 仓库；
- AGENTS.md；
- 风险宪法模板；
- 数据字典；
- 策略模块定义；
- 研究假设日志。

**不写选股策略。**

## Phase 1 — Data Foundation

建立：

- 股票主表；
- 日线；
- 复权；
- 财务 PIT；
- ST/停牌/退市历史；
- 行业 PIT；
- 交易规则历史。

验证：

- 数据完整；
- 无未来函数；
- 可复现。

## Phase 2 — Market + Sector Radar

完成：

- Market State；
- Industry Strength；
- Strength Change；
- Breadth；
- Candidate Snapshot。

只观察，不下大资金。

## Phase 3 — Strategy Prototypes

分别做：

- Breakout v0.1；
- Pullback v0.1；
- Catalyst v0.1。

不能混样本。

## Phase 4 — Backtest + OOS

输出：

- 执行现实化后的结果；
- regime 分解；
- 参数敏感度；
- trade distribution；
- stress test。

## Phase 5 — Paper + Small Live

最重要目标：

> **验证人的执行 + 系统实际数据链路。**

不是赚多少钱。

## Phase 6 — Intraday

只有出现明确证据：

> 日线策略有效，但执行和盘中确认仍明显影响结果

才购买分钟/实时数据。

## Phase 7 — Broker API

最后考虑。

满足：

- 策略经过足够样本；
- live 行为稳定；
- 风控成熟；
- API/合规明确；
- 有 kill switch。

---

# 27. 第一批真正值得 Codex 做的任务

不是“写个选股程序”。

优先级应当是：

### Task 1：Repository Foundation

完成项目结构、依赖、测试、Git、AGENTS。

### Task 2：Data Contract

定义：

- schema；
- PIT 时间字段；
- unique key；
- source；
- data quality rule。

### Task 3：Tushare Ingestion

只接：

- security master；
- calendar；
- daily；
- adj factor；
- daily basic；
- financials；
- index。

### Task 4：Historical Rule / Status

这是容易漏掉但价值极高的模块：

- ST；
- suspend；
- delist；
- board；
- IPO；
- price limit history。

### Task 5：Data Audit

随机抽股票/日期和官方或第二数据源核对。

### Task 6：Market Snapshot

最后才开始计算第一批真正的研究特征。

---

# 28. 第一批真正值得我们在 ChatGPT 做的研究

与此同时，ChatGPT 侧不需要等程序全部写好。

可以建立四个固定研究模板：

## Daily Market Review

市场状态、行业、主题、风险。

## Company Deep Dive

业务、财务、估值、催化、风险。

## Trade Plan Review

是否 READY、失效点、风险、执行条件。

## Post-trade Review

策略结果与行为执行分开评价。

未来每笔交易都必须能回答：

> 如果今天我没有持仓，我是否仍然愿意按当前价格和当前信息建立这个仓位？

这个问题用来削弱成本锚定。

---

# 29. 我们暂时不要做的事情

- 不上来就训练 AI 预测涨跌；
- 不让大模型凭 K 线截图“看图算命”；
- 不自动下单；
- 不买一堆昂贵行情；
- 不做 100 项指标加权总分；
- 不对 20 个参数暴力优化；
- 不用回测最优参数直接实盘；
- 不把 ST/北交所/次新和普通策略混为一谈；
- 不因为某个策略近期亏损就临时改规则；
- 不用收益目标倒逼交易频率。

---

# 30. 最终的核心哲学

我们最终不是要建一个：

> “预测下只牛股的 AI。”

而是建：

> **一个让错误快速暴露、让正确交易有机会奔跑、让所有决策有证据链、让系统持续从真实数据中更新的交易操作系统。**

它的优势如果最终存在，应该来自组合：

```text
市场状态判断
+
行业/主题识别
+
基本面与预期变化
+
相对强弱
+
高质量催化理解
+
可重复的 Setup
+
不对称风险收益
+
严格组合风险
+
执行纪律
```

而不是来自任何单一指标。

---

# 31. 当前版本的正式原则（建议冻结）

> **研究可以主观，风险必须客观。**  
> **策略可以适应环境，纪律不能随仓位盈亏改变。**  
> **先定义什么情况下错，再考虑能赚多少。**  
> **不因为跌得多买，不因为赚了一点卖。**  
> **亏损不能自动变长期投资。**  
> **加仓必须来自更多正面证据，而不是更低价格。**  
> **消息用于发现，原始来源用于确认。**  
> **价格强度是证据，不是结论。**  
> **基本面是解释和验证，不是低 PE 崇拜。**  
> **所有策略必须经过真实可成交条件下的 OOS/小资金验证。**  
> **没有 Setup、没有赔率、没有失效点，就没有交易。**  
> **现金是有效仓位。**

---

# 32. 下一步

下一步不应该再继续扩展理论。

正确动作是：

**启动 Codex Phase 0 + Phase 1。**

第一阶段交付物应当只有：

```text
repo foundation
data schema
data dictionary
market-rule history schema
risk constitution template
Tushare ingestion skeleton
data quality tests
```

在这批东西经过 REVIEW 以前：

> **不让 Codex 开始“优化策略”。**

---

# 参考资料与核查来源（截至 2026-09-30）

## 交易规则 / 官方信息

1. 上海证券交易所，《上海证券交易所交易规则（2026年修订）》  
   https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml

2. 深圳证券交易所，《深圳证券交易所交易规则（2026年修订）》  
   https://www.szse.cn/lawrules/rule/trade/current/t20260424_620190.html

3. 北京证券交易所，《北京证券交易所交易规则》（2026）  
   https://www.bse.cn/jygl_list/200028217.html

4. 中国证监会，《证券市场程序化交易管理规定（试行）》  
   https://www.csrc.gov.cn/csrc/c100028/c7480577/content.shtml

5. 上海证券交易所，《程序化交易管理实施细则》  
   https://www.sse.com.cn/lawandrules/sselawsrules2025/trade/universal/c/c_20250612_10781696.shtml

6. 巨潮资讯网  
   https://www.cninfo.com.cn/

7. 财政部/税务总局，《关于减半征收证券交易印花税的公告》  
   https://www.mof.gov.cn/jrttts/202308/t20230828_3904235.htm

## 数据与券商基础设施

8. Tushare 数据权限说明  
   https://tushare.pro/document/1?doc_id=290

9. Ricequant RQData Python API  
   https://rqdatad-us2.ricequant.com/doc/rqdata/python/index-rqdatac

10. 东方财富 EMT / 量化平台下载与 API  
    https://emt.eastmoneysec.com/down

11. 平安证券专业交易 / 量盈 QMT  
    https://stock.pingan.com/static/webinfo/agencybrokerage/agencybrokerage.html

## Codex / Skills

12. OpenAI, Introducing the Codex app  
    https://openai.com/index/introducing-the-codex-app/

13. OpenAI Developers, Rethinking skills and prompts  
    https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra

14. OpenAI Developers, Skills  
    https://developers.openai.com/api/docs/guides/tools-skills

## 学术研究：用于形成假设，而非保证未来收益

15. Li et al. (2026), *The disposition effect and monthly momentum in China's A-share market*, Pacific-Basin Finance Journal.  
    https://www.sciencedirect.com/science/article/pii/S0927538X26002714

16. Yang, Gebka & Hudson (2019), *Momentum effects in China: A review of the literature and an empirical explanation of prevailing controversies*.  
    https://www.sciencedirect.com/science/article/pii/S0275531918302046

17. Ma, Liao & Jiang (2024), *Factor momentum in the Chinese stock market*, Journal of Empirical Finance.  
    https://doi.org/10.1016/j.jempfin.2023.101458

18. Truong (2011), *Post-earnings announcement abnormal return in the Chinese equity market*.  
    https://www.sciencedirect.com/science/article/pii/S1042443111000205

19. Lan et al. (2024), *Post earnings announcement drift: A simple earnings surprise measure...*  
    https://www.sciencedirect.com/science/article/pii/S1057521924003922

20. Li, Chen & Jiao (2026), *Moderate and Useful: The Performance of Quality Factor in Chinese Market*.  
    https://journals.sagepub.com/doi/10.1177/21576203261457355

21. He, Jiang & Xiong (2026), *Earnings Management and Price Informativeness*, NBER Working Paper 35178.  
    https://www.nber.org/papers/w35178

---

## 版本说明

**v1.0 / 2026-09-30**

本文件是对此前完整讨论的 REVIEW，不代表任何交易策略已经被历史或实盘证明有效。  
所有策略参数仍属于待验证假设；后续任何改变必须进入 `strategy_changelog.md`，保留原因、日期、证据和验证结果。
