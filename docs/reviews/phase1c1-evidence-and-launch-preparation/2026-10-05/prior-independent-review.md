# Phase1C.1 Finite45 正式执行与工程收尾：独立 Review

**PASS：有限45正式应用通过，Phase1C.1 工程修复线 CLOSED。本批没有新的阻断性工程 finding，不需要修改后再次提交 finite45。** 全历史数据准入仍 BLOCKED，Phase1C.2 实际运行仍 CLOSED。

审查 SHA：`222cf660878da3d8fa67bfbce9f896731e83769f`。独立数据核验完成于 `2026-10-05T05:46:09+00:00`，所在地日期为2026-10-05。实现和实际批准固定 `546b57bcbb9af9e8b703a9f8edbfd1986f83bca4`；两版之间仅5个文档文件变化，171个已接受源码、测试、SQL、配置、依赖及设计 pins 全部不变。Git工作区干净。

| 审查范围 | 独立裁定 |
|---|---|
| 有限事实审批及正式部署 | PASS；原8份审批文件逐字节保留，匹配实际用户执行授权 |
| 原库追加与历史保全 | PASS；新增恰好9 bindings / 45 observations，0 episodes / 0 codes；34表旧行集完整内容hash不变 |
| 原库及正式副本两代结果 | PASS；均fixture_only=false，各两代126 COMPLETE；每代402,246 source / 252 resolved / 401,994 quarantine |
| finite45工程收尾 | CLOSED；原进口事务P1已关闭，当前执行没有新工程finding |
| 全历史证据及数据质量 | BLOCKED；402,060 findings；不能把有限事实批准扩大为全历史身份、日历、alias或NULL政策批准 |
| Phase1C.2生产运行 | CLOSED；证据、精确预算、生产执行路径及具体运行授权仍需匹配准入 |

**正式应用与重建已独立复核。** 通过项目managed shared/read-only锁读取原库、正式隔离库和0400备份。对原库34表排除本次明确许可的新增记录后，完整有序旧行集hash与应用前基线相同。新identity为3 episodes / 18 codes / 24 bindings / 252 observations；新Context1、generations2、audits2。旧Context2、generations4、audits4及旧批准时间均保留。

独立验证181个immutable raw，从raw重新转换原库第一代全部126输出；原207行的完整value、identity、NULL均不变，新增恰好批准的45条精确raw UUID/ordinal/date观察，adj_factor/daily_basic/stk_limit各15条。其余三代使用这组已经独立重建的值重新序列化，逐项核对物理Parquet、lineage、SQL注册、quarantine及COMPLETE manifest。四时区重新打开managed连接，并对27个受增量影响的输出重新从raw转换，结果一致；两个旧Context完整payload保持不变。

完整402,246行处置账本与重建结果逐行匹配，无重复或漏行；42个未证明endpoint aliases、15个daily mirrors继续quarantine。dv_ratio/dv_ttm/pre_close的raw NULL各3条均保留，typed字段没有补值。strict133为VALID / EXACT，133 checked、0 failures，原receipt evidence hash保持不变。本Review没有重新采集133请求、注册Context、导入事实或创建新generation/audit。

**402,060不是402,060个工程bug。** 两个原库及两个正式隔离库audit全部finding payload按finding_key排序重新计算，完整hash均为 `0cf91e72740f90e7a325b79d327c31907ef183d8b43de5a11ee04a77e3aae19d`，SQL详情与最终交付一致。实际规则组成如下：

| 当前规则 | 每代finding数 |
|---|---:|
| IDENTITY_NO_SCOPED_PROVIDER_BINDING | 401,994 |
| SESSION_NOT_CERTIFIED | 63 |
| MISSING_REFERENCE_PRICE | 3 |
| 合计 | 402,060 |

独立SQL完整旧新join确认402,147→402,060：移除90条（身份45、缺因子15、跨端点30），新增3条，净减少87。另有1,374个相同范围外事实的批准引用在新Context中重授权，原事实和旧审批来源保留；400,683个相同key/payload保持不变。这里的“移除”指新audit不再发出，旧audit和finding仍完整保留；未把所有历史findings标成独立关闭。

新增3条均为000022.SZ在2013-01-04、07、08的stk_limit原始pre_close=NULL，转换后仍为NULL；对应daily的pre_close分别为10.17、10.03、10.15。daily的值存在不授予跨端点替换权限。三个finding仍blocking、EVIDENCE_REQUIRED、无exception approval。这是有限身份被正确解析后显现的源数据/端点语义缺口，不撤销有限身份批准，也不重新打开进口事务修复。不得为了总数下降填NULL、关规则或借用daily值。causal仍certified0 / excluded_unknown60，不能将空eligible分母写成PASS。

