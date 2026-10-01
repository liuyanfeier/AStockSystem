# AStockSystem — Phase 1C Core Market Data Foundation 设计 v1.0

> 日期：2026-10-01  
> 前置状态：Phase 1B implementation accepted；Phase 1B.1 accepted；历史 identity findings retained  
> 目标：建立 2013-01-01 ～ 2026-09-30 的 A 股核心市场历史数据基础，做到可追溯、可恢复、可重建、身份可解释。  
> 明确不做：策略、信号优化、回测选优、券商接入、自动下单、分钟数据、新闻/公告、财务 PIT。

## 0. Executive decision

Phase 1C 不一次性交给 Codex 全量执行。拆成四个 Gate：

```text
1C.0  Identity Bootstrap + Contract v2 + Curation Governance
      ↓
1C.1  Bounded Historical Slice + Curation + Resume Test
      ↓
1C.2  Full Core-Market Backfill (2013-01-01 → 2026-09-30)
      ↓
1C.3  Rebuild / Completeness / Incremental Acceptance
```

每个 Gate 单独 Review。**当前只授权 1C.0。** Phase 1B 已证明 provider 数据不是“ts_code 永远不变”的简单世界。先冻结身份、venue、contract 和 curation 语义，再下载几千万行数据。

## 1. Phase 1C 的核心原则

三层事实必须分开：

```text
Raw provider fact
    ↓
Curated provider-native fact
    ↓
Research-resolved fact
```

Raw 保存 Tushare 原样字段和值语义。Curated 做类型转换、日期转换、单位命名明确化、lineage、provider identifier 保留，并尝试解析 security_id；unresolved 不删除。Research-ready 只使用 `identity_status = RESOLVED` 的行。

任何 unresolved / ambiguous 都进入 quarantine，不能 drop、猜测、根据名称合并、根据数字尾数映射。

## 2. 一个重要架构修正：证券身份和交易 venue 分开

Phase 1B.1 已证明：

```text
security_id ≠ ts_code
```

Phase 1C 再增加：

```text
security identity ≠ provider list_date ≠ market venue effective date
```

北交所是典型案例。北交所于 2021-11-15 开市交易；但部分原精选层公司的 `list_date` 早于 2021-11-15。北交所规则又规定相关上市时间在监管意义上可自精选层挂牌连续计算。因此系统必须同时保存：

```text
provider_list_date
venue_trading_start
```

对于 AStockSystem 的 **BSE 交易市场研究 universe**：

```text
venue_trading_start = max(provider_list_date, 2021-11-15)
```

这只表示“该证券什么时候进入北交所交易 venue 的研究范围”，不改写监管意义上的连续上市时间。

任何 Tushare `.BJ` 历史记录若发生在 2021-11-15 之前：

```text
retain raw
classify PRE_BSE_LEGACY
exclude from BSE market universe
```

不要删除。

## 3. Identity Bootstrap

### 3.1 stable `security_id`

Phase 1C 使用 deterministic UUID5（固定项目 namespace）作为初始 security_id。初始 listing episode seed：

```text
exchange
+
identity anchor identifier
+
provider_list_date
```

SSE / SZSE：如果 normalized provider code 唯一、listing episode 无冲突，`anchor_identifier = provider ts_code`。

BSE：如果存在官方 old/new mapping，`anchor_identifier = official old code`，因此旧代码和 920 新代码得到同一个 `security_id`。

不允许 `name`、current industry、last digits、current market label 参与 security_id 合并判断。

### 3.2 once allocated, never recompute silently

deterministic UUID5 用于第一次 allocation 与 clean rebuild。一旦某 `security_id` 已进入本地 identity registry，provider 后续更正 list_date / name 不允许静默生成新的 security_id；必须作为 identity revision REVIEW。

## 4. BSE old/new code source policy

Tushare 当前提供 `bse_mapping`，输出 `name / o_code / n_code / list_date`，单次最大 1000 条，总数据量文档称 300 以内。

