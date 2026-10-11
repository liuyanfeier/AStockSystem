# Research V1：下一批直接开发入口

目标：真实行情 → 独立 Research Store → Market Regime / Screening → 候选观察报告，
并生成第一份真实股票研究观察卡。范围是当前研究用途，不发起新的全历史 Phase1 项目。
本文件是可实施设计与任务范围说明；下面的 Research 模块/命令尚未实现，本轮不采集/导入真实数据。

## 第一份报告怎么来

1. 先确定报告截止时间、实际行情截止日、观察 universe、基准指数、窗口和来源。
   下一批建议从连续近期日线（约 120 个交易日的研究窗口）开始；不足则缺项并报告，
   不从 21 个离散历史日计算伪连续收益。120 日是开发建议，不是已批准采集成员或交易阈值。
2. 以用户提供且来源可验证的真实文件，或另行明确授权的近期采集作为输入。
   文件先进入独立 raw 与 manifest；网络授权须明确成员/窗口、预算、HTTPS 端点、目的地与停止条件。
   不运行旧 probe/slice/RAW49 控制器，不重试旧失败/未知，也不消费未许可全历史申请。
3. 导入新 Research Store，验证原生身份、日期/主键、单位、空值、来源、可用时间、
   完整窗口、ST/停牌/限价与数据覆盖，记录用途 CURRENT_OBSERVATION。
4. 程序计算描述性市场趋势、宽度、成交/波动、相对强弱；筛出有足够真实输入的观察候选。
   排名仅缩小研究范围，不能贴“已验证策略/买点”标签。全市场宽度必须有当次足够 universe，
   仅自选池时写“池内宽度”，不能代表整个市场。
5. 候选至少生成一张包含价格/成交表现、来源/截止时间、入选理由、反面风险、
   缺项及不交易/失效条件的卡片。基本面、行业/主题、公告未验证就标 UNKNOWN，
   不凭涨幅或 AI 联想制造催化归因。
6. 保存私有输入 manifest、参数/代码版本、计算快照和 Markdown 报告。
   可同时选择人工指定股票；不强迫每天产出推荐或交易。用户负责最终判断与券商手工执行。

## 具体调用哪些已有能力

| 环节 | 已有代码/数据 | 首批新增部分 |
|---|---|---|
| 设置/路径/秘密 | paths.py、settings.py、CLI 与依赖 | 独立 Research 目的地与离线默认 research 子命令 |
| 日行情与指数字段 | data/contracts.py 与 config/contracts；phase1/contracts.decode | Research adapter：保留真实源版本与单位；用户文件使用明确 schema，不伪造 provider envelope |
| 时间/身份 | data/availability.py、identity.py、provider_identity.py；phase1/domains 的时点语义 | 当次 universe 与可用时间验证；严格限制历史身份范围；不靠字符串后缀猜证券 |
| 来源与持久化 | warehouse_lock.py、raw_validation.py、来源 hash/原子发布方法 | 独立 store schema、run/input manifest、原子导入和快照；不调用旧库迁移 |
| 旧真实数据参考 | 旧 raw 181 manifests、真实日行情/因子/每日信息样本；RAW_ONLY 47回执 | 只读检查字段和有限历史观察；每份来源另验证用途；不是现成最新报告输入 |
| 计算/输出 | pandas、NumPy、DuckDB、PyArrow 已安装 | 连续窗口特征、Regime、可解释筛选、观察卡/报告；现有包目前全空 |
| PIT/复权参考 | domains.known_versions、adjusted_price、historical_snapshot | 只在输入身份/时间/因子证据满足时使用；不以 pipeline.build 绕过真实 facts 准入 |

Market Regime 的描述性向量至少包括趋势、上涨/下跌与均线宽度、成交活跃、波动和风格代理。
先展示指标、变化和数据限制，标签/权重/阈值进入版本参数并经验证；不擅设交易风险预算。
Screening 先使用可解释的流动性、相对强弱、趋势/波动与数据合格条件，返回明确排除原因。
成交单位需由契约从“手/千元/万元”等精确归一；缺失 ST/停牌不得默认正常可交易。

## 计划新增/扩展的文件

| 文件（计划） | 责任 |
|---|---|
| src/astock/research/store.py | Research schema、受管连接、原子导入、查询、run manifest |
| src/astock/research/inputs.py | 明确来源文件 adapter、时间/身份/单位/覆盖检查；后续采集与导入分开 |
| src/astock/features/market.py | 连续窗口、收益/波动/成交与相对强弱计算 |
| src/astock/regime/market.py | 市场描述性向量、缺项和覆盖；不暗含交易参数 |
| src/astock/screening/candidates.py | 可解释条件、候选/排除原因、证据字段 |
| src/astock/reports/research.py | 市场摘要、候选观察卡、反面风险、缺项和报告快照 |
| src/astock/cli/main.py（或其 Research 子模块） | 新离线 Research 入口；旧工具保留审计兼容后逐步退出 |
| tests/test_research_*.py | 真实形状合成输入、时间/单位/覆盖/缺失、事务/报告一致性 |

预计 CLI 先实现 import / market / screen / report；名称和参数在首批实现中落实。
当前不能运行 astock research report，README 没有把计划命令作为可运行命令展示。
无需增加新的框架、服务、券商 SDK 或同功能的第二套项目。

## 数据用途与容量

首批真实数据必须满足报告截止时间，迟到数据使用实际观察时间；历史下载不得因 trade_date
较早就回填 available_at。当前观察和历史 contemporaneous/backtest 明确分开。
原三库、RAW_ONLY catalog、实际响应、消费账本只读保留，不向旧 store 追加 Research schema。

当次获取优先按业务窗口，先测量试点行数/磁盘后扩展，容量纳入整体 50GB/100GB。
只存必要字段、连续窗口、增量 raw 和可重建派生结果；报告/真实研究卡及未来交易日志私有保存。

## 可复核验收

- 一次有合法来源的真实输入可通过完整链路生成市场摘要、候选清单和至少一张观察卡。
- 同一 raw/版本/参数重复运行输出一致；派生可从保留来源重建。
- 合成回归覆盖未来信息、断档、未知身份、重复/冲突、单位错误、零/缺失、停牌/ST、
  无交易日、不足窗口与覆盖偏差；网络在测试中关闭。
- 报告逐项关联输入/时间/参数，解释入选与排除、局部覆盖、数据陈旧和反面风险。
- 不产生订单、不改变用户风险预算；没有合格候选时允许空列表。
- 替换完成后迁移调用方、移除被替代业务代码；历史 decoder/证据按明确只读用途保留。

结论：可以立即开始上述离线业务实现。第一份“最新真实股票报告”仍需真实近期输入和这些模块，
不能将本轮方向重置宣称为 Research V1 已经运行完成。
