# 本批验证记录

基线为普通合并已接受PR #8后的main `0159d72b67b111b5d21a81624bbbb363c231baa7`。
本批直接用户任务为Decision Loop V0；无新市场API/破坏性私有删除/交易风险授权。

- 33项决策/组合/增量/实验反例通过；与原公司研究及增量组合共57项通过。
- 真实V2 Store/来源只读复算，原706095条日行情保留；三个公司合成两日增量各130连续日。
- 保留披露重查、模拟新信息、模拟人工动作与复盘已执行；真实持仓UNKNOWN，模拟持仓不计算伪账户权重。
- 实际`research decision-close`离线命令成功；生成[中文报告](close-command/DECISION.md)。
- 同一期原指标、原假设与源Hash保留；新增财务/公告差异、不可比/未知/未来信息、来源绑定人工确认和隐私反例通过。
- 合成Breakout实验包含费用/滑点和亏损结果，不调整参数求漂亮结果，不声称策略有效。
- Doctor及原12合同通过；完整回归的受测SHA/结果和最终HEAD CI会在PR验证记录中明确，pending不当成功。

普通开发中出现两项局部错误：纸面实验日志中的Decimal不能JSON序列化，以及隐私反例缺省人工来源字段。
修复为明确序列化和缺来源时按私有处理；未跳过失败测试或放松保护。
开发期自身生成的报告草稿保存在新私有draft目录；未改已接受V2/V3或用户真实记录。

[代码/输入/输出Hash](REPRODUCTION.json)、[本批使用源保全](PRESERVATION.json)、
[离线增量](INCREMENT_REHEARSAL.json)、[未授权清单](ACQUISITION_PROPOSAL.json)随Git提交。
外部Reviewer没有私有Raw/PDF时不能据这些摘要宣称供应商真实性独立通过。
完整当前Review见[REVIEW](../../../REVIEW.md)；最终固定版本从PR HEAD取得，不使用旧CI冒充。

运行实现87b3bc471a1f82ee04357d5563030c4b94c5756f本地完整回归：1234 passed、1 warning，1319.02秒。
之后自查补同计划观察结束/未决状态跨日延续及禁止重写初始计划，57项相关反例通过；最终HEAD完整CI另核验。
未把前一SHA的全量结果冒充后续SHA的本地全量结果。