Phase 1C 使用它作为 structured convenience source，但 **不是唯一 authority**。必须与北京证券交易所官方“新旧代码对照表”逐 pair 比较。要求 old code / new code 集合完全匹配才允许批量 admission。

BSE 映射页的 `list_date` 不是代码 switch date。

Switch date：6 个试点证券为 `2025-05-06`，其他存量映射为 `2025-10-09`。试点名单必须来自北交所官方公告，不允许通过代码模式猜测。

非试点的 identifier interval：

```text
old.BJ  [provider_list_date, 2025-10-09)
new.BJ  [2025-10-09, ∞)
```

试点：

```text
old.BJ  [provider_list_date, 2025-05-06)
new.BJ  [2025-05-06, ∞)
```

这里的 interval 用于 **identifier effective truth**。knowledge time 仍按当前系统实际 observation 记录，不能伪装成 2025 年当时已抓取。

## 5. `T600018.SH`

保持 `UNRESOLVED`：raw 保留；不 strip `T`；不 map 为 `600018.SH`；不分配到当前 `600018` security_id；不影响 2013+ backfill，因为该 episode 在研究窗口开始前已结束；若未来需要 2006 年以前历史，再专门解决。

```text
T600018.SH is quarantined
but is NOT a Phase 1C blocker.
```

## 6. Contract Catalog v2

Phase 1A 的 `config/contracts/v1/` **不可修改**。Phase 1C 新建：

```text
config/contracts/v2/
```

任何生产命令必须显式指定 contract version。禁止 implicitly use latest，以保证历史 run 可重现。

### 6.1 v2 datasets

Phase 1C 核心 catalog：

```text
stock_basic
bse_mapping
trade_cal
daily
daily_basic
adj_factor
stk_limit
stock_st
suspend_d
```

`index_*` 暂不进入本 Gate；在核心股票仓库通过后再接。

### 6.2 `stock_basic` v2 fields

请求：

```text
ts_code
symbol
name
fullname
market
exchange
curr_type
list_status
list_date
delist_date
```

明确不把 `industry / area / act_name / act_ent_type / is_hs` 作为 Phase 1C historical research fields，因为这些 current snapshot 字段不可直接回填为历史 PIT。

### 6.3 `daily` v2

请求：

```text
ts_code
trade_date
open
high
low
close
pre_close
change
pct_chg
vol
amount
ah_vol
ah_amount
```

Tushare 当前说明 `ah_vol / ah_amount` 从 2026-07-06 开始有数据，历史 NULL 保留 NULL。

### 6.4 `daily_basic` v2

一次 backfill 很昂贵，因此 Phase 1C 直接请求当前文档完整常用字段：

```text
ts_code
trade_date
close
turnover_rate
turnover_rate_f
volume_ratio
pe
pe_ttm
pb
ps
ps_ttm
dv_ratio
dv_ttm
total_share
float_share
free_share
total_mv
circ_mv
limit_status
```

但“下载了”不等于“全部 PIT backtest eligible”。后面有单独使用政策。

### 6.5 `stk_limit`

保留：

```text
trade_date
ts_code
pre_close
up_limit
down_limit
asset_type
exchange
```

Raw 保留 provider 返回的所有 asset type。Curated A-share price-limit table 只接受 `asset_type == STK AND identity RESOLVED`。

Tushare 2026-09-07 changelog 已记录 ETF 涨跌停数据迁移到 `etf_limit`，因此不能把历史 `stk_limit` 的 asset scope 当作永远不变。

## 7. Curation specs

Provider Contract 和 Curated Schema 分开。新建：

```text
config/curation/v1/
```

至少包含 `daily / daily_basic / adj_factor / stk_limit / stock_st / suspend_d`。

每个 spec 明确：source contract version、source column、target column、logical target type、nullable policy、unit、identity requirement、research usage class。

这样空 provider response 也可以生成有类型的 empty curated table，不依赖 PyArrow 从空数组猜类型。

单位命名必须显式，例如：

