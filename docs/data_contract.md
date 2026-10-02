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

## Phase 1B probe boundary

The approved versioned plan covers eight endpoints, four fixed historical anchors
and the latest open SSE date resolved within September 2026. Request fields are
explicit; stk_limit additionally requests pre_close, asset_type and exchange.
Exact credential endpoint validation is separate from documentation URL validation:
HTTPS api.tushare.pro, default/443 port, root path, no userinfo/query/fragment/redirect.
Code 2002 is official PERMISSION; 40101 AUTH remains an observed classification.

Migration 003 transactionally rebuilds both lineage tables to extend CHECKs while
preserving parent/child rows. Only PROBE governance rows and raw Parquet are persisted.
Canonical config hash is SHA-256 of compact sorted-key UTF-8 JSON of plan and the
ordered eight contract definitions (dates ISO); schema hash is the same encoding
of ordered Arrow (field name, type string) pairs. Raw SHA hashes exact stored Parquet
bytes. Logical fingerprint separately hashes sorted columns then canonical JSONL
rows ordered by natural-key encoding with full-row tie-breakers; values/nulls are
not replaced. Parquet may promote integral numeric values in mixed numeric columns
without changing numeric meaning; original provider scalar types appear in audit.

Atomic publication uses a closed/fsynced temporary file and POSIX no-clobber hard
link, followed by temp unlink and directory fsync. This supplies atomic visibility
without os.rename's overwrite race. DB registration follows publication; orphan
completed files survive registration failure and are not marked registered. No part
is overwritten; new probe batches use new UUID runs. Counters, byte/schema hashes,
row counts and sidecars are verified after a batch.

For every historical capture, availability_basis=OBSERVED_CAPTURE and
available_at=retrieved_at. This records observation now, never historical event-day
knowledge. Phase 1B captures are ineligible for historical backtests. No curated
market schema is frozen. Exact token bytes are checked in generated raw bytes,
decoded Parquet values, sidecars and aggregate review drafts before public export.
Errors/logs never include provider bodies or exception inputs. No runtime logs are
written by this probe. Public metadata is aggregate-only; private/raw paths remain ignored.

## Phase 1B.1 identity boundary

Provider-native identifier validation (nonblank exact text) and normalized A-share
validation (six digits plus SH/SZ/BJ) are separate. Keep native values in immutable
raw captures; normalization findings require explicit classification and evidence,
never filtering, prefix removal or overwriting. Raw DQ PASS does not imply identity
PASS: the probe gate also checks `identity_status` and remains PARTIAL for unresolved
normalization. Existing Phase 1B reports retain their original metrics and status.

`security_identifier_history` uses the eleven fields and append/resolve rules in
[Security Identifier History](security_identifier_history.md). Mapping admission
requires authoritative evidence, exact effective intervals, independently allocated
security IDs and unambiguous source scopes. Select knowledge versions before event
intervals. OBSERVED_CAPTURE availability cannot precede retrieval; publication dates
alone cannot establish an intraday timestamp. No real mappings are seeded here.

This bounded audit reads existing captures only and fetches public evidence, never
market-data API responses. Private full-row findings stay ignored; the public review
contains only the three anomaly identifiers, classifications, evidenced transitions
and resolution limits. Historical backfill and Phase 1C require separate approval.

## Phase 1C.0 addendum: identity and typed curation governance

Catalog v1 remains immutable. Python callers must supply `catalog_version='v1'`
 or `'v2'`; there is no implicit latest catalog. Phase 1B continues using v1.
Catalog v2 adds `bse_mapping`, extends daily/daily_basic fields and excludes
current industry/ownership classifications from historical identity research.
No new stock_basic snapshot is needed: the existing v1 identity columns are
sufficient for this bootstrap; fullname/currency are not fabricated retrospectively.

`config/curation/v1/` declares Arrow types, null preservation, provider units,
identity requirements and dataset usage. Empty schemas come from these specs.
No values are rounded or scaled implicitly. Daily after-hours fields permit
historical nulls before their documented 2026-07-06 start.

