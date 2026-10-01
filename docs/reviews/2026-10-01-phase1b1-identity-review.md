# Phase 1B.1 Identity Resolution Audit

## Status and boundary

Implementation complete; identity audit/data gate **PARTIAL**: two anomalies are
explained, one remains unresolved. No Phase 1C, backfill or new market-data API
requests. Existing Phase 1B batch `a3771e7b-3b2c-4fa0-a730-4e296a5268ac` only.
A private local report was created before public evidence lookup or implementation.
Exact rows and counterpart details remain ignored under `data/private/phase1b1/`.
This public artifact contains no full raw rows or full stock lists.

## Three anomalies

| Anomaly identifier | Classification | Authoritative transition date | Resolved? |
|---|---|---|---|
| `T600018.SH` (SSE/D) | **UNRESOLVED**; related legacy provider anomaly candidate | No provider alias effective interval verified | **No**; native value retained, no normalized mapping assigned |
| `835305.BJ` (stock_st, 2025-08-13) | **HISTORICAL_IDENTIFIER_CHANGE** → `920305.BJ` | **2025-10-09** | **Yes**, historical/current-code mismatch explained; no real security_id seeded |
| `839680.BJ` (stock_st, 2025-08-13) | **HISTORICAL_IDENTIFIER_CHANGE** → `920680.BJ` | **2025-10-09** | **Yes**, historical/current-code mismatch explained; no real security_id seeded |

The two exact new identifiers each occur once in the existing all-status universe;
current delisted records are retained. This explains current-universe join failures,
not automatic permission to normalize historical rows or promote research data.

## Authoritative evidence

- [BSE official old/new table](https://www.bse.cn/service/code_mapping.html):
  rows **187** and **174** explicitly provide the two pairs above. Its listing-date
  column is not the switch date. Pairs were checked on the visible official page;
  no last-digit inference or blanket 83/87→920 conversion was used.
- [BSE remaining-stock switch notice, 2025-09-12](https://www.bse.cn/important_news/200026735.html):
  effective **2025-10-09**, independently verified on the official page.
- [BSE pilot launch notice, 2025-04-25](https://www.bse.cn/important_news/200025603.html):
  six pilot stocks switch **2025-05-06**; other 242 stocks continue old codes.
  [Pilot selection notice, 2025-04-11](https://www.bse.cn/important_news/200025487.html)
  identifies the six companies; neither anomaly belongs to that pilot. Both
  notices were checked through official-domain indexed text when direct fetches
  failed. Thus 2025-08-13 precedes these two stocks' actual switch.
- [SSE historical index notice, 2004-12-28](https://www.sse.com.cn/market/sseindex/diclosure/c/c_20150911_3984889.shtml)
  associates historical `600018` with the predecessor.
  [Issuer 2020 interim report](https://www.portshanghai.com.cn/wenku/www/202008/28170828nhmg.pdf)
  describes the successor's IPO/share-exchange absorption of the predecessor.
  [Issuer 2018 interim report](https://www.portshanghai.com.cn/wenku/www/202006/18100116hnjq.pdf)
  states the successor's **2006-10-26** listing. Official-domain indexed issuer
  text supports separate predecessor/successor review, not code-based identity equality.

## SSE finding and evidence limits

The local capture spells the native identifier **T600018.SH**, not T00018.SH.
[Tushare repository issue #1683](https://github.com/waditu/tushare/issues/1683)
reports T00018.SH for a matching historical record. Correspondence is an inference
from local attributes, not proof that the two vendor spellings are interchangeable.
This is a user-submitted issue, **not provider confirmation**; its proposed correction
and claim of relisting are not accepted as authority. No account identifier or full
issue text is reproduced here.

The native-format finding is real, but provider error versus intentional legacy
namespace remains unconfirmed. Do not strip the prefix, overwrite source identifiers,
or map the predecessor to today's `600018.SH` security_id. Exact provider alias
semantics/effective intervals and independently reviewed stable ID allocation remain
open; the predecessor's exact official termination notice was not verified.
No KNOWN_PROVIDER_ANOMALY label is asserted without sufficient confirmation.

## Identity model and validation

Migration 004 creates only `security_identifier_history` with all eleven required
fields. Exact source/type/identifier/exchange scopes, half-open effective intervals,
append-only knowledge versions, as-of resolution and transactional overlap checks
are implemented. Only observed knowledge is eligible: availability cannot precede
retrieval. Date-only publication evidence does not become an invented timestamp.
No real mappings are inserted. See [model semantics](../security_identifier_history.md).

Raw/source validation and normalized six-digit validation are separate; native
non-normalized identifiers survive storage. Source DQ PASS cannot make the data gate
PASS while identity requires review. Original Phase 1B raw objects and public reports
remain unchanged. Local migration preserved **8 runs / 47 manifests**, with **0 identity
rows**; the 20 inspected objects' byte hashes still match their original sidecars.

## Verification and review handoff

- Full offline pytest: **226 passed**; 16 added cases, including BSE pilot/general
  boundaries, disjoint code reuse, knowledge revisions, native Parquet retention,
  overlap rejection/rollback, migration preservation and unresolved-identity gate.
- Offline doctor, twelve contracts and bounded plan validation: **PASS**.
- Existing CI remains Python 3.12, locked dependencies, pytest and offline diagnostics,
  with an empty TUSHARE_TOKEN. Final pushed-revision CI is verified in the handoff;
  synthetic probe tests use MockTransport and are not a rerun of the real probe.
- Explicit staging only; private reports, real .env, credentials, databases, raw/
  curated/warehouse data, .tools and .venv are excluded and audited before commit.

**Phase 1C recommendation:** hold pending reviewer approval and the remaining provider
identity evidence. This audit does not close Phase 1B's other historical coverage or
availability limitations. Stop here; no Phase 1C implementation is authorized.
