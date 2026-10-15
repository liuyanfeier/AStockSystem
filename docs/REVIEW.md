# 当前交付与验证：M0清理收尾、M1日常任务首段

当前分支`codex/daily-workflow-foundation`，整体实施基线`83a9c8819baa2c8986c74116ddd0c4aff8cd140a`。
[整体方案](SYSTEM_DESIGN.md)、[当前状态](CURRENT_STATE.md)、[日常使用](DAILY_WORKFLOW.md)、[研究合同](STRATEGY_RESEARCH_V1.md)。

用户已批准按整体目标自主继续普通实现、修复、验证及向`liuyanfeier/AStockSystem`本分支推送，GPT仅由用户按需介入。本文件是证据入口，不是新增人工Gate。最新批准包含精确旧合成测试清单的实际清理；不扩展新市场API、其他私有破坏性清理、真钱参数或交易。

## 变更与验收结果

原daily仍依赖CLI编排及公开行情JSON，人工记录需要手写JSON。本批提取原生`run_close`，daily与旧decision-close共用；市场分析明确排除私人Journal，返回MarketSnapshot V1。来源向量共享纯函数，原数值和谱系继续复现。

中文`research record`可录入已阅/备注、持仓快照和实际已发生成交。回执、成交/持仓与范围声明在同一事务内追加；幂等请求、预览Hash、模式、时间和更正链校验保护旧记录。部分卖出200→100只在用户明确补录剩余100时更新；未提供则保留原股数及待核对。已阅不解除风险，现金/完整性不继承，晚录不回填过去报告。私有报告持仓区显示已报股数，公开白名单排除私人回执与组合。

报告JSON绑定渲染源码Hash后寻址，格式变化生成新文件对，旧JSON/Markdown不覆盖；故障修复/格式迭代不再与旧同内容报告冲突，回归验证旧字节保留和同版本幂等。合成财务数字在报告内明确称为合成夹具，避免固定措辞冒充真实披露。

旧基线绑定旧执行Hash，代码演进后不能把整份Hash不等直接当业务数据失真。迁移现在要求原Store内精确旧快照锚点及公开旧Hash一致，再比较全部重新计算的公开业务字段；仅代码Hash/原私有快照Hash作为旧与新执行元数据分别保留。篡改数值/来源/参数/缺口或缺失旧锚点仍拒绝，原Store不写入。

独立工作Journal继续五表容器，新增类型化INPUT/ACCOUNT事件，无新依赖、源库升级或另一条行情实现。PositionScope唯一实现移至portfolio并保留旧导入兼容；旧CLI重复编排已移除。更完整业务schema、通用计划操作与三策略PAPER尚待后续实现。

## 实际受测版本和CI

