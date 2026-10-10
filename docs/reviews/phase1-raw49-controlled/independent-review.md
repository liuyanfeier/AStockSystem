# RAW50 实际执行、源版本修复与后续执行方式：独立 Review

审查最终 SHA：`66b1cec4914d51f75b0cf4f5211623a03dd9de2d`；实际调用 SHA：`5672e8f8464b20e3437ab94bd3ef17cbb05f7bcf`。

**结论：F1-R 修复 PASS，本轮执行记录与保全 PASS；真实来源试点尚未成功。已审查的 Phase1 工程问题闭合，完整历史数据准入仍 BLOCKED。下一步直接诊断连接并受控处理剩余49成员，不重开 Phase1C.1。**

本次同时提供已封闭验证的外层执行控制器和真实独立预授权策略。用户直接转交配套执行 Prompt 后，可在固定66b1采集内核下连续完成诊断、剩余成员采集、失败隔离、离线分析和全量交付方案。这个范围不包括全量HTTP、生产事实采用/生成或旧请求重发。

## 1. 软件修复与材料核验

- 独立复跑 `tests/test_phase1_source_versions.py`：**14 passed / 220.98s**。验证 CAPTURE / DOCUMENT_FACT 的自洽 V1/V2 替换攻击被拒绝、原始数据集限制保留、真实执行版本的封闭生产形状兼容、旧代保留、A/B 重建和更正增量。
- 直接读取 GitHub job114159752197：checkout 精确为66b1，**1005 passed、6 warnings、1343.36s**，doctor 与合同/specs步骤成功。未在审查工作区再重复全套1005项。
- V2 的22个冻结文件逐个与 Git5672 原字节、原实际pins比较；V1逐个与此前 Gitb350 原字节比较，均一致。
- ZIP CRC、唯一成员、471项逐文件长度/SHA256通过；38项 public-implementation 与当前源码/文档一致。包 SHA256：`24d21351d0e7159a3baf9d484f99bbccf15619ea3262a2a5705f793edaa3ac56`。
- 三个原库字节不变；146656个历史文件及171项冻结记录核验通过（去重/规定排除后实际hash146825路径）。停止的新capture库/driver/summary与冻结清单及包内字节一致。
- 原库和真实新库均无审查者SQL写入，审查者真实网络请求0。只对新库的字节副本做 SQL 取证，原库不创建审查锁。

源版本选择现在锚定物理核验的原capture plan，或不可变document source/实际批准pins；descriptor和generation里的第二份pins不能覆盖它。缺字段V1必须有旧协议、旧store、登记对象和固定版本证明；缺字段/null的V2不能退回V1。缓存命中也重新校验全部冻结文件。此前 F1-R 已关闭；无需再给作者一个“只修这一点”的批次。

## 2. 真实停止到底说明什么

实际库保留1条授权、1次attempt、3个事件：`CLAIMED → CALL_ENTERED → UNCERTAIN`。无raw对象、回执、事实或generation；49个成员未尝试。剩余计划的成员确实等于原50计划去掉第一个SSE2014，顺序、字段、日期和origin保持不变。

从 `CALL_ENTERED` 到 `UNCERTAIN` 是 **0.276928秒**。这不能证明请求未发送，也不能据此判定DNS、TLS、权限或服务端原因。客户端的CALL_ENTERED发生在HTTP client/stream构造之前；当前事件只证明已经进入受预算约束的调用步骤。

本轮没有“账号权限不够”或“行情接口数据错误”的证据。17个来源试点、6个行情请求均未调用；没有任何实际响应可用来证明接口权限、截断、空结果或PIT vintage可用性。

## 3. 工作方式的问题与调整

上一份Prompt明确要求首错停止、不追加诊断，所以本次作者遵守了批准范围。**这个严格策略由审查者设定，当前阶段应调整。** 不重发一个结果未知的旧请求，和停止整个项目、每次再交回Review，是不同的决策。

当前内核将所有transport异常丢弃原类别。独立注入ConnectError、ConnectTimeout、WriteTimeout、ReadTimeout、RemoteProtocolError，五种都只持久化成 `TRANSPORT_UNKNOWN_NO_RESEND`。因此本轮无法还原具体原因；后续必须留下固定白名单的异常类别/errno/阶段，不能再只留“未知”。不得记录异常原文、请求、token、frame locals或敏感traceback。