```text
vol         → volume_hands
amount      → amount_cny_thousand
total_share → total_share_10k
total_mv    → total_mv_10k_cny
```

换手率和股息率目标列使用 `_pct`。不做 rounding。

## 8. Curated file layout

Raw 仍保持 request-level immutable objects。Curated 不复制 2 万个小文件，而是按 dataset + year 合并：

```text
data/curated/tushare/<dataset>/
    year=2013/
        curation_run=<uuid>/
            part-000.parquet
    year=2014/
        ...
```

Phase 1C 初期：one curated Parquet per dataset-year。

Curated 文件 immutable。重建产生新的 `curation_run`，不覆盖旧文件。

## 9. 新增 governance tables

Phase 1C 需要 migration 005（具体编号按 repo 当前状态）。

### 9.1 `security_venue_history`

建议字段：

```text
security_id
venue
effective_from
effective_to
provider_list_date
provider_delist_date
source
available_at
retrieved_at
evidence_source
```

用途：SSE/SZSE listing venue、BSE 2021-11-15 venue boundary，以及未来 venue transition。

### 9.2 `curation_run`

```text
curation_run_id
dataset
partition_key
started_at
finished_at
status
code_commit
config_hash
input_manifest_hash
identity_snapshot_hash
row_count
resolved_count
quarantined_count
```

### 9.3 `curated_object_manifest`

```text
object_id
curation_run_id
relative_path
sha256
schema_hash
row_count
min_event_date
max_event_date
```

### 9.4 `identity_quarantine`

```text
quarantine_id
dataset
provider_identifier
event_date
reason
raw_object_id
curation_run_id
first_seen_at
```

reason 至少支持：

```text
NO_IDENTIFIER_MAPPING
AMBIGUOUS_IDENTIFIER
NON_NORMALIZED_IDENTIFIER
OUTSIDE_IDENTIFIER_INTERVAL
PRE_BSE_LEGACY
ASSET_OUT_OF_SCOPE
```

### 9.5 `dataset_date_audit`

```text
dataset
trade_date
curation_run_id
provider_rows
resolved_rows
quarantined_rows
duplicate_count
cap_hit
status
details_safe
```

public review 只提交 aggregate。

## 10. Curated common lineage fields

每一行 curated market fact 至少能追到：

```text
source
provider_identifier
security_id nullable
identity_status
event/trade date
raw_object_id
curation_run_id
retrieved_at
source_record_hash
```

`source_record_hash = SHA256(canonical provider row)`，用于判断同 natural key 的 same content vs revision/conflict。

## 11. Curated table semantics

### 11.1 `daily_bar`

建议列：

```text
security_id
provider_identifier
trade_date
open
high
low
close
pre_close
change
pct_chg
volume_hands
amount_cny_thousand
after_hours_volume_hands
after_hours_amount_cny_thousand
...lineage
```

Raw value 不做舍入。

### 11.2 `daily_basic_snapshot`

列名必须带单位，例如：

```text
turnover_rate_pct
turnover_rate_free_pct
pe
pe_ttm
pb
ps
ps_ttm
dividend_yield_pct
dividend_yield_ttm_pct
total_share_10k
float_share_10k
free_share_10k
total_mv_10k_cny
circ_mv_10k_cny
```

### 11.3 `adjustment_factor_observed`

只保存 provider factor + lineage，不在此表直接生成 qfq/hfq。

### 11.4 `price_limit_daily`

仅 resolved A-share STK：

```text
security_id
trade_date
pre_close
up_limit
down_limit
exchange
```

### 11.5 `risk_warning_daily`

```text
security_id
trade_date
type
type_name
```

不从股票名称推断 ST。

### 11.6 `suspension_daily`

完整保留：

```text
security_id
trade_date
suspend_type
suspend_timing
```

null timing 和 intraday timing 不能混。

## 12. Historical availability / backtest eligibility

Phase 1C 不允许用“今天下载到的历史值”自动宣称当年 PIT。每个 dataset 明确 usage class。

