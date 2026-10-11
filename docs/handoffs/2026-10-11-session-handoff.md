# AStockSystem 会话交接：截至 2026-10-11

本文面向没有聊天背景的新会话。先读第 1–3 节，再按第 8 节定位证据；需要实施时再读对应原 Prompt、实际独立 Review 和许可文件。本文是导航和状态快照，不能替代运行许可、原始证据或独立审查。

## 1. 接手时先知道这些

- 仓库：`/Users/yanliu/Documents/AStockSystem`；GitHub：`liuyanfeier/AStockSystem`；当前分支：`main`。
- 本轮交接前 HEAD：`c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db`。这是 RAW49 的**文档交付 SHA**；实际 RAW49 运行 SHA 是 `66b1cec4914d51f75b0cf4f5211623a03dd9de2d`。不要混淆交付代码与实际执行版本。
- **Phase 0 已通过；Phase1C.1 工程独立 CLOSED；Phase1C.2 已 STARTED；整个 Phase1 真实历史数据准入仍 BLOCKED。** 策略、回测、券商、实盘自动交易尚未进入授权范围。
- 最新批次已完成作者交付，状态：`PHASE1_CONTROLLED_SOURCE_ACQUISITION_AND_FULL_DELIVERY_PLAN_REVIEW_READY`。**等待独立 Review；此会话没有收到该批次最终独立 PASS 或全量执行许可。**
- 最新 RAW49 已结束：49 个新成员各一次，26 COMPLETE、21 RAW_RETAINED、2 FAILED，47 份回执，49 个响应对象，0 未尝试、0 新 UNCERTAIN。两项空返回保持 HOLD。不能再启动控制器。
- 前一 RAW50 的 SSE2014 UNCERTAIN 保留。新采集库共 50 次历史 attempt：旧 1＋新 49；这不等于本轮重新发送了 50 次。
- 最新批次只追加新的 RAW_ONLY 采集存储；原三库 SQL 写入 0，新生产 facts/generations/adoption 0。原始窗口 COMPLETE 不代表研究准入或全历史完整。
- 全历史任务已经形成 76,629 个具体种子请求及有限预算，**execution_license=false**。不要把方案、代码可用、源样本成功或用户以前的批次许可当作当前全量许可。
- 本交接只新增此文档，不修改冻结源码、旧证据或旧交付 ZIP；文件尚未提交，因此之前 SHA 的 CI 不涵盖这份新交接文档。

### 三条必须分开判断的线

| 判断 | 含义 | 当前结论 |
|---|---|---|
| 工程验收 | 代码、回归、恢复、事务、审计等机制是否满足要求 | 多轮工程修复已通过；最新运行源码 F1-R 获独立 PASS |
| 真实执行许可 | 某一 exact SHA、成员、预算、端点、目的地是否有匹配独立批准和人类授权 | RAW49 的有限许可已消费结束；全量任务未许可 |
| 研究数据准入 | 历史分母、身份、交易日、规则、PIT vintage、覆盖和重建是否充分 | 整体 BLOCKED；不能用于宣称完整历史研究验收 |

## 2. 项目目标与合作方式

项目在 Mac 上建立可审计的 A 股数据与研究基础。长期路线是：数据来源 → PIT 仓库 → 市场/行业/主题分析 → 候选及基本面/催化研究 → 独立策略评估 → 风险过滤 → 交易计划 → 人类确认/早期手工交易 → 复盘。Phase 0–7 路线依次为治理、数据基础、市场/行业雷达、策略原型、OOS/walk-forward、纸面及小规模交易、盘中、券商接口。当前仍在 Phase1 数据基础。

用户通常把 ChatGPT 的设计/独立审查 Prompt 放到以下外部目录，再交给 Codex 实施：

`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/`

Codex 读取材料、核验是否合理、实现/验证、在具体授权内执行、提交推送并核实最终 exact-SHA CI；ChatGPT/独立 reviewer 查代码仓和私有证据，再给意见。**Codex 作者不能自行签独立 PASS、生成假的生产审批、猜测 reviewer 身份/时间或宣布 Phase1 FINAL PASS。** 用户保留范围与最终决策。

后期采用“一批完成、集中 Review”：无需每个小修复/commit 暂停。局部来源缺口不阻止独立离线模块继续；HTTP 停止也不意味着停止全部离线工作。但新真实调用、部署和数据采用必须落在实际批准范围内。

