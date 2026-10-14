# 真实002执行、数值与重建验证

## 实际授权与版本

本轮实际直接用户消息：“批准002固定299请求，continue_on_error=true”。它指向前一交付的固定清单和hash；
私有保存实际消息、准确范围、逐成员许可及记录时间，没有新造人工/GPT签名。
记录时刻与四小时有效期为操作方更窄约束，不伪称额外人工签署时刻。

执行HEAD：0275a63a72dda95f19c4f9eb7df3575ebee4aa7b，Git干净，002目录未有历史消费，令牌存在；正常网络权限进程。
plan hash：2006eb17e875ff65043d9fe6c6f919b33b05acb19426eaf71a3000ad7b20caf1。
实际执行implementation hash：d8e4b225e7e45ac0c77531ced03af8e3f4d826794e88eba1d1a0d18deaaed778。
固定2026-04-01—2026-10-12，299请求/299最大尝试，2MiB/598MiB/新增2GiB；
目的地data/private/research-v1/market-v2-20261013-002，continue_on_error=true、每成员一次。
真实API实际299；没有自动重试、重定向、扩大日期、购买权限、诊断HTTP、订单或私有破坏性删除。

## 采集与准入

297 COMPLETE、2 FAILED、0 UNKNOWN、0 UNATTEMPTED；297成功回执通过read_capture/capture_status。
两份index_basic(market=CSI)均IDENTITY_CALENDAR_EMPTY；空响应Raw与claim/result保留，未重发/改写。
stock_basic原生CNY、SSE2320/SZSE2905/BSE349；日历各195自然日、128开市日且一致；
index_classify真实31、src=SW2021；31份index_member_all返回5914行、严格is_new/有效日/归属验证。
真实daily706576行/128日、adj_factor708924行/128日、index_daily256行、suspend_d14行、stock_st201行。
这些是实际响应行数，当前池应有分母另按上市日和原生证券身份计算；不以返回行数宣称历史完整覆盖。
总响应Raw字节75,276,227，远低于598MiB；每响应均流式限2MiB，未命中行限/截断/秘密/时钟/容量熔断。

失败导致capture-import缺基准身份，采用最小离线修复：现有make_capture_bundle增加benchmark_bundle输入，
先完整验证旧bundle，再仅选缺少的index_basic。旧2身份hash：
2970ad96dd2fab36648b0e59a58d811e69c66e9331b6a6c8e0425c10ea4ee274、
5d49c0c546261a022df849f510aa93e0e06532a3faa160b5d45b5a031baf4f86；原取得时间2026-10-13 03:43 UTC，
原market=SSE、同窗口/同基准/同研究日历；原plan/approval/claim/result/Raw逐hash校验，不改原来源。
V1→V2仅指数身份可不绑定股票队列；目的、窗口、基准列表、日历、时序和4项证据仍严格绑定，
旧股票身份/价格不能借此跨池，USER_DECLARED身份不能补缺。FAILED从不升级。

修复源码SHA68c94e144d5fbdf245547c2b0146ca7835915d8b；离线新implementation hash：
13a0110b7a28a4d7d1ce62df6bd5820f560b0b154731fa74c2a0ba05beb48d5e。
它与真实执行D8分开；原执行许可不授权新版任何新API。当前299已全部消费，下一次真实请求另批明确范围。

## 可复现依据

原机器计划和失败状态均不改。原capture-import加可选--benchmark-bundle，不新建平台：

~~~bash
# 全部离线；路径为现有私有相对路径，不发布Raw、许可或个人记录。
uv run --offline --frozen astock research capture-import \
  --capture-dir data/private/research-v1/market-v2-20261013-002 \
  --benchmark-bundle data/private/research-v1/capture-20261012-v1-1-attempt-4/a621f1e750ce2b7490786edf84ce68ada9c0e0a43ae5ec306ca9119beef6c111.bundle.json
uv run --offline --frozen astock research radar \
  --bundle 64f88be1c6058c7fae56585c2f6ce2cfe417b78051065b74645714d1c35ecf53 \
  --as-of 2026-10-14T02:34:35.207270+00:00 \
  --store data/private/research-v1/market-v2-20261013-002/research.duckdb \
  --output reports/private/research-v1/market-v2-20261014-002 \
  --public-output docs/research/results/2026-10-14-real-market-v2
~~~

发布使用现有白名单，完整MD/JSON在Git；不含Journal、持仓、成交、个人备注、人工观察或原始路径。
默认参数未改；报告CURRENT_POOL_WITH_GAPS、5574当前身份、31行业、1347全量合格/10展示。
末日已上市5573，价格5561、缺12，1只窗口后上市；20日有效5519、MA60有效5440。

18只实际股票覆盖5板块/12行业及正负收益，直接JSON Raw+stdlib statistics/math重算
收盘、复权20日收益、MA20、MA60、平均成交额CNY、成交活跃比，共108项通过。
配置相对容差1e-11/绝对容差1e-9（math.isclose取较大界）；最大绝对差约2.98e-8为成交额量级的舍入差。
NUMERICAL_CHECK.json保存每股票期待值、实际差与256份价格/因子Raw来源hash。
不调用生产features/screening计算作为期待值；样本为规则化跨板块/行业强弱选择，非个人观察清单。

重复同Store/参数/as-of报告字节digest相同；用相同原Raw及4项侧证据导入独立新DB，
再由新对象重推导/逐SQL行比对并运行同一service，完整私有报告digest相同。
独立DB重建仍使用同一生产adapter，软件测试和18股独立算术共同补充；不宣称第三方独立验证供应商原始真实性。

## 检查与保全

针对性64 passed（83.93s），含8项新增指数复用/边界回归；Doctor、12合同与v2九合同PASS。
初次新测试fixture缺少临时父目录，修正后最终64全通过；未跳过/删除重要回归或放松安全验证。
源码68c94e1全量本地回归1183 passed、1 warning（1396.86s）；后续仅状态/报告/验证文档变化。最终HEAD CI以PR实际记录为准，不以旧1175冒充。
原155655保护文件changed=0/missing=0；原106关联391文件和001全部5文件hash继续核查不变，
002新capture链/Raw另冻结899文件hash供交付前复核。没有覆盖旧Store或日志。

新002目的地含原Raw、保留副本、主Store/报告和独立重建DB：921,038,692字节；私有完整MD/JSON 104,593,097字节；合计1,025,631,789字节，小于2GiB。公开投影约12.5MiB另计全项目容量。

最终本地回归后盘点15个确认根（仓库及仓库外历史工作目录、测试/模拟目录），complete=true/error0：逻辑35,026,736,672字节，去重inode文件blocks 36,063,379,456字节；352,344文件/1,848数据库。另52个已知散落临时文件1,021,112逻辑字节。50GB目标/100GB上限内。盘点为此时文件stat，pytest保留轮换会变化；不将APFS共享extent或目录blocks视为已测，容量变化不表示手工清空旧数据。

实际CLI capture-import --benchmark-bundle重放通过，返回相同规范化bundleID；幂等导入没有重写来源。交付前496个Git可见文件明文/编码/解码凭据检查无违规，公开投影无个人路径/Journal/手工观察；git diff --check通过。