`daily`: `SIGNAL_ELIGIBLE_NEXT_SESSION`。完整 EOD bar T 只能服务 T+1 或更晚决策，禁止同日收盘成交回测使用完整 T bar。

`daily_basic`: `CURRENT_RECONSTRUCTION`。全部字段先下载，但 Phase 1C **不授权历史 alpha backtest 使用 PE/PB/PS/股息率**。这些估值字段可能涉及后续财务修订语义，真正 PIT 验证留给 Phase 1E。市场/流动性字段可用于数据研究和现状重建，但在 Phase 1E 前不要把其历史表现称为严格 PIT 策略证据。

`adj_factor`: `AUDIT_RECONSTRUCTION_ONLY`。不用 current observed factor 作为唯一历史 signal 调整机制。

`stk_limit`: `EXECUTION_CONSTRAINT_ONLY`。

`suspend_d`: `EXECUTION_FACT_ONLY`。

`stock_st`: `UNIVERSE_RISK_STATE_ONLY`。Tushare 当前明确提示早期历史可能无法完全补齐；Phase 1C 必须保留 coverage caveat。

## 13. 价格复权：不用未来 anchor

Tushare 官方 qfq 公式是：

```text
price_t × factor_t / latest_factor
```

如果 `latest_factor` 来自未来，价格 level 会随着未来 corporate action 改写。我们未来趋势/突破研究不应依赖这种未来 anchor。

### 13.1 causal adjustment

使用 `daily.pre_close` 构造只依赖当时信息的连续价格 scale。对于同一 security：

```text
scale_0 = 1

scale_t =
    scale_{t-1}
    × close_{t-1}
    / pre_close_t
```

然后：

```text
causal_open_t  = open_t  × scale_t
causal_high_t  = high_t  × scale_t
causal_low_t   = low_t   × scale_t
causal_close_t = close_t × scale_t
```

如果 `pre_close_t == close_{t-1}`，scale 不变；发生除权除息时，scale 从当日开始变化。

这是一条 forward/causal continuous-price chain，不是 Tushare 的 qfq quote。

### 13.2 adjusted return

官方 `daily.pct_chg` 已按除权后的昨收计算。验证：

```text
causal_close_t / causal_close_{t-1} - 1
≈
pct_chg_t / 100
```

### 13.3 adj_factor 作为独立审计

还应验证：

```text
(close_t * factor_t) /
(close_{t-1} * factor_{t-1}) - 1
≈
pct_chg_t / 100
```

若长期大量不一致：BLOCK / REVIEW，不能自动选一边覆盖另一边。

## 14. Full backfill partition strategy

历史冻结区间：

```text
2013-01-01
→
2026-09-30
```

2013~2014 是 warm-up。未来策略成绩期仍从 2015 或更晚开始。

### 14.1 one dataset-year = one BACKFILL run

例如：

```text
daily / 2019
daily_basic / 2019
adj_factor / 2019
...
```

每年约 240~250 个 open dates，因此现有 `part-000 ... part-999` 足够。

每个 open date 一次 request，哪怕返回 0 rows 也保存一个 immutable empty capture，证明请求执行过。

### 14.2 Why not one run for 2013~2026

原因：part 编号上限、crash resume、年级 audit、单年重做、config/version boundary、Review 更简单。

## 15. Request pacing

Phase 1C 继续：

```text
single process
single thread
>= 1.25s between live attempts
```

约 48 requests/min。

虽然部分接口当前权限允许更高频率，但 `stock_basic` 当前文档为 50/min，Tushare 2025-11-10 changelog 还记录账号不允许多个 IP 同时在线提取；个人 Mac overnight backfill 不需要追求极速。

目标：稳定、可恢复，不是最快。Phase 1C 不并发 API。

## 16. Process lock

新增本地 exclusive lock，例如：

```text
data/warehouse/.backfill.lock
```

