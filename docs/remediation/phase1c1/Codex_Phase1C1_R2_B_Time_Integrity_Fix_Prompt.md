# R2-B P1 时间规范化修复：一次交付统一复审

用户明确转交本条后，授权AStockSystem完成本次工程修复与隔离合成回归。当前审查SHA为`63a166b89f44850dd9fa2efa8ab06c0e49a8bfd5`，实施基线`2f2592968a7f8e2500ee5e0bd3772a15a5c621f5`；R1 FINAL PASS保留。此次修复不得写原warehouse、重签生产Approval或在原库续跑B。修复final-SHA统一REVIEW通过后，reviewer更新匹配执行批准，原用户已授权的有限B再继续；不重新调查历史cases，不增加内部Gate停顿。

先读取独立审查：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-03_Phase1C1_R2_B_Blocker_Independent_Review.md`

以及AGENTS、原有限B授权/指令、原R1/R2设计、F1–F3修复、现有private blocker包与不可改的独立审批包。后续用户授权仅在本条范围内覆盖AGENTS历史“不改获批实现”的限制；原库、旧证据、旧批准和零市场请求要求仍有效。

## 必须一次修完的根因

1. 冻结新design addendum，明确仅R2 resolver的UTC instant canonical serialization。新增文件，不改已批准design-v1/addendum1–3、旧manifest和review。只对明确aware datetime字段使用`astimezone(UTC)`及固定六位微秒/Z；null不变，拒绝naive datetime。不得用`replace(tzinfo=UTC)`重新解释时刻，也不得降低时间精度或忽略1微秒变化。event/valid_from/valid_to等date不能转换或改日。

2. 建立一个共享canonical payload/member函数，使ProviderResolver.snapshot_hash、resolver_payload、load_context_resolver的payload校验及pinned/live成员比较使用相同规则。保留成员按immutable ID排序和既有观察集合/顺序语义。不要只改会话TimeZone、只改hash，或对原mixed-offset批准直接替换成UTC读回hash。明确协议在新批准实现中的版本/设计pin，旧v1 hash保留为历史证据，不自动接纳为新协议。

3. 保留F3的checksum、snapshot membership、missing/tamper拒绝以及原Context在新增unrelated/superseding成员后仍使用其固定集合。仅忽略等价offset表达差异；必须继续拒绝真实instant、native、dataset/event/raw scope、security/episode、code interval、evidence/approval、decision status/version或成员内容变化。不要移除比较、接受任意hash或绕过guard。

4. 不全局改receipt_integrity.serial/digest、原frozen identity/context、raw serialization、旧logical hashes或SQL001–007。原市场值、NULL、native、批准历史scope/证据及knowledge instants不改。优先在既有SQL008–010语义下解决，不因offset问题把TIMESTAMPTZ降为naive/VARCHAR。若需要模型/协议新增字段，先在addendum说明有限影响并集中提交审查，不自行部署或隐式自动迁移旧Context。

## 必要回归与真实材料只读预检

5. 实际SQL测试使用临时合成存储，并经过managed writer/lock guard：008–010部署→导入合成cases→register_context→关闭连接→重新打开→load pinned resolver /select完整代 /重建。至少覆盖Asia/Shanghai和UTC交叉读写，另加America/New_York及Asia/Kathmandu；输入同时含UTC和+08:00，时间包含六位微秒与published_at=null。要求hash、canonical payload、成员比较、JSON roundtrip一致。不同offset指向同一instant可通过，1微秒不同必须失败。不能只测试预先全为UTC的Python模型。

6. 包括两条entry path：首次注册的resolver hash gate、已注册snapshot的pinned/live比较；后者要在持久化/reopen后更换会话时区。覆盖正常same-context完整代重建及material tamper/missing member失败。保持F1缺factor、F2精确逐日causal status、F3append/supersession后的旧Context复现回归，不放宽NULL/价格/factor/因果政策或容差。

7. 对原有限实际case-set与交付的isolated-root只做managed read-only预检。证明新canonical协议下原payload与四时区SQLreadback一致，所有aware instant与非时间字段不变；binding first_observed_at仍等于精确scope最早raw retrieved_at。真实3episodes/3codes/12bindings/192行、63NOT_CERTIFIED、1374范围外、0exception/0BSEtransition均不扩大。该只读预检不注册新生产Context，不修改原v1或旧failed isolate，不制造author生产Approval。合成注册与真实读取证据分开记录。

8. 输出新Context/resolver候选变化清单与diff：旧v1的case/DQ/resolver/Context/file hashes、候选规范hash、engineering SHA/设计新pin和需要reviewer填写的新批准字段。保留原历史事实批准；不自行填新actual approval/review_ref或把新实现回标旧SHA。若当前Approval模型要求统一新review_ref/time与availability，明确列出要由reviewer新增版本裁定的元数据，原records/files不改、历史instant不倒填。candidate hash不是生产批准。

## 交付一次后停止

9. 守住原DB hash`2942773e732b3fc60ba32be1a04c359aed16bcfc9c1a0b416a0dc56103993fba`、schema001–007/19tables、181raw、旧252curated/lineage、1102保护文件、133strict receipts、旧identity/attempts/audits、全部旧批准和失败预演包。用当前token扫描新交付和decoded实际证据，token不打印/不入Git。transport denial/spy为0；禁止所有provider/market请求，包括metadata/mapping/calendar和133重跑。Phase1C.2 CLOSED。

10. 聚焦开发中跑必要测试；全部修复/报告完成后一次完整离线suite、doctor/contracts、secret scan和最终exact-SHA CI。推送后读取实际run/jobs/logs。公开文档写问题、最终行为、回归、版本影响和完整保全；真实candidate、读取证据、日志/副本留ignored private，新建修复目录，旧包不覆盖。

交付`r2-b-time-integrity-fix-review.md`、private evidence-index、冻结addendum、implementation/test diff、候选Context影响清单、最终SHA/CI。作者状态`R2_B_TIME_INTEGRITY_FIX_REVIEW_READY`。集中等待一次独立修复REVIEW；不要自行更新approved hash、关闭本P1或宣布R2 FINAL PASS。

修复通过并生成匹配reviewer执行批准后，按原有限B授权从verified007基线准备**新的**隔离预演，重新验证backup/原库库存后继续两代COMPLETE publication/DQ/rebuild与final review。已有失败isolated-root保留，不在其已导入旧记录上重复import造成版本/PK混杂。预期仍192resolved+402054quarantine，historical completeness/real-data admission保持BLOCKED；Phase1C.2继续关闭。
