# 当前Review：PR #4后采集熔断与公开隐私修复

用户明确授权：核对并普通merge已接受PR #4，集中修复P1/P2、官方文档只读核对、离线准备、测试、提交/新PR和精确HEAD CI。**新真实Tushare请求未获授权，本批为0**；不修改原106消费、删除私有数据、设定风险参数或交易。

## 基线与实际变更

PR #4固定head d5feb9f1420dc071b70137ab4768e2268f36891b 已由用户提供独立ACCEPT，1164 passed。
执行前核对：本地clean、head精确一致、PR open/mergeable、main仍为05479b5，精确head的push CI成功（run38378924067）。
按本次授权普通merge为main **80675e04ab4f645506d111b04dbb8bbfbc7df01f**，历史保留、无force push。
新修复分支 `codex/research-capture-safety`；累计diff：`git diff 80675e0..HEAD`。
本批最终审查SHA从新PR head取得，不把旧PR CI替代新HEAD CI。
[已接受V2交付记录](https://github.com/liuyanfeier/AStockSystem/blob/d5feb9f1420dc071b70137ab4768e2268f36891b/docs/REVIEW.md)保留。

- P1：HTTP401/403/429立即停；连续三次相同HTTP错误熔断；连续三次传输错误（允许连接/DNS/超时交替）熔断。成功响应重置计数；无自动重试。显式continue允许单次临时故障继续。
- 既有I/O、内部未知、发布、秘密、时钟、不可变对象、截断及行限立即停不降级；补足超2MiB的立即停。claim/FAILED/UNKNOWN保持不可变，安全日志只记数字HTTP状态或固定错误类别。
- P2：默认移除人工观察卡和整个Journal；来源字段使用明确白名单，自由来源描述/请求扩展不公开。public协议升至RESEARCH_PUBLIC_V2_1；不修改私有完整snapshot、Store或历史报告。
- 没有新增依赖、schema、平台、调度器或重试框架。Research Store与V2业务算法保持。
- [新业务投影与复现](research/results/2026-10-13-capture-safety/README.md)：真实10股全部市场/特征/radar及4候选一致；299闭合Mock完成。合成行业不冒充真实业务。

## 验证与审查入口

源码修复提交 **bbb302e7910bc14d8d01c5cf98a74387de9e8450**。针对性测试72 passed（41.39s）；第一次针对性运行中继续编辑源码导致code hash变化，两项缓存/旧报告复现测试失败；冻结源码后完整重跑上述72项通过，没有删除或跳过测试。
同一冻结源码完整本地回归 **1175 passed、1 warning、1307.20s**；warning为既有多线程fork弃用提示。最终HEAD全套以新PR对应的CI为准，PR描述固定精确SHA和实际CI链接/结果；旧SHA成功不能替代最终HEAD。
Doctor PASS、12 contracts PASS；默认capture dry-run market_requests=0。
新测试覆盖299计划持久401/403/429、500/503、连接/交替超时熔断、成功重置、body/disk cap，以及人工观察/私人来源/Journal的JSON+Markdown反例。
保全155655文件changed=0/missing=0；秘密违规0；15根容量32,736,449,871逻辑字节、33,761,505,280去重inode文件blocks，complete=true。
[完整验证摘要](research/results/2026-10-13-capture-safety/VALIDATION.md)记录口径与私有证据局限。
已接受的全部重要回归与安全检查保留；作者验证不是独立Review PASS。

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen pytest
uv run --offline --frozen astock doctor
uv run --offline --frozen astock data contracts
uv run --offline --frozen astock research capture --plan config/research/market-v2-proposal.json
# 最后一条是离线dry-run；未经批准不能添加--live。
git diff --stat 80675e0..HEAD
~~~

## 固定采集申请与未完成业务

[准确方案/合同验收点](RESEARCH_V2_ACQUISITION.md)：保留2026-04-01—2026-10-12、128交易日、299请求、2MiB单响应/598MiB预留/2GiB目的地；没有暗中增加10月13日。批准与执行时不能称此方案为当天最新窗口。
plan hash：`16e127efb7d920e9df8b5eb653bf52a6f2a261174f15b51900fb5ef6b1e87855`；
implementation hash：`d8e4b225e7e45ac0c77531ced03af8e3f4d826794e88eba1d1a0d18deaaed778`。
没有实际许可，目的地未创建；实际HUMAN许可须绑定上述hash、逐项成员、canonical目的地、有效期和continue策略。
官方index_classify输出src与输入src语义存在歧义；保留严格版本检查，实际不匹配不准入，列为首份真实响应验收点；未做接口权限探测。

真实全市场/31行业业务尚未验收。取得准确整批授权后直接采集、导入既有Store、生成中文日报/JSON及公开投影。
失败/UNKNOWN不重写；被消费成员的重新请求与扩大范围另需明确许可。下一业务为基本面/公告催化与候选退出计划，不重开全历史Phase1。
