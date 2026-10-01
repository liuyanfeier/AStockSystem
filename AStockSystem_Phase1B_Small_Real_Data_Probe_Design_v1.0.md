# AStockSystem — Phase 1B Small Real-Data Probe 设计 v1.0

> 日期：2026-10-01  
> 前置状态：Phase 1A ACCEPTED  
> 目标：第一次安全使用真实 Tushare Token，验证“真实 provider → raw capture → lineage → 数据质量审计”的闭环。  
> 明确不做：历史全量回填、生产 curated/warehouse 市场表、策略、信号、回测、券商、自动下单。

## 0. Phase 1B 的定位

Phase 1B 不是建库阶段，而是 **Reality Check**。我们现在要回答：

- 真实 Token 是否能通过 HTTPS-only client 工作？
- 真实接口字段是否与文档一致？
- 返回数据量是否会碰上 row cap？
- NULL / 重复 / 字段顺序 / 类型到底是什么样？
- 历史 ST、停牌、涨跌停、复权因子与日线如何对应？
- 同一历史请求重复获取是否逻辑一致？
- raw object 和 lineage 能否在不泄露 Token 的前提下完整保存？

只有这些问题通过，Phase 1C 才允许开始 2013→现在的全量核心市场回填。

## 1. 开始前必须完成的三个修正

### 1.1 精确锁定 Tushare endpoint

Phase 1A 只强制 HTTPS，但当前代码理论上仍可能接受 `https://some-other-host.example`。真实 Token 第一次发送前，credential boundary 必须缩到：

```text
scheme   = https
hostname = api.tushare.pro
port     = default 443 only
path     = empty or /
query    = none
fragment = none
userinfo = none
redirect = forbidden
```

实现上最好只有一个生产常量：

```text
TUSHARE_HTTPS_ENDPOINT = "https://api.tushare.pro"
```

真实 client 不接受用户任意传 host。继续保持：

```text
verify=True
follow_redirects=False
trust_env=False
```

不得因为连接问题关闭 TLS、改成 HTTP 或自动走未知代理。不要做 TLS 证书 fingerprint pinning；证书会轮换。

### 1.2 增加 `PROBE` ingestion mode

当前 `ingestion_run.mode` 只有 `AUDIT / SNAPSHOT / INCREMENTAL / BACKFILL`。Phase 1B 的真实样本不应该被误认为生产 snapshot，因此加入：

```text
PROBE
```

并创建新 migration，**不要直接改写已经通过 Review 的 migration 002**。如果 DuckDB 不方便修改 CHECK constraint，使用事务化、安全、带测试的表重建 migration，并证明已有 synthetic rows 不会丢失。

### 1.3 enrich `stk_limit` contract

当前 contract 新增请求字段：

```text
pre_close
asset_type
exchange
```

最终请求：

```text
trade_date
ts_code
pre_close
up_limit
down_limit
asset_type
exchange
```

理由：Tushare 官方说明 `stk_limit` 覆盖全市场、包含 A/B 股和基金；`asset_type` / `exchange` 帮助确认记录资产范围，`pre_close` 可与 `daily.pre_close` 做独立交叉校验。不要只用 `ts_code` 后缀推断资产类型。

## 2. 真实 Token 的安全使用

用户不要把 Token 发给 ChatGPT 或 Codex 对话。Token 只存 Mac 本地 `.env`。如果本地未配置 `TUSHARE_TOKEN`，live probe 必须 fail closed，并提示：

```text
TUSHARE_TOKEN is not configured.
Configure it locally outside chat/model input.
```

不要让 Codex 询问“把 token 发给我”。内部使用 `SecretStr` 或等价秘密类型。

以下对象全部禁止包含 Token：

```text
repr
exception
provider error object
ingestion_run
raw_object_manifest
manifest.json
review markdown
CLI output
Git diff
logs
```

Probe 完成后，对本轮生成的 raw run directories、sidecar manifests、review artifact draft、runtime logs（若有）扫描真实 token 的精确字节串，只输出 `SECRET_SCAN: PASS/FAIL`。如果 FAIL，不提交 review artifact，隔离泄漏文件，Phase 1B BLOCKED。

## 3. Real HTTPS client

新增一个很小的真实 Tushare REST client，例如：

