# 代码迁移与删除清单

2026-10-11；依据实际源码、导入、动态 adapter、CLI、配置 pin 与回归。
本批不删除源码、配置或回归测试，不添加替代业务框架。
DEPRECATE 表示退出新业务默认入口；现有历史命令并未被代码禁用。
MIGRATE/后续 DELETE 是带验收条件的计划，不表示迁移已完成。

| 路径/能力 | 分类 | 实际用途与依据 | 下一步/退出条件 |
|---|---|---|---|
| paths.py、settings.py、cli/main.py、uv.lock、pyproject.toml | KEEP | 诊断、秘密类型、路径、依赖与实际入口；doctor/tests 使用 | 保留；Research 子入口拆分后再评估 CLI 历史部分 |
| data/availability.py、identity.py、provider_identity.py | REUSE | 知识时间、来源域身份、官方码/原生表示；有时点回归 | 新 adapter 遵循相同语义；有限身份不能放大全市场 |
| data/contracts.py、curation.py | REUSE | v1/v2 契约、单位、空表类型与配置摘要；不是空占位 | Research adapter 复用验证；新版契约独立版本，不改旧 bytes |
| data/warehouse_lock.py、raw_validation.py | REUSE | 锁前连接、读写权限、物理 raw/sidecar 证明 | 新 store 复用，保留竞争/kill/fork/攻击回归 |
| data/raw_writer.py、receipt_integrity.py | REUSE | 不可变发布、回执/谱系；也耦合旧 schema/请求 | 只复用适合新 store 的原语；旧 migrate/写入路径不自动调用 |
| data/tushare_client.py | REUSE | 实际 HTTPS/端点/重定向/秘密保护，不是 SDK 占位 | 新采集边界另实现持久预算/停止策略；不自动继承旧重试行为或许可 |
| data/slice_errors.py、audit.py、transport_diagnostics.py | KEEP | 安全错误、MOCK/RequestParams、脱敏观测被旧/新数据工具导入 | 不把旧 MOCK/传输探针当业务采集器；按依赖逐步提取 |
| data/probe.py、probe_review.py、probe_audit.py | DEPRECATE | 固定 Phase1B 探测/审查；真实历史仍需可读验证 | 不用于新增研究采集；迁移活跃调用后删除旧生产入口，必要审计留存 |
| data/slice_plan.py、slice_capture.py | DEPRECATE | 固定133/21日演练与消费生命周期，有回归/历史账本 | 不重跑；Research ingestion 替代后移除新增采集路径，保留消费读取 |
| data/slice_curate.py、slice_dq.py、bootstrap.py | MIGRATE | 实际类型化清洗、因果审计、有限身份，非通用 universe 服务 | 提取通用单位/校验；验证旧源→新观察查询；不制造全市场身份/日历 |
| data/receipt_schema.py、receipt_migration.py | KEEP | schema007 检验与显式迁移仍被旧回执/回归依赖 | 历史读取兼容；新 Research schema 不走旧部署 |
| data/reconstruction.py、reconstruction_dq.py、admission_delta.py | MIGRATE | R2 Context、审批绑定、事务合并、generation 与 DQ 的真实现 | 新用途复用事务/来源/时间原则；独立验证再退出旧业务写入，保留读回 |
| data/acquisition_proposal.py、admission_metadata.py、admission_offline.py、admission_rehearsal.py | DEPRECATE | 特定旧审批/合成候选演练工作流，仍被其他代码/测试导入 | 不作为研究前置流程；移出活跃消费者后删重复工作流，回归保留有意义部分 |
| data/admission_metadata_live.py、full_backfill_v1.py、capture_continuation_v3.py | DEPRECATE | 精确七请求/全量方案/停止库延续；新 Phase1 引用工具函数和历史读取 | 没有新调用许可；迁出通用辅助函数与消费读取，再删除旧 live 入口 |
| data/__init__.py | KEEP | 包初始化，只有 docstring；不是业务功能 | 保留包本身，不据此宣称已有功能 |
| phase1/contracts.py、domains.py、core.py | REUSE | 解码、知识/有效时间、复权、规则、原生身份和 hash | adapter 复用；既有源码/设计 pin 不被随手改写 |
| phase1/pipeline.py、interpretation.py、evidence.py、fact_admission.py | MIGRATE | 来源重推导、批准绑定、事实/质量/谱系/原子 generation、真实来源校验 | Research Store 另设用途/读接口；不能直接把真实 fact build 当普通导入 |
| phase1/acquisition.py、authorization.py、legacy.py | MIGRATE | durable 授权/消费、请求停止、原三库只读保护 | Research ingestion 按当次许可复用原则/原语；旧消费 adapter 持续保留 |
| phase1/planning.py、application.py、coverage_targets.py、__main__.py | DEPRECATE | 全域目标、全历史请求/申请与旧CLI；不是业务筛选 | 不执行全历史计划；覆盖衡量转为具体报告用途，迁移后删除旧业务入口 |
| phase1/versions.py、__init__.py | KEEP | 来源版本判定、原始 pin 与动态 decoder 依赖 | 保留历史版本只读验证，不能冒充新 V2 来源 |
| phase1/fixtures.py、production_fixture.py | KEEP | 真实路径的闭合合成/生产形状演练；有攻击与兼容回归 | 只用于测试，不作真实批准 |
| compat/phase1/v1、v2-5672（38个文件，388,476逻辑字节） | KEEP | versions.adapters 动态加载契约/domains；两份 design 重复但有 hash 依赖 | 冻结解码资产；全部来源独立新 decoder 等价验证或封存恢复后才退出 |
| features、regime、sectors、screening、catalysts、portfolio、backtest、reports 八包 | NEEDS_VERIFICATION | 当前只含 Reserved docstring；paths.REQUIRED_DIRECTORIES 与 doctor 要求这些目录 | 在已有包实现业务；不通过删目录/改检查伪装清理。完成能力后变 KEEP |
| config/regime.yaml、risk.yaml、universe.yaml、data_sources.yaml | NEEDS_VERIFICATION | disabled/null 的配置骨架，test_config 明确验证；无运行时策略解析器 | 新功能引入版本加载器，保留未知语义；风险参数待用户批准 |
| config/contracts、curation、dq、slices、probes、full_backfill_v1、phase1 | KEEP / DEPRECATE | 契约/DQ/冻结版本保留；固定演练配置退出新业务。存在运行/配置/历史 hash 依赖 | 新配置另版本；旧 replay 参数不扩大许可，不能仅按旧命名删除 |
| tests/test_*.py、warehouse_worker.py、fixtures | KEEP | 全套1005项基线，时间/事务/回执/源版本/进程保护等真实回归 | 不删重要断言、不skip；迁移后修改消费者与等价验证，淘汰仅确证无价值的重复测试 |
| 本批可证明无依赖的源码 | DELETE：0 | 空包仍为 doctor 所需；旧 live 代码仍有导入/CLI/历史源依赖 | 不做主观批量删除；文件名扫描不是删除证据 |