原有保护机制还会在每个成员前扫描146656历史文件，近期约54秒/次。按候选行情30126个请求的纯扫描上限，成本约450小时；这只是候选计算，不是实际总请求数或完工预测。RAW49仍复用当前已审查的完整保护，不在真实执行时关掉它。全量计划应一次解决保护粒度：明确旧目录写入隔离、全量开/闭批校验、批内内容校验/检测机制、故障恢复和实测成本，不能仅改为mtime缓存。

现在采用**冻结66b1内核 + 已审查外层控制器**。旧内核仍按首错停止一个segment；外层根据已审查策略隔离失败、诊断并为尚未尝试成员生成确定性子计划。子计划批准是本报告预授权策略的机器化派生，不能由工程作者任意另签Review。

## 4. 本轮有限执行预授权

控制器：`outputs/private/raw50-source-version-independent-review/controlled_raw49.py`，SHA256 `54e536641dc4d9f990da101ccdc0bef1d850b39c5cae7234977f0eebe5df8404`。

独立封闭验收 **16 passed / 20.91s**：范围/旧消费变异拒绝、敏感异常文字不落盘、一次transport失败后48个新成员继续、同数据集失败隔离后其他数据集继续、连续两次transport失败停止、401/403整体停止、缺失执行结果整体停止。使用真实未改的采集内核及闭合MockTransport；TEST批准/根目录全部明确标记，真实socket封禁。

策略唯一根目录 `/Users/yanliu/Documents/AStockSystem`；唯一新capture目的地 `data/private/phase1-integrated-v1`；源码HEAD和pins必须保持66b1且Git clean。初始49计划hash `39968a70d7fecb296c39cc7483546827415f04148dd4182f9938d6261fc49f4d`；初始消费hash `46f265ac726ab13c1d8605712d38ad0ea1b62190a5872c2800c2a433164bc729`。

预授权包括：

1. 对唯一主机 `api.tushare.pro:443` 最多3个DNS/TCP/TLS诊断周期，HTTP0、token0。连接恢复后自动进入新成员采集。初始诊断持续失败时不消耗新的市场请求，继续离线定位与交付。
2. 原49个成员最多各一次；以当前持久化消费为准，只减去已消费成员及本轮数据集HOLD。日期/参数/字段/顺序/origin不变，预算不补回、不增加、不替代。旧133、SSE2014与其他旧FAILED/UNKNOWN/UNCERTAIN均不重发、不重置。
3. 一个新transport UNCERTAIN保留原事件，进行有限连接诊断；恢复后尝试下一未消费成员。连续两次新transport失败即整体暂停，避免在全局网络不可用时耗光预算。
4. 返回体/数据合同/业务错误保留raw并HOLD该dataset，继续其他独立dataset；已成功raw仍只表示RAW_ONLY。HTTP401/403、跨三个独立数据集持续business error、历史/许可/源码/范围异常、次级报错或无进展整体停止。
5. 子计划与实际approval/human链均落盘并由当前内核重新验证。直接用户授权明确覆盖这项有限策略及确定性许可派生；不得用TEST批准或伪造授权时间/内容激活。

保留原作者remaining49申请license=false。本报告配套 `raw49-recovery-policy.json` 是另一份真实独立预授权文件，用户许可仍需要本次直接转交Prompt。控制器只可原字节复制，不能换代码/策略后沿用此Review。

## 5. 同一批次交付，下一步围绕真实数据完成

诊断/采集完成或达到真正全局阻断后，继续本批离线分析和必要修复：定位实际网络类别，检查已有响应的合同/权限/截断/空值/PIT限制，准备已失败raw的独立派生候选及全量历史交付方案。若需要修改canonical源码，在所有真实调用停止后进行，先冻结实际66b1来源版本；新代码不能冒用本轮许可继续HTTP。

全量交付方案应一次给出各域边界/分母、可计算请求/attempt预算、存储与速率、PIT与规则/身份来源、覆盖验收、第二来源抽查、真实A/B重建和增量验证。全量新读请求应设计有记录、有上限的重试/退避与幂等归并，保留每个attempt，不能把一次网络异常永久当成资料不存在，也不能抹掉旧unknown/重新包装133来退款。执行全量仍需那份具体实现与预算的整体审查授权；本报告不是无限HTTP或生产研究准入。

证据目录：`outputs/private/raw50-source-version-independent-review/`。文件包括 `artifact-check.json`、`live-ci-verification.json`、`test-verification.json`、`transport-error-category-probe.json`、控制器测试log、控制器、策略和机器决定。本轮目标是让真实接入和全量交付方案一起推进，避免把每次普通故障拆成一个新工程阶段。
