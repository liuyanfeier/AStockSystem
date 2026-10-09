# Codex：Phase1C.2 修复 + 精确28真实日历采集 + 统一交付

在 /Users/yanliu/Documents/AStockSystem 执行本批。一次完成修复、必要验证、绑定许可、原 capture store 追加升级、精确28真实日历采集、结果与保全审计，最后集中交付 independent REVIEW。内部步骤满足条件即可连续执行，不在修复后单独交一次“readiness”。

本 Prompt 更新上一份“只修复并等待 Review”的执行安排。Phase1C.1 工程关闭、Phase1C.2 已开始；研究准入缺口保持真实。将本 Prompt 交给 Codex 并明确要求执行，即授权下述完整精确范围，包括最多28次新的日历数据请求和限定 capture store 追加写入。保存你实际收到的用户指令；当前审查方只生成批准条件/Prompt，没有运行任何真实请求。

## 输入与独立条件批准

- 基线 Git SHA：`d3b505869cc28d1140c0b9c08863ce3cb8a39853`
- 已独立验证的补丁：/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/Phase1C2_Call_Entry_Clock_Guard.patch
- 新回归范例：/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/work/test_phase1c2_claim_clock_boundary.py
- 之前 Review：/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-09_Phase1C2_Startup_Independent_Review.md
- **独立有条件批准**：/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c2-combined-authorization/independent-conditional-exact28-decision.json
  - 字节 SHA256：`2032a74d629ff398b3ff49df7974697a9722a37281d21fd4033d1362d0e4aa2a`
- **已审查的修复后精确 application**：/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c2-combined-authorization/expected-exact28-application-after-reviewed-patch.json
  - 文件字节 SHA256：`cb036c423ba8d9611b7155626ebbe2c333c47ba93ef305b1cc1b6de4b950636b`
  - canonical application hash：`7496aec07fc7ff26bf5eb67204f574eea2ec472a38e417ab6bfb50db91bb257a`
- 原批次目录：data/private/phase1c2-startup/2026-10-08-v1/
- 原 baseline：上述目录 continuation-baseline.json，canonical hash `b5f18ff30f97012db03fc29304fcf13052cfa12ceabe79cf43d1d88bce0a65b1`。
- 原 capture DB：data/private/full-backfill-v1/capture.duckdb，升级前 SHA256 `b96fb71660643aeb07359c65b49afdb721acdfcc5a71d648149a6463e6c21625`。
- 原库、旧 metadata、171 pins、146,656历史文件：按原 preservation-baseline.json 验证；精确限定 capture DB 是本次被批准改变的例外，其旧六表行集、旧 objects 与旧消费历史保持不变。

独立批准针对**已经测试的确切源码字节及现有28成员**，没有提前宣称未知未来 Git SHA 整体通过。批准由当前独立审查方生成；执行方只核验条件并绑定实际 SHA，不得自己模拟新的 independent Review。全部条件成立即可激活并执行，无需另一次中间 Review；条件不成立，实际调用保持0，完成独立工作后提交 blocker。

## 1. 修复、测试和冻结执行 SHA

应用提供补丁。仅在 enter() 事务内、CALL_ENTERED 插入前增加：

```python
if old.instant(at)<old.instant(claimed):
    raise Error('CALL_BEFORE_DURABLE_CLAIM')
```

修复后 capture_continuation_v3.py 的 SHA256 必须恰为：
`59a68cc35f8da10c0d2bea048e5e60fda22896ceada8ed1ad2fe41e1ed60ad0b`。

不格式化整个模块、不改 DDL、DESIGN、legacy runner、diagnostics、依赖锁或 workflow。这次独立批准只覆盖该两行变化。把新时钟回拨用例整合到已有 tests/test_capture_continuation_v3.py：post-CLAIMED 回拨1秒，HTTP0，仅 CLAIMED、attempt1、receipt0、重开 audit 通过、同成员/后续成员停止、旧六表不变。保持原42项；本批应为43项。如测试失败或需要其他运行时代码变化，不继续真实请求。