## 主动删除的后续责任

Research V1 首批建立单一 query/import/report 路径和明确 consumers 清单。
迁移完成的旧生产分支应在同批或紧随的迁移提交删除，不接受“新实现可用但旧实现永久仍活跃”。
验收须覆盖相同合法输入、拒绝/缺失/冲突、单位/时间、来源读回、故障/回滚及恢复。

历史 decoder、真实消费账本与必要回归属于来源兼容资产，不是第二套活跃研究系统。
若某旧文件同时含通用 helper 和过期 live 入口，先迁出依赖并验证，不能删除 helper 破坏旧证据读取。
本批没有替换任何数据业务实现，所以没有以“已替换”名义删除未经迁移验证的代码。


## Research V1 实际迁移（2026-10-12）

- REUSE：warehouse_connection/lock、RecordTimes、严格JSON/原字节hash、旧raw侧证据验证、
  统一物理来源/冻结decoder验证；不改变旧原库、pins、消费和真实执行事实。
- MIGRATE完成：原features/regime/screening/reports空包已添加实际观察模块；所有Research
  market/screen/report共用research.service；没有另保留一套被替代业务实现。
- KEEP：历史decoder/审批/审计、已有重要回归。CLI菜单测试随新research入口更新允许集合，
  doctor/秘密保护测试不删不弱化。旧真实采集入口未用于Research，不在本批主观删除。
