# 合并执行：固定 RAW50 试点 + 源版本绑定修复

**人类授权生效规则：用户把本 Prompt 直接转交为执行指令时，授权以下具体动作。独立 Review 本身不是人类许可。** 这是一次连续批次，固定 SHA 完成真实试点，真实调用停止后完成已知源版本绑定修复，最后一次交付。不要先重新申请整个 Phase1 的开始资格，不逐接口、函数或文件等待确认。

## 1. 输入与准确范围

在 `/Users/yanliu/Documents/AStockSystem` 工作。阅读：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-10_Phase1_Consolidated_Independent_Review.md`
- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1-consolidated-independent-review/capture50-independent-approval.json`
- 同目录 `approved-candidate-plan.json`、`artifact-check.json`、`transform-binding-probe.json`、`test-verification.json`。
- 审查者复现：`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/work/probe_phase1_transform_binding.py`。
- 原交付：`data/private/phase1-consolidated-fix/2026-10-10-v2/` 的申请/消费/保护/索引；原路线图、当前 operations 与本报告。

最新直接用户转交授权覆盖本批 **最多50真实请求、只写新增目的地、随后离线F1修复/兼容/测试/commit/push/CI**，取代此前完成批次的0请求等待限制。Phase1C.1工程已CLOSED、Phase1C.2已STARTED；全Phase1研究准入仍BLOCKED。当前独立批准仅CAPTURE50_RAW_ONLY，不是完整派生工程PASS。

授权请求成员为原申请的27未消费日历 +17来源试点 +6原保留行情，固定成员/日期/params/fields/顺序/origin和预算。plan hash `97a590200cc276e6a6ec000c5248827e26d3a4d28de35a22aaaba4e78296bbdc`。全局消费快照 hash `82ae79d29f008d15c6bb5505aa168d23777f64d8b25b333d5fb7555d43b33720`。

原133、已消费FAILED/UNKNOWN/UNCERTAIN、SSE2013旧FAILED、SZSE2013未知及BSE HOLD 不重发/不改状态；不新增文献/诊断/备用源请求，不换日期或接口消耗剩余预算。首个新错误即停止所有剩余真实调用，不自动恢复。真实采集不包括生产fact adoption/build/increment、旧FAILED采用、全量展开、研究/回测。

## 2. 先执行已审查的固定 RAW50

真实运行 SHA 必须为 `5672e8f8464b20e3437ab94bd3ef17cbb05f7bcf`，Git clean、所有本次 pins 和CI匹配。不要修改源码/配置/运行文件，也不要先在 canonical 根做F1修复；不 reset 用户变化。若实际HEAD/消费不匹配，继续可独立离线工作并集中报告，不能擅自签新SHA许可。

唯一新目的地：`/Users/yanliu/Documents/AStockSystem/data/private/phase1-integrated-v1`，使用本次V2新catalog/授权/attempt/event/receipt与对象文件。三个原数据库、旧仓库34表/原capture11表、原metadata、所有旧raw/curated/批准事实/171项保持不变；原库SQL写入0。允许必要的现有托管锁与规定的读写保护，不写旧数据内容。

将审查报告、真实独立批准JSON、固定plan原字节复制到 root 内 ignored 的 `data/private/phase1-consolidated-fix/2026-10-10-v2/independent-review/`。批准JSON中 evidence 指向该处 `independent-review.md`；复制后的报告SHA256必须与批准JSON完全一致。不得改变审核者、approved_at、plan/root/pins/预算或审核正文来“通过校验”。这是真实审查者文件，不能用TEST_ONLY文件替代。

记录用户本次直接转交的实际文字/消息为人类授权证据，保存其真正字节与SHA256。构造human许可：`execution_license=true`、`source=DIRECT_USER`、真实instruction、实际authorized_at不早于独立approved_at、`review_hash=digest(真实approval)`、root内实际证据path/hash。不要伪造时间、消息来源或用户已经说过的内容；不要让模型生成的TEST许可证当成人类授权。

现场检查实际全局消费等于冻结baseline、目的地未有任何与prior_consumption=[]不符的消费、所有成员仍未消费、全历史保护/171pins/原三库哈希一致、凭据已私有配置。若现有新catalog非空，不清空或覆盖来匹配申请。实际账号权限未知是试点问题，不先调用接口探测。token只来自已有私有环境，禁止显示/记录值或任何编码形式。

使用现有 `python -m astock.phase1 execute --live` 的托管入口执行固定plan/baseline/approval/human，禁止私写绕过runner的HTTP脚本。每成员至多一次，间隔至少1.25s、无retry/redirect，首错停止当前50计划。授权注册先于claim，回执/源文件按当前严格合同保存；报错/中断claim永久消费，所有新失败保留body/source和原状态。不以count/has_more、少于cap、收到HTTP200或RAW_RETAINED等于真实数据准入。

