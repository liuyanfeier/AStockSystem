# 当前Review：Research V2市场与行业雷达

用户授权本批普通软件开发、离线/既有真实来源只读研究、测试、PR/CI与一次完整采集方案；
新真实市场采集、破坏性私有删除、交易风险授权仍需明确批准。
用户另外明确要求真实业务报告入Git，覆盖旧“全部研究报告私有”规则；Raw/许可/个人账户仍不公开。

## 基线、验收与变更

已独立接受PR #3 head edcc8f55071abd77ae1e415773bc000aa815601a，核对相同head的CI成功（1121 passed）后，
按本次任务普通merge进入main 05479b523e3718d09e9b5b6b1773a3f318b1b0be。
本批codex/research-v2；累计diff：`git diff 05479b5..HEAD`，最终固定HEAD从本批PR head取得。
不改写历史，不自动合并本批PR；旧106尝试/源字节保持，本批真实新市场API0。

验收以可解释日报为主，要求来源、连续窗口、分母、板块/行业扩散、集中度与观察/退出准备。
**完整行业雷达软件可运行；真实全市场/行业未验收，因299请求尚未获授权。**

| 变更 | 实际实现/入口 | 重要边界 |
|---|---|---|
| Git业务交付 | [结果目录](research/results/2026-10-13-research-v2/README.md)、public_results白名单 | 已提交完整业务数值和观察卡；不以“都在本机”替代；个人日志不发布 |
| P2修复 | acquisition + local_failures回归 | I/O、未知内部/发布/完整性错误立即停；截断/满cap停；三次同类协议/提供者拒绝熔断；旧消费不reset |
| V2批量与当前池 | market_capture/market_inputs + versioned Tushare合同 | 三交易所真实源闭合；CNY/L/上市日/market，BSE显式参考日历；V1 dump/hash不变 |
| 市场/行业日报 | 同一service/features/screen，research/radar，`research radar` | 默认20/60不调参；有效分母、5板块、SW2021 L1等权/中位数；仅描述无仓位 |
| 增量/修订 | increment.compose、`radar --component --revisions` | 新bundle追加、旧报告保留；冲突显式source选择，完整日历复验；不同因子vintage披露 |
| 性能 | 一次代码/交易所分组，bounded Store expectation cache | 每次仍检查Raw hash/SQL；新as-of/代码/Store重新推导；非永久可信缓存 |
| 采集方案 | [固定299请求申请](RESEARCH_V2_ACQUISITION.md)、config/research/market-v2-proposal.json | 128日，598MiB响应预留、2GiB新增盘上限；真实新请求0 |

[设计/运行口径](RESEARCH_V2.md)，[最小迁移记录](CODE_MIGRATION.md#research-v2实际迁移2026-10-13)。
旧Level B完整Review见[此前edcc8f5的Git版本](https://github.com/liuyanfeier/AStockSystem/blob/edcc8f55071abd77ae1e415773bc000aa815601a/docs/REVIEW.md)，原私有报告/失败账本保留，不复制为巨大archive。

## 实际验证

本地完整功能版本bcb2d862334b24b26bc6c31a89f9ce76131d7df1：1160 passed、1 warning、1299.48s。
随后两项边界修复（协议熔断范围、公开JSON来源列表压缩）固定源码
03da51eb20f5986b622e9199d9353feb36753f17：全部Research155 passed、88.12s。
最终HEAD全套以对应CI检查为准；两次本地结果不冒充同一受测版本。
闭合299 Mock均COMPLETE；独立数值验证拆股、5/20/60、分母/新股/缺口、行业等权/集中度、
top-N全量分开、前日/as-of、source/池伪造拒绝、无文档分页拒绝、单日增量/更正与旧报告复现。
本批240项真实原指标一致，真实4候选保留，未虚构行业/调参。

早期新增测试曾将Pydantic封装后的ValueError误期望为ResearchError，已正常修正异常类型期待，
仍检查确切拒绝语义；没有跳过失败、删除重要测试或关闭安全验证。
完整回归期间补足单日增量计划，并在业务报告复核修正50%中性宽度不误判一致、行业缺样本不宣称扩散；
旧完整运行主动中断，不列为通过；修复后重跑全套成功。
最终扩展熔断后，原gzip测试预期“失败完39次”与新P2范围冲突，已更新为三次失败后停止，
保留压缩响应拒绝、无Raw/无准入与36未尝试断言；其余Research154项在修正前已通过。
最终全套/受测代码版本、保全/容量与CI以[验证摘要](research/results/2026-10-13-research-v2/VALIDATION.md)
和PR的精确head checks为准，pending不能冒充成功；作者结果不是独立Review PASS。

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen pytest
uv run --offline --frozen astock doctor
uv run --offline --frozen astock data contracts
uv run --offline --frozen astock research capture --plan config/research/market-v2-proposal.json
# 上条仅dry-run，无HTTP；--live不能在未批299范围时执行。
git diff --stat 05479b5..HEAD
~~~

## 下一批与恢复

先审查本批代码/报告/具体请求；若用户批准299请求，再固定干净版本执行、导入并输出真实市场/行业雷达。
不把合成行业成功称现实验收，不把LOCAL_CAPTURE_BOUND称独立供应商认证；reviewer若无私有Raw注明限制。
当前计划截止2026-10-12，超过时效需要更新一次明确整批明细再批准，不暗中顺延。
真正后续重点是公司基本面/公告、候选计划、退出与复盘；没有新全历史Phase1、删除私有源、改风险预算或订单。