- 新增人工journal为持仓/退出/复盘的最小记录基础；后续业务迁移仍需验证时点/输出/故障与恢复。

旧171源码pin基线的主CLI及菜单测试随业务入口改变，其余169项同字节；
原CLI/test字节从a00c7dd可恢复，未改历史pin清单/审查。实际来源运行23pins与V1/V2兼容archive
仍原字节，不把历史整体源码基线当新功能禁止修改代码的Gate。


## Research V1.1实际变更

| 能力 | 分类 | 本批验证/边界 |
|---|---|---|
| data.raw_writer.atomic_new_file | REUSE | 新publication薄包装，完整临时字节校验、fsync、无覆盖发布；冻结旧文件不改 |
| Raw/报告直接最终open(xb) | DELETE（代码分支） | 被上述路径完全替换；写入失败、kill、报告双文件恢复及旧SQL回滚回归验证，无两套发布路径 |
| raw_validation.strict_json / full_backfill_v1.secret_present | REUSE | 仅纯解码/秘密检查；不调用旧采集/审批/原SQL路径，旧pins不改 |
| 旧48请求提案 | MIGRATE | 新研究独立39成员合同/日期/预算，旧版保存在Git；未执行两版提案，不沿用旧许可证 |
| inputs/store/service/journal/features/screening/reports | KEEP + 扩展 | json原响应、来源等级、状态合并、证据/DB键核验、原始逻辑及待核实；单一分析路径 |
| phase1/compat及重要回归 | KEEP | 来源读取/冻结兼容仍被依赖；不作批量删除，不以新研究验收改写旧事实 |

没有新增服务、依赖、Curated副本、日常核验旁路或缓存框架。100股128日完整分析约5秒，
未发现需要牺牲来源核验的瓶颈。新增纯研究合同仅用于当次CURRENT_OBSERVATION，不替代
历史Phase1解码事实，也不修改既有历史消费账本。
## Research V1.1 P1补充

KEEP：五表Research Store、原JSON响应adapter、原子发布、人工日志与旧重要回归。
REUSE：strict_json、CapturePlan、hash/时间和保留来源原语；增加小型evidence语义核验模块。
DELETE：records直接复制manifest自报LOCAL_CAPTURE_BOUND等级的旧授予行为，替换为统一链验证。
MIGRATE：外部capture路径读取与Store保留hash路径均输入同一核验函数；无schema升级、旧库改写或第二套业务计算。
NEEDS_VERIFICATION：Level B真实39采集与最新20/60观察报告、数千证券遍历优化；本批不执行或提前宣称通过。

## Research Level B真实试点

| 能力 | 分类 | 迁移和验证 |
|---|---|---|
| 原Store/service/features/regime/screen/report/journal | KEEP | 真实默认20/60及250项Raw抽查、保留Raw重建，不建立平行选股实现 |
| TLS与原子发布/秘密/来源链原语 | REUSE | 可选已授权继续及失败Raw保留，失败不得成为COMPLETE证据 |
| 固定拒绝detail/count、默认gzip协商、只读单capture bundle | MIGRATE | 类型受控metadata/显式identity/同范围互不重复成功来源组合，旧分支直接替换，无schema迁移 |
| 旧批准无continue_on_error | KEEP | 默认首错停兼容；可选bool必须合法绑定实际授权 |
| 根据自报count认定完整、原异常文本记录、失败Raw升格 | DEPRECATE / 禁止 | 实际日期/行/日历、固定安全错误类别、完整合法COMPLETE链分别验证 |
| 全市场遍历成本/行业催化/实际持仓复盘 | NEEDS_VERIFICATION | 本批10股实测不等于数千股或完整业务验证；下一批按研究价值推进 |

本批不删除历史数据处理代码/重要回归，不改旧消费账本；无新依赖或风险参数生效。


## Research V2实际迁移（2026-10-13）