原有8个 runtime/design/config/DDL pins，只有这份 SOURCE pin改变，其余须与条件批准中一致。与基线比较全部运行时代码、配置、依赖、SQL、CI变更，不允许借同一批加入其他可执行变动。测试与脱敏说明、最新范围说明允许更新；原 AGENTS startup 的0数据API约束被本批直接用户执行指令和精确条件批准仅在下述28范围覆盖。

完整本地测试、doctor 和现有离线检查各跑一次；新增回归预计令全套由915变916，按真实结果记录。完成源码/测试/脱敏批次说明提交和推送，锁定执行 SHA S、Git干净；等待并读取**S本身**成功的 CI job/log、checkout SHA 和测试结果。不得用基线915通过替代S的CI，也不预填未来SHA。当前warn只如实保留，不扩大为无关重构。

## 2. 一个新副本的完整28 mock

在新私有版本目录中，通过既有共享锁管理器只读核对原库、metadata与未升级的原 capture DB，保存升级前原 capture DB 的受控快照以及旧六表完整有序行集。原始/171/旧候选/旧 ZIP 不变。

以原 capture DB 的新副本执行 upgrade_copy 和全部28 closed MockTransport请求；使用当前真实时间链的 FIXTURE 许可，只写该副本。禁止复用旧已消费 mock DB 或把副本回写 production。

验收必须包括：旧六表与 baseline完全一致，新28 attempts/84 events/28 receipts，全部 final五文件/receipt物理核验、关闭重开复验、fixture_only=true、research=false。任一失败保留失败版本，不继续生产升级或请求。

从真实原始消费记录生成 PROPOSED application，并与输入的已审查 expected application 按完整内容/canonical hash匹配；保持：

- 28个 member_id、request descriptors、origin_plan、object_id、执行顺序、destination、依赖和raw-only语义全部一致。
- membership hash：`15cbff858f3f5fbbd6873ef6149346902cd4d2f13e76c2f54d62b648e01902f5`。
- 初始 consumption hash：`d1fba2dde1b71f02c67f71b9597fb11629853cc6e8320e2508bd850d591f6314`。
- canonical application hash：`7496aec07fc7ff26bf5eb67204f574eea2ec472a38e417ab6bfb50db91bb257a`。

保持原 baseline、原 protected manifest 引用，不改 schema、字段、namespace 或 execution_license 字段来追求新的hash。application 本身保持现有 PROPOSED/execution_license=false；生产许可通过单独 review/human 绑定表达，这是现有协议要求。

## 3. 自动激活许可，不再单独等待 Review

只有下面全部通过，才把当前独立条件批准绑定到真实生产 review/human：

1. 上述精确源码/8 pins/基线运行时代码范围匹配。
2. S提交、干净工作区、S精确CI与本地回归通过。
3. 新副本28 mock及physical reopen通过。
4. 完整 application、baseline、旧六表、原物理 capture DB hash、旧消费和历史保全精确匹配。
5. 保存实际直接用户执行此完整 Prompt 的指令、真实时间、Prompt/独立条件批准哈希，绑定精确application。不得复制旧 startup 的 data_API_budget0 或 fixture 人类许可当新授权。
6. 新 activation proof 逐条列证据路径/hash，记录此审查方条件决定、实际SHA S和application hash。

如果缺少实际用户执行本完整 Prompt 的指令，保持未激活，不虚构人类来源；直接用户指令已明确授权时，继续，不再重复询问。

使用现有 v3 review/human 严格字段，不放宽 authorize()。review以 PRODUCTION许可 namespace、实际S、exact application/baseline/membership/pins/destination/budget、execution_license=true组成；review_ref指向本独立条件批准的SHA256/位置，reviewed_at使用条件决定中的真实时间，不伪造新的审查时间或审查人。

human_evidence必须是真实 DIRECT_USER/ACTUAL_USER_INSTRUCTION、scope EXACT_CONTINUATION_EXECUTION、application_hash正确的实际用户记录，保存完整原指令与真实来源。human.review_hash准确匹配；instruction_ref准确匹配该证据path/hash；授权时间遵从真实用户指令及批准生效时间链，不回填或虚构。明确记录这是按已独立核验条件激活，**不是作者 self-review PASS**。旧所有许可保留，不复用或覆盖。

激活文件保存在新私有目录。许可全范围仅为这一28成员一次尝试和指定原 capture store 的追加升级/对象写入，不包含任何研究准入。

