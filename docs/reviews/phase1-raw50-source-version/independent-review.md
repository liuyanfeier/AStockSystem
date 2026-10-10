# Phase1 Consolidated Independent Review

审查 SHA：`5672e8f8464b20e3437ab94bd3ef17cbb05f7bcf`。日期：2026-10-10。

**结论分为两条：固定 50 请求的 RAW 采集工程与方案独立审查通过；完整派生工程仍 CHANGES REQUIRED，剩 1 项 P1（F1 的源版本绑定）。** F2、F3、F4、F5 的本轮修复通过。不得把本结论写成整个 Phase1 完成，或整个派生数据已经通过准入。

本报告签发独立审核者的 **CAPTURE50_RAW_ONLY** 限定批准。真实运行仍需要用户直接授权，其范围应与配套 Prompt 一致；本次 Review 没有发出真实 API、没有创建实际生产数据或伪造人类许可。取得授权后无需先重做所有工程或逐接口询问：可以在上述固定 SHA 先采集，调用全部结束/首错停止后完成 F1 离线修复与一次合并交付。

## 剩余发现：F1-R — P1，转换版本还可由库内声明替换

位置：`src/astock/phase1/pipeline.py:123–140`、`:178–207`。

本批已正确重推导完整 facts/quality，拒绝上次 EPS、时间、源行、eligibility、增删事实的六类自洽变异。但选择哪一个已注册转换版本，仍依赖 generation/descriptor 内的 `transform_pins`。该值只与另一个库内声明比较，没有最终绑定到 immutable source 的实际 transform pins 或捕获源的已授权 plan pins。

独立离线复现使用真实导入入口创建 V2 证券 identifier 来源，source.json 明确保留当前 V2 pins，request metadata 明确该 identifier **仅用于 daily**。保持 source/body 文件和哈希不变，在审查者隔离 fixture 库内将 descriptor/generation 的转换声明改成已注册 V1，并按 V1 重算 facts/quality/lineage/content hash。结果：

- V2 原 facts 的 `payload.datasets=["daily"]` 被 V1 去掉，变成未限定数据集的 payload。
- `verify_generation_inputs`、`validate_lineage` 仍通过，lineage 返回 VALID。
- 公共 query 没有拒绝这一版本替换；本最小样本无 listing episode，未声称它已返回可用生产财报。

这是“重推导规则也必须来自固定源”的残留完整性问题，不是测试名称或文档差异。复现没有篡改原生产库，未发现现有真实数据被污染。

修复应将最终所选版本锚定到实际来源：CAPTURE 对应原 store 中经授权验证的 plan pins；DOCUMENT_FACT 对应不可变 source.json 的 transform pins/实际事实批准版本。无 transform 字段的真正 V1 证据只能由已验证的旧 store/注册信息识别，不能让任何 V2 输入任意退回 V1。若以后确实需要新转换，单独作为有来源、有批准的派生转换，不替换旧输入版本。对自洽重算版本/事实集合的上述攻击增加回归，保留真正 V1 正向兼容。

## 五项修复的验收

| 项目 | 独立结论 | 证据与限制 |
|---|---|---|
| F1 源推导 facts/quality | 原六类漏洞修复通过；F1-R 尚需修复 | 输入、源行、完整集合、quality 和旧代均重新验证；新版本替换攻击仍可绕过 |
| F2 跨码财务 | PASS | 四财务域、两公告版本、旧码/新码报告、跨 episode/冲突、知悉截断均经相关回归验证 |
| F3 独立生产来源重建 | PASS（闭合生产形状） | DERIVED_ONLY 分离来源性质与采集权限；A/B 一致、更正/幂等、原源只读；真实历史准入未获批准 |
| F4 实际授权留存 | PASS | 注册在 claim 前原子提交，actual approval/human/evidence/hash 绑定 attempt/event/source/receipt；缺失/变异及进程死亡回归通过 |
| F5 覆盖目标 | PASS（软件能力） | 公共入口生成有证据的日历/上市期望，整日/整证券缺行可见；vintage/状态/规则/行业和未知分母区分，实际历史覆盖仍不足 |

## 独立验证与保全