```text
src/astock/data/tushare_client.py
```

不要使用官方 SDK 进行 credential-bearing request path，因为当前公开 SDK / HTTP 文档仍以 plaintext HTTP 为默认路径，而 Phase 1A 只证明 HTTPS 当前技术可达。

职责仅限：

```text
typed request
→ HTTPS POST
→ provider envelope validation
→ typed table response
```

不要让 transport class 写数据库、写文件、做业务转换或指标计算。

安全约束：

```text
exact endpoint pinned
TLS validation enabled
no redirect
no proxy/env trust
single-threaded
no request body logging
no response body logging on errors
```

Phase 1B 请求量很小，不做并发。建议至少 1.25 秒一次 live call，约 48 calls/min，兼容较低频率接口。

Retry 只允许 ConnectTimeout / ReadTimeout / ConnectError / HTTP 5xx，最多 2 次 attempt。AUTH / PERMISSION / redirect / invalid schema / contract violation 不 retry。

## 4. Provider response validation

Tushare REST 成功响应必须至少满足：

```text
HTTP 200
provider code == 0
data is object
data.fields is list[str]
data.items is list[list]
每一行长度 == len(fields)
fields 无重复
```

真实请求显式指定 `fields`，不依赖 provider 默认列集合。

正式增加安全错误类型：

```text
AUTH
PERMISSION
TRANSPORT
REDIRECT
PROVIDER
INVALID_RESPONSE
```

官方 REST 文档说明 `code=2002` 是权限问题；Phase 1A 观测到 `40101` 对空/无效凭据返回鉴权失败。因此：

```text
2002  → PERMISSION
40101 → AUTH（observed behavior）
其他非0 → PROVIDER
```

仍只保存 provider numeric code，不保存 provider `msg` 原文。

## 5. 本阶段只 Probe 8 个 endpoint

只允许：

```text
trade_cal
stock_basic
daily
daily_basic
adj_factor
stk_limit
stock_st
suspend_d
```

暂不调用 index_*、财务、行业、公告、新闻、分钟、资金流、龙虎榜。先验证 A 股基础证券、价格、状态和可交易性数据链路。

## 6. Probe 日期

使用 **4 个固定历史 anchor + 1 个 recent anchor**。

### A — 2015-07-08

历史集中停牌压力样本。上交所后续官方材料确认 2015 年 7 月上旬异常波动期间存在上市公司集中申请停牌现象。主要检查 `suspend_d`、日线缺失解释和历史 security coverage。

### B — 2019-06-25

Tushare `stk_limit` 官方文档示例日期。主要检查：

```text
daily.pre_close
vs
stk_limit.pre_close
```

以及 `asset_type / exchange`。

### C — 2020-08-24

创业板交易制度切换日期。深交所官方确认该日起存量创业板股票涨跌幅限制同步调整为 20%。这里只验证 provider 数据表达，不在 Phase 1B 写历史规则引擎。

### D — 2025-08-13

Tushare `stock_st` 官方文档示例日期。主要检查 `stock_st`、security identity resolution、ST 与 price-limit 数据交叉。

### E — latest completed session as of 2026-09-30

不要硬编码“9 月 30 日一定开市”。先用 `trade_cal` 在：

```text
2026-09-01 .. 2026-09-30
```

中解析 `max(cal_date where is_open = 1)`。解析结果写入 local probe manifest 和 sanitized review 摘要。

## 7. `stock_basic` Probe

为了避免默认 `list_status=L` 造成幸存者偏差，明确请求：

```text
exchange ∈ {SSE, SZSE, BSE}
list_status ∈ {L, D, P, G, UN}
```

最多 15 个 partition。每个 request 请求 contract 完整字段。如果返回行数 **恰好等于 max_rows=6000**，判定 `POTENTIAL_TRUNCATION`，不能静默认为完整。

公开 Review 只提交 aggregate：

```text
count by exchange/status
observed market labels
duplicate count
null count
code format summary
```

不提交完整股票清单。

## 8. 五个日期的横截面 Probe

每个 anchor date 请求：

```text
daily
daily_basic
adj_factor
stk_limit
stock_st
suspend_d
```

