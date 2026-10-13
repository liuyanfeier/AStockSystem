# Research V2 验证摘要

## 固定受测版本

- 基线main：05479b523e3718d09e9b5b6b1773a3f318b1b0be（普通merge PR #3，原1121回归保留）。
- 本机全套：bcb2d862334b24b26bc6c31a89f9ce76131d7df1，**1160 passed、1 warning、1299.48s**。
  唯一warning是macOS多线程fork弃用提示；没有测试跳过。
- 后续协议熔断范围与公开来源列表压缩：源码03da51eb20f5986b622e9199d9353feb36753f17，
  **全部Research155 passed、88.12s**。这不是最终HEAD的本地全套结果。
- 最终文档/报告提交不再改变上述源码；最终固定HEAD及**该HEAD的完整CI结果**从本批PR head/checks读取。
  实际CI链接与结果也写入PR正文；不能用bcb本地通过冒充03da/最终HEAD全套通过。
- doctor PASS、12 dataset contracts PASS（均离线）；299请求capture dry-run：真实HTTP0。
- 新43项回归不替代旧1121项；最终HEAD CI运行全部。旧gzip测试更新为三次协议拒绝后熔断，
  保留拒绝压缩、无Raw/无准入、36未尝试断言，并有新故障注入测试。
  早期正常修复/主动中断记录不计通过，没有关闭安全验证或删除重要回归。

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen pytest
uv run --offline --frozen pytest tests/test_research*.py
uv run --offline --frozen astock doctor
uv run --offline --frozen astock data contracts
uv run --offline --frozen astock research capture --plan config/research/market-v2-proposal.json
git diff 05479b5..HEAD
~~~

## 实际业务与独立数值

既有真实10股/2指数/128日截至2026-10-12，不请求新数据、不写原Store：
**240项旧指标逐值一致，4候选保持**。原Level B250项Raw直接算术/覆盖检查作者结果也已脱敏入Git。
当前真实行业数据没有采集，缺分类10只、行业轮动UNKNOWN；来源是本地无签名采集链，
缺私有Raw访问的GPT可以审查业务计算/输出/代码，不能独立据摘要认证供应商。

299成员闭合Mock全部COMPLETE、真实市场HTTP0；拆股因子、五板块、新上市、缺价格/因子、
行业等权/中位数、有效分母、集中度、共同成员前日变化有独立确定期望。
行业合成报告中的结论始终SYNTHETIC。当前池/成员不能充当历史PIT，
空ST/停复牌不证明正常，缺策略/可成交性/财务公告核实/批准风险预算，候选trade_eligible=false。

公开features来源以source_hash_set_id引用source_hash_sets，可还原完整hash集合；候选卡保留直接hash。
6000股/260个共同来源的序列化回归<10MiB，完整业务指标保留；不修改私有输入或公开个人日志。

## 性能

[优化前](performance-before.json)100/500股特征约0.082/1.482秒；
[100股初测](performance-store-before.json)与[1000股Store/6000股特征实测](performance-after.json)口径分别披露。
分组后6000股×128日特征约1.168秒；1000股Store258,473行，导入39.16秒，
冷验证4.805秒、同对象重复验证0.715秒，含缓存后的雷达1.626秒，目的地90,238,499字节。
性能测量固定4ce99a8源码/对应code hash；后续描述标签/公开压缩/协议停止修改不是重新性能实测。
不是6000股全Store实测，不是实际API性能；256MiB编码预期缓存上限超过时回到冷推导。
每次仍核验Raw hash/SQL；新代码/as-of/对象重新推导，缓存不能授予来源等级。

## 保全、秘密与容量

保留基线155,655个保护文件，**字节/大小changed0、missing0**。
旧106次真实消费/失败/UNKNOWN和历史来源未重写、未重放；本批私有破坏性删除0、旧库写0、订单0。
提交候选478文件完成实际token明文/编码/解码检查，violations0；公开JSON私有路径/个人标记0。
完整私有日志/许可/Raw不提交，公开仅业务/方法/边界。

本批实盘盘点**14个确认根**，含仓库外历史工作目录、实际保留pytest根、
所有本批合成演练/性能目录。**complete=true，读取错误0**。合计361,446文件、1,914数据库，
逻辑字节**32,860,999,001**（32.86GB），
去重inode文件blocks **33,927,413,760**（33.93GB）。
文件blocks不含目录/APFS共享extent，因此不承诺等量删除可释放空间；符号链接不跟随。
50GB目标/100GB上限不变；14根不是对未知外部备份的完整性保证。
这是测试/投影完成时点，不把之后小量Git提交/文档字节说成已计入。
pytest自动轮转临时目录，人工未清空历史私有目录。

| 确认根（脱敏标签） | 文件 | 数据库 | 逻辑字节 | 文件blocks字节（每根） |
|---|---:|---:|---:|---:|
| astock-v2-after-001 | 1,777 | 1 | 88,734,330 | 94,117,888 |
| astock-v2-after-final-001 | 1,777 | 1 | 90,316,182 | 95,703,040 |
| astock-v2-before-001 | 2 | 0 | 77,678 | 81,920 |
| astock-v2-before-002 | 1,777 | 1 | 12,728,156 | 18,026,496 |
| astock-v2-published-demo-001 | 1,777 | 1 | 4,347,402 | 10,649,600 |
| astock-v2-published-demo-002 | 1,777 | 1 | 4,347,402 | 10,649,600 |
| astock-v2-published-demo-compacted | 1,777 | 1 | 4,356,390 | 10,657,792 |
| astock-v2-published-demo-final | 1,777 | 1 | 4,350,398 | 10,653,696 |
| 当前仓库（含私有数据） | 176,466 | 203 | 18,926,623,960 | 19,489,726,464 |
| 仓库外历史Codex工作目录 | 76,901 | 787 | 8,204,401,835 | 8,402,071,552 |
| pytest-206 | 4,927 | 330 | 1,815,625,130 | 1,827,643,392 |
| pytest-236 | 66,301 | 513 | 3,440,409,882 | 3,616,198,656 |
| pytest-237 | 12,205 | 37 | 132,602,272 | 171,732,992 |
| pytest-238 | 12,205 | 37 | 132,077,984 | 171,208,704 |

私有完整证据：data/private/repository-governance/2026-10-13/research-v2/；
容量capacity-final.json，受测日志、security.json、preservation.json同目录（保全文件名astock-v2-preservation.json）。
本批没有靠删除实际数据换容量；[新299请求](../../../RESEARCH_V2_ACQUISITION.md)598MiB响应预留、
2GiB新增磁盘上限未授权，不继承旧试错许可。
