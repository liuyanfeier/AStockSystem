# 本批验证摘要

源码与测试固定在 bbb302e7910bc14d8d01c5cf98a74387de9e8450；后续提交仅包含文档与新公开投影。
最终PR head的完整CI须单独核对，精确SHA、CI运行URL及实际结果保存在PR描述/checks；本地成功不替代CI。

| 核查 | 实际结果 |
|---|---|
| 针对性Mock/隐私/兼容 | 72 passed，41.39s |
| 完整离线回归 | 1175 passed、1 warning、1307.20s；既有多线程fork DeprecationWarning |
| Doctor / data contracts | PASS / 12 PASS，未探测行情权限 |
| 299 dry-run | 通过；原plan hash不变、market_requests=0 |
| 闭合299 Mock→Store→日报 | 299 COMPLETE；SYNTHETIC，不是现实全市场验收 |
| 旧真实10股业务复算 | 全部市场/特征/radar与4候选一致；原私有snapshot和Store SHA256不变 |
| 旧捕获账本只读核对 | 106=39 COMPLETE+66 FAILED+1 UNKNOWN；新真实目的地不存在 |
| 受保护数据SHA256核查 | 155655文件，changed=0、missing=0 |
| 秘密/公开路径检查 | 484个已跟踪/待提交文件，明文/编码/解码凭据违规0；新公开JSON/MD隐私反例通过 |
| 最终容量盘点 | 15个确认根，complete=true，错误0；仓库、外部历史工作目录、保留pytest与本批模拟目录均覆盖 |

容量：**32,736,449,871逻辑字节（32.74GB）**、33,761,505,280去重inode文件blocks；348,227文件、1,849数据库。
按文件stat盘点、全局hardlink去重；不解析APFS共享extent、不跟随symlink、不把估算作为可释放空间保证。
pytest保留根会随后续测试变化；这是本次回归结束后的时点，不是永久容量值。目标50GB、上限100GB不变，
本批没有执行私有破坏性清理，299方案新增2GiB预算不延续旧106许可。
完整日志、逐根容量和保护文件索引保留在ignored私有工程证据；公开摘要不是独立供应商真实性证明。

HTTP403/429/401反例：显式continue仍只消费1成员；持续500/503在3成员停止；连续连接/交替超时在3成员停止，
不会消费全部299。临时故障后成功重置计数、可继续；FAILED/UNKNOWN不重写，日志不包含原生异常或响应错误文本。
超2MiB、截断、行限、本地I/O/发布/未知内部/秘密保护保留。目的地预算超限在请求/claim之前拒绝。

公开投影RESEARCH_PUBLIC_V2_1使用明确来源字段白名单，默认不含人工观察、Journal、自由来源说明或请求扩展。
新真实/合成业务投影均保留单位、可知时间、来源hash、全部指标/有效分母、程序候选与计算方法；私有原报告未改。
旧Level B的PRIVATE_RAW_SHA256/PRIVATE_EVIDENCE_SHA256是脱敏hash别名，历史输出未发现个人绝对路径/实际日志内容，保留。