| Dataset | Permitted research usage |
| --- | --- |
| daily | SIGNAL_ELIGIBLE_NEXT_SESSION, subject to actual availability |
| daily_basic | CURRENT_RECONSTRUCTION; historical valuations are not strict PIT alpha |
| adj_factor | AUDIT_RECONSTRUCTION_ONLY |
| stk_limit | EXECUTION_CONSTRAINT_ONLY |
| suspend_d | EXECUTION_FACT_ONLY |
| stock_st | UNIVERSE_RISK_STATE_ONLY |

Identity admission requires verified local raw lineage, a reviewed direct BSE
extract and exact equality of every provider/official old-new pair. Neither names
nor code suffixes establish identity. Mapping effective dates do not imply
historical knowledge availability. Observation timestamps remain current.

Migration 005 contains governance only. There are no curated market row tables
or historical download/curation runners. Future writers must register validated
immutable objects against curation runs and verify quarantine raw-object references.
The private authority file is a human-reviewed evidence boundary, not an automatic
web scraper or an assertion that arbitrary JSON is official evidence.

## R1-G1 exact completion proof

A slice COMPLETE is admitted only with exactly one raw manifest for its run,
matching receipt object UUID, dataset, typed params, immutable request plan and
contract. Actual file hash/schema/count/event bounds, exact sidecar object set and
capture-contract identity must all match. Reject missing evidence, duplicate JSON
keys, type coercion and symlinks (including directory/metadata components).
Generic raw runs may have multiple valid parts; empty run sets and zero-manifest
runs never pass. A valid zero-row object follows its existing endpoint policy.

Resume, completion, promotion, curation and DQ share this proof. Invalid historical
receipts remain unchanged; new operation failure evidence is separate. Recovery
never creates absent sidecars/contracts. Normal admission requires a unique exact
007 binding. `astock data slice audit --batch UUID` opens the warehouse read-only,
requires no token and never captures, claims or migrates. Explicit
`--legacy-preflight` checks unbound old evidence but grants no normal admission or
review approval. Verification commit/time are separate from capture provenance.
R1-G1 implements and tests these guarantees on synthetic isolated storage only;
DB process locking/atomic claim remain R1-G2, real deployment/validation R1-G3.


## R1-G1 independent review corrections

PENDING must describe an unexecuted request: zero attempts, no object/failure,
pre-created RUNNING run with no finish/error and zero request/raw/row counters,
no registered raw manifest and no accepted binding. Batch preflight and claim
reject contradictory execution evidence with `PENDING_EXECUTION_CONFLICT`;
upgrade/client construction/fetch cannot precede this check. Preserve all old
facts. Pre-created `started_at` alone is not execution evidence. IN_FLIGHT local
recovery and FAILED/UNCERTAIN blocking retain their existing semantics.

Normal007 admission and repeat upgrade require the exact migration ID, persistent
main tables, required columns/types/nullability and PK/UNIQUE/FK/CHECK guarantees.
The locked DuckDB engine compares normalized catalog structures against an isolated
in-memory reference built from versioned SQL; CHECK expressions are parsed catalog
values, not SQL source-string comparisons. Invalid/shadow schemas fail closed with
`BINDING_SCHEMA_REQUIRED` (upgrade name conflicts: `UPGRADE_SCHEMA_CONFLICT`).
No source database is repaired. Before publishing version7, the explicit upgrade
checks the same structure within its transaction; only that internal path can
omit the not-yet-published version record. See the [G1 correction report](reviews/2026-10-02-phase1c1-r1-g1-fix-review.md).


## R1-G2 writer ownership and crash policy

Disk mutation requires an exclusive OS guard acquired before connecting/preflight,
held through local publication and finalization. Read-only audit uses a shared guard
and BEGIN snapshot; never upgrade reader ownership. Stable lock files remain ignored.
Claim atomically reserves the attempt and ingestion request counter before any fetch.
Uncertain committed claims are never retried; orphan/extra/incomplete local evidence
blocks rather than being registered, overwritten or reconstructed. Slice directories
must contain exactly the registered part and both complete metadata files; generic
multipart raw rules remain unchanged. Preserve historical pre-created RUNNING/start
times. See the [writer/lifecycle policy](phase1c1_writer_lifecycle.md) for coverage,
crash outcomes and the unimplemented R2 generation/quarantine/append-only audit
requirements. G2 validates synthetic storage only; it grants no real-data acceptance.