全部结束或首错停止后立即做原有保护、实际消费/事件/授权/回执/对象审计，输出实际sent/complete/raw/failed/uncertain/stranded/未发送数量和主/次错误。保护扫描仍需完整内容hash；当前约52s/次是既有成本，不为追求速度关闭或改成mtime缓存。没有额外实时请求预算。

## 3. 调用全部停止后，完成 F1-R 与 V2 冻结兼容

即使试点首错停止，继续完成下面的独立离线工作。真实调用期间保持运行SHA不变；调用停止后允许本批必要源码/测试/独立版本注册/工具/脱敏文档改动、commit/push/最终SHA CI。

首先冻结真实采集版本5672的合同、实际转换adapter/必要运行源码/DDL/design与原pins，注册可验证的 **旧V2** 源版本。保持现有V1冻结字节/registry/171项不变。未来current pins变化后，刚捕获的V2来源必须仍按原plan/批准/实际source pins只读验证，不覆盖旧pins、旧批准、旧source/receipt或把生产来源改为fixture。不得归档一个未实际执行过的替代版本冒称5672。

修复 `pipeline.py` 的最终转换选取：

- CAPTURE descriptor的转换必须与实际源store里经授权验证的原plan pins一致，不能仅与generation中另一份transform_pins一致。
- DOCUMENT_FACT转换必须锚定实际不可变source.json/真实事实批准的版本。source里的transform_pins存在时不能忽略。
- 真正V1缺字段来源只能从已验证旧store/固定注册版本证明；V2不能任意fallback到V1。不通过删除字段、补当前pins或关闭版本注册校验使旧source通过。
- 保留有版本/实际证据的合法转换变更渠道；新派生转换有明确独立记录，不替换旧输入版本。

重跑审查者攻击：原始source/body不变，仅库内自洽切换到已注册V1、重算facts/quality/lineage/generation后，必须被拒绝。加入CAPTURE和DOCUMENT_FACT两条相应回归、四域/数据集身份范围约束、真正V1/V2正向兼容、未知版本与审批变异、旧代和增量/A-B一致性。不得只限制为“必须current pins”，那会毁掉刚采集的合法旧V2来源。

所有派生生成/更正/查询/PIT/完整覆盖回归在闭合fixture或production-shaped TEST根进行，不能将TEST批准流入canonical生产。真实新增raw/catalog只读核验源/授权/消费和固定版本，不做生产fact import/build/adoption，也不推广F1修复前的派生数据。原三库内容完全不变。

## 4. 同批输出真实试点答案与剩余计划

从已保留响应/实际停止证据回答：权限/业务错误、字段/envelope、cap/截断和空结果语义、日历civil/pretrade跨窗、财务公告/报告/修订可见性、证券/行业/参考来源的实际限制。未调用成员的答案明确未知，不能追加调用补答案或把当前download当historical vintage。

基于实际消费提出一个匹配停止态的未发送恢复候选与覆盖计划，license=false，未消费成员/顺序/预算/版本明确；不重新写calendar26/25专用工程。已有FAILED/UNKNOWN/UNCERTAIN不重发、不退款。若当次全50成功，报告实际覆盖与下一份各域有限/全量候选预算；成功试点不自动授权全量请求。

更新原验收矩阵，F1修复、本次真实RAW试点结果、软件和外部coverage/vintage/身份/规则限制分列。原252有限批准观察复用，不拆新的15/45身份批次。只处理这项已知残留和与本批实际证据直接相关的必要离线工作，不重开已通过F2–F5作为独立Gate。

## 5. 一次验证，一次交付

开发时仅跑针对性回归；最终源码冻结后跑一次本地完整suite、doctor/适用合同/specs、原库/保护/固定项保全、decoded/encoded凭据与暂存审计、最终精确SHA CI。保留真实运行5672 SHA与后续修复代码SHA的区别，不能用新SHA冒充真实调用代码；原991CI只证明旧5672。纯封包/文字变更不制造额外代码SHA循环。

一次交付：综合结果报告、两个SHA/各自CI关系、实际API/消费/回执/授权和原库保全、F1攻击现在拒绝+真实V2兼容、actual原始取证及试点答案、未发送恢复/下一批覆盖申请、私有ZIP/逐文件清单/索引、Git和凭据审计。新的实际数据/许可证仍ignored，只有源码和脱敏文档可提交。

最终状态 `RAW50_EXECUTION_AND_SOURCE_VERSION_INTEGRITY_FIX_REVIEW_READY`；真实结果按实情记录SUCCESS/PARTIAL/STOPPED，不许用测试数代替请求结果。全Phase1准入仍BLOCKED直到真实历史覆盖及最终审查。这个Prompt的直接转交允许上述具体真实采集与离线修复，后续恢复/新HTTP预算需要新的匹配批准，不需要逐文件重复询问。
