# 直接执行：诊断连接、受控完成RAW49、集中解决接入问题并交付全量方案

**用户把本Prompt直接转交为执行指令时，授权下面的具体动作及确定性许可派生。** 最新直接授权覆盖本批诊断/RAW49和离线交付，替代旧批次的“HTTP0/任何首错都交回Review”限制。旧133及所有旧FAILED/UNKNOWN/UNCERTAIN不重发、不重置；完整Phase1准入尚未通过。

不要新建只修一个日志点的批次。先使用审查者已交付的冻结外层控制器处理真实接入，再把必要离线修复和全量数据交付方案一起完成，最后一次交付。

## 1. 输入与实际许可

项目 `/Users/yanliu/Documents/AStockSystem`；工作区审查材料：

- `/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-10_RAW50_Source_Version_Independent_Review.md`
- 同工作区 `outputs/private/raw50-source-version-independent-review/` 下 `raw49-recovery-policy.json`、`controlled_raw49.py`、`artifact-check.json`、`live-ci-verification.json`、`test-verification.json`、`controller-verification.json`。
- 作者上一批 `data/private/phase1-raw50-source-version-fix/2026-10-10-v1/` 的delivery-index、remaining49申请、停止事件、新库冻结清单和global-legacy-before。

F1-R独立PASS；Phase1C.1工程CLOSED、Phase1C.2 STARTED，Phase1真实历史准入BLOCKED。当前批准只包括独立策略中的原49个未尝试成员、最多3个无HTTP/token的DNS/TCP/TLS诊断周期、新capture追加和之后的离线工作。

真实运行HEAD必须保持 `66b1cec4914d51f75b0cf4f5211623a03dd9de2d`、Git clean、当前全部pins匹配。不要在真实调用前修改源码/合同/README/AGENTS或commit；这份最新直接指令已经定义有效范围，不靠提前改仓库文档获得许可。不reset用户改动。

## 2. 一次准备，启动已审查控制器

把Review原字节复制为：

`data/private/phase1-raw49-controlled-execution/2026-10-10-v1/independent-review/independent-review.md`

把策略、控制器、控制器验收JSON原字节复制到同目录，分别命名 `raw49-recovery-policy.json`、`controlled_raw49.py`、`controller-verification.json`。核对策略中的报告/控制器SHA256；控制器不可改，不能用作者生成的新approval替换实际独立策略。原remaining49申请保持false，原RAW50审批和SSE2014停止证据全部保留。

记录用户本次直接转交的实际文本/消息为 root 内私有授权证据；保存真实字节和hash。构造parent human JSON：`execution_license=true`、`source=DIRECT_USER`、真实instruction、实际authorized_at、`review_hash=digest(实际raw49-recovery-policy)`、root相对evidence path/hash。不要把更早的Review请求当成此次执行许可，也不要伪造时间或TEST授权。

此直接指令明确允许已审查控制器为原49未消费成员，按预授权策略生成精确子plan/approval/human文件；这是原真实独立Review的限定派生，不是工程作者自行签新的独立Review。子plan只能减去实际持久化消费和本轮HOLD数据集，不能改参数、换成员、补预算或推广新源码。

