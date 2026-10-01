# Data Contract

## Dataset requirements

每个未来数据集必须在接入前定义下列项目；不满足的记录应拒绝或隔离，并写数据质量日志，不得静默修补。

| 项目 | 必须明确的含义 |
|---|---|
| source | 供应商／官方文档标识、接口或原文定位、使用权限；多源不能静默混合 |
| natural key | 业务身份、来源以及版本键；证券身份不依赖公司名称 |
| time fields | 事件、报告期、发布、可用、有效和实际获取时间；注明精度 |
| availability | 采用何种证据确定当时可知；不以报告期代替公开时间 |
| revision | 保留原版本，追加新版本、修订来源与发现时间 |
| unit | 价格币种、股／手、元／万元、百分比／小数；转换必须可追溯 |
| timezone | 时间戳带时区；入库规范 UTC，市场日历与展示使用 Asia/Shanghai |
| null policy | 未知、未发布和不适用必须区分；不能把 NULL 改成 0 |
| duplicate policy | 同键同内容可幂等跳过；同键异内容拒绝并记录，不能最后写入覆盖 |
| quality checks | 主键、缺失、类型、单位、时间顺序、有效区间、跨源差异与覆盖范围 |
| PIT behavior | 对决策时点筛选当时可用版本，再按当时有效状态解释 |

## Time semantics

- **Event time**：事件发生时间；行情使用成交／bar 时间，财务使用 `period_end` 描述报告期。Phase 0 无财务表，不给无报告期的数据强加该字段。
- **Publication time (`published_at`)**：来源首次公开该版本的时间。只有日期时要保留原精度，不能编造盘中发布时间。
- **First availability (`available_at`)**：在声明的研究模式下，证据支持的最早可用时点；不得早于该版本公开时间。
- **Effective time**：事实或规则适用的时间范围，例如 `valid_from/valid_to` 或 `effective_from/effective_to`。已公布但尚未生效的规则不能提前执行。
- **First observed / retrieval time**：本系统首次收到来源版本的时间。未来原始接入元数据必须保存此时间和原始对象定位／校验值。

历史“公开信息可知”研究与“本系统实际捕获”研究必须显式区分：前者仅在有来源证据时重建公开可用时点，后者不得早于系统首次收到数据。不得用今天的下载时间伪称历史公开时间，也不得用历史公告时间假装本系统当时已捕获信息。接入前需在数据集元数据中声明模式、证据与精度；Phase 0 未建立这些接入元数据表；Phase 1A 新增的治理表仅存追溯信息，不代表已接入数据。

`published_at` 可以为 NULL，但 `available_at` 不能缺失：未知发布时间不能用事件日猜测可用时点。若无法提供有依据的保守可用时点，该记录不能进入可回测数据。仅有公告日期的记录不能支持盘中研究。

时间戳采用 DuckDB `TIMESTAMPTZ`，查询连接应显式使用 UTC。DATE 为交易所本地日历日期，不进行跨时区平移。

## PIT and revisions

状态与规则区间采用 **[from, to)**，NULL 的结束表示当前版本尚无已知结束日期，不表示未来永远有效。记录修订时追加版本，不能就地缩短旧区间来改写历史知识。

时点查询至少需要 `available_at <= decision_at`；再选择指定来源下当时已知的最新版，并检查该版本的有效区间。多来源冲突、同一适用范围规则重叠、同可用时点异内容必须拒绝静默选取。基础 SQL 不实现这些查询或跨行重叠检查，Phase 1 必须补充相应审计与测试。

保留历史退市、ST、停牌、板块、行业与指数成分。`security_master` 是版本化基础身份记录，并不能单独覆盖全部状态历史；专门历史数据集在 Phase 1 定义。

## Execution availability

`market_rule_history.sell_delay_trading_days` 仅表示买入后变得可卖所需的最少后续交易日数。买入日为第 0 日，之后按适用交易所的开市日计数，周末／休市日不计。0 仅表示这一限制不额外推迟可卖日期；NULL 表示未知，不能解释为 0。该字段不保证成交，也不描述现金清算、交收或可取资金时间。当前不保留现金交收字段；未来如有明确需求，应另建字段并定义其时间单位、日历与起算事件，不能从可卖延迟推导。

