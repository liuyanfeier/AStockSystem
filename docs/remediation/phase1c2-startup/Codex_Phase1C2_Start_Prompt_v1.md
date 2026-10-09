# Codex Phase1C.2 启动 Prompt：运行准备、受控继续与精确采集申请

仓库：`/Users/yanliu/Documents/AStockSystem`。基线最终 SHA：`6f5e3361bb8aff59621b72c38e89de96c668953d`。

完整独立 Review：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-08_Phase1C1_Consolidated_Evidence_Independent_Review.md`

最新阶段决定（取代旧提案的“待用户确认”）：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-08_Phase1C1_Closure_And_Phase1C2_Start_Decision.md`

已有 R1/finite45、F1–F4/root clone 工程结论保持关闭/通过；本轮不是再次重做这些修复。目标是集中解决真实连接诊断与后续未消费成员继续执行的运行机制，完成新阶段的精确申请后一次交付 Review。

## 已授权的阶段与本批执行范围

用户最新直接指令已要求：Phase1C.1工程修复通过后，尽快推进Phase1C.2。独立Review确认已关闭的R1/finite45、F1–F4/root clone保持通过，因此Phase1C.2启动批次已获授权；不再援引最初R1/R2时期“不得开始Phase1C.2”的旧限制，不再次询问阶段批准。

开始实施时，将实际用户执行指令及当前阶段决定写入新的 `docs/reviews/phase1c2-startup/` 授权记录，并在 `AGENTS.md` 追加当前 Phase1C.2 startup 范围，明确取代旧阶段暂停；保留历史授权记录，不能把旧许可证重签为新许可。用户当前指令优先于历史范围文档。

本Prompt属于Phase1C.2第一批运行准备与受控采集实施。历史身份、session、reference price、DQ和Context仍有真实缺口，继续作为研究数据准入门槛，不把它们一概作为进入本阶段准备工作的前置条件。

将本Prompt交给Codex并要求执行，即授权一次性完成A–E：离线设计/实现/验证、下述限定无token连接诊断和四个精确只读文献GET。它们不再分别等待阶段/文献许可。保留实际用户执行指令、Prompt文件哈希和分开的诊断/文献账本；本审查对话没有声称已经运行这些动作。

真实calendar/market和生产账本升级依赖尚未实现、未独立Review的新运行机制。本批集中完成这些依赖及具体执行申请，数据API保持0；不得自行签独立Review、重发旧请求或用阶段批准替代runtime匹配许可证。最终交付一次集中Review。

**本批：数据 API 0、原 133 replay0、原库写入0、旧 metadata/真实 capture store 写入0、真实账本升级0、Context/DQ 注册0、消息/邮件0。**

已有两个已消费日历请求不重发：旧 SZSE2013 FAILED/unknown delivery，以及新 SSE20121201..20121231 UNCERTAIN。不能重新调用 CLI、换 store/root/run/fields/contract，或拆分/扩展日期来绕过消费。28 个未执行成员本批同样不发送。BSE6、行情6、stock_basic、mapping、namechange/stock_company 探测全部保持未许可。

## A. 定位连接问题并增加安全诊断

先只读检查已保存调用材料和本机运行配置。事实为 CALL_ENTERED 后0.328542秒进入UNCERTAIN，没有HTTP响应；旧代码只记录统一reason，不能把猜测写成根因，也不能把旧请求改为“未送达”。

检查执行环境、DNS/系统网络配置、显式路由/代理存在性、证书配置、沙箱/工具许可记录；只输出脱敏的状态/类别。当前 runner 使用 `trust_env=False`，不要假定环境代理一定被使用；同时不要自动改成trust_env=True、关闭TLS验证、选择第三方代理或发送token给诊断服务。

执行本Prompt时，最多对 `api.tushare.pro:443` 各做一次 DNS、TCP connect、TLS handshake。每阶段至少记录实际开始/结束UTC、耗时、状态及安全的异常类别。总 DNS<=1/TCP<=1/TLS<=1；依赖失败则后续不执行；不得发 HTTP GET/HEAD/POST、认证数据或重试。TCP/TLS尽量共用同一连接；若实现必须新建连接，明确记录实际连接数，不超过一次TLS连接。其他host/proxy/备用IP的主动探测不在授权内。任何失败不阻断后续独立的离线实施。

