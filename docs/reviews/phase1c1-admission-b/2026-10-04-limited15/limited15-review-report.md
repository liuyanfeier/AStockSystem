# Admission B 有限15原库执行交付

作者状态：**ADMISSION_B_LIMITED15_FINAL_REVIEW_READY**。有限身份追加、正式匹配副本和原库工程验收完成；全局 DQ **BLOCKED**，全历史前置未完整，Phase1C.2 **CLOSED**。等待独立最终 Review，作者不宣称完整准入 PASS。

## 批准与执行

原样使用独立批准 ZIP `1876ad1e51dd31a16abcf38278a001813c0119c16e1833e9e987bd15b202d59b`，24成员/CRC/source bytes及167 exact accepted file pins核验通过。review_ref `2026-10-04_Phase1C1_Combined_Independent_Review@45554a142a8e8d3e1b6cb0147db537bc88d1b55e#ADMISSION_B_LIMITED15`；真实批准时间 `2026-10-04T08:13:46.338396+00:00`。批准/material/Context实现固定 `45554a142a8e8d3e1b6cb0147db537bc88d1b55e`；实际执行SHA `045117792370c864a11a3d423b80d24b6d949fd1`，仅授权说明变化；最终交付SHA及exact-SHA CI由提交后private final-handoff记录，避免自引用。

未修改源码、tests、SQL、config、依赖、冻结设计或批准payload；未重新签发review_ref/time，也未把fixture材料转作生产批准。专用metadata运行license仍false；本批未调用live CLI。

## 当前备份和匹配复验

原库基线/备份及首次隔离执行取得managed exclusive owner。私有验收辅助查询列名错误后释放锁，保留完整现场；恢复时重新取得独占锁并完整复验原库、备份、181raw、strict133及全部既有文件。恢复验收与原库追加期间持续持锁，所有连接先取得managed owner。当前可读备份完整保持部署前 DB `c687fc514a78ef8b68b6c89907b9932a42465d2b2cab5ae383647616287ca0e2`，34表/schema001–010匹配批准基线；不重复迁移，不覆盖旧007备份。181raw完整manifest/sidecar验证、strict133VALID/EXACT/failure0，旧Context及两代重建验证通过。保全记录133,707既有文件；保留旧失败现场、审批、raw/curated、receipt/attempt/time及报告。

新的正式匹配副本路径固定在专用ignored隔离root，复制文件逐bytes一致、目标无硬链接/逃逸。副本使用实际批准Context，fixture_only=false，不启用allow_fixture。两代126完整输出、实际DQ、同Context重建及四时区reopen/select均通过后才开始原库追加。私有旧audit查询误用checked_at（实际observed_at）导致一次隔离验收中断，此时原库尚未追加且hash不变。失败脚本/日志/现场保留；只修正私有查询并重新验收已完成的两代，不新增隔离generation或DQ。封包辅助索引另有一次旧账本文件名错误，实际旧账本按历史manifest hash验证存在；新索引引用正确路径，原错误引用及更正说明同时保留。未出现获批写入事务失败、静默restore或原库替换；各获批接口保留自己的事务边界，恢复证明和备份留private。

## 原库实际有限追加

Context hash `470017335c3e7fd9f69480b35e2ac3012ceea2892a3f94706fdfcfb5af262475`；原库Context ID `c7aee09e-7b22-4485-8cdd-2f9781f42de9`。merged resolver `837d06d825d6852b1a9125ef6f1656876fa535339d84a2dfd3626bba33df36d6`。

| 实际对象 | 原库结果 |
|---|---|
| identity delta |3 daily bindings、15单观察日code intervals、15精确raw observations、0新episode |
| merged身份 |3episodes/18code intervals/15bindings/207observations |
| 第一代 COMPLETE |`e164eab1-d2a9-4c99-8ac2-f80f7e01b2c1`；126输出 |
| 第二代 COMPLETE |`270b4f3b-e2d4-4c2f-9d25-260347477276`；126输出 |
| 每代source守恒 |402246source=207resolved+402039quarantine |
| 旧192行 |全部值及旧审批metadata相同 |
| 新15行 |000022.SZ3、000043.SZ3、300114.SZ9；exact approved UUID/ordinal/event |
| 未批准范围 |镜像15仍quarantine；2probe不加入delta/133；其他endpoint/alias/factor/session/BSE均未批准 |

原库与正式副本的相同真实Context语义hash、schema/source/quarantine及DQ finding-set/causal统计完全相同；两代重建匹配。批准时间改变造成的15行binding_available_at和schema metadata使用实际生产批准，未套用旧fixture物理hash。重复import/register/complete不增加旧记录或改终态时间。

## DQ、处置链和仍缺证据

原库audit IDs `c04d767a-d48d-484b-8cba-9d8e285650aa`、`f6e4be79-67ac-41c0-9102-1b92a0a0f571`。每代402147 findings，local/batch均BLOCKED，因果certified0/unknown60，63session仍未认证。身份闭合不证明因子/其他endpoint或session完整。

相对旧Context，30finding不再发出，新增45blocking findings（15MISSING_DAILY_FACTOR、30CROSS_DATASET_MISSING_OR_PROVIDER_ONLY）；400728payload原样，1374精确pre-BSE处置只在新Context中按真实Review重新授权并保留原生产ref/time/hash。旧30key及全部旧audit没有删除或声明关闭。private完整处置索引引用旧402246 source/15756旧finding/402132后续finding账本，仅追加本批15行和30/45/1374精确差异，可重建旧新处置，不重复整个不变账本。

## 保全、测试与停止

原库部署后DB整体hash `27aabd6143d977decefefb8eb1f1b2b9e66ee29c14045d9df284871bcecf065f` 正确变化；历史保全以全部34表旧行子集摘要和既有文件bytes判断。133,706旧文件保持原bytes（仅获批原DB整体变化），新增504原库输出/lineage文件逐登记闭合。181raw、252旧curated/lineage、1102受保护文件/frozen identity、旧审批/receipt/attempt/timestamp不变。旧Context和两显式COMPLETE代仍可重建；原库与副本四时区只读审计前后DBbytes各自不变，strict133证据hash前后一致。

最终本地全套736 passed；doctor、两版contracts及其他既有offline plans/specs通过。decoded secret scan和显式staging audit通过；最终exact-SHA CI及warning明细封存于private handoff。公开Git只提交授权和脱敏报告，DB、raw、批准及行级证据保持ignored。

**市场/provider/HTTP/socket实际调用0；133未重跑；仅此次有限追加完成；全局数据准入BLOCKED、Phase1C.2 CLOSED。** 交付后停止，等待独立Limited15最终Review，不自动扩大scope或启动回填。
