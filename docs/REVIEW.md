# 当前交付与 Review 入口：Research V1

2026-10-12。用户明确关闭重置/统一Review批次：独立审查基准
`a00c7dd544a331fe42c319a1c8ab9826027b988d`，其CI成功、1008 passed。
本批直接开发实际研究业务，不重启全历史Phase1或普通文档治理任务。
此入口随提交维护；Reviewer读取实际diff、相关依赖、测试与对应head的CI，
作者摘要不等于独立PASS。无法访问私有来源时应注明数据核验局限。

## 当前范围与业务结果

用户授权：独立简洁Research Store；真实行情/连续窗口/用途/来源；Regime、筛选与真实观察报告；
候选同步入场观察、反面证据、失效和不交易；私有持仓/日志最小能力；近期采集预算；
容量覆盖仓库外历史工作目录。允许连续commit、普通修复/测试；
未批准新市场API、私有破坏性删除或交易风险/订单。本批这些实际操作均为0。

已经从本机保留且只读核验的真实来源产生报告，而不是只交设计：

| 业务运行 | 实际结果与边界 |
|---|---|
| 输入 | 5股、2026-09-28至09-30连续3交易日；10文件来源bundle、身份/行情/因子/日历；不是最新120日行情 |
| 默认观察配置 | 20日收益/60日均线：筛选0、人工观察5；长窗口、12自然日陈旧与状态/基准/基本面缺口明确披露 |
| 三日探索配置 | 显式非默认短窗口：程序观察候选5；没有策略验证或交易资格，不冒充长期筛选 |
| 复现与恢复 | 同一输入/代码/参数/as-of/日志的快照与报告字节相同；新独立store从保留来源重建，结果相同 |
| 候选/退出准备 | 每卡入场观察、反面证据、逻辑失效、不交易和退出跟踪；risk_budget=null、trade_eligible=false |
| 持仓/日志 | 人工POSITION与PLAN/EXECUTION/EXIT/REVIEW追加、更正、截止时间过滤、复盘到期；未导入用户实际持仓，不推算券商账户 |
| 最新连续输入 | [48请求具体预算](RESEARCH_ACQUISITION.md) / [请求清单](../config/research/acquisition-proposal.json)可批准；当前execution_authorized=false，没有live命令 |
| 全项目容量 | 最终5个确认根含当前仓库、旧Codex工作和本批测试临时目录，约31.16GB文件blocks；未手工删除私有数据 |

实际参数、操作和schema见[RESEARCH_V1](RESEARCH_V1.md)，状态见[CURRENT_STATE](CURRENT_STATE.md)。
默认报告run：`d1f46b8a9e578902eb0bdc14c0af09212041da900ceba5800695f09df1631d82`；
三日探索run：`11dbc787ee494dec55fbaae0bd9580a0181b2b58c143661efb3d83eef3fc6f52`。
报告在本机reports/private/research-v1/，原字节/DB在data/private/research-v1/；
公开Git不含真实行情行、私密研究、账户、成交、许可或凭据。

## 版本与实际变更

基线：`a00c7dd544a331fe42c319a1c8ab9826027b988d`。
分支：[codex/research-v1](https://github.com/liuyanfeier/AStockSystem/tree/codex/research-v1)。
业务实现提交：`aad5f52a48c0a2d62d268dc7b4b1066d710b9ccb`；随后提交同步操作/预算/验证。
最终审查对象取PR当前head或`git rev-parse HEAD`，审查开始记录固定SHA。
本分支基于已审查重置分支；main未自动合并。审查本批请比较以下明确范围：

~~~bash
 git rev-parse HEAD
 git log --oneline a00c7dd544a331fe42c319a1c8ab9826027b988d..HEAD
 git diff --stat a00c7dd544a331fe42c319a1c8ab9826027b988d...HEAD
 git diff a00c7dd544a331fe42c319a1c8ab9826027b988d...HEAD
~~~

核心路径：research/inputs、store、legacy、service、journal；features/market、regime/market、
screening/candidates、reports/research和cli/research。共用一个分析路径、5表store，无新依赖/服务。
复用warehouse_connection/lock、RecordTimes、严格JSON/hash、raw侧证据和冻结物理来源校验；
未使用旧pipeline.build，没有旧store schema或真实消费状态改写。
旧重要回归完整保留；CLI允许菜单测试随实际新增research入口扩展，并保持doctor/秘密断言。
[迁移记录](CODE_MIGRATION.md)说明原占位包落实，无被替代业务路径遗留。
容量工具增加显式外部根、跨根inode去重、缺失/权限错误及符号链接计数。

## 验证与 reviewer 重点

聚焦合成回归37 passed（Research、容量、CLI）。业务源码aad5f52对应完整离线回归
**1032 passed，1个既有fork弃用警告，1239.28秒**；未skip重要回归或关闭网络禁止。
公开CI以[分支运行](https://github.com/liuyanfeier/AStockSystem/actions?query=branch%3Acodex%2Fresearch-v1)
或PR checks核对准确head、状态和日志；未完成不等于通过，旧a00c7dd成功不能冒充新HEAD成功。

1. 原子事务及中途失败不能部分导入；旧库拒绝迁移，锁先于连接。
2. 精确原生身份、真实捕获/可知时间、自然日日历、单位与公司行为因子；
   中间断档/末日缺失不能跨越；未知ST/停牌/限价不能成为交易资格。
3. 原字节/证据保留；从原字节重推导比对DB，来源/事实/输出篡改失败；报告可重复且仅私有输出。
4. 池内宽度的有效分母、同日期基准、短窗口和陈旧数据；筛选排除与空列表，不能虚构全市场/催化。
5. 人工日志追加/更正/知识时间，已有逻辑/退出条件和复盘提醒；未推算持仓或自动交易。
6. 新预算仅提案；不重放已消费失败/未知，不因软件通过扩大授权；外部历史/临时容量不遗漏。

doctor、v1/v2 contracts、identity/slice specs、统一23契约离线校验通过。
作者本机自检：原155,655数据文件全hash不变；4个主要原DB同hash且无WAL。
旧171源码基线中169项同字节；主CLI和菜单测试2项因新增业务入口按本批授权修改，
原版本仍在a00c7dd及旧Git历史，未改旧pin清单或历史审查事实。
23个实际运行pin及V1/V2冻结来源archive保持不变；没有把旧阶段根源码冻结扩大为新开发禁令。
私有核验结果保留data/private/repository-governance/2026-10-12/，公开只含脱敏计数与方法；
没有私有访问权限时不能把这些摘要写为独立数据验收。实际真实报告也不需要用户每批额外打包转交。

## 缺口与下一批

最新连续120日及基准真实报告尚待预算批准/新输入；当前真实运行是历史三日样本，
完整Market Regime、公司/催化、策略有效性、正式退出/组合风控及回测未完成。
下一批优先补当次近期数据、验证默认配置候选，并核实候选公司与持仓退出逻辑。
不把未知填零、不按成本价擅设止损/仓位、不为此重建庞大历史审批框架。
源码和文档可按commit回滚；私有store/raw/报告与日志需整组备份，Git不能替代私有数据恢复。