为未来 capture 增加允许列表诊断：error type/阶段、是否收到headers、实际body字节数/是否EOF、真实时间、路由模式、被批准的endpoint host和TLS验证状态。记录上下文必须脱敏；禁止repr(exception)/request/headers/body/环境值泄露token、proxy userinfo、查询参数凭据或私有证书内容。不使用诊断结果自动证明旧调用未送达，不自动重试。

若无法确定历史故障原因，写 `UNKNOWN_PAST_TRANSPORT_REASON` 并给出未来可观测能力及本次连通性事实，不填写猜测的TLS/proxy根因。

## B. 受审查的停止账本继续机制：只在副本与closed mock实施

当前固定store为 `data/private/full-backfill-v1`；6张表、29成员、1许可证、1plan、3事件、0receipt；数据库SHA256：
`b96fb71660643aeb07359c65b49afdb721acdfcc5a71d648149a6463e6c21625`。

先对原store持项目共享锁只读核验；在新private候选目录复制完整封存证据进行实施与测试。不得直接修改真实store、原warehouse或旧metadata。候选/fixture路径不能作为可替换的生产消费库。

先写清并冻结新协议设计，然后完成实现和离线验证，不在设计后要求一次小Review、实现后又停一次。最终一起提交。

设计必须解决全部约束：

1. 保留所有旧6表既有行、origin plan、UUID、descriptor、旧review/human bytes/hash和事件时间；不更新/delete旧历史、不补造旧HTTP响应、不开新生产库绕过消费。旧协议源码/设计/catalog/DDL以原字节归档/保留，新协议另建版本。
2. 允许的不是“清除UNCERTAIN”，而是追加匹配review＋human批准的隔离/继续授权。旧UNKNOWN仍阻断该逻辑成员和依赖它的事实认证；只有被精确批准、在所有旧/新协议ledger均无CLAIMED/CALL_ENTERED的成员可候选继续。
3. 授权至少绑定真实固定store的canonical路径和封存基线、精确28候选集合/顺序/hash、旧origin plan/license、终态成员、实施SHA/clean root、协议/descriptor/contract/配置/DDL pins、预算、时间和独立review及实际human指令。实际开始时验证最新受保护历史和当前消费摘要；不能仅凭离线快照断言仍未消费。
4. 28成员仍保持既有origin/UUID，新的执行授权另追加；既有plan license不能覆盖。必须明确每个新CALL_ENTERED/response/receipt对应哪个新授权，且原注册历史可完整回查。不能把新发送归因给旧SHA的许可证。
5. 跨版本共享一个消费键 `endpoint/dataset/params` 和同一个固定生产store。字段/contract/命名/路径改变不生成重试机会。旧及新状态共同参与消费与预算核验；同一逻辑成员永远最多一次attempt。
6. 并发、崩溃及managed锁：授权验证/注册/claim/预算消耗/attempt binding必须有清楚的事务与持久化顺序。发生不确定新调用即停止本批，保留新消费，不能自动追加更多隔离规则继续发送。
7. 原始响应成功、合同解析、完整性认证、venue/session/identity/DQ/research admission分别表示。不把保留原始字节等同于data completeness，未认证leading previous仍未知。旧COMPLETE验证语义不弱化。未知cap/空/截断不得冒充完整；如引入新未认证保留状态，说明物理保全与可选用规则，禁止进入研究Context。
8. 对旧协议来源使用原pins和真实原origin验证；新代码不得因所有旧plans必须匹配当前新pins而丢弃/放宽旧验证。生产升级只给出append-only方案及回滚/保全条件，本批不部署。

实现可选择增加独立模块/附加表/协议分派，具体名称由你决定；不要仅移除 `PLAN_STOPPED_NO_RESEND` 或 `CROSS_PLAN_MEMBER_NOT_REUSABLE`。

## C. 精确四个文献GET

执行本Prompt已包含这一只读范围，无需再单独询问。申请来自：
`data/private/phase1c1-consolidated-evidence-launch-admission/2026-10-08-v1/exact-attachment-and-index-request-proposal.json`