用原子 O_EXCL 创建。若已有锁，拒绝第二个 live backfill。不自动覆盖。提供显式 stale-lock 检查命令，不允许 silent force unlock。

## 17. Resume semantics

Backfill run 的完成事实来自：

```text
raw_object_manifest.request_params.trade_date
```

恢复时：

```text
planned open dates
-
already captured dates
=
remaining requests
```

不能只看 last part number。

同一个 `dataset + year + config_hash + contract_version` 如果是失败/中断 run，可显式 resume。如果 contract/config/code 语义已改变，使用 new run_id，不得往旧 run 追加不同语义数据。

## 18. Provider row-cap rule

仍然：

```text
row_count == documented max_rows
→ POTENTIAL_TRUNCATION ERROR
```

不能认为“刚好满 6000 = 完整”。如果未来 `daily / daily_basic / stk_limit` 某日碰 cap，Phase 1C 停止该 dataset-year，先设计明确 repartition。不要临时逐股票暴力抓取。

## 19. Completeness model

完整性不是：

```text
len(daily) == len(daily_basic) == len(stk_limit)
```

Phase 1B 已证明这种要求不成立。

按日期构造分类：

```text
expected venue securities
observed daily
full-day suspended
listing boundary
delisting boundary
identity quarantine
asset out of scope
pre-BSE legacy
provider-only cross-table row
unexplained missing
```

Daily expected universe 的基础是 `security_venue_history`，不是今天的 stock list。BSE before 2021-11-15 不属于 BSE universe。

Phase 1C.1 必须真实验证 Tushare `delist_date` 对最后交易日的语义。在验证前，rows near delist boundary → `BOUNDARY_REVIEW`，不要自作主张 `+1 day`。

## 20. Cross-table DQ

每个 dataset-year 完成后：

- daily ↔ daily_basic：交集 close 在 tolerance 内相等；差集只报告和解释，不强求相等。
- daily ↔ stk_limit：resolved A-share STK 的 pre_close 在 tolerance 内相等。
- daily ↔ adj_factor：factor > 0，并做 causal-return / factor-return / pct_chg audit。
- stock_st：identity resolved，type/type_name consistent。
- suspend_d：full-day `S` 通常没有 daily row；例外保留 REVIEW。
- identity：2013+ target A-share rows unresolved traded row → ERROR，除非明确 quarantine/out-of-scope。

## 21. DQ severity

ERROR 至少包括：checksum mismatch、schema contract violation、natural-key conflicting duplicates、row cap hit、raw lineage break、curated lineage break、ambiguous identity、unresolved in-scope traded security、BSE official/provider mapping conflict、cross-table value mismatch beyond audited tolerance、secret leak。

WARN / REVIEW 可包括：known pre-window T600018、provider-only status row、delist boundary not yet classified、stock_st early-history coverage caveat。

不能通过设置阈值把 ERROR 变成 PASS。

## 22. Backfill atomicity

每个 raw request 沿用：

```text
temp
→ fsync
→ checksum
→ no-clobber publish
→ manifest DB transaction
```

每个 curated dataset-year：

```text
build temp curated parquet
→ DQ
→ checksum
→ no-clobber publish
→ curated manifest
→ curation_run SUCCEEDED
```

如果 DQ ERROR，不 promote 为 research-current；但可保留 failed output 供私有 audit。

## 23. Research-current pointer

不要用文件覆盖表达“最新”。DuckDB 保存 `curation_run status`，Research view 只选择 approved/succeeded curation_run。未来 revision 完成后再切换。这样旧研究仍可按旧 curation_run 重现。

## 24. Phase 1C subgates

### 1C.0 — Identity Bootstrap + Contract v2 + Governance

允许少量网络：

```text
Tushare bse_mapping: 1 bounded request
BSE official mapping/notice: public evidence fetch
```

优先复用现有 Phase 1B stock_basic raw，不全量 backfill。

交付：contract v2、curation specs、migration 005、security_id allocation、BSE identifier history、security venue history、identity quarantine、curation governance、synthetic tests、sanitized review。