**交付、历史文件和CI通过。** 独立核验632个manifest文件、6个external数据库、334条active引用，ZIP633成员的CRC、唯一名称和逐成员原始bytes。原171固定pins、8份审批、保留Prompt和上一轮Review副本准确一致。141,740个执行前受保护文件及136,598个更早历史文件保持原bytes；原库是唯一获准变化的旧数据库。备份hash等于应用前原库，mode0400且34表可读。当前材料/ZIP按凭据literal及base64/hex/URL表示扫描，252个压缩Parquet解码后再次扫描，0命中。

通过GitHub connector独立取得job及实际日志，确认最终checkout正是222cf66，locked dependencies和所有离线步骤成功，**753 passed / 4 warnings / 1042.11秒**。[最终SHA CI](https://github.com/liuyanfeier/AStockSystem/actions/runs/37265030423)。源码不变，复用上轮独立119个针对性回归及相同实现的753测试证明，没有重复运行全套测试；本轮原库/正式副本/备份和输出验收全部实际执行。

原库应用前hash：`27aabd6143d977decefefb8eb1f1b2b9e66ee29c14045d9df284871bcecf065f`；应用后及独立读取前后hash：`30953a9ff2622c85724794b268bc878ea2494684d6faccd5ab0fc5cbb378eb81`。正式副本hash：`594aec45ccf77828c72ec4350f9638b0ef7b9a38db2a18462bc447dd1a2d5ba8`。实际Context hash：`5bb73a54850e4328b8cfc0305185a77d001bf7841984bdd5e73ab2190898256c`。作者ZIP hash：`66e1076f56b5ccdfcff20d81b8ab11a37d4579c91e8640b57f23a23ae5410ba1`。

固定metadata store、原license、旧失败isolate、候选preview和旧证据均保全。metadata仍为1 consumed / 6 unattempted / 0 response / 0 civil rows，第一条TRANSPORT_UNKNOWN_NO_RESEND；远端delivery及账户权限UNKNOWN。本Review不许可retry、补发、reset或换store。Reviewer原库写入0、市场/provider/文献请求0；网络仅GitHub只读CI核验。

**进入Phase1C.2还需要三组具体成果，可合并为一次工作和一次集中Review。**

1. 计划范围的venue/calendar与历史identity/native证据。当前63 sessions未认证；普通历史386,249、BSE13,030、unknown1,224、special60、历史code/alias57仍隔离。按共享来源和成员集补证，不逐行审批；1,374已批准pre-BSE范围外继续原处置，不作为重新等待身份的缺口。现有63有限session不等于2013–2026全市场calendar分母。
2. 端点完整性与可用性边界。处理上述3条reference price语义以及各endpoint历史覆盖、cap/分页、unexplained empty、特殊资产/alias的实际缺证；本轮没有批准全历史NULL政策。用完整成员表说明覆盖或明确提出范围变更供Review，不自行缩到3发行主体后宣称原全量目标完成。
3. 匹配证据的生产运行准备、完整plan/API预算和用户具体授权。已有30,126合成membership/恢复证明继续有效，但其[admission_offline.py](/Users/yanliu/Documents/AStockSystem/src/astock/data/admission_offline.py:70)只接收FakeTransport，旧[fetch_slice](/Users/yanliu/Documents/AStockSystem/src/astock/data/tushare_client.py:97)仍锁定133范围。这不是本次工程bug；它明确说明未来真实全量入口尚不能靠换日期/换license启动，需要独立版本的必要适配和离线验收。既有合成规模不证明账户权限、全历史真实IO或吞吐。

准入不能要求尚未采集的全历史raw完整性、年度真实重建及最终coverage/causal先完成；这些属于实际回填之后的验收。但拟执行范围的前置证据、安全生产入口、具体预算与许可仍须闭合。工程CLOSED和全历史数据BLOCKED可以同时成立。

下一批使用[联合补证与Phase1C.2运行准备Prompt](/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Codex_Phase1C1_Evidence_Closure_And_Phase1C2_Launch_Preparation_Prompt.md)。一次处理共享证据、必要新运行适配及具体取证/启动方案；不再重复finite45部署、旧审批模板、同输入两代重建或旧压力测试。外部事实无法取得时，一次交准确取证申请及其他已完成部分，不继续以相同BLOCKED结果制造新修复批次。该Prompt必须由用户明确转交后执行；本Review不直接开放Phase1C.2。

独立可复核结果位于 `outputs/private/phase1c1-finite45-formal-independent-review/`：artifact/data/isolated-DQ/exact-SHA CI四份JSON，配套三个只读核验脚本、工程收尾裁定、审查manifest和handoff。没有复制原数据库、raw或凭据。
