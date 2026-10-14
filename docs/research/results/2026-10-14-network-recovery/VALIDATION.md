# 2026-10-14 网络恢复与002离线准备

本批仅合并、网络诊断和离线核对。真实市场API请求 **0**，业务HTTP请求 **0**；
未读取Token进行连接测试，未发送任何Tushare请求体，未创建002采集目录或许可。

## 合并与诊断事实

PR #6仍为8a3a90ba3633f9193e78844a7d7b341166bfaa83、open/mergeable；
[push CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38410281563)与
[PR CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/38410502162)均success，
独立审查记录1175 passed、5 warnings。干净Git后普通merge为
7961e02e091e7ab91e3fdf034ba7da0f9d2c48cb；没有force push。

2026-10-14 02:05—02:07 UTC，在采集器同机、同用户、同一个项目Python3.12环境进行对照：

| 上下文 | DNS | TCP443 | TLS与证书 | 业务HTTP |
|---|---|---|---|---:|
| 默认受限执行进程 | 成功，2地址 | OSError / errno9 | 未进入 | 0 |
| 正常网络权限进程 | 成功，2地址 | 成功 | TLSv1.2、默认CA验证成功 | 0 |
| 正常权限，同版本HTTPX/httpcore连接栈 | 隐式解析成功 | 成功 | HTTPX certifi CA、CERT_REQUIRED、hostname校验成功，TLSv1.2 | 0 |

HTTP(S)_PROXY/ALL_PROXY大小写环境变量均不存在，NO_PROXY未设；macOS HTTP/HTTPS/SOCKS/PAC启用标志均0。
默认路由接口未呈现utun/tun/ppp特征，应用防火墙mode1；没有改变代理、VPN、路由、防火墙或证书配置。
直连成功说明当前正常进程出站通路可用，不代表所有企业网络策略或VPN状态都已穷尽排查。

**已复现受限执行上下文的TCP失败；解除该执行限制后，同配置直连与证书校验成功。**
恢复措施是在具有正常网络权限的进程执行未来已授权采集，保持trust_env=False、verify=True与固定HTTPS端点。
无需新增代理或修改生产代码。001只保留安全分类TRANSPORT_CONNECT_ERROR，未保留原生异常，
因此对照定位了当前可复现障碍，不能声称已从旧日志证明当时唯一根因。
TLS可达不等于Tushare业务权限/响应格式通过；这些仍需首次获准真实响应确认。

复核方法（不产生HTTP）：默认与正常网络权限各用同一解释器执行
socket.getaddrinfo('api.tushare.pro',443)及socket.create_connection(...,timeout=8)，
随后ssl.create_default_context().wrap_socket(...,server_hostname='api.tushare.pro')。
另用同版本httpcore.SyncBackend().connect_tcp(...,timeout=8)，
start_tls使用HTTPX verify=True/trust_env=False生成的certifi上下文；关闭连接，**不调用write/send或HTTP客户端请求**。
系统代理/路由仅保留启用、loopback和接口类别摘要，不发布代理URL、凭据、网关或私有主机信息。
私有诊断原始摘要、时间和离线清单保留；公开内容为上述脱敏投影。

## 最终002范围（仍待用户明确授权）

机器计划：[market-v2-recovery-proposal.json](../../../../config/research/market-v2-recovery-proposal.json)。
parse_plan/capture dry-run已复核全部299成员；与001解析后的计划仅destination不同。

- plan hash：2006eb17e875ff65043d9fe6c6f919b33b05acb19426eaf71a3000ad7b20caf1。
- implementation hash：d8e4b225e7e45ac0c77531ced03af8e3f4d826794e88eba1d1a0d18deaaed778。
- 日期2026-04-01—2026-10-12，128计划交易日；当前上市SSE/SZSE/BSE A股，SW2021一级31行业、沪深300/中证500。
- 299请求/299最大尝试；含001 SSE UNKNOWN成员的一次**明确新批次重新请求**与原298未尝试；001不重发/重置。
- 单响应2MiB、总响应598MiB、新增磁盘2GiB；目的地data/private/research-v1/market-v2-20261013-002，尚不存在。
- 批准后许可显式continue_on_error=true；单次一般传输失败留痕并继续其他未尝试成员，连续3次传输错误停。
  HTTP401/403/429立即停；连续3次相同HTTP或协议/提供者错误停；I/O、未知内部异常、秘密、发布、
  时钟、截断、行限、响应与磁盘预算异常立即停。每成员一次，不自动重试/重定向/加成员/购权限。
- 固定窗口不自动延长；10月14日核对时截止日尚在7自然日时效内，若实际批准/执行时超出用途时效先明确更新范围。

本轮工程/诊断授权不等于002执行授权。批准时保留实际用户消息、准确范围与匹配hash，
不捏造额外人工签名或GPT审批事实；实际HTTP前再次核对干净Git、成员、目的地、有效期和原消费保全。

## 离线验证与保全

- 继续策略/本地故障针对性回归：42 passed，11.59s；含299形状403/429一次停、持续/混合传输三次熔断、
  成功清计数、不可重发、秘密与预算保护。全部Mock；不是供应商业务验收。
- Doctor与12数据合同检查通过。生产源码/依赖/两份机器计划无修改，implementation hash不变。
  本批没有重复完整1175本地回归；1175来自上述已审查版本CI，不能冒充新文档HEAD的CI。
- 原106次消费关联391文件逐SHA256与原基线一致；001仍1 UNKNOWN/298未尝试，0回执。
  为001全部5文件另保留SHA256基线并在交付复核，无删改；旧库写入、私有删除、交易操作0。
- 最新全项目盘点沿用10月13日16根（含仓库外）：33,622,439,763逻辑字节、34,619,711,488 inode文件blocks；
  本批只有轻量诊断/文档/Mock测试产物，未重新声称完整实时容量已盘点。整体50GB目标/100GB上限不变。
- 无新Raw/Store/行业或全市场研究结果。已有10股报告保留；网络可达不能替代真实全市场覆盖与数值抽查。

交付前检查：489个Git可见文件明文/编码/解码秘密检查无违规，公开诊断无个人绝对路径或私有投影标记；git diff --check通过。