### 1C.1 — Bounded Historical Slice

建议真实切片：

```text
2013-01
2020-08
2021-11
2025-05
2025-10
2026-07
2026-09
```

覆盖 warm-up 早期、创业板制度变化附近、BSE 开市、BSE 两次代码切换、`ah_vol/ah_amount` 新字段和最近市场。

必须人为中断一次再 resume，验证 raw → curated、identity、venue、DQ、causal adjustment、delist/list boundary。

### 1C.2 — Full Backfill

通过后才拉 2013-01-01 → 2026-09-30：

```text
daily
daily_basic
adj_factor
stk_limit
stock_st
suspend_d
```

trade_cal / stock_basic / identity 先完成。

### 1C.3 — Acceptance

要求 clean rebuild from raw、same curated logical hashes、resume test、selected raw re-fetch consistency、full coverage report、identity quarantine report、causal adjustment audit、incremental next-session update、CI green。

之后才允许 Phase 2 Market / Sector Radar。

## 25. Phase 1C PASS Gate

最终 Phase 1C 只有满足以下条件才 PASS：

1. v1 contracts 未被改写；
2. v2 contract 明确；
3. BSE mapping provider vs official 无未解释冲突；
4. stable security_id allocation 可重建；
5. BSE 2021-11-15 venue boundary 正确；
6. 2025 两批代码 switch 正确；
7. T600018 保持 quarantine；
8. full history raw lineage 完整；
9. dataset-year resume 可用；
10. no cap truncation；
11. curated one-year rebuild logical hash 稳定；
12. identity unresolved in-scope traded rows = 0，或明确 REVIEW 阻塞；
13. daily cross-check errors = 0；
14. causal return audit 通过；
15. daily_basic valuation fields 尚未被错误标记为 PIT alpha-ready；
16. Phase 1B / historical reports 未被重写；
17. GitHub CI 全绿；
18. 无策略 / backtest / broker/order code。

## 26. 当前不做的事情

Phase 1C 不做：index universe、industry、theme、financial PIT、announcements、news、minute bars、market regime、selection、strategy、portfolio、broker、orders。

## 27. 当前官方/Provider evidence（2026-10-01 核查）

Tushare：

- `stock_basic`  
  https://tushare.pro/document/1?doc_id=25
- `trade_cal`  
  https://tushare.pro/document/1?doc_id=26
- `daily`  
  https://tushare.pro/document/1?doc_id=27
- `daily_basic`  
  https://tushare.pro/document/2?doc_id=32
- `adj_factor`  
  https://tushare.pro/document/2?doc_id=28
- `stk_limit`  
  https://tushare.pro/document/2?doc_id=183
- `stock_st`  
  https://tushare.pro/document/2?doc_id=397
- `suspend_d`  
  https://tushare.pro/document/2?doc_id=214
- `bse_mapping`  
  https://tushare.pro/document/2?doc_id=375
- qfq/hfq formula  
  https://tushare.pro/document/2?doc_id=146
- Changelog  
  https://tushare.pro/document/1?doc_id=9

BSE：

- Exchange introduction / 2021-11-15 opening  
  https://www.bse.cn/company/introduce.html
- 2021 listing-rule transition  
  https://www.bse.cn/important_news/200010914.html
- official old/new code table  
  https://www.bse.cn/service/code_mapping.html
- pilot list  
  https://www.bse.cn/important_news/200025487.html
- pilot switch 2025-05-06  
  https://www.bse.cn/important_news/200025603.html
- remaining switch 2025-10-09  
  https://www.bse.cn/important_news/200026735.html

## 28. Final design principle

Phase 1C 不追求“尽快下载完”，而追求：

> **任意一条 2013~2026 的市场记录，都能回答：它原来叫什么、当时在哪个 venue、对应哪个 security_id、从哪个 raw object 来、是否有身份歧义、为什么可以或不可以进入研究。**

这才是后面 Market Regime / Industry / Strategy 可以信任的数据地基。
