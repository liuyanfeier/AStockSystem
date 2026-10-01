# Phase 1A Transport Audit — 2026-10-01

Base: `975bacd9c6fe8e61e13b0e453be2cd076ed19998`. Scope: credential-free security audit only. No SDK execution, real token, `.env`, successful data response or market-row persistence.

## Official documentation and inspected artifact

The [official HTTP API manual](https://tushare.pro/document/1?doc_id=130) describes `http://api.tushare.pro` and JSON `api_name`, `token`, `params`, `fields`. It documents code/message/data responses. It does **not** establish an authoritative HTTPS support guarantee.

[PyPI metadata](https://pypi.org/pypi/tushare/json) identified Tushare **1.4.29** at inspection time. Downloaded the [wheel](https://files.pythonhosted.org/packages/33/3e/d426a56e5feac9b0aaada1c6b0745ed03422d4a713295e0bbb44c8ea86fe/tushare-1.4.29-py3-none-any.whl) into memory, verified its advertised SHA-256, and statically read `tushare/pro/client.py`. Did not install/import it; project dependencies and lock remain unchanged.

Artifact SHA-256: `82554af953ea5ac3d8771d42330493181031c7e68dccce03a491c7356e9ba4b2`.

Observed source defines `__http_url = 'http://api.waditu.com/dataapi'` and calls `requests.post` at `<base>/<api_name>`. Thus this inspected release uses a different HTTP host/path from the manual. The commented localhost URL is not the active default. Neither plaintext endpoint was called.

## Observed technical behavior

Manually POSTed a REST-shaped stock_basic request to **https://api.tushare.pro**, requesting only `ts_code` with empty params. The only token values were the empty string and the literal deliberately-invalid test value. Normal CA/hostname validation stayed enabled; redirects disabled; no HTTP fallback.

| Token mode | UTC capture time | HTTP / provider code | TLS / redirect | Data |
|---|---|---|---|---|
| Empty | 2026-10-01T03:05:33.713021Z | 200 / 40101 | TLSv1.2 / none | null |
| Deliberately invalid | 2026-10-01T03:05:33.963582Z | 200 / 40101 | TLSv1.2 / none | null |

Both responses were JSON objects with code, data, detail, msg and request_id keys; only safe structural observations are recorded here, not provider payloads. No Location header. Certificate subject `*.tushare.pro`, issuer `ZeroSSL RSA DV SSL CA 2`; default certificate validation succeeded.

Initial probes at 03:02:32Z returned ConnectError. Fresh-client retry with `httpx.Client(verify=True, follow_redirects=False, trust_env=False, timeout=20)` succeeded as above. A separate empty-token system-curl POST also returned 200/40101, no redirect and ssl_verify_result=0. The initial connectivity failure was not hidden and was not solved by disabling TLS checks.

For a manual repeat, use a fresh verified httpx client for each of the two fixed token modes and POST JSON `{api_name: stock_basic, token: <empty-or-deliberately-invalid>, params: {}, fields: ts_code}` to the HTTPS URL. Never load settings, environment tokens or `.env`; never print/save raw response bodies. This live audit is outside pytest/CI. Local scratch observations stay under ignored `.tools/phase1a-audit/`.

## Gate, inference and limitations

**Technical HTTPS gate: PASS for Phase 1A foundation work.** Observed certificate validation and REST-shaped structured authentication rejection establish present technical reachability. They do not establish official HTTPS support, real-token compatibility, entitlements, historical completeness, uptime, future certificate behavior or successful data retrieval. Both token modes receiving the same error does not prove invalid-token handling beyond the observed rejection.

Inference: a future dedicated HTTPS client may be feasible, but its design and real-credential use require Phase 1B review. Do not instantiate the default SDK with a real credential. Current repository transport accepts only `httpx.MockTransport`, sends an empty token, rejects non-HTTPS endpoints and all 3xx responses, and exposes only typed sanitized errors. Mock tests prove these local safeguards; they do not verify the provider's future behavior.