统一 `trade_date=<anchor>`，不要逐股票循环。大约 30 次请求，加上 trade_cal、stock_basic partitions、重复一致性请求，总调用仍很少。

## 9. Raw persistence

Phase 1B 第一次真正写 raw data，但不写生产 curated / market warehouse tables。

每个 dataset 一个 `PROBE` ingestion_run，一个 dataset 的多个 request 属于同一 run。例如：

```text
data/raw/tushare/daily/run_id=<uuid>/
├── part-000.parquet
├── part-001.parquet
├── part-002.parquet
├── part-003.parquet
├── part-004.parquet
└── manifest.json
```

Raw Parquet 保留 provider 字段名称和值语义，不做投资层转换。

写入必须：

```text
write temp
→ close
→ checksum
→ atomic rename
→ manifest insert
```

失败时不能留下看似合法的半文件。重复 probe 创建新的 run_id，不能覆盖旧 part。

## 10. Phase 1B 暂时不持久化 curated

这里修正早期设想：

> **Phase 1B 只持久化 raw + lineage，curated transformation 仅在内存中做 audit preview。**

因为我们正是要观察真实 NULL、字段类型、provider anomalies、BSE code、历史状态和 row cap。在观察前冻结 curated schema 属于反向设计。

Phase 1C 再基于真实证据冻结：

```text
daily_bar
daily_basic
adj_factor
price_limit_daily
risk_warning_daily
suspension_daily
```

## 11. Raw hash 与 logical fingerprint

`raw_object_manifest.sha256` 表示 **最终保存的 Parquet 文件 bytes hash**，不要把它描述成 HTTP response 原始字节 hash。

另外计算一个仅用于 audit 的 deterministic logical fingerprint：

```text
provider values/nulls preserved
canonical column order
rows sorted by contract natural key
deterministic JSONL-like encoding
SHA-256
```

Phase 1B 暂时只把 logical fingerprint 放入 sanitized review artifact，不扩 permanent DB schema。

## 12. 重复一致性 Probe

重复请求：

```text
daily
trade_date=20190625
```

比较两次独立 capture 的：

```text
fields
row_count
natural-key set
logical content SHA-256
```

期望 logical hash 一致。Raw Parquet byte hash不强制相同。如果 logical hash 不同，保留两次 raw capture，Phase 1B = PARTIAL，不得静默 normalize 掉差异。

## 13. Data Quality Audit

至少输出以下审计。

### Provider / contract

```text
requested fields
observed fields
row count
documented cap
distance to cap
natural-key duplicates
null counts
```

`row_count == documented max_rows` 直接判 `POTENTIAL_TRUNCATION = ERROR`。

### daily

检查：

```text
high >= max(open, close, low)
low <= min(open, close, high)
price > 0
vol >= 0
amount >= 0
close - pre_close ≈ change
100 * change / pre_close ≈ pct_chg
```

容许 provider rounding，只记录 mismatch count 和误差摘要，不自动“修正”。

### daily_basic ↔ daily

报告：

```text
intersection
only_daily
only_daily_basic
close_mismatch
```

### stk_limit ↔ daily

对 `asset_type == STK` 交集检查：

```text
stk_limit.pre_close ≈ daily.pre_close
```

按 exchange 分组统计，不依据涨停百分比重算。

### adj_factor ↔ daily

报告：

```text
intersection
only_daily
only_adj
null/nonpositive factor
```

要求因子正数，但异常不自动删除。

### stock_st

检查：

```text
natural key duplicate
type/type_name consistency summary
code can resolve against stock_basic all-status universe
```

不要通过股票名称字符串重新判断 ST。

### suspend_d

区分：

```text
S = suspension
R = resumption
suspend_timing null = full-day style record candidate
suspend_timing non-null = intraday timing
```

对于 `S + suspend_timing is null` 检查当日是否通常没有 daily row。这里只做 audit，不先写成硬业务规则；任何例外保留并 Review。

### BSE

公开 Review 只记录 count、observed suffix/pattern summary、unexpected pattern count。禁止基于当前代码规则猜历史旧代码或自动生成 mapping。

## 14. Availability

Phase 1B 下载的是今天回看历史得到的数据，因此历史 raw capture：

