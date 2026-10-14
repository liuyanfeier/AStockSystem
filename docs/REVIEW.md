# 当前Review：PR #6合并、网络恢复与002最终离线准备

当前用户授权普通合并已接受PR #6、无Token/无业务HTTP的DNS/TCP/TLS诊断和必要工程修复，
**明确未授权002整批真实API**。默认策略调整为有限失败继续、系统性故障熔断，不重发已消费成员。
没有制造新的人工/GPT审批事实。

PR #6固定8a3a90ba3633f9193e78844a7d7b341166bfaa83、push/PR CI均success、无冲突、开始Git干净；
普通merge进入main7961e02e091e7ab91e3fdf034ba7da0f9d2c48cb。
本批分支codex/research-network-recovery；基线7961e02；实际diff仅网络证据、当前状态和采集准备说明。
生产代码、依赖、计划、Store、算法及风险参数均未改。固定最终HEAD及其检查从Git提交/CI读取，
不以旧SHA的成功冒充新HEAD成功。

[完整脱敏诊断、复核方法与002清单](research/results/2026-10-14-network-recovery/VALIDATION.md)已提交Git。
同机同用户同Python对照：默认受限进程DNS成功、TCP errno9；正常网络权限进程DNS/TCP/TLS成功；
同版本HTTPX/httpcore与certifi、trust_env=False、verify=True也通过直连TLS。
当前环境/系统代理未启用，未修改VPN/代理/防火墙/证书；无需生产代码或代理改造。
未来已获准采集使用正常网络权限进程。此证据定位当前可复现执行障碍；001原始安全分类不足以证明当时唯一根因。

本批真实市场API/业务HTTP均0，002尚未创建/授权；供应商权限与字段格式未验收。
原106相关391文件hash无变化；001仍1 UNKNOWN、298未尝试、0 Raw/回执，原claim/result保全。
原[首次停采记录](research/results/2026-10-13-market-v2-first-attempt/REPORT.md)不改写。
此前完整业务/CI/容量及保全记录见[上一批Review](https://github.com/liuyanfeier/AStockSystem/blob/8a3a90ba3633f9193e78844a7d7b341166bfaa83/docs/REVIEW.md)。

离线dry-run完整299成员、002目的地未用、与001仅目的地不同：
plan hash `2006eb17e875ff65043d9fe6c6f919b33b05acb19426eaf71a3000ad7b20caf1`；
implementation hash `d8e4b225e7e45ac0c77531ced03af8e3f4d826794e88eba1d1a0d18deaaed778`。
2026-04-01—2026-10-12、三市场/31行业/两指数、299次最大尝试、2MiB/598MiB/2GiB；
目的地data/private/research-v1/market-v2-20261013-002。
包含1个已UNKNOWN成员的一次明确新批次请求＋原298未尝试，旧001绝不reset。
实际许可应显式continue_on_error=true；每成员一次，传输连续3次熔断，401/403/429立即停，
相同HTTP/协议连续3次熔断，I/O/秘密/时钟/截断/行限/预算等立即停，自动重试0。

针对性Mock回归42 passed（11.59s），Doctor与12合同PASS；完整1175是已审查8a3CI结果，
本批文档变更没有重跑完整本地套件。全部Hash不变，下一步只需用户明确批准准确002范围与继续策略，
实际HTTP前重新核查干净版本、许可、未消费目录与时效。取得真实来源后直接运行既有Market Radar，
补齐跨市场/行业数值抽查与公开真实业务报告；不新增数据平台，不以网络成功宣称业务通过。