新的人类指令可在其明确范围内取代旧批次的暂停规则。不能把旧文档中的 `Phase1C.2 CLOSED`、`R2 LOCKED` 无限套用到当前；也不能把“允许进入阶段”解释成无限 API/原库写入许可。最新 `AGENTS.md`、具体 Prompt、实际 Review/人类许可和持久账本一起决定边界。

## 3. 当前工作现场与证据锚点

### 3.1 最近的 SHA 与 CI

| 项目 | 精确版本/证据 |
|---|---|
| 前一 RAW50 实际运行 | `5672e8f8464b20e3437ab94bd3ef17cbb05f7bcf`；首个 SSE2014 传输未知后停止 |
| 来源版本修复 / RAW49 实际运行 | `66b1cec4914d51f75b0cf4f5211623a03dd9de2d`；23 个运行 pin 固定；[CI 38033728809](https://github.com/liuyanfeier/AStockSystem/actions/runs/38033728809)，1005 passed |
| RAW49 文档最终交付 | `c1a9ef7f0ebb063f4b0ebd3ec6e4733a15e6f5db`；只改 9 份脱敏文档；[CI 38043097292](https://github.com/liuyanfeier/AStockSystem/actions/runs/38043097292)，1005 passed / 6 warnings，2232.25 秒 |
| 最终 CI 其他步骤 | locked dependencies、doctor、contracts、probe plan、identity/slice specs 等均 success；CI 的 TUSHARE_TOKEN 为空，无真实 API |
| 本批附加离线证据 | 私有候选生成器断网测试 7 passed；OS 隔离探针是合成 fixture 验证，不能称生产保护方案获批准 |

CI 只认证该 exact SHA 的软件检查。此前出现过“测试数很多但独立攻击仍能复现”的情况，不能用测试数量替代审查或真实覆盖证据。

### 3.2 三个旧原库与新采集库

以下路径相对仓库根目录。旧原库在最近批次中全部只读；后续未经匹配批准不能升级或写入。

| 存储 | 路径 | 最后交付 SHA256 |
|---|---|---|
| 原 warehouse | `data/warehouse/astock.duckdb` | `30953a9ff2622c85724794b268bc878ea2494684d6faccd5ab0fc5cbb378eb81` |
| 原 metadata | `data/private/phase1c1-admission-metadata-live-v1/metadata.duckdb` | `91a2c5d20df935795e0e2b736175af13fb6b7b5f6092231a9e96975fd30b9ece` |
| 原 capture | `data/private/full-backfill-v1/capture.duckdb` | `7293111ae2a69d75484c4897a567c2116ad601ef659987d199287d43b4915ee3` |
| 新统一 RAW_ONLY catalog | `data/private/phase1-integrated-v1/catalog.duckdb` | `bc45330f6e0c49534712b0383eee3e7fe65d14eb0854ff2d12d59e15dd12daf8` |

旧 warehouse 已有授权部署的 schema001–010；旧 capture 有原六表及已授权的五张 v3 表。新统一工程 schema/目录独立，不应再往旧原库安装新实现。完整表/行集清单以私有证据为准，不通过文档数字重造现场。

最后完整保护检查：2026-10-10 11:40:09 UTC（北京时间 19:40:09），146,656 个保护文件、171 个冻结项、旧版本登记、原三库、新 catalog 及停止后 245 个新存储文件保持不变，47 回执只读审计有效，扫描 54.10 秒。

本交接于 2026-10-11 重新核验当前 HEAD、23 个运行 pin、原三库字节、新 catalog 字节和最新 ZIP 哈希均匹配上述交付记录；**没有重跑 146,656 文件完整扫描、全套测试或实时查询 GitHub**。涉及下一次真实运行时必须做其要求的新鲜 preflight，不能把本次有限核验当作新的全量保全或执行许可。

### 3.3 最新私有包

私有根目录（下文简称 `LATEST`）：

`/Users/yanliu/Documents/AStockSystem/data/private/phase1-raw49-controlled-execution/2026-10-10-v1/`

- ZIP：`Phase1_RAW49_Controlled_Recovery_And_Full_Delivery_Review_Private.zip`，6,193,462 字节，3472 个唯一成员。
- ZIP SHA256：`ed2b5e22653183164d5f05f2c96f504fa34fe309149ca8e4a1f8a9b0501372c0`。
- `delivery-index.json`：入口；绑定执行 SHA、交付 SHA/CI、全量申请、旧包及状态。
- `delivery-manifest.json`：逐文件路径、长度和 SHA256。ZIP CRC、唯一成员、逐文件哈希、解压后请求清单及配置凭据扫描均通过。
- `package-verification.json`、`final-delivery-verification.json`：封包和再次打开验证结果；这些外部校验记录不必出现在其自身认证的 ZIP 中。
- ZIP 包含本批真实许可链、原控制器、子计划、响应、回执、新 catalog、冻结源码和离线证据；**不复制三个旧原库及整个旧历史数据集**，它们以路径和摘要引用。

这些文件是 ignored/private；只克隆 GitHub 不会得到完整现场。缺少私有证据时报告缺失，不能用 fixture、合成审批或猜测数据补齐。

## 4. 已经完成的工作：阶段时间线

| 阶段 | 实际成果 | 保留的问题/区别 |
|---|---|---|
| Phase 0 | Python3.12/uv、设置与秘密类型、doctor、基础 SQL、契约/治理、pytest/无 token CI；隐藏项目文件已显式提交 | `settlement_t_plus_n` 的卖出限制与现金结算语义已拆清；不是写入真实交易规则 |
| Phase1A | Tushare SDK/HTTPS/端点/字段及账号接入安全审计 | 不使用 SDK 默认 HTTP 发送凭据；固定 HTTPS、验证证书，不擅自换端点/路由 |
| Phase1B | 有界 47 请求真实来源探针和 raw 留存 | data gate PARTIAL；当前样本/证券列表不等于完整历史 |
| Phase1B.1 | 三个身份异常取证；native/normalized 校验分离；`security_identifier_history` 区间及 as-of 模型 | 两个 BSE 换码解释成立；SSE 异常仍未确认，不能猜映射 |
| Phase1C0 / C1 | 身份 bootstrap、21 日/7 切片有界历史演练，包含 2025-04-30；133 请求事实、raw/curated/lineage | 后续发现完整性、身份/DQ/上下文问题，进入 R1/R2；原133禁止重跑 |
| R1 G0–G3 | 严格回执绑定、锁/连接/线程/fork 生命周期、备份、副本迁移、原库 additive007 部署和离线验收 | 133 exact receipts、181 raw、252 旧 curated、当时17历史表/1102文件保全；R1 FINAL 后续独立通过，不能再读旧 pending 报告为当前状态 |
| R2 A/B | 供应商绑定/episode、DQ 策略、Context/发布/隔离、时间完整性修复；matched-v2 审批后008–010和受控发布 | 不把 resolver 当前知识回填历史；v1 失败与旧审批保留 |
| Admission A / limited15 / finite45 | 证据闭合、事务原子性修复、副本演练、实际有限批准的原库追加；有限 identity 观察累计252 | finite45：9 bindings/45 observations；最终252 resolved、401994 quarantined；402060 DQ findings/63未认证session仍阻断 |
| Runner/启动准备 | 全天停牌 NULL、raw 发布竞态、多计划固定存储、描述符哈希/root 绑定等修复；集中日历/文献申请 | 重建和采集许可分开；没有把旧错误消费重置为可用预算 |
| Calendar29 / Phase1C2启动 | 有限文献取证、实际日历尝试与连接诊断、继续机制及新版本演练；阶段正式启动 | Calendar29 有1 UNCERTAIN，不能重发；阶段启动不等于28日历/行情获许可 |
| Calendar28 / 备份脱离 | 126 备份端同字节脱离硬链接获独立维护审查；252 路径 nlink1，主126 inode/历史字节保持；追加五张 v3 表后有限日历尝试 | 首个 SSE2013 返回200/code0/365行但 envelope 多字段被旧解析器拒绝，FAILED/0回执/27未发；driver 次级重复键报错保留；不能重跑旧 driver |
| Phase1整体工程 | 新统一 `astock.phase1`：采集/恢复、身份/状态/规则、行情/因果复权、财务/行业 PIT、覆盖/as-of、重建/增量；23非空合同/全域合成演练 | 原967测试通过后仍被独立 Review 找到3P1/2P2；软件覆盖不代表真实覆盖 |
| 合并修复 | 原始证据重推导、跨码财务、生产来源独立重建、持久授权链、目标分母覆盖；70→71合成事实、独立 A/B 更正/增量 | 生产形状仍是闭合 mock，实际审批不可由 TEST 根迁移 |
| RAW50 / F1-R | 原50计划在5672运行，首个 SSE2014 UNKNOWN；冻结实际执行 V2，修复转换版本选择及旧版本兼容，最终66b1获独立 F1-R PASS | 真实0对象/0回执/49未尝试，旧 UNCERTAIN永久保留；不能再运行原50计划 |
| 受控 RAW49 / 全历史申请 | 原字节独立外层控制器在66b1按预授权派生子许可，三段完成49新成员；源限制、保护测量、全域具体请求/成本/恢复/验收方案；c1a9交付 | 26 COMPLETE＋21 RAW_RETAINED＋2 FAILED；本批作者交付待独立 Review；全量未许可、整体准入 BLOCKED |

“旧252 curated 文件”和“252有限 identity observations”是两个不同概念；“每代126输出”和“252 resolved 行”也不是同一个计数。逐代/逐请求/逐行证据应按各阶段 manifest 核验。

## 5. 典型问题、已做的修复与不能丢的经验

### 5.1 身份不是六位代码字符串

实际 SSE/D raw 原生异常是 **T600018.SH**；旧 Tushare issue 及最新固定探针用 **T00018.SH**。二者没有已批准 alias 证据。最新 T00018 过滤返回空，不能证明原异常消失，也不能擅自去 T、改代码或合并历史600018前后法律实体。

BSE 两个异常为835305.BJ→920305.BJ、839680.BJ→920680.BJ，官方换码日期 **2025-10-09**；不能套用 **2025-05-06 六股试点**。不得按尾号推映射。native 标识、source/type/exchange/effective interval、published/available/retrieved、stable security/episode分别建模；原始格式验证与规范化验证分离。

**跨码财务问题**：历史查询不能只按今日 native code 找财报；必须从稳定身份/episode解析适用历史 identifier，保留旧码财报版本。代码重用/继承公司不是自动同一证券。

### 5.2 数据库内“自洽”不能证明事实正确

曾把财务值或 available_at 改错，再重算所有库内哈希，审计仍通过、增量仍保留。修复要求按不可变 source body/行号/授权/契约重新推导完整事实、时间、质量、eligibility及lineage。query/rebuild/increment 同样验证来源，不能只信 generation 或 DB 自己的摘要。

**F1-R版本替换攻击**：即使把 descriptor/generation 的 pins 同时改成另一个登记版本，也不能覆盖实际 capture origin plan 或不可变 document source/实际批准的转换版本。V2 缺少证明不能冒充 V1；真正有证明的 V1 必须保留可读兼容。实际已执行源码先按 Git 原字节冻结，再修复当前代码。

### 5.3 事务完成不等于成功事实可发布

回执必须精确绑定 request/run/object/contract/params/raw/schema/sidecar/lineage。空 requested run、0 manifests 不应给 PASS。raw 在发布途中被改动不能首次 COMPLETE、重开才发现；事务前后及物理 readback 都要证明完整。

Importer 曾把 merged resolver 的校验放在 commit 之后，导致报错却留下持久行。修复将批准 observation 原顺序检查、old＋delta merged readback/hash验证置于管理事务内；不能排序已签 payload、只验增量或捕获失败后静默恢复原库。

迁移与读审计要分开：授权部署会改变 DB 整体 hash，历史保全比较旧表内容和保护文件；strict read-only audit 则要求前后 DB 字节 hash 不变。

### 5.4 连接、线程、fork 和文件描述符都是边界

G2 曾发现未托管连接在晚拿锁后仍可写，以及非持锁线程 fork 遗留锁 FD。检查范围包括连接/代理/游标/关系对象生命周期、thread/context、异常/进程死亡、fork-child状态，不能只在顶层CLI加一把锁。

备份同字节也可能留下 hardlink 写穿风险。126 备份端脱离是独立获批维护动作，保持主文件 inode/内容；旧 STORE_HARDLINK 阻断已经关闭，不能再把它当当前缺陷，也不能无授权 unlink 旧文件。

RAW49 之后的合成保护探针发现：OS 路径拒写能挡 overwrite/unlink/rename/chmod/hardlink/symlink，却不能撤销**继承的可写 FD**。初次绕过与修正结果均保留；fresh exec + close_fds、安全 stdin/stdout/stderr 后示例攻击被拒绝。这只是 fixture 原型，完整原目录/alias/其他写入者/监测死亡保护仍需实现和独立批准。

### 5.5 时间与 PIT 不能用日期字段补猜

区分 event/period_end、effective interval、published_at、available_at、retrieved_at 和 knowledge_as_of。ann_date/f_ann_date/update_flag 出现在今天下载的财报里，不证明历史原始版本当时可得；要找原始/更正 archive、精确发表证据和匹配 policy。

R2 修过 resolver digest 与 pinned-member 时间比较，要求显式 v2 design/protocol pins，四时区同 Context；不修改旧审批时间来适配新代码。新来源更正不能抹掉旧 as-of 答案；NULL 不变成0，date-only不捏造具体时刻，future publication不补旧版本。

### 5.6 覆盖必须有目标分母

只有已出现的数据才能自洽的 DQ，会漏掉整个证券/交易日缺行。需要证券/episode×有证交易日、财报/版本、规则/行业 interval 等明确义务，输出 expected/observed/missing/conflict/uncertified/source-backed-not-applicable及unknown denominator。

缺 bar 不自动代表停牌，稀疏 ST/suspend 没有行也不自动代表 NORMAL。合法全天停牌的 `suspend_timing=NULL` 已回归覆盖；制度、板块、IPO/ST规则和供应商完整性都需各自时间证据。

### 5.7 请求消费、审批链和故障隔离

审批要持久绑定 claim→CALL_ENTERED→source→receipt，而非CLI内存中检查一下。失败/进程死/传输未知不退款；不能换字段、目录、contract、日期表示或 plan 名称来清除旧消费。root绑定必须 canonical absolute，clone不能复用批准绕过消费。

旧内核首错停止一个 segment。RAW49 **仅在实际独立预授权范围内**由冻结外层控制器隔离 dataset错误并派生未消费子计划，继续其他独立来源。这不是作者可以普遍自行批准新子任务的规则。

旧传输错误只有 `TRANSPORT_UNKNOWN_NO_RESEND`，无法倒推 DNS/TLS/权限/是否发到服务器。RAW49 的一次 DNS/TCP/TLS PASS 与49个新HTTP200/code0，只证明当前有界接入；旧 SSE2014 原因仍未知。诊断不能暗带HTTP/token，异常记录用阶段/白名单类别/安全errno，不能记录请求、凭据或异常原文。

旧 driver 的次级重复键 TypeError说明报告链本身可能失败。保留原日志，使用明确标注的 post-exit SQL读回证据；不能把缺报告当成功、改写原时间戳，或为重做日志重发请求。

### 5.8 验证和文档常见误区

- 不在全套测试旁并行生成私有 data 文件：旧 doctor 的目录只读快照曾因此误报；停止演练后单独复验，保留失败记录，不改冻结测试掩盖问题。
- 完整保护扫描最近约52–57秒/次，必须计入全量成本；不能直接关 guard、改mtime缓存或把旧文件复制到别处后当没有消费。
- 最终CI可能需22–37分钟；等待 exact SHA 结果，不能借前一 SHA 的通过冒充新实现验收。源码未变时可按具体Prompt复用旧运行CI，文档交付SHA仍单独记录。
- README、architecture、operations、矩阵保留了多个历史段落；`docs/architecture.md` 的“现在只有Phase0”是历史边界，**已落后实际实现**。顶部最新报告/交接优先，历史语句不擦除。
- 平台自动审批拒绝与项目未授权不同；保存拒绝原因，做不依赖阻碍的已授权工作，不能绕过平台。之前拒绝记录是历史，不是当前所有执行都禁止。用户授权必须具体落到实际命令/范围。
- 辅助证据脚本也有真实失败：本批 planner 测试拼接位置导致NameError，消费视图误读attempts字段导致KeyError，普通沙箱无法启动嵌套sandbox，optional ps受限制。均未产生额外API/原库写入；纠正/负例/限制记录保留，不能把它们写成独立验收通过。

## 6. 最新 RAW49：结果和未决项

本次依据原字节实际独立 Review、policy、controller，以及人类直接“继续吧”与配套 Prompt。控制器 SHA256：`54e536641dc4d9f990da101ccdc0bef1d850b39c5cae7234977f0eebe5df8404`；policy digest：`37e20c21dc42aced3f2af625fb5e34669f8865021978cc5b559ef92b5a38704c`。

26日历＋17源探针＋6行情，各成员一次，原顺序/params/fields/origin固定；最多3诊断周期，实际只用1。实际三个segment消费29、12、8个新成员。49次不同CALL_ENTERED，最小相邻间隔70.88696秒，满足≥1.25秒；无retry/redirect、新未知或次级控制器错误。

| HOLD | 实际返回 | 不能做的推断 |
|---|---|---|
| stock_basic：`ts_code=T00018.SH, exchange=SSE, list_status=D` | HTTP200/code0/0行，FAILED / UNEXPLAINED_EMPTY | 不能当原T600018异常已解决；不能猜别名、证券不存在或当前600018与前身同一ID |
| index_member_all：`ts_code=600519.SH, is_new=N` | HTTP200/code0/0行，FAILED / UNEXPLAINED_EMPTY | 不能当无行业；N/Y语义和taxonomy历史仍需官方证据及scope核验 |

成功财务普通/银行样本、分类、行情、状态等只证明这些 exact 响应的物理留存/契约验证。低于cap、has_more=false或count匹配不认证全市场/全历史；真实来源尚未采用为生产facts。

`hold-disposition-proposal.json` 只提议独立、未批准的 exact-filter空观察，不改 FAILED/receipt/time，不产生absence/identity结论。`actual-source-limitations.json`、`actual-source-answers-private.json`记录字段、NULL、count/cap等观察及权限/vintage限制，不能再发请求补缺口。

## 7. 下一步可能需要做什么

### 7.1 眼前下一步：独立审查，而非再采集

给 reviewer 最新 report＋LATEST私有ZIP/index＋全量任务。收到新 Review/Prompt 后完整读取，先对照实际 SHA/范围/证据；认可的问题在明确授权内集中修复，保留旧材料。没有后续人类指令时保持停机，不自动推进全量或adoption。

### 7.2 全历史统一任务已经准备，但存在实质前置条件

目标 **2013-01-01–2026-09-30**；财务义务包括2011Q1起必要前置报告，2026Q3未到公告期限的不能标缺失。申请新目的地为 `data/private/phase1-full-historical-v1`，它只是拟定路径，不能因此创建生产库或运行。

已校验181原raw/497889行，5919个stock_basic native，加供应商旧/新码列中248个额外native，得到6167个请求种子。**它们不是6167个已批准security_id，也不是官方完整历史证券分母。** 保留供应商248映射不等于官方全部映射证明；已有252有限身份观察原样复用，不再拆15/45小批。

| 域 | 清单种子数（证据裁剪/复用前） |
|---|---:|
| 日历 | 42 |
| 证券分区 | 9 |
| 六行情/状态接口的civil date候选 | 30,126 |
| 2016起bak_basic候选 | 3,926 |
| 四财务域 | 25,164 |
| 行业分类及N/Y成员候选 | 12,340 |
| 最小参考000300.SH | 5,022 |
| 合计 | 76,629 |

清单含具体params、fields profile、contract/hash、logical id、顺序、条件、复用/HOLD。193精确已存/已消费范围复用或HOLD，9重叠范围HOLD，76427条件新候选；不是立即调用清单。`full-request-units.ndjson.gz` SHA256：`2167b7d39fa23009600d3b008e92a9e2915f90817271ed81d494fe2c934305a0`。

有限上限：native最多8192；最坏core2,119,899＋600,000 cap/split＋1,000,000官方档案/文献/第二来源，合计 **3,719,899 request units / 11,159,697 attempts**。1,000,000档案池是预设上限，不是已取得URL库存或宽泛浏览许可。未来新任务成员拟最多3次attempt、5/30秒退避、≥1.25秒、单worker、no redirects、UNKNOWN持久保留；**旧133/旧失败/RAW49预算仍retry0**。cap拆分只能由证据驱动，不能为绕开UNKNOWN改params。完整机制还需要实现/匹配审查，不能直接复用RAW49许可。

需要一次集中处理的五项范围决策：

1. **历史证券与session分母**：官方listing/delist/code/episode/venue有效区间、完整性证据；现有种子和今天L/D/P不能补足全历史。
2. **财务原始/更正vintage**：取得可信披露档案/明确版本与时间；或人类明确缩小为当前snapshot交付，不能仍称完整PIT。
3. **旧状态/行业/规则来源**：尤其2016前证券历史、旧SW taxonomy/membership、历史板块/ST/IPO/lot/卖出限制/交易时段等，不用今日信息回填。
4. **资源与权限**：最近free177,534,152,704字节（约165.3GiB；旧方案文本粗记约168GiB，不是新保证）；拟2TiB峰值/64GiB预留没有实际配足。假设50KiB财务、10MiB日行情、256KiB档案，5倍峰值约2.63TiB，已超过拟配额；每attempt16MiB×最大预算更大。需实测/供给/明确缩范围，不能删旧字节补空间或私购权限。
5. **完整运行策略/保护实现**：≤256成员/1800秒批次、开闭批完整hash、OS隔离/old-writer排除、无继承旧可写FD、监测gap/death停止、关批前不得promotion、进程死亡后保留claims并fresh full scan。目前仅方案和fixture探针，生产等价性未独立通过。

成本算术（非完成预测）：76427新候选最小spacing26.537小时＋299批开闭扫描约8.674小时，尚未计网络/解析/退避/重建。最大attempt间隔约3874.895小时，按attempt批计算保护扫描约1264.675小时；旧任务JSON另有按unique units计的扫描公式，不能忽略retry增加批次数。该申请预算虽有限，资源/来源可行性仍BLOCKED，不能宣称全量ready。

全量验收还需实际批准来源下的覆盖、无未来信息、身份/规则/行业区间及原始vintage，独立第二来源抽查、真实独立A/B逻辑重建、更正/幂等增量、全部source version和许可链再证明，以及独立最终数据准入。当前mock A/B通过不能代替这些真实验收。

## 8. 文件导航：从哪里继续查

下列仓库相对路径均以 `/Users/yanliu/Documents/AStockSystem` 为根。

| 想知道什么 | 优先读什么 |
|---|---|
| 当前边界/源码约定 | `AGENTS.md` 顶部；本交接；最新具体人类 Prompt |
| RAW49最近交付 | `docs/reviews/phase1-raw49-controlled/{report.md,authorization.md,independent-review.md,execution-prompt-v1.md}` |
| 实際消费/许可/停止现场 | LATEST下 `delivery-index.json`、`stopped-audit.json`、`stopped-rowsets.json`、`actual-budget-chain-check.json`、`actual-call-spacing-check.json`、`execution/` |
| private真实原始字节 | `data/private/phase1-integrated-v1/`；LATEST ZIP内 `capture/`；旧raw通过manifest路径引用 |
| 完整方案/条件 | `docs/phase1/full-historical-delivery-task-v1.md`；LATEST下 `full-historical-delivery-task.json`、`full-request-units.ndjson.gz`、`cost-storage-and-scope-decisions.json`、`acceptance-evidence-matrix.json` |
| 审计/保全/CI/凭据 | LATEST下 `final-preservation.json`、`new-store-frozen-inventory.json`、`ci-final.json`、`ci-jobs-final.json`、`ci-job-final.log`、`public-staged-audit.json`、`delivery-manifest.json`、`package-verification.json` |
| F1–F5与F1-R修复 | `docs/reviews/phase1-consolidated-fix/report.md`、`docs/reviews/phase1-raw50-source-version/report.md`、`docs/phase1/design-v2.md`、`docs/phase1/source-version-integrity-design.md` |
| 新统一入口/操作/矩阵 | `src/astock/phase1/__main__.py`、`docs/phase1/operations.md`、`docs/phase1/acceptance-matrix-v2.md`；operations里的生产命令都是条件模板，不能照抄即运行 |
| 身份与最初三异常 | `docs/reviews/2026-10-01-phase1b1-identity-review.md`、`docs/security_identifier_history.md`、`docs/data_contract.md`、`docs/data_dictionary.md` |
| R1锁/回执/原库部署 | `docs/phase1c1_writer_lifecycle.md`、`docs/reviews/2026-10-02-phase1c1-r1-g3-final-review.md`；该旧报告的pending/LOCKED是历史 |
| R2/finite45 | `docs/reviews/r2-final-v2/r2-final-review.md`、`docs/reviews/phase1c1-import-atomicity-finite45/2026-10-04/`、`docs/reviews/phase1c1-finite45-formal-execution/2026-10-05/` |
| C1关闭/C2开始 | `docs/remediation/phase1c2-startup/2026-10-08_Phase1C1_Closure_And_Phase1C2_Start_Decision.md` |
| 长期目标/早期设计 | 根目录 `AStockSystem_Trading_System_Review_v1.0.md`、Phase0/1A/1B/1C设计及Prompt；只作历史背景，不直接扩大现在授权 |

更早 private 包入口：`data/private/phase1-consolidated-fix/2026-10-10-v2/delivery-index.json` 与 `data/private/phase1-raw50-source-version-fix/2026-10-10-v1/delivery-index.json`。最新index已绑定前包SHA，顺着链查即可，不必先扫整段聊天。

当前源码分工：

- `acquisition.py / authorization.py / core.py / legacy.py`：采集、持久许可、请求身份/范围、旧全局消费和保护。
- `evidence.py / fact_admission.py / interpretation.py / versions.py`：文献/旧raw解释、独立fact许可、不可变源版本。
- `pipeline.py / domains.py`：source-derived事实、审计/生成/重建/增量、身份/财务/行情/状态/规则/行业/as-of。
- `coverage_targets.py / planning.py / application.py`：义务分母、全域候选、执行申请。
- `fixtures.py / production_fixture.py`：纯合成/closed production-shaped演练；不是生产审批材料。
- `tests/test_phase1_integrated.py`、`tests/test_phase1_consolidated.py`、`tests/test_phase1_source_versions.py`：近期统一工程/攻击/版本兼容回归。旧 `src/astock/data/` 和 `compat/phase1/{v1,v2-5672}/` 的冻结实现不可顺手改。

## 9. 新会话的安全接手步骤

1. 确认 cwd、当前人类指令及有没有新Review；读本交接、AGENTS顶部、RAW49报告/Prompt、LATEST index、全量任务。
2. `git status` / `git log` 检查用户改动。本文是新增未提交文档，不reset它或其他用户改动；不要为凑旧clean SHA直接checkout/reset。
3. 核验待用实际证据、SHA/pins、消费、namespace/目的地和批准范围；只克隆Git而缺private时明确报告不足。
4. 若没有后续实施授权，等待独立Review。可以整理/解释用户明确要求的材料，但不能自行续跑旧控制器、升级原库、adopt/build真实facts或启动全量HTTP。
5. 有具体工程修复授权时，先冻结设计/执行版本，做新版本和闭合synthetic回归；不改历史成功/失败事实；完整复验和exact-SHA CI后统一交付。
6. 有具体真实运行授权时，还须匹配独立审批、实际人类许可、成员/预算/端点/目的地/clean SHA、新鲜备份/锁/保护/账本和停止条件；不能只看本文或JSON中的一个true字段。

初次只读检查可用：

```bash
cd /Users/yanliu/Documents/AStockSystem
git status --short
git log -6 --oneline
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen astock doctor
uv run --offline --frozen python -m astock.phase1 specs
```

需要软件复验时串行执行 `uv run --offline --frozen pytest`；不要同时写data/private演练。doctor/specs不发市场请求。旧原库使用管理read-only连接；SQL审计前后字节/WAL检查按规格执行，不能用未托管duckdb连接绕锁。新demo只在明确fresh TEST目录中按具体授权执行，不复制TEST许可到生产。

raw/curated/warehouse、private报告/许可、DB/WAL、`.env`、`.tools`、`.venv`不入Git；不在聊天/日志中打印token。轻量脱敏审查材料放`docs/reviews/`，大量运行证据放ignored private。staging显式列文件并扫描literal/编码/decoded凭据；保存历史Review及失败现场。版本审批、人类许可与平台注册审批三者互不替代。

### 可复制给新会话的开场指令

> 请接手 `/Users/yanliu/Documents/AStockSystem`。先完整读 `docs/handoffs/2026-10-11-session-handoff.md`、`AGENTS.md` 顶部、`docs/reviews/phase1-raw49-controlled/report.md`、`docs/phase1/full-historical-delivery-task-v1.md` 和最新 private delivery-index。当前基线 c1a9ef7，RAW49已消费结束，整体数据准入BLOCKED，全量license=false，等待独立Review。先核对现场和我随后提供的具体Review/Prompt，保留所有用户改动/旧证据；不要自行采集、重试消费请求、写原库、采用真实facts、运行全量或宣称FINAL PASS。区分历史状态和最新直接授权，收到明确范围后集中完成其允许的工作并验证exact SHA/CI。

## 10. 本交接的验证范围

2026-10-11仅做材料读取、Git/23pin/四个DB文件/ZIP字节核对和此文档整理。没有新市场/元数据/文献/诊断HTTP、没有原库SQL写入、没有重跑采集或全套CI，没有修改旧报告或ZIP。最新1005-test CI、全保护扫描及3472成员包校验是2026-10-10交付记录，精确时间见原JSON；此文档不制造新的独立验收。
