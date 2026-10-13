# 可直接通过Git审查的业务结果

用户明确要求真实业务报告随代码进入Git。本目录不存Raw、数据库、实际许可或个人账户记录。
来源hash/本地证据等级可定位私有数据；缺Raw访问权时不能仅据公开摘要独立认证供应商。

| 结果 | 数据性质 | 可以核查什么 | 不能据此声称什么 |
|---|---|---|---|
| [既有真实有限样本雷达](actual-limited/b05c9b012b88d5fda9fe69506e6709c42d2a51998c92e74557e7a6619d2de326.md) · [JSON](actual-limited/b05c9b012b88d5fda9fe69506e6709c42d2a51998c92e74557e7a6619d2de326.json) | LOCAL_CAPTURE_BOUND，10股/2指数，128日截至2026-10-12 | 5/20日、MA20/60、板块/分母、4候选与全部观察条件；240项原指标一致 | 不是全市场；没有真实行业来源，不虚构银行/地产行业统计 |
| [行业雷达软件样例](synthetic/fcf28a97072a2b0fba89e001eeb6a00517aa42ee66994af4310e2878796b2f32.md) · [JSON](synthetic/fcf28a97072a2b0fba89e001eeb6a00517aa42ee66994af4310e2878796b2f32.json) | SYNTHETIC，闭合299请求/10股/31分类 | 五板块、拆股因子、新股/缺行情/缺因子、等权行业、候选集中度、前日变化 | 合成价格和行业不是真实市场结论或授权 |
| [Level B完整真实业务报告](../2026-10-13-level-b/REPORT.md) · [独立算术核查](../2026-10-13-level-b/QUALITY.md) | 上一轮真实交付的脱敏投影 | 原4候选、10股2指数逐证券指标、250项Raw算术/覆盖检查作者结果 | 没有私有Raw访问时无法独立重做提供者链；不是策略有效证明 |
| [优化前特征实测](performance-before.json) · [100股Store初测](performance-store-before.json) · [1000股Store/6000股特征测量](performance-after.json) | 确定性合成性能实测，当前功能代码 | 不同口径的实际耗时/行数/磁盘；同对象缓存与冷验证分开 | 不把6000股特征耗时说成6000股完整Store实测或真实API耗时 |

公开JSON的features通过source_hash_set_id引用source_hash_sets，完整来源hash可还原；
观察卡保留直接hash列表，私有输入不变。6000股输出大小回归防止来源列表重复膨胀。

所有观察卡risk_budget=null、trade_eligible=false，不代表用户实际持仓。
前日指标用当前可知来源复算，同一当前池/行业队列；不是历史PIT。
报告复现：相同保留bundle、代码/配置、as-of重算，输出确定。重建到不同本机路径会改变
manifest/私有证据hash和报告ID；对应业务数值仍应一致，不能伪称跨路径ID天然相同。

~~~bash
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen python scripts/research_v2_demo.py --work /private/tmp/独立新目录
uv run --offline --frozen python scripts/benchmark_research_v2.py \
  --output /private/tmp/性能结果.json --store-stocks 1000 --work /private/tmp/独立性能目录
uv run --offline --frozen pytest tests/test_research_v2.py tests/test_research_increment.py \
  tests/test_research_capture_local_failures.py
~~~

下一实际业务步骤：[固定299请求申请](../../../RESEARCH_V2_ACQUISITION.md)。
本批实际新市场API0，已有真实数据只读研究，完整行业现实结论等采集后验收。
