# 合并修复与候选 B 隔离演练交付

2026-10-04。作者状态：**COMBINED_REMEDIATION_B_REHEARSAL_REVIEW_READY**。专用 metadata 工程与实际隔离演练自检通过；数据 DQ 仍 **BLOCKED**。等待独立联合 Review，未执行正式 B，Phase1C.2 **CLOSED**。

## 基线与实现

独立接受基线 `088b02febccd07f68ddcf2dc6d42613ba69e9d35`。身份演练实际实现 `017f4c1bee63f59a0de84eca60432f015dde6b34`；最终 metadata 实现 `ae1c0d54446e78155ca718f2680b978b0dbb5d4e`。其间仅补 dedicated HTTPTransport 环境隔离、原始响应流保留与对应测试，身份/SQL/政策/旧 guard 依赖 bytes 一致。最终材料 SHA 和 exact-SHA CI 由提交后封存的 private `final-handoff.json` 记录，避免报告自引用。

保留旧来源、设计、审批及所有失败现场。D1 新索引准确标识2013年11月修订、2013-11-30决定日期、正文2013-08-05施行；首次网站发布时间及后续适用/替代未知，不认证2020/2026 session。

## metadata 专用准备

旧7个 SZSE trade_cal plan bytes、canonical hash `fb2c0792fdb6548c5849df398a56206e52802ca4bfab78da6f4ca3cdf5553a35`、members、fields、contract和 execution_license=false原样保留。独立模块固定HTTPS POST、禁retry/redirect/环境代理及证书配置、one-attempt/member、跨run持久预算、持锁pacing与不确定停止。

实际无网络mock走7次HTTP构造和SQL/file路径，42 civil rows，原始streamed response bytes（异常压缩只保留hash/长度并停止）、安全source、typed Parquet、manifest/sidecar/receipt各自闭合。真实系统时钟 start间隔最低 `1.345947` 秒；重开7项ALREADY_VALID且DB/time不变。失败、tamper、部分文件、writer/readonly/escaped、并发与时钟异常回归覆盖。生产入口拒绝fixture许可证。只有独立exact-SHA批准、匹配运行许可及用户明确7次授权齐全后才可运行；账号权限UNKNOWN，未probe。结构完整不等于session认证。

## 有限候选及真实演练

取得000022更码公告原始PDF，另两组复用已核验的官方原文。仅提000022/000043/300114当日old-native的15条 bounded daily观察：3 proposed bindings、15个单观察日半开官方代码区间、0新episode；已有3个episode及旧审批metadata原样复用。30条bounded观察和另2条2020-08-24probe分别核验。15条镜像new-native继续quarantine；probe不进入133成员或本候选，未推断通用alias/去重。3组provider问题仅草案，未发送或上传。

生产候选批准字段null/false。演练Approval使用CANDIDATE_REHEARSAL_ONLY、真实本次时间与独立material hashes；Context fixture_only=true，并有combined design/external-evidence封存envelope。新原库只读一致副本无输出硬链接或path escape。实际完成非空SQL import、幂等、完整old+new snapshot、原133/126父约束、Context、两代derive/DQ/rebuild及四时区managed close/reopen/select。默认register/start/publish/complete/select/DQ均拒绝fixture。

| 实际项目 | 结果 |
|---|---|
| 每代输出与源行 |126 COMPLETE；402,246源行精确守恒 |
| resolved/quarantine |207 / 402,039；旧192 rows完全相同，新增15 |
| 两代重建 |logical/schema/quarantine/source一致；findings hash一致 |
| 四时区 |Shanghai/UTC/NewYork/Kathmandu均精确选择两代 |
| DQ |402,147 findings；local/batch均BLOCKED |
| finding增量 |移除30，新增45；旧1,374范围外处置仅在fixture内引用复用并保留原生产出处 |
| 因果 |certified0、unknown60；0 mismatch不能作PASS |

新增45 findings是15个MISSING_DAILY_FACTOR与30个CROSS_DATASET_MISSING_OR_PROVIDER_ONLY。身份解决不批准其他endpoint绑定/因子/session。旧15,756 finding和402,246完整账本按hash引用保留，仅生成本批行级/finding差异，不重跑30126stress。

## 保全与验证

原库SHA256 `c687fc514a78ef8b68b6c89907b9932a42465d2b2cab5ae383647616287ca0e2`，34表/schema001–010内容及DBbytes不变；strict133 VALID/EXACT、failure0，181raw、252旧curated、1,102受保护文件/frozen identity保留。127,354既有文件与255基线tracked文件实际逐bytes验证；AGENTS仅授权追加。旧库、raw、receipt/attempt/time/approval均未改。

最终本地全套 **736 passed，1 warning**；doctor、两版contracts和现有全部offline plan/spec诊断通过。metadata57与snapshot11针对性回归通过。decoded secret scan及显式staging exclusions通过；最终exact-SHA CI在private handoff和最终答复给出。第一次全套因并行诊断日志创建干扰readonly目录快照失败，保留日志；停止材料写入后重跑通过，未修改旧测试。

## 待裁定与停止

有限15候选、专用live工程及fixture演练供联合Review；作者不签生产case/DQ/Context批准。正式B需真实匹配批准材料和用户授权，并重新计算生产Context，不能复用fixture hash。真实7次metadata还需单独许可证/人类授权，取得响应后的session仍需裁定。

普通历史身份、BSE、镜像alias/overlap、同scope factor/其他endpoint、各venue session、特殊资产及NULL缺证继续分别保留。bounded/全历史准入仍BLOCKED；没有把后续回填结果当作已完成。

**本批真实市场/provider请求0，原库写入0，133未重跑；文档HTTP1次（指定官方PDF）独立记录。** 公开材料只有脱敏摘要；全部候选、日志、差异、DB/raw及失败现场留ignored storage。

## 待运行命令与 session 证据

以下仅是未来运行方式，本批未执行。独立 Review 和人类授权后，以最终被批准的 checkout SHA 填写新的匹配许可证；当前所有模板均 execution_license=false。命令：

```sh
export PATH="$PWD/scripts:$PATH"
uv run --offline --frozen python -m astock.data.admission_metadata_live   --root /Users/yanliu/Documents/AStockSystem \
  --plan data/private/phase1c1-admission-a-evidence/2026-10-04/szse-metadata-plan-v1.json \
  --license /absolute/path/to/independently-approved-live-license.json --live
```

取得后先逐 member 验证固定42日期、原始body/HTTP-source/typed/manifest/sidecar/receipt及各真实时间闭合；将每个 cal_date、is_open、pretrade_date 与 exact request、source hash、retrieved/available 关联为新版本 external session 候选。不得由 civil completeness 或本批 mock 推导真实 session；真实候选须独立裁定适用交易所、日期范围、证据 hash 和批准时间，再计算生产 DQ/Context，不能加入原133 membership。
