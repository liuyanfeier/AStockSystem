# Research V2：市场与行业雷达

本批从已独立接受的PR #3 / edcc8f5开始，普通merge进入main
05479b523e3718d09e9b5b6b1773a3f318b1b0be，再建立codex/research-v2。
旧106次尝试和原始来源不重放、不重写；本批新的真实市场请求为0。
完整业务目标继续以[项目宪章](PROJECT_CHARTER.md)为准。

## 业务入口

使用已有五表Research Store、同一features/screen/service、观察卡与私有日志。
增加供应商当前上市池、板块比较、市场宽度、申万2021一级行业队列、前日变化及中文日报。
当前池不能当历史证券全集；当前行业成员也不是历史PIT行业或动态主题。

~~~bash
export PATH="$PWD/scripts:$PATH"
# 只显示固定299请求，不调用市场API：
uv run --offline --frozen astock research capture --plan config/research/market-v2-proposal.json
# 仅在新的实际整批授权后，才使用 --live --approval 私有匹配许可.json。
# 对保留完整响应，沿用现有捕获导入和独立Store：
uv run --offline --frozen astock research capture-import --capture-dir 私有捕获目录
uv run --offline --frozen astock research radar --bundle 实际bundleID \
  --as-of 带时区的截止时间 --store 私有独立Store.duckdb \
  --output reports/private/research-v1/radar \
  --public-output docs/research/results/新日期
# 全流程合成演示（闭合Mock，不读凭据、不调用真实市场）：
uv run --offline --frozen python scripts/research_v2_demo.py --work /private/tmp/独立新演示目录
~~~

按用户最新明确要求，`--public-output`发布可入Git的业务MD/JSON；采用白名单，删除私有路径、
实际许可内容、Raw、账户/持仓/交易/复盘记录。保留业务数值、来源hash、方法与缺口。
公开JSON将features重复来源hash列表合并为source_hash_sets，通过source_hash_set_id引用，
观察卡仍保留hash，全部业务指标不删减。发布器不自动commit/push；交付时将结果随代码提交。现有`report`的完整私有输出仍保留。
可直接审查的报告、数值验证与性能见[本批结果入口](research/results/2026-10-13-research-v2/README.md)。

## 来源、覆盖与行业口径

- 当前证券池由SSE/SZSE/BSE三个`stock_basic(exchange=...,list_status=L)`分区真实返回构建。
  保留原生代码、交易所、供应商market、上市日、状态、CNY币种，不根据后缀猜身份或板块。
  CURRENT_A_SHARE_L必须有三份绑定采集链，且universe集合与原响应完全一致。
  来源缺失时只能是PROVIDER_SAMPLE；无身份/日历/价格指标保持UNKNOWN。
- V2输入、计划与供应商contract显式新协议。V1模型默认字段与dump不变；旧manifest/plan/hash
  仍按旧协议验证。LOCAL_CAPTURE_BOUND仍验证plan/claim/approval/result/Raw链，不接受自报等级。
  本地TLS链不是供应商签名；合成来源不能成为真实市场证据。
- `daily`和`adj_factor`按每个实际开市日期批量查询。不使用未文档化offset/limit；命中行限、
  has_more或重复/冲突拒绝采用。需要重新分区时另建明确方案，不偷偷追加调用。
  因子10000、classification1000是本地安全上限，不是供应商承诺的分页/完整性上限。
- 上市不足窗口仍保留在池分母，排除上市前日期后判断连续尾窗；停牌/行情缺失不跨越补窗。
  每日覆盖分母是“当前池当日已上市成员”，不是返回行数，也不是当时历史全集。
  `source_coverage`逐日给出价格、因子、上市前排除与缺失代码；稀疏ST/停复牌缺席不代表正常。
- [Tushare日历文档](https://tushare.pro/document/2?doc_id=26)明确北交所参考沪深。
  V2将此作为显式参考依据，只有沪深窗口自然日历一致时使用，不伪造BSE API响应。
  北交所行情、因子、行业成员覆盖仍独立核验，不能据参考日历宣称已覆盖。
- `index_classify(level=L1,src=SW2021)`返回必须吻合固定31行业代码；成员按31个l1_code、
  is_new=Y分区。保留in_date/out_date；未知有效日不补造。重叠/缺分类冲突拒绝导入。
  当前池没有行业归属时列缺口；行业返回的池外证券另计，不篡改当前池。
  行业指标是个股等权均值、中位数与分布，不是市值加权行业指数。

## 市场、行业与候选如何解释

日报输出单日/5日/20日上涨下跌平盘、MA20/60、新20日高低、成交额与活跃/波动分布、板块宽度，
每个指标带有效分母和缺失数，原因可重叠；行业20日样本未覆盖已分类池时不标BROAD扩散。指数与宽度一致性、20日扩张/收缩只是描述；
超过50%表示多数，恰好50%为中性，不是已验证仓位规则。position_weight和risk_budget保持null，trade_eligible=false。

行业输出5/20日分布、宽度、均线比例、候选数/行业集中度、头部名单、同期相对基准及扩散标签。
强度变化比较当前与前日都具有20日指标的共同个股；单独记录change_denominator。
前日计算使用同一as-of来源、同一当前池/行业成员，不能冒充当时已知的报告或PIT复盘。
当前市场/板块宽度前日比较分别披露分母，分母变动可能影响比例。

仍沿用默认20/60筛选及同一排序。合格总数与top-N显示数分开，遗漏数、新出现/持续/退出全量记录。
银行等行业占候选多数时在观察卡明确共同风险；候选卡继续提供反面证据、触发观察、逻辑失效、
不交易条件和后续退出跟踪。财务/公告/催化尚未核实，不产生订单。

## 性能、版本与增量

先测逐股扫描，再改为一次按代码/交易所分组；输入成员判断也改为set。
同一Store对象最多复用一份同bundle/as-of/代码版本的256MiB编码预期，超过上限不缓存。
每次仍读SQL并检查全部保留对象hash；首次/新as-of/新代码/新对象重新Raw推导。
这不是持久缓存，不保证全市场大快照都能命中；首轮1000股Store与6000股特征分别有实测。

新来源导入生成新bundle，旧源和报告不覆盖。`radar --component 旧bundleID --revisions 私有选择.json`
组合已各自验证的来源；当前证券池以第一个bundle为准，池外旧成员另记。
相同值重复合并保留component_sources；冲突必须显式record-key→source-hash选择，不自动last-wins。
record-key可由`research.increment.revision_key`生成；因子回溯修订与身份/行业变化也是显式来源版本问题。
组合后重新检查完整自然日历、证券类别、上市日与交易日。

V2计划支持1日增量窗口；默认完整身份/行业刷新是45请求（1日daily+factor、其余43元数据/状态请求），
是可运行的保守起点，不是已批准的日更计划。当前299请求只覆盖初始128日窗口。
后续可以按明确版本复用较旧元数据并披露时间；本批不引入通用调度器或自动滚动采集。

## 实际业务边界

既有10股真实128日来源重新计算为有限样本雷达，240项原指标与上一版一致、4只候选不变；
没有真实行业来源，因此实际行业排名/轮动仍UNKNOWN。完整行业雷达当前只有合成软件示例。
[299请求整批方案](RESEARCH_V2_ACQUISITION.md)待新的用户批准；批准前不能宣称真实全市场验收。
下一业务重点仍为公司基本面/公告催化、候选交易计划和退出，不重开2013年以来Phase1历史工程。
