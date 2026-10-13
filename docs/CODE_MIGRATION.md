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