EOD 使用完整收盘后数据，不能模拟同日收盘前决策／成交。Pre-close 必须使用当时留存的部分日行情与行业状态；不允许用完整收盘数据替换。成交时间还必须满足数据实际可用时间及适用交易规则。

## Reproducibility and retention

未来派生结果记录输入版本／校验值、代码 commit、配置版本、生成时间及 run ID。失败候选也保留。原始数据尽量只追加；错误结果通过新版本及修正说明处理，不改写旧报告。

质量日志的 `observed/expected/details` 禁止包含秘密。文本规则与来源标识提供存储位置，不能替代官方证据审核。基础 DDL 的 CHECK 只保证局部格式／顺序；规则正确性、区间重叠和供应商历史覆盖仍需应用层验证。

## Phase 1A contract catalog and time types

`config/contracts/v1/*.yaml` contains twelve Tier-A `DatasetContract` v1.0 definitions. `required_fields` specifies requested columns, not universal nonnull constraints. Natural keys apply within a provider capture; future stored identity must also include source and retrieval/version. Nullable key components such as `suspend_timing` require explicit normalization before ingestion. Fetch partitions and quality checks are proposed plans, not implemented download/validation jobs.

Each contract cites the official endpoint documentation checked on 2026-10-01. `max_rows: null` means undocumented/unknown, never unlimited. Documented caps are not completeness guarantees: future fetchers must detect truncation and audit partition coverage. Official update windows are descriptive, not publication evidence or availability guarantees. All policies remain `UNKNOWN_UNTIL_EVIDENCE`. No production timestamps are assigned.

`RecordTimes` separates `event_date`/`event_at`, `published_at`, `available_at`, exact `retrieved_at`, `availability_basis` and `time_precision`. Aware datetimes are required; persist UTC, retain local event dates. Precision values are DATE, MINUTE, SECOND, MICROSECOND and UNKNOWN; declare the weakest source precision rather than inventing seconds. Supported evidence bases:

- `MARKET_CLOSE_RECONSTRUCTED`: audited reconstruction from market close, with source-specific release lag.
- `PROVIDER_DOCUMENTED_SCHEDULE`: documented schedule with independently validated conservative handling.
- `SOURCE_PUBLICATION`: verified source publication evidence.
- `CONSERVATIVE_NEXT_SESSION`: explicit conservative calendar-based policy.
- `OBSERVED_CAPTURE`: actual system observation; available_at cannot precede retrieved_at.
- `EXECUTION_FACT`: private execution fact with verified event/knowledge evidence.
- `UNKNOWN`: retain raw metadata, leave available_at null, exclude from decision/backtest inputs.

The nullable staging type does not relax Phase 0 tables' required available_at. Promotion into research tables requires evidence and an eligible timestamp. SQL table changes for market records and automatic reconstruction are deferred.

## Raw objects, lineage and privacy

Future append-only, source-shaped captures use:

```text
data/raw/<provider>/<dataset>/run_id=<id>/
    part-000.parquet
    manifest.json
```

Never overwrite a capture. Record SHA-256 of exact stored bytes, a schema hash using a future documented canonical field/type encoding, exact retrieval time, row count, event-date bounds and sanitized parameters. `RawObjectManifest` currently validates metadata shape only; there is no writer or checksum computation pipeline. Content/schema hashing, atomic writes, aggregate run-count reconciliation and retry/idempotency rules need Phase 1B design/review. Contract hashes must use a documented canonical encoding before real ingestion.

Migration 002 links manifest `(run_id, dataset)` to ingestion runs. Parameters have a narrow typed allowlist; drop credentials, headers, unknown/nested fields and invalid values before serialization. Audit dates use ISO format; future provider-wire conversion to YYYYMMDD remains unimplemented. Errors retain only category and numeric HTTP/provider codes. Never log response bodies/messages, exception text, or Pydantic `.errors()` input values. Existing free-text Phase 0 quality logs also require this discipline; their DDL does not automatically sanitize text.

Public Git must never contain provider tokens, broker credentials, balances, holdings, personal executions, private reports or raw provider datasets. Store private work in ignored `private/` or `data/private/`; raw/curated/warehouse captures and generated reports stay ignored. Commit only lightweight sanitized summaries under `docs/reviews/`. Ignore rules reduce accidents; explicit staging and diff audits remain mandatory.
