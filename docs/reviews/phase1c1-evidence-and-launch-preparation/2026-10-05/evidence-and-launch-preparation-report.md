# Evidence and Phase1C2 launch preparation

作者交付状态：`EVIDENCE_AND_PHASE1C2_LAUNCH_PREPARATION_REVIEW_READY`。
本批执行日期为 2026-10-06；目录沿用授权 Prompt 建议的 2026-10-05-v1。
上一轮 finite45 与 Phase1C.1 工程线已独立 CLOSED；本批新增能力及候选事实
等待集中独立 Review。全历史数据准入仍 BLOCKED，Phase1C.2 实际运行 CLOSED。

## 已完成的新增工作

追加独立 `FULL_BACKFILL_CAPTURE_V1` 模块、CLI、catalog 和离线存储 DDL。
生产路径需要匹配的外部审查、实际用户授权、实现 SHA、设计/contract/member
pins 和预算；默认无执行许可。原 Tushare bounded133、FakeTransport-only
admission、SQL001–010 与既有171文件保持不变。新增入口不调用旧 `_fetch`。

新入口将 claim/CALL_ENTERED 先提交，再进入单次 HTTPS transport；禁重试、
环境代理和 redirect，TLS 校验及跨重开至少1.25秒调用开始间隔。完整 body、
source、source-typed Parquet、manifest、sidecar 全部闭合验证后，receipt 与
COMPLETE 一起提交。未知调用/失败不重发；无效 UUID、cap、空响应、缺文件、
篡改和未claim成员孤立目录均阻止计划继续。typed capture 尚未获研究准入。

闭合 mock 测试覆盖六个非空端点、原生标识/NULL/整数类型、生产许可分支、
权限/模式/截断/cap/empty、落盘/注册/promotion故障、重开及预算/pin/orphan。
六个完整fixture captures已实际落盘并重开校验；真实socket与旧provider调用0。
旧30,126合成规模及恢复证明复用，没有重跑压力产物或宣称全历史IO已验证。

## 共享证据与候选边界

24次 DOCUMENT HTTP预算已耗尽：15次受限网络连接失败、6份HTTP200正文、
3次BSE HTTP403。逐次台账、实际body/text/hash/定位及失败记录保留；搜索仅
用于发现URL。另实际读取9份既有网页正文及7份既有发行主体PDF原文。

新[stock_st文档](https://tushare.pro/document/2?doc_id=397)记载历史起点
2000-01-01、1000行上限及早期无法补全的限制；新[suspend_d文档](https://tushare.pro/document/2?doc_id=214)
记载2000-01-03起、5000行上限。账户权限和实际历史完整性仍 UNKNOWN。
[bse_mapping文档](https://tushare.pro/document/2?doc_id=375)的old/new/list_date
字段不能替代官方切换有效日、证券episode或具体行情端点的历史native表示。

[SZSE2013休市通知](https://www.szse.cn/disclosure/notice/general/t20121225_501056.html)
支持1月4日开市及元旦/周末休市；[SSE2025休市安排](https://www.sse.com.cn/disclosure/dealinstruc/closed/c/c_20241223_10767110.shtml)
支持5月6日、10月9日恢复开市和具体假期区间。它们作为文献候选保留，尚未
变成完整session/真实previous认证，亦未复制到其他venue。

| 当前范围 | 剩余事实与处置 |
|---|---|
| ordinary386,249 | 缺联合issuer/shareclass、listing/termination episode、official event code及endpoint native证据；5584carry仍仅调查分组 |
| BSE13,030 | 复用248主体/31,248cell矩阵，分别6pilot与242迁移；原完整官方pair-row、episode/native/calendar证据仍缺；新403不补事实 |
| historical57 | 42endpoint aliases、15daily mirrors继续隔离；数值相同不证明alias |
| unknown1,224 / special60 | 资产/episode仍缺；689009官方CDR与provider STK冲突保留，T600018/code reuse不合并证券身份 |
| reference-price3 | 000022.SZ在2013-01-04/07/08的stk_limit原pre_close=NULL继续阻断；无历史NULL政策或跨端点替值许可 |

没有新文献同时满足额外identity binding的全部事实，因此新增identity/DQ
exception/Context候选0。交付明确理由及文献事实提案，不制造空批准模板。
原252解析行、401,994隔离行、1,374已批准pre-BSE范围外处置均保留。
当前DQ仍为401,994identity +63session +3reference price =402,060。

## 可直接审查的后续申请

主申请冻结36个exact venue年度calendar及2012年12月previous lookback窗口，
各member/params/fields/contract/hash/保存路径/单次预算/停止条件完整。
旧6个UNATTEMPTED窗口只列非叠加替代；旧1个FAILED仍已消耗，delivery与账户
权限 UNKNOWN。CALL_ENTERED不证明远端收到，也不能称provider拒绝。
SZSE2013重叠新范围需先外部reconciliation与单独审查；同逻辑失败请求不可
通过改run名/新store重发。BSE provider参数适用性尚缺文献，不能用SSE替代。
另有独立9次未来公开文献申请，本批不执行、不转用已耗尽24次预算。

首个市场安全切片提案明确为2013-01-09六端点、6次上限、reserve/retry0，
并非缩减全目标。全目标仍2013-01-01..2026-09-30、六datasets和获批venue。
calendar、历史universe/native、端点完整性/空响应政策、account permission、
新入口独立Review及实际human license未齐前，首批不能运行。

全计划v3保留gross base上界30,126（6×5,021 civil days，仅合成保守上界）；
真实session/member分母未认证，verified reuse0，126只是候选，不预扣。
额外cap分片数量及全执行预算 UNKNOWN，calendar36、identity新请求、分片、
reserve和备份分别列出。旧Parquet外推不含新body JSON开销，磁盘容量及真实
吞吐不宣称PASS。全历史raw完整性、年度真实rebuild与coverage/causal终验
明确留在回填后，未冒充本轮前置证明。

## 验证、保全和交付

最终源码针对性回归61 passed；完整离线suite814 passed / 1 warning / 451.86秒；
doctor、contracts与specs结果
及最终exact-SHA CI在private handoff/manifest中固定。本批无原库部署。
原库hash仍`30953a9ff2622c85724794b268bc878ea2494684d6faccd5ab0fc5cbb378eb81`；
34表完整行集、schema001–010、171pins及145,156个受保护文件逐项保全。
固定metadata hash仍`91a2c5d20df935795e0e2b736175af13fb6b7b5f6092231a9e96975fd30b9ece`，
1consumed/6unattempted/0responses不变。没有finite45重导入、Context注册、
generation/DQ重建、133重跑或旧metadata resume/reset。

凭据检查包含literal/base64/hex/URL及压缩Parquet解码；仅脱敏文档/新模块、
测试/catalog/DDL提交Git，DB/raw/完整成员/ZIP均ignored private。最终SHA与CI
由交付handoff精确关联，作者不宣布新能力独立PASS或全历史准入PASS。

主private材料：`data/private/phase1c1-evidence-and-launch-preparation/2026-10-05-v1/`。
active chain复用原完整source账本并叠加exact207+45事实，没有重生成不变大账本。
最终package含primary index、完整manifest、sources、proposals、offline验收、
保全/secret结果和CI；旧大账本/DB按精确外部hash引用。

真实市场/provider/metadata/calendar/mapping请求0，原库写入0，133 replay0。
集中独立Review及后续匹配用户运行授权是下一停止点；本批完成后停止。