| 能力 | 处理 | 验证与边界 |
|---|---|---|
| 五表Research Store、features/screen/service、观察卡/私有日志 | REUSE | 同一业务路径，旧指标/候选不变，不新增并行平台 |
| V1输入/计划/响应与本地采集证据 | KEEP | 旧dump/hash按旧协议，真实保留来源仍可验证，不重写旧消费 |
| 市场池/行业输入、批量请求 | MIGRATE | 显式V2扩展，CURRENT池三分区来源闭合；旧逐股模式仍用于读取原试点，不再是全市场默认 |
| 逐股重复扫描全部行情 | DELETE（实现分支替换） | service一次分组，features共享；旧无索引扫描调用已移除，测试覆盖数值/缺口 |
| 每次同对象全Raw推导 | MIGRATE | 有界同版本缓存；每次Raw hash/SQL检查，冷启动/as-of改变重推导；不关闭保护 |
| 补丁覆盖同日来源、自动last-wins | 不引入 | 新bundle追加；冲突显式选择，旧报告复现；因子不同vintage披露 |
| 完整私有报告→GPT不可见 | MIGRATE | public_results白名单输出Git业务报告，个人日志/Raw/许可仍私有 |
| 历史Phase1与冻结compat | KEEP / DEPRECATE | 本批不重构，不删除真实来源/回归，不借此开启全历史采集 |

## PR #4后最小修复（2026-10-13）

| 范围 | 状态 | 实际迁移 |
|---|---|---|
| Research V2/Store/radar | KEEP | 采用已接受PR #4；不新建框架/schema |
| acquisition故障路径 | MIGRATE | 数字HTTP安全分类、认证/限流立即停、三次HTTP/传输熔断；原消费/保护保留 |
| public_results | MIGRATE | RESEARCH_PUBLIC_V2_1，移除人工观察/Journal，来源白名单与固定描述；旧私有报告不改 |
| 旧报告/原106消费 | KEEP | 历史输出保留；新公开投影追加，不改真实执行事实 |

## PR #5收尾与首次真实全市场尝试（2026-10-13）

| 范围 | 状态 | 实际迁移 |
|---|---|---|
| 旧进程死亡回归的多线程fork | MIGRATE | 仅测试改为新Python解释器；保留os._exit、durable claim、无call/回执和拒绝重发断言；生产实现hash不变 |
| Research Store/radar/响应合同/安全保护 | KEEP | 无HTTP响应，无法据此确认合同或权限错误，不修改生产实现 |
| 原106消费/新增UNKNOWN/保护历史文件 | KEEP | 追加独立失败事实与公开停采投影；不覆盖、删除或重置 |

## 002实际行业雷达后的最小兼容修复

| 范围 | 处置 | 验证与迁移边界 |
|---|---|---|
| research/tushare.make_capture_bundle、cli capture-import | REUSE/MIGRATE | 可选已验证benchmark_bundle，仅缺少的指数身份；不新建Store或采集平台 |
| research/evidence.capture_grade | KEEP/MIGRATE | V1指数身份进入V2可不绑定旧股票队列；用途/窗口/基准/日历/完整4证据不放松；股票来源不能借此跨池 |
| tests/test_research_benchmark_reuse.py | KEEP | 8回归覆盖合法补缺、旧文件不改、缺回执/错误窗口基准日历/旧股票越界/用户声明身份拒绝和V1兼容 |

所有真实采集在修复前D8实现完成；离线新版13a0110b…不承接已消费许可。旧失败、Raw、Store及历史代码没有删除/覆盖。

本批Research V3：新增`company/`为KEEP（轻量证据/公司卡/条件化草案），ResearchStore、features/screen、
publication与Journal为REUSE，全部只读复用既有真实窗口。原V2实现与回归未替换或删除；没有双轨价格/行业计算、
新DB或旧数据迁移。`catalysts/`原为空命名骨架，本批实际催化研究统一在company层，不能将空骨架称已实现。
## Decision Loop V0

新增decision层复用Journal五表、features/radar和compose；没有替换旧采集/历史解码或新建行情实现。
LinkedResearchStore只读链接组件，后续日更不复制旧窗口。portfolio/backtest旧目录仍为空占位，
本批小型组合观察和合成实验位于decision，不宣称完整组合/回测系统完成；未来迁移保持单一生产实现。

## 日常任务 M1 首段（2026-10-15）