- GitHub 连接器直接获取最终 job/log，核实 checkout 精确 SHA；**991 passed、6 warnings、job success**，旧 c199 CI 没有替代最终 CI。
- 独立运行 75 个相关用例：首次 **74 passed / 1 failed / 424.33s**。唯一失败是我从审查工作目录启动时，某 CLI 测试依赖仓库 cwd，报 ROOT_STORE_NAMESPACE_CHANGED；在文档规定的 canonical 仓库 cwd 单独重跑同一用例，**1 passed / 9.23s**。这覆盖了 75 项用例，不冒称首次整批全绿，也不将我的启动目录问题归为新代码缺陷。
- 相关回归含完整 35 次 CLOSED production-shaped capture、授权中断、A/B rebuild、更正增量、四财务域跨码/PIT、六类派生变异、真实 V1 冻结兼容。所有本地测试写入审查者工作目录，真实 transport 被禁用。
- 独立核验 ZIP：715 个索引文件、CRC、唯一/精确成员集合、文件字节长度和 SHA256，打包的 public implementation 与实际 Git 工作树文件一致；包 SHA256：`8a9dea6bc6c957e8a12c2412f7f2c9927b63bbed538459775bf311e7470a015b`。
- 独立逐字节核验保护清单引用、146,656 历史文件条目、171 固定项；按原例外/去重规则实际检查146,825条路径。三原数据库 SHA256 均与冻结快照/上次 Review 一致，无 WAL。
- compat V1 的每项文件逐一与 Git `b350787...` 原版本字节比较，通过；不是仅信任作者 registry 的声明。
- 原库没有重新建立 SQL/锁连接，原行集计数引用冻结快照；独立字节相同证明内容未变。全保护校验与封包/计划检查约44s。原仓库在审查末尾仍干净。

## 为什么允许先 RAW 采集

F1-R 发生在派生 generation 的转换选择。固定采集入口不从可变派生 descriptor 选择转换：它按本次实际批准 plan pins 解码，保留完整 HTTP/body/source、typed/manifest/sidecar，并由实际持久授权链验证 receipt。当前采集路径、停止/消费和保存机制通过检查。

因此允许先获取原始证据，把派生使用继续封闭；无需让一个派生层漏洞重复阻止所有来源试点。并未豁免源合同、首错停、保全或凭据检查。新 production facts/identity/vintage/规则批准、旧 FAILED 日历采用、完整市场覆盖、研究/回测都不在本次 RAW 许可中。

## 限定独立批准

- 执行 SHA：`5672e8f8464b20e3437ab94bd3ef17cbb05f7bcf`，不得在真实调用期间修改运行文件/源码 pins。
- 固定根：`/Users/yanliu/Documents/AStockSystem`。
- 唯一新增采集目的地：`data/private/phase1-integrated-v1`，使用本批 V2 新 store；不部署到三个原数据库。
- 固定 plan hash：`97a590200cc276e6a6ec000c5248827e26d3a4d28de35a22aaaba4e78296bbdc`。
- 当前消费快照 hash：`82ae79d29f008d15c6bb5505aa168d23777f64d8b25b333d5fb7555d43b33720`。
- **最多 50 个请求，27 原未消费日历 → 17 来源试点 → 6 原保留行情**，成员、日期、fields、params、顺序、来源与本批申请完全一致；独立比较与上次50成员也完全一致。新 canonical catalog 在审查时不存在，计划 prior_consumption 为空。
- 每成员至多一次，间隔≥1.25s，retry/redirect=0，首次新错误停止所有剩余调用。未发送预算不得退款后改成员/日期/范围；已消费失败/未知不重发。
- 允许新目的地 V2 catalog、授权/attempt/event/receipt及完整响应文件追加；三个原库、旧133/已消费失败、历史文件、171项、原 metadata 和旧仓库写入0。
- 仅 RAW_ONLY；无生产 evidence import/build/增量/派生数据准入、旧FAILED采用、全量展开或研究/回测权限。诊断/文献/备用源HTTP不是这50请求的一部分，不得自行新增。
- 满足真实人类授权和平台权限、Git clean/固定pins/当前消费/全保护时方可执行。实际 token 仅从已有私有环境读取，不显示。审批文件将本报告 hash 作为实际 evidence 引用；复制到 root 内时必须字节一致。

## 同批完成后续离线修复

真实调用完成或首错停止后，冻结本次执行 SHA 的 **真实 V2 源版本**，再修复 F1-R。新代码必须能只读复核刚捕获的5672版本实际 plan/审批/源 bytes，不能因“版本不再等于当前 pins”使刚采集数据变孤立，也不能覆盖旧 pins。

新版目标、完整派生真值和生产形状测试在隔离目录进行。真实新 raw/store 只读检查，生产派生准入继续 false；F1修复/兼容、试点实情、剩余预算及覆盖计划一次交付后统一 Review。已授权范围不逐成员/函数询问。发生新失败时保留证据和消费，离线修复工作仍继续，未经新匹配批准不得恢复未发送 HTTP。

本次没有新增不相关 Gate。历史 Phase1C.1 工程 CLOSED、Phase1C.2 STARTED 保持；Phase1整体仍要真实覆盖、PIT/身份/状态/规则证据、第二来源及最终准入验收。

## 审查者证据

工作根：`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an`。

- `work/check_phase1_consolidated_artifacts.py`、`work/probe_phase1_transform_binding.py`。
- `outputs/private/phase1-consolidated-independent-review/artifact-check.json`。
- `outputs/private/phase1-consolidated-independent-review/transform-binding-probe.json`。
- `outputs/private/phase1-consolidated-independent-review/live-ci-verification.json`。
- 同目录的批准 JSON、固定候选 plan 和 test verification 是本次交接材料，不能与 TEST production-shaped 许可证混用。
