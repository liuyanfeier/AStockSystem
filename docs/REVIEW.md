# 当前Review：PR #5收尾与真实全市场首次采集

本轮直接用户消息提供GPT独立结论：固定27ed313a6b8506476c570b0c5e5d338066d9d3da的P1/P2软件ACCEPT，
固定299方案APPROVED，并明确允许匹配检查后真实采集。本轮消息及审批引文是授权审计来源，
私有记录保留；没有额外伪造人工/GPT签名或独立审批事实。首错停、消费不可变、无自动重试/扩围、
无私有删除、无风险授权/交易边界保持。

## PR #5收尾与累计diff

开始时Git干净、PR open/mergeable、head精确27ed313、main80675e0。旧push CI38390555073成功，
但PR CI38390643634失败；日志两次测试执行分别为CLAIM_BEFORE_ACTUAL_AUTHORIZATION和SIGSEGV。
原测试在已初始化DuckDB的多线程进程fork，还复用早于新授权的模拟时钟。
直接合并先被自动审批拒绝，因此沿用户授权的最小测试修复路径执行。

仅测试提交29c30b11e77f476cfad3ef3de4e9a19f3d36bbf2：独立Python解释器、基于当前时刻且不回退的mock时钟；
保留os._exit(73)、拒绝socket、重开后一条durable claim、零CALL_ENTERED/回执及原/下一成员均拒绝重发。
生产实现未改，重要回归与安全检查未跳过/删除。

- 针对性43 passed；独立复跑5轮各43 passed。
- 本地完整1175 passed、1 warning、1271.95s；Doctor、12 contracts PASS。
- [push CI38402228635](https://github.com/liuyanfeier/AStockSystem/actions/runs/38402228635)：1175 passed、5 warnings、2413.81s，精确checkout29c30b1。
- [PR CI38402232299](https://github.com/liuyanfeier/AStockSystem/actions/runs/38402232299)：1175 passed、5 warnings、2444.80s，合并29c30b1与80675e0。
- 两套后续诊断、12/v2九合同及离线计划检查均成功，随后[PR #5](https://github.com/liuyanfeier/AStockSystem/pull/5)
  普通merge为main8ab3a7c6e84a25d645e29085fd9757dbfabc12c4，无force push。

当前分支codex/research-market-v2-live，合并后仅状态/停采事实和未授权恢复提案变化。
Store、算法、参数、合同和生产采集未改；累计diff：git diff 27ed313..HEAD，新PR diff：git diff 8ab3a7c..HEAD。
最终固定HEAD及该HEAD CI由新PR描述记录，不能用29c30b1成功替代最终HEAD成功。
[上一批Review](https://github.com/liuyanfeier/AStockSystem/blob/27ed313a6b8506476c570b0c5e5d338066d9d3da/docs/REVIEW.md)保留。

## 实际授权、执行与业务结果

新main再次dry-run：299完整成员、干净Git、令牌存在、目的地未有历史消费；两个批准hash匹配。

- plan：16e127efb7d920e9df8b5eb653bf52a6f2a261174f15b51900fb5ef6b1e87855。
- implementation：d8e4b225e7e45ac0c77531ced03af8e3f4d826794e88eba1d1a0d18deaaed778。
- 2026-04-01—2026-10-12；CURRENT_OBSERVATION；SSE/SZSE/BSE上市A股、SW2021一级31行业、沪深300/中证500。
- 299请求/299最大尝试、单响应2MiB/总598MiB/目的地2GiB；固定001，无自动重试、购买权限、追加日期/诊断HTTP。
- 实际HUMAN许可绑定hash、逐成员、canonical目的地、有效期及continue_on_error=false。
  recorded_at和四小时有效期是本地记录与更窄操作约束，不伪称另一份用户签署时间。

**首个stock_basic(SSE,L)发生TRANSPORT_CONNECT_ERROR：1尝试、0 COMPLETE、0 FAILED、1 UNKNOWN、298未尝试。**
没有HTTP响应、Raw或可用回执；首错停、无重发。read_capture/capture_status核验计划/许可/claim/result链。
安全分类不能区分DNS/连接/TLS根因，不能据此认定权限不足、凭据无效或字段合同错误。
stock_basic/index_classify/index_member_all实际格式与权限未验收；严格版本/秘密/TLS/预算保护不放松。

[中文停采记录](research/results/2026-10-13-market-v2-first-attempt/REPORT.md)和
[白名单JSON](research/results/2026-10-13-market-v2-first-attempt/snapshot.json)已进Git。
新接收股票/行业/日期/价格记录0，真实总体分母UNKNOWN；MA20/60、市场与行业、筛选NOT_RUN，候选数量null。
未建Store/重建，无Raw可做跨市场股票数值抽查；旧10股/4候选保留，不替代全市场验收。
本交付是实际停采证据，真实全市场业务未通过；原许可、日志、个人信息保持私有。

## 保全、容量及剩余阻断

原106状态39 COMPLETE/66 FAILED/1 UNKNOWN保持，391相关文件hash无变化；
155655保护文件changed=0/missing=0。新001目录78,521字节，无Raw，UNKNOWN未恢复。
采集后16根盘点含仓库外历史工作目录、测试/模拟产物：33,622,439,763逻辑字节、34,619,711,488去重inode文件blocks，
340333文件/1961数据库，complete=true。APFS共享extent/目录blocks不可观测；pytest保留轮换造成时点差异，
没有手工私有删除。50GB目标/100GB上限保持。[完整验证与秘密检查](research/results/2026-10-13-market-v2-first-attempt/VALIDATION.md)。

实际阻断是连接失败，根因未确定。本次许可不变成试错/重发许可。
[恢复提案](../config/research/market-v2-recovery-proposal.json)固定同299成员/日期/预算，仅目的地改002，
明确包含1 UNKNOWN成员的新批次重新请求＋原298未尝试；001不清空，原106不改。
新plan hash：2006eb17e875ff65043d9fe6c6f919b33b05acb19426eaf71a3000ad7b20caf1；implementation仍d8e4b225…。
dry-run通过、0市场调用，execution_authorized=false；**新提案未授权**，需明确新批次及完整联网执行环境。
不新增诊断HTTP、权限购买或平台。取得来源后直接复用Store/radar/公开投影与数值抽查，随后进入基本面、
公告催化、候选计划与退出复盘。