|能力|处置|实际结果与边界|
|---|---|---|
|daily/decision-close内联编排|MIGRATE完成|统一调用decision.application.run_close；旧命令只保留参数适配，原重复编排已移除|
|公开行情JSON作为内部接口|DELETE该依赖|原生MarketSnapshot V1来自同一analyze计算；市场分析可明确排除私人Journal|
|来源向量压缩|REUSE/提取|features.lineage纯函数供原生快照与公开投影共用，原数值/来源向量等价|
|PositionScope|MOVE|唯一实现迁入portfolio.models；decision.models兼容导入，不保留两份类型|
|Journal/独立五表工作容器|REUSE/扩展|增加类型化INPUT/ACCOUNT、批量事务和更正链约束；原来源库/schema/旧行不改写|
|portfolio包|部分落地|新增人工事实/范围服务；组合估值仍复用decision.portfolio，不宣称完整风险引擎|
|旧公开基线复现|MIGRATE|必须精确原锚点+全部业务字段等价；分开旧/当前执行Hash，不跳过数值或来源验证|
|中文录入CLI|新增薄适配|所有写入由portfolio.manual负责；已阅/持仓/成交与下一次报告接续，无第二套日志实现|

完整合成来源到录入/下份日报及旧真实来源均已读回，故障回滚/幂等/晚录/隐私/模式测试保留。
未删除历史decoder、消费读取或旧采集代码，没有新增依赖；通用计划、策略与PAPER继续按路线演进。

## M1计划、待办与恢复（2026-10-15）

- 复用Journal事件/受管事务：新增RESEARCH_INPUT类型，记录计划创建/重开、结束及明确复核；唯一解析服务供问答与日报使用，不改冻结run/旧行或源库schema。
- 复用原ResearchPlan/ReviewAction/compare：先解析当前计划与明确动作，再进入原判断路径；将上次未决判断在组合计算前接续，persist不重复接续。没有第二套研究/组合计算。
- 提取旧精确市场锚点核验函数，供基线复算和计划引用共用；计划引用不冒充新行情验收。
- 新增小型纯待办投影及不可覆盖运行回执：两份小JSON/尝试，无新数据库、服务、缓存框架或依赖。恢复复用同一run_close及原子发布，不迁移旧消费状态。
- 保留现有故障/时点/隐私/锁回归；新增完整原生计划结束/重开、部分持久化/发布恢复和输入变化拒绝。跨基线迁移及新公司来源接入尚未实现，不将同一基线的20对象上限称作长期无限管理。

## M2同一规则与执行内核（2026-10-15）

- REUSE/提取：连续交易窗口及调整价共享`features.market`纯函数；新三组规则使用同一价格口径，旧原生市场/基线数值继续复现。
- 新增版本化`StrategyFrame`与单一`evaluate_strategy`；日常简报、独立形态扫描及三组实验都调用该函数，不各写一套入选公式。
- REPLACE：旧`decision.paper.simulate`的执行循环已移除，改为`backtest.execution.run_execution`的薄适配；旧协议/10项回归保留。新三组共用该内核的现金、次日开盘、退出待成交、估值和费用计算，不长期维护两条执行逻辑。
- 保留来源Store、compose/独立Journal、冻结解码和原始消费；无schema升级、依赖新增或真实采集。缺少公司/账户不阻止独立形态扫描；未知价格/交易状态不赋予成交资格。
- 尚未迁出所有旧Phase1活跃工具或完成真实PAPER准入；合成迁移通过不等于完整历史执行规则验证。

## M3已核验输入共享（2026-10-15）

- REUSE：Store.snapshot/Raw重建/SQL等价/as-of、compose与精确旧锚点保持原实现。没有扩大缓存或迁移原库。
- REPLACE：市场上下文和旧基线核验中为提取行业成员而重复snapshot/compose的调用已移除，成员从该次完整analyze使用的已核验输入提取。
- REFACTOR：三组观察计算提取为同一函数；独立扫描先读取来源，日报则在当前市场计算末尾消费同一输入。旧“日报再独立扫描一遍Store”的调用已移除，没有平行选股公式。
- 验证：24项相关反例与原生六次闭环通过，真实前后完整业务等价；普通运行69.390秒、同采样降49.6%。代码和测量边界见[当前Review](REVIEW.md)。
