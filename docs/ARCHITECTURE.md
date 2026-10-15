# 架构与迁移边界

当前整体架构以[系统设计](SYSTEM_DESIGN.md)为准，实际能力以[当前状态](CURRENT_STATE.md)为准。本文保留已有来源读取、存储和迁移边界；下文日期对应历史基线及后续追加，不能将当时缺口当作今天未实现的能力。

2026-10-12。以 [宪章](PROJECT_CHARTER.md) 与当前用户授权为准。

## 业务主路径

~~~text
已授权真实来源 / 用户提供的真实文件
  → raw + 来源/时间/消费记录
  → Research Store（独立路径、用途与质量状态）
  → Market Regime / Industry & Theme / Screening
  → 公司与催化研究 / 候选观察报告
  → Strategy Setup / Entry + Exit / Portfolio Risk
  → 用户确认与手工交易
  → Trade Journal / Attribution / Backtest & Validation
~~~

Research V1 从当前观察研究开始，随后扩展持仓/退出、策略验证和日志。
Research Store、Features、Regime、Screening、报告及人工日志已在Research V1实现；
其余为目标架构，模块完成前不得宣称可运行。

## 已有资产与边界

| 层 | 现有实现 | 迁移方式 |
|---|---|---|
| 运行环境 | paths.py、settings.py、Typer、uv.lock | 保留；新入口沿用秘密类型、路径校验与离线默认 |
| 通用数据语义 | data/availability.py、identity.py、provider_identity.py、契约/单位 | 复用可验证语义；新用途不能扩大旧身份范围 |
| 持久性与保全 | warehouse_lock.py、raw/回执验证、事务、来源 hash | 新 store 继续锁前连接、不可变 raw、原子发布；旧库只读 |
| 旧有界演练 | probe*、slice*、admission*、reconstruction*、capture v1/v3 | 停用业务采集入口；保留历史审计/回归，按依赖逐步退出 |
| 统一 Phase1 | phase1/contracts.py、domains.py、pipeline.py、versions.py 等 | 用 adapter 复用解码/时点/来源校验；不把全历史审批链搬进新业务 |
| 历史来源兼容 | compat/phase1/{v1,v2-5672} | 被 versions.adapters() 实际调用；冻结字节，供旧来源读取，不作为新业务系统 |
| 业务层 | features/regime/screening/reports已实现观察路径；sectors/catalysts/backtest仍空 | 共用research.service，不维护平行筛选/报告框架 |

## Research Store 最小设计边界

已使用 ignored data/private/research-v1/，与旧原库和统一capture store隔离。
五表为research_meta、research_bundle、research_observation、research_report、research_journal；
观察按dataset储存证券、日历、行情、因子和显式状态；原字节/侧证据按hash在旁raw/留存。
导入先完整验证，再在受管连接内事务提交；分析从原字节重推导比对标准化观察。
快照记录代码/参数/来源/as-of/日志，报告生成路径只接受专用私有根。
尚无实时采集、公司研究、交易/组合schema；不为未实现能力提前建复杂框架。
每条数据记录原生证券/来源、事件日、retrieved_at、available_at、单位、raw hash 与用途。
当前上市名单是当次观察 universe；不用于冒充历史可交易证券全集。当前抓取的旧财务修订值
仅能作当前研究，未经 vintage 证据不能参与历史 PIT 回测。UNKNOWN/CONFLICT 不归零、不静默填充。

复用纯函数时仍验证契约/版本。pipeline.build() 会进入真实 fact 准入与来源授权逻辑，
不能直接拿它当一个普通 Parquet 导入器。新用途不通过改 license、复制 synthetic approval、
修改 source pins 或放松旧 guard 来实现。具体能力和迁出条件见 [代码清单](CODE_MIGRATION.md)。

## 替换与退出

先建立单一 Research 读接口，验证旧/新数据的身份、单位、时间、缺失与输出；迁移消费者后
删除旧业务生产入口、旧配置加载和重复实现。保留有真实来源绑定的只读 decoder 与必要历史回归，
直至所有留存来源均已用新 decoder 做独立等价读回，或确认只需封存恢复而无需在线读取。

删除条件是依赖扫描、迁移测试、来源/逻辑输出等价、故障行为和恢复验证；不是文件名带 Phase1。
旧库不被静默升级，冻结旧 approval/source bytes 不重新签名。每批在开发分支提交并可回滚，
真实私有数据的破坏性清理另经用户确认。

## 文档与隐私

主入口是宪章、CURRENT_STATE、ROADMAP、本文、RESEARCH_V1。历史工作流通过 HISTORY 导航，
旧状态不自动扩大/阻断新授权。代码仓库只保存源码、契约和脱敏摘要；真实行情、实际许可、
候选研究、持仓、成交和日志进入私有目录。Git 与数据备份分别管理。

Research V3在既有Raw→ResearchStore→Market Radar上增加`company/`离线层：
验证固定市场投影、行业归属→有限研究分配→来源/财务/催化目录→公司卡/简明摘要/条件化退出。
无新Store表、数据平台或订单路径；公司研究不改旧采集代码或来源事实，JSON目录与原始PDF分别公开/私有保留。
## Decision Loop V0

真实市场Store只读 → 有限公司证据版本/初始计划 → 指标检查与证据差异 → 四类研究状态
→ 专用小型私有Journal Store追加PLAN/REVIEW/EXIT → 私有组合与白名单中文摘要。
真实/模拟记录分目录，账户完整性/现金/时效不足保持UNKNOWN，不产生订单。
行情增量用LinkedResearchStore复用原compose链接来源，不复制旧窗口或建设新数据平台。