其完整request-set checksum为 `59c0ba53cc07eb37801a3c77f46d3d978940ee5c18f9c5dccdbba547f2043703`；独立Review已核验4URL均为实际原文中的literal链接。预算4是新范围，不是旧38额度的余额；每URL最多1次GET，retry/redirect0、无auth/token、不跟随返回的新URL或下载其他附件。

- https://www.sse.com.cn/aboutus/publication/factbook/documents/c/10170569/files/cdccf6c0b46a4c0cadc0a531ecc3aad7.pdf
- https://www.sse.com.cn/aboutus/publication/factbook/documents/c/10170570/files/9a7b8e0d00e84d358d02fbba056f7bda.pdf
- https://www.sse.com.cn/aboutus/publication/factbook/documents/s_list.shtml
- https://www.sse.com.cn/xhtml/js/common/table_config.js?v=V3.7.9

使用descriptor中准确的新存储路径，建立追加不可重发的文献ledger。请求前记录实际用户授权与request-set hash；已有相同url/body足够则复用，不为次数重复GET。未知/403/redirect保留原终态，不自动重发；不同独立成员可继续。按真实PDF页码/原文位置提取候选issuer/code/share-class/listing/termination事实。landing/字段说明没有事实就保持缺口；不要把2012/2013两份年鉴外推到整个2013–2026年。

无论取证成功失败，都继续全部独立离线工作后集中交付。实际执行仍须记录用户启动本Prompt的指令；若另有新指令明确排除此范围，遵从最新指令并继续其他工作。

## D. 新阶段可执行申请与持续数据阻断项

将运行准备与研究准入分别呈现。全部未解决identity401994/session63/reference3仍登记；旧3Context/6generation/6audit保留。候选绑定非空且证据充分才能形成提案；不得重导finite45、注册Context或降低DQ分母。

准备exact28日历继续申请，明确首项及后续成员是否有依赖、尚缺SSE2012前驱与SZSE2013、BSE6 HOLD；允许保存窗口不能自动认证所有63session或完整交易日全集。

对行情6仅准备raw-only候选申请，2013-01-09六端点scope不静默改变，仍无真实调用。逐endpoint列permissions、字段、contract、cap/empty完整性、所需日期/成员依据以及数据状态。未知不伪造为PASS；当前catalog不支持的metadata6不加入。

保留完整2013-01-01..2026-09-30目标、全部原venue/六端点，verified reuse0、额外分片/IO/总预算未知。在获得真实响应与相应批准之前，不发放全量许可证、不把30126base上界当已批准可执行预算。

## E. 必要验证与一次交付

只针对新增运行能力增加必要验证，复用已通过旧测试。必须包括：旧真实副本history/哈希保全；无许可证/伪造human/旧SHA/clone root/集合变化拒绝；已消费UNKNOWN永不重发；28候选对global ledger真未消费；新授权不重写origin；未批准或依赖缺失成员拒绝；并发claim与崩溃后单attempt；新异常停止且再次运行不新增HTTP；五文件变异不能COMPLETE；诊断产生凭据/异常repr泄露时失败；未知cap/NULL/previous不误认证；完整性与研究状态不能互相替代。

使用closed httpx.MockTransport，禁止测试真实token/数据网络。旧及新完整测试按实际变化执行必要的一轮，精确SHA CI，检查doctor/offline plans。新失败修复完再一次Review，不按每个case/字段/文件请求小Review。

交付一个包：设计、代码/测试变更、真实连接诊断许可与结果（未许可就0）、可选四文献许可/ledger/source/页码、真实原库和capture store只读保全、候选升级完整行集证明、新精确28/行情6 proposal且execution许可证false、持续阻断矩阵、凭据扫描、manifest/index/ZIP/handoff、finalSHA与对应CI。

目标状态：`PHASE1C2_STARTUP_AND_EXACT_ACQUISITION_REVIEW_READY`。作者不能签独立Review、批准真实数据API或升级生产store。本批交付后停止真实动作，等待一次集中Review。

最终报告开头明确：本批实际做了什么、连接是否可用、旧UNKNOWN未重发、继续机制是否仅离线完成、哪份exact application可以进入下一次独立审查；不要用“更多材料待补”代替清楚的实际阻断事实。