|版本|已验证结果|局限|
|---|---|---|
|M0运行实现`3ddd5172a2190e3f53ccb6306411169218f7ac85`|本地全套1264通过、失败/跳过0，1436.61秒，1项macOS fork警告；来源指纹一致|这是M0，不能覆盖本批M1|
|M0文档提交`ba240a404f0e9b8b9b04bb767d599c71495c9ee3`|[远端完整CI成功](https://github.com/liuyanfeier/AStockSystem/actions/runs/38688022367)，checkout为该SHA|M1尚未包含|
|M1主实现`74a16b954bec3f353d6c6d451614f0b5d7d169bf`|本地扩展270项通过，125.39秒；前后综合源码指纹一致|包括完整原生合成来源闭环；不是盈利验证|
|持仓区股数/合成措辞/渲染版本修复`1e43cb652a9f52898d62141568231a0d84bb4000`|提交SHA上97项相关回归通过，指纹一致|[该SHA完整CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38695943659)当前仍执行中，尚无本批全套PASS结论|

后续证据/文档提交不在正文自引用最终HEAD。审查时从分支`git rev-parse HEAD`读取最终版本，再核对[该分支CI](https://github.com/liuyanfeier/AStockSystem/actions?query=branch%3Acodex%2Fdaily-workflow-foundation)的实际checkout和结果。前一个SHA成功不能冒充最后HEAD通过。这里是作者实际diff自查与验证，不冒充独立审计。

```bash
.venv/bin/python scripts/managed_pytest.py tests/test_research*.py \
  tests/test_manual_workflow.py tests/test_native_market_context.py \
  tests/test_daily_profile.py tests/test_decision_loop.py tests/test_decision_increment.py \
  tests/test_decision_paper.py tests/test_cli.py tests/test_company_research.py \
  --expected-peak-bytes 300000000
.venv/bin/astock doctor
.venv/bin/astock data contracts
.venv/bin/astock data contracts --catalog v2
.venv/bin/astock research daily --profile config/daily/retained-evidence.json --check
.venv/bin/astock research daily --profile config/daily/retained-evidence.json
```

测试使用合成数据且禁止网络。完整闭环用例没有替换market_context/company核验，实际执行Source Store导入、基线锚点、数值计算、事务与报告；只注入合成时钟。最初新夹具少两天闭市日历被拒绝，补完整夹具后通过；原失败日志与工作目录保留，没有跳过保护。Doctor及原12/v2九合同PASS。

[机器验证、完整合成样例与真实脱敏重查](research/results/2026-10-15-daily-workflow/README.md)包含参数、as-of、代码与来源Hash、日志/JUnit Hash及局限。真实重查仍截至10月12日行情、10月14日观察；原行情库及31份PDF SHA256不变，真实持仓UNKNOWN，无新公告/行情、市场HTTP和订单均0。

## 获准清理、容量与恢复边界

用户批准清单SHA256 `78c785ec7b751d79af91d78fae9e96019f12db7c428ec488d38ab216c68b93fb`后，重验逐文件元数据、根inode、进程和保护引用，完成1626旧合成子目录删除及707别名unlink。实际普通文件长度11,078,189,085字节；382保护目录、失败缓存原字节、原行情库与31PDF不变；父根不删、别名不跟随。公开[执行回执](research/results/2026-10-15-storage-lifecycle/CLEANUP_RECEIPT.json)绑定私有执行日志Hash，原待批准记录保留为历史。

13:45:56—13:46:25的17根清理后快照36.740GB逻辑长度、37.800GB去重inode文件blocks，complete=true、错误0；包括5.921GB受管完整回归产物。M1后续测试与报告另有小量增量，受管占用随机器验证登记；当前本地不再重复整套约6GB回归，远端执行完整CI。50GB目标、100GB上限不变；逻辑移除不是APFS物理释放测量。

M1末尾15:03:18—15:03:49同17根复测为37,382,244,316逻辑字节、38,539,157,504去重inode文件blocks，complete=true、错误0；已包含本轮追加测试与报告。[容量回执](research/results/2026-10-15-daily-workflow/CAPACITY.json)绑定私有逐根清单Hash，之后小量证据/文档/Git另有增量。

代码可按提交回滚；私有Journal已追加新类型事件时应保留当前读取器或先隔离工作副本，不能用Git回滚当作数据恢复。合成目录可按锁文件/生成器重建语义，不保证历史随机ID/数据库同字节。原真实来源、消费/FAILED/UNKNOWN及个人事实不得通过reset/retry恢复；本次批准不扩展其他历史目录清理。

## 后续与保全

M1继续通用计划录入、低噪声待办与失败恢复；M2按首轮研究合同实现回踩/突破/简单趋势及统一PAPER。真实日更仍需重新绑定最终实现Hash、准确成员/时间窗/预算/新目的地的授权；旧49请求提案未执行，也不自动随日期扩大。没有用户真实账户或风险参数时继续观察/模拟，不声称真实使用验收。

用户已有六个文件删除和五份未跟踪蓝图保留，不混入本批提交。历史[Decision Loop Review](https://github.com/liuyanfeier/AStockSystem/blob/8fb35e9eeb69e5d63c30ac07969d45ec90976277/docs/REVIEW.md)、[M0 Review](https://github.com/liuyanfeier/AStockSystem/blob/ba240a404f0e9b8b9b04bb767d599c71495c9ee3/docs/REVIEW.md)及[交接](handoffs/2026-10-15-project-and-decision-loop-handoff.md)保留对应当时事实。
