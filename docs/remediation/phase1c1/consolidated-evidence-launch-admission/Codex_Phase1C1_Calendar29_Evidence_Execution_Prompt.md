# 交给执行 Codex：限定 Calendar29 取证

只有用户明确要求执行本 Prompt 时才获得这29次日历调用的授权。阅读、引用、上一轮离线修复授权或审查报告都不构成用户执行许可。执行前保留用户本次明确指令，并据此生成真实 human authorization；不得用候选或作者验证 metadata 代替它。

## 已通过的范围及输入

仓库 `/Users/yanliu/Documents/AStockSystem`。实现/执行 SHA 必须为 `57812dd921df0720680b3034c186734852f13648`，source/design/catalog/DDL 与独立批准 pins 一致；真实请求完成或停止前保持 Git 干净及该 HEAD，不修改/提交跟踪文件。

读取独立报告：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/2026-10-08_Phase1C1_Runner_Repair_Independent_Review.md`

批准文件目录：
`/Users/yanliu/Documents/Codex/2026-10-02/referenced-chatgpt-conversation-this-is-an/outputs/private/phase1c1-runner-repair-independent-review/calendar29-review/`

使用原字节的 `calendar29-production-plan.json` 与 `calendar29-external-review.json`。`calendar29-human-authorization-PENDING.json` 是明确未签的示例，不能拿它执行。只依据实际用户指令生成匹配的独立 human 文件：协议/namespace 为 FULL_BACKFILL_CAPTURE_V2_1 / PRODUCTION；approval_hash 精确绑定外部 Review；authorization_ref 指向私有保存的真实本次用户指令；authorized_at 为真实授权记录时间，满足 reviewed_at≤authorized_at≤现在；execution_license=true。记录授权时不要追认未来时间或编造用户指令。

外部 Review 的 canonical checksum 为 `6f6aef26ae9fd6548ca4b6cbbc2276470d4316d9bd2095c8cc03ec74dc5e4939`，human 的 approval_hash 必须精确等于它；该值不是缩进JSON文件的字节SHA256。production plan canonical checksum 为 `dd89dad8c44ca437c743f77f396d7633cb05b2d01a34d2831ec1c4c81373501e`。

外部 Review 中的 execution_license=true 只表示独立审查批准确切29成员；没有实际 human 授权、--live、匹配SHA/clean root 和本地凭据时仍须零调用。

## 本批允许和禁止的操作

只运行29个 trade_cal 请求，SSE15＋SZSE14，严格采用批准 plan 的执行顺序、params/fields/contract/completeness规则；每member最多1attempt，总预算29，最小调用开始间隔1.25秒，retry/reserve/redirect0。保存根唯一固定为：
`/Users/yanliu/Documents/AStockSystem/data/private/full-backfill-v1`

SZSE2013＋BSE6继续HOLD。旧6个UNATTEMPTED窗口不叠加、旧FAILED窗口不重发或重置。行情6、stock_basic、mapping、其他provider API、公开文献9、全量回填和Phase1C.2都不在本次授权。文献HTTP0、133 replay0、原仓库写入0、finite45 reimport0、Context/generation/DQ rebuild0。

不得改新runner/catalog/DDL/contract/完整性规则/批准plan，不能注入自制production transport、换root/store、绕过live/许可/类型/日期/cap/empty/previous校验。账户权限、cap和实际历史覆盖目前UNKNOWN；该批取证会得到实际响应或实际失败，不能先标PASS。任何异常均保留原事实，不补零、不换接口、不自行扩大预算。

## 执行与停止

先核验报告/批准文件hash、旧原库/metadata、171pins及当前保护文件baseline；原仓库与metadata只用managed共享只读连接。确认固定capture store不存在，或为既有匹配v2.1账本且完整审计通过；遇到意外store/schema/consumption不要删除、迁移、清空或改名。保护所有旧v1/v2和失败证据。

本地凭据只经现有settings读取，不写聊天、命令参数、报告、source或日志。使用既有实际CLI入口：`python -B -m astock.data.full_backfill_v1 capture`，提供--root、上述--plan、上述--review、实际--human-authorization与--live；保持真实HTTPS、no retry、no redirect，不能把mock模式用于本批。

实际请求全部由runner产生CLAIMED/CALL_ENTERED、不可变五文件及receipt/event。异常、403、权限不足、未知delivery、空/截断/类型/previous不符、文件变异或预算问题立即停止。保留consumed/未调用成员和错误，不自动再运行CLI。CALL_ENTERED不证明远端收到，也不等于provider拒绝；失败是证据，不是补发理由。

若29成员全部完成，关库后用managed连接对全部五文件/receipt/event/origin许可证进行离线重开校验，核验开始间隔、attempt数和HOLD零调用。只做本地reconcile/readback，不以额外HTTP验证成功。禁止删除不完整capture、用新许可清除消耗或恢复旧metadata。

任何时刻缺少许可或检测到pin/HEAD/clean root不符，零调用并明确报告阻断，不能由作者重新签外部Review。

## 取证后的提案与交付

完整body/source/typed/manifest/sidecar均为当前抓取时间的source事实；research_admitted/historical_PIT_eligible仍false。不要导入原trade_calendar、减少原DQ finding或新注册Context。

用真实响应按venue和日期为现有63session/previous矩阵增加候选证据与定位：哪些完整窗口支持哪些日期，哪些previous关系在相邻窗口可观测，哪些leading predecessor或缺失窗口仍UNKNOWN。不得跨venue复制、把mock星期一到五当真实日历或把当前provider页面当2013时点可用。涉及SZSE2013/BSE的事实继续HOLD，不自动扩展请求。

输出一份汇总报告、machine decision、完整实际成员/attempt/来源/时间/许可证账本、成功与失败原物、五文件闭合和保全/凭据报告、manifest/index/ZIP/handoff。原库34表使用相同DB字节+无WAL+managed只读核验或完整行集比较；旧metadata状态/hash、171pins、所有既有保护文件不变。文件增加可以进入新的baseline，但不能掩盖旧文件变化。

本批不改实现；复用已经独立核验的120定向/873完整测试。实际重开与保全检查不可用pytest摘要代替。采集结束或停止后才可以创建/提交脱敏交付文档；最终报告区分原获批执行SHA与最终文档SHA，核验最终精确SHA CI。DB、raw、完整private许可/plan/ZIP和凭据不进Git。

若成功：`CALENDAR29_EVIDENCE_CAPTURE_REVIEW_READY`；若途中失败：`CALENDAR29_EVIDENCE_CAPTURE_BLOCKED_REVIEW_READY`。都须明确实际attempt、COMPLETE、FAILED/UNCERTAIN和UNATTEMPTED数，HOLD7零调用。实际session认证仍等待独立证据批准；Phase1C.1整体/全历史准入仍BLOCKED，Phase1C.2仍CLOSED，行情执行许可仍未获准。

提交一次集中独立Review后停止；不得顺带执行首批行情或开始回填。不能承诺这29次成功就意味着Phase1C.1全部完成。