## 4. 连续生产升级与真实精确28

使用 existing upgrade_production(...,live=True) 对**固定规范根目录**原 capture DB追加5张v3表和冻结baseline。旧6张表完整行集保持不变，已有objects不变，不删除旧记录，不新建旧成员或改origin。不得用mock副本替换原DB、绕过owner/lock/source/consumption检查。

随后使用 existing capture_production(...,live=True) 顺序执行已签的28成员。真实token仅从既有安全配置读取成SecretStr，不打印token、请求体或异常repr。不要新增HTTP实现，不用fixture transport，不重写runner；私有编排只调用现有受限函数。

每成员 max_attempts=1，总数据 API budget<=28，开始间隔>=1.25秒，retry/redirect=0；保持execution SHA S不变、工作区干净，整个调用期间不提交或修改tracked文件。每次调用必须通过现有全局消费、保护历史和匹配许可检查。

任何新成员出现FAILED/UNCERTAIN、孤立CLAIMED、时间异常、文件/回执不一致或进程中断，立即停止后续真实成员，保留已消耗attempt和原始证据。不得退款、重置、补发或换license重试，也不得为了“28完成”制造mock补齐。完成结果核验和统一交付即可，部分停止也是一个真实、可审查的结果。

原 SSE2012 UNKNOWN、已消费/重叠 SZSE2013不得重发，BSE6保持HOLD。不得重跑133；不执行market6、metadata6或全量回填，不新增文献GET/连接诊断，不写原warehouse/旧metadata/Context/DQ。

## 5. 结果、保全与一次交付

完成/停止后，关闭重开托管production DB，audit及逐个实际有效receipt physical_validate。导出旧六表完整不变证明、新attempt/event/receipt行集、每成员终态、原生body/source/typed/manifest/sidecar与SHA/source lineage、实际尝试数/未执行数、升级前后物理hash以及permit/application/实际用户绑定。

旧capture DB本次获得限定变更，报告应明确“原capture DB按许可追加升级/消费”，不能再声称整个旧DB字节不变。保护文件只允许该DB批准变更；所有其他146,656历史集合中的文件、171pins、原warehouse/旧metadata及旧objects继续按原hash核对。保留升级前快照，不把已发生的新消费回滚到快照；研究admitted=false、leading previous/session身份缺口如实保留。

发布结论区分：
- F1修复与条件批准激活；
- 真实raw采集的尝试/有效回执/未执行/停止原因；
- 日历窗口完整性与跨窗pretrade检查；
- leading/session/identity/research仍未获认证。RAW_ONLY采集不要求DQ402,060先清零。

一次完成暂存/凭据扫描，包含DB行集、Parquet解码值及ZIP；真实.env、token、原DB、行情对象/私有授权材料不提交Git。保留全部旧包。

新目录建议：data/private/phase1c2-combined-fix-calendar28/2026-10-09-v1/（实际日期和新唯一版本）。
最终交付该目录中的：
- combined-review-report.md，最小diff、43回归/全套/S精确CI、activation proof；
- 独立条件批准原件、实际用户授权、匹配application/review/human、生产追加升级proof；
- actual-call ledger、final physical/readback proof、完整保全/安全审计；
- Review ZIP、manifest、delivery-index.json、final-handoff.json；
- 执行代码SHA S，最终Git状态干净。

为减少重复CI，在S提交前准备脱敏批次说明，执行后将完整结果放新private交付目录，可读Markdown直接供Review；此时最终代码SHA仍为S，S的完整CI已通过，不因生成私有报告再提交代码。若确需追加公开脱敏结果，则仅提交docs差异得到最终D，保留执行S与最终D的清楚关系并取得D CI；不要改运行时或追溯声称实际请求发生在D。

最终状态：
- 全部28真实请求达成有效回执：PHASE1C2_COMBINED_TIME_FIX_AND_CALENDAR28_REVIEW_READY。
- 部分真实采集停止或激活条件失败：同一统一报告明确BLOCKED/PARTIAL、已消费/未执行及原因；不隐去失败、不要求用户先审“修复完成”后再提交实际结果。

全部内部条件通过就连续完成1–5，最后一次交给独立Review。不要把上述自动条件变成额外的人类确认阶段。