启动命令形状（human实际路径按上述保存）：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Users/yanliu/Documents/AStockSystem/src \
/Users/yanliu/Documents/AStockSystem/.venv/bin/python \
/Users/yanliu/Documents/AStockSystem/data/private/phase1-raw49-controlled-execution/2026-10-10-v1/independent-review/controlled_raw49.py \
--policy /Users/yanliu/Documents/AStockSystem/data/private/phase1-raw49-controlled-execution/2026-10-10-v1/independent-review/raw49-recovery-policy.json \
--human /Users/yanliu/Documents/AStockSystem/data/private/phase1-raw49-controlled-execution/2026-10-10-v1/human-runtime-license.json
```

从项目根执行。控制器只调现有正式CLI，按原方式从已有私有settings取token；不写私有HTTP脚本，不输出token/环境值/异常全文/请求或敏感traceback。诊断使用同一固定主机、直接TLS与验证证书；不注入代理、不换endpoint、不关闭TLS。若实际运行环境需要平台网络/路径权限，按这份具体已授权命令申请，不能借旧BLOCKED记录认定人类没批准本批；真实自动审批拒绝要原样保留理由，不能绕过。

执行前核对当前原三库/保护基线、实际新库消费及合法停止态、全局消费与pins。原实际执行的V2已冻结；原新库1个UNCERTAIN、0回执、49未尝试必须匹配。若已有人消费新成员或HEAD变动，不能清空现场去适配本许可。

## 3. 故障处理方式已经改变

内核仍按首错停止一个segment，外层受控恢复：

- 初始最多3个DNS/TCP/TLS诊断周期；HTTP0/token0。诊断失败有阶段/白名单异常类/安全errno，不再只有“未知”。初始持续连接失败不消耗新行情请求。
- 一次新UNCERTAIN保留现场，不重发该成员；有限诊断恢复后处理下一未消费成员。连续两次transport失败停止真实调用，防止全局不可达时耗尽49预算。
- 一个dataset的业务/返回体/合同错误，保存raw并HOLD该dataset，继续其他独立dataset。不要把一处字段错误扩成所有域的停止，也不要在未审查新decoder下偷偷改旧内核。
- 401/403、跨三个数据集持续business error、任何历史/凭据/许可/pins/范围/次级报告异常、无进展，整体停止真实调用；随后继续独立离线定位/修复/全量方案，不能把“停止HTTP”解释成“整个任务停止”。

原49成员仍各至多一次、≥1.25s、无API retry/redirect、原順序/params/fields/origin不变；26日历+17来源+6行情，旧SSE2014和所有旧133/消耗失败不包含在内。最多3个诊断周期是独立预授权，不是API重试预算。新库SQL/对象/授权/plan/event/receipt可追加；三个原库SQL写入0，旧保护文件/171固定项/历史证据不变。真实fact adoption/import/build/increment和全量HTTP仍未授权。

控制器的异常类别记录只在本批私有新目录落盘。若发现EACCES/EPERM或明确环境问题，检查真实执行环境/平台授权、依赖和已有配置，不把它猜成供应商数据错误。只做可逆且有证据的本地修复；需要新凭据、付费权限或更改网络路由时，集中说明具体缺项，不要求用户在聊天里发token。

## 4. 真实调用停止后，继续同一批次的离线工作

先审计全部新attempt/授权/事件/对象/回执与原库/历史保全，再冻结新capture停止后的字节/清单。报告已调用、成功RAW、失败、未知、HOLD和未尝试，不把预算或测试数当成真实结果。所有成功响应也保留RAW_ONLY状态，不能因HTTP200或低于cap宣称完整历史覆盖。

从实际证据集中回答连接故障原因、账号/接口权限、envelope/fields、截断/空值、日历窗口、财务公告/更正/vintage、证券/行业/参考来源限制。普通接入问题继续离线修复、使用现有保留body验证，并准备明确的独立派生候选；不重发未知或失败请求去补证据。未调用部分明确未知。

若确需修改canonical源码/合同/版本支持，所有真实调用先停止；按已通过机制冻结本批实际66b1源码/pins，再修复、闭合回归、一次最终完整suite/精确新SHA CI。新代码不能沿用本轮许可再执行HTTP。没有源码变更时复用已核实66b1的1005-test CI，不再为每个离线动作重复跑全套。

AGENTS/README/operations中有效状态在调用全部停止后统一更新，注明最新真实授权和旧批次规则的适用范围，保留历史记录。提交只有源码和脱敏文档；数据库、token、真实授权与证据仍ignored。

## 5. 下一份交付必须是全量历史数据交付方案

将2013-01-01–2026-09-30各域放在一个执行/验收任务中：证券和退市历史、行情/复权/状态、财务PIT、行业、历史规则、最小参考数据。原252有限identity观察复用；不再拆新的15/45准入小批。

给出实际可证分母、可复用raw、缺失来源/版本、精确或可确定展开的request清单、总request/attempt预算、成本与存储、速率、断点恢复、隔离错误和有界重试。全量新读请求的重试保留每个attempt/原UNKNOWN且有预算上限、退避与内容幂等，不能仅用“永不重发”制造永久覆盖缺口；旧133和旧消耗禁重发边界仍保留，任何确需例外集中列出待批准范围，不能通过改params绕开。

保护性能作为同一方案处理：旧路径写入隔离/锁与检测机制、开/闭批完整hash、批内校验、进程死后的恢复、准确扫描频率与小规模实测。当前RAW49不得关闭完整保护或改成mtime缓存；全量方案不能把54秒全库扫描放进每个请求而不算成本。

验收要包括覆盖/无未来信息、历史身份/规则/PIT vintage、第二来源抽查、真实A/B重建/更正增量、来源版本再证明。客观缺失的历史vintage或权限一次列成明确范围决策；不要反复生成只有公式、total_budget=null和license=false的“小试点再申请”。申请在本次交付时仍未获全量许可，给独立Review的是可执行的具体全量任务。

## 6. 一次交付

交付综合报告、实际66b1执行/控制器/预授权hash、真实诊断类别和RAW49消费/成功/HOLD、原历史保全、必要离线修复及SHA/CI关系、实际来源限制和全量执行验收申请、私有ZIP/清单/索引、凭据/Git审计。状态 `PHASE1_CONTROLLED_SOURCE_ACQUISITION_AND_FULL_DELIVERY_PLAN_REVIEW_READY`；真实采集按实际SUCCESS/PARTIAL/BLOCKED记录。

全局连接确实未恢复时，也完成不依赖网络的离线分析和方案，并集中列出唯一需要外部改变的条件；不能消耗更多请求，也不能宣称全量ready。完整Phase1结束条件仍为真实历史交付及最终验收，而本批应推动到那份统一任务。