```text
retrieved_at = 真实抓取时间
availability_basis = OBSERVED_CAPTURE
available_at = retrieved_at
```

它只表达“本系统现在看到了这份历史记录”，绝不表达“事件当日市场已能看到这个版本”。

因此：

> **Phase 1B 数据不得进入任何历史策略回测。**

## 15. Local database

Phase 1B 可以在默认 ignored DuckDB 中建立 migration 1~3 和 lineage rows，但不得建立生产 `daily_bar / strategy_signal / trade_plan / backtest / portfolio / orders` 等表。

Probe run 失败：

```text
status = FAILED
finished_at = exact time
safe error category/code
```

已经成功保存的 raw object 不删除，以供审计。

## 16. CLI

建议：

```bash
astock data probe plan
astock data probe run --live
astock data probe status
```

`plan/status` 默认离线。真正网络请求必须显式 `--live`。不要添加 `sync / backfill / sync-all`。

## 17. Permission Gate

8 个 endpoint 必须全部真实成功。若 provider code = 2002，则记录 `PERMISSION`；可以继续安全收集其他 endpoint 证据，但最终 Phase 1B 不得 PASS。

当前官方权限信息显示 `stock_st` 至少需要 3000 积分，多数基础接口 2000 起；5000 积分档提供更高频率和常规数据无总量上限，因此仍建议 5000 积分档。

## 18. Public Review Artifact

Git 只提交：

```text
docs/reviews/YYYY-MM-DD-phase1b-review.md
docs/reviews/YYYY-MM-DD-phase1b-observed-schema.json
```

允许包含：

```text
commit SHA
run IDs
dataset
request count
row count
observed field names/types
null/duplicate counts
cap warning
cross-table mismatch counts
logical fingerprint
DQ status
permission status
```

禁止 Token、raw provider body、完整股票清单、完整行情 row、raw Parquet、账户/个人数据。

## 19. PASS Gate

只有全部满足才 PASS：

```text
1. exact api.tushare.pro host pinning
2. no redirect / no HTTP fallback
3. PROBE ingestion mode
4. PERMISSION error category
5. stk_limit enriched fields
6. real-token HTTPS handshake succeeds
7. all 8 endpoints permission succeeds
8. no exact row-cap hit without repartition
9. raw Parquet + manifest + lineage can be reconstructed
10. duplicate historical request logical hash matches
11. DQ audits complete
12. token exact-byte scan PASS
13. raw/private files ignored by Git
14. GitHub only has sanitized review artifacts
15. CI synthetic tests green
16. no production curated market schema
17. no strategy / backtest / broker code
```

任何无法解释的 schema mismatch、row truncation、identity ambiguity、cross-table mismatch 都不能被“清洗掉”来换 PASS。

## 20. Phase 1B 后

PASS 后才进入 Phase 1C，冻结核心市场表并开始 2013-present 全量回填。PARTIAL 则只修 provider/data issue，不进入全量。

## 21. 参考资料

Tushare：

- HTTP API / provider code 2002  
  https://tushare.pro/document/1?doc_id=40
- 权限与频次  
  https://tushare.pro/document/1?doc_id=290
- stock_basic  
  https://tushare.pro/document/1?doc_id=25
- trade_cal  
  https://tushare.pro/document/1?doc_id=26
- daily  
  https://tushare.pro/document/1?doc_id=27
- daily_basic  
  https://tushare.pro/document/2?doc_id=32
- adj_factor  
  https://tushare.pro/document/2?doc_id=28
- stk_limit  
  https://tushare.pro/document/2?doc_id=183
- stock_st  
  https://tushare.pro/document/2?doc_id=397
- suspend_d  
  https://tushare.pro/document/2?doc_id=214

Exchange anchor：

- 深交所：2020-08-24 创业板涨跌幅制度调整说明  
  https://www.szse.cn/aboutus/trends/news/t20200821_580924.html
- 上交所：关于 2015 年 7 月上旬集中停牌的后续说明  
  https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20160527_4121070.shtml

---

## Phase 1B 核心原则

> 第一次真实数据不是为了“尽快拿到历史库”，而是为了尽早发现我们对数据的误解。

如果 Phase 1B 能把错误暴露在几十次 API 请求阶段，就不要把它拖到几百万行数据以后才发现。
