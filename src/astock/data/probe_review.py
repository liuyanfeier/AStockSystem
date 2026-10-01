"""Export only aggregate Phase 1B review evidence, after exact-token scanning."""

from pathlib import Path
from datetime import date

from pydantic import SecretStr

from astock.data.probe_audit import canonical_json
from astock.data.raw_writer import atomic_new_file, secret_scan


BASE_COMMIT = '46402ebb789da2e0ee884992cfed84337a30072b'


def export_review(root: Path, summary: dict, token: SecretStr, stamp: str):
    if date.fromisoformat(stamp).isoformat() != stamp:
        raise ValueError('Review date must be ISO date')
    if summary['secret_scan'] != 'PASS':
        raise ValueError('SECRET_SCAN: FAIL')
    public = dict(phase='1B', status=summary['status'], base_commit=BASE_COMMIT,
        implementation_commit=summary['code_commit'], batch_id=summary['batch_id'],
        resolved_recent_date=summary['resolved_recent_date'], anchors=summary['anchors'],
        runs=summary['runs'], captures=summary['captures'], errors=summary['errors'],
        cross_audits=summary['cross_audits'], repeat_consistency=summary['repeat_consistency'],
        lineage_reconciled=summary['lineage_reconciled'],
        raw_reconstruction_verified=summary['raw_reconstruction_verified'],
        secret_scan='PASS', stock_basic=summary.get('stock_basic'),
        availability_basis='OBSERVED_CAPTURE', backtest_eligible=False)
    schema = canonical_json(public)+b'\n'
    run_table = '\n'.join(f"| {dataset} | {r['status']} | {r['request_count']} | {r['row_count']} | {r['raw_object_count']} |"
                          for dataset, r in summary['runs'].items())
    text = f'''# Phase 1B Review — {stamp}

## Status and commits

Phase 1B: **{summary['status']}**, pending reviewer approval. Base: `{BASE_COMMIT}`.
Exact implementation: `{summary['code_commit']}`. Batch: `{summary['batch_id']}`.

## Scope and live transport

Dedicated REST client pins https://api.tushare.pro, TLS verification enabled,
redirects forbidden, environment proxies disabled. Single thread, at least 1.25s
between attempts, at most two attempts for connect/read timeout/connect error/5xx.
TLS errors are not retried. SDK is not used. No HTTP fallback. First request is
SSE trade_cal for 2026-09-01 through 2026-09-30; missing token blocks before storage.
AUTH classification for 40101 is observed Phase 1A behavior; permission 2002 is
[officially documented](https://tushare.pro/document/1?doc_id=40). Real transport
success is measured by successful captures, not inferred from empty-token probes.

Resolved recent date: {summary['resolved_recent_date']}. Historical anchors:
2015-07-08, 2019-06-25, 2020-08-24, 2025-08-13. Plan is capped at 47 logical
requests; retries can raise attempts to 94. No per-security loop or full backfill.

## Raw / lineage and permissions

| Dataset | Run status | Attempts | Rows | Objects |
|---|---|---:|---:|---:|
{run_table}

Unlisted endpoints were not reached. Failed-run safe error categories/codes are in
the adjacent aggregate JSON; no response body/message is published.
Migration 003 preserves populated 002 runs and FK-linked manifests, adding PROBE
and PERMISSION. Repeated migration is tested. Migrations 001/002 stay unchanged.
Raw byte hash means exact Parquet bytes, not HTTP response bytes. Atomic no-clobber
publication uses a POSIX hard link of a closed, fsynced temp file; unlike os.rename,
it cannot overwrite a concurrently created destination. Manifest insert follows
publication; completed orphan files survive DB failure for audit, never count as
registered objects. Sidecars record OBSERVED_CAPTURE and available_at=retrieved_at.

Lineage count reconciliation: {summary['lineage_reconciled']}.
Parquet checksum/schema/row counts and sidecar reconstruction: {summary['raw_reconstruction_verified']}.

## DQ and repeat consistency

Adjacent JSON contains requested/observed fields and types, per-capture null and
duplicate counts, documented caps/distance, exact-cap errors, OHLC/positive-price/
volume/amount checks, daily change and percentage errors, cross-table comparisons,
ST type labels and unresolved-code counts, suspension full-day candidates, BSE
pattern aggregates, and deterministic logical hashes. Price/change tolerance is
0.011 currency units; percentage tolerance is 0.011 percentage points. These cover
reported rounding only; mismatches are retained, not corrected. Missing price rows
are not imputed; cap hits, identity ambiguity, unexplained mismatches or permissions
prevent PASS. Provider values/nulls remain local; full stock lists/market rows are
never in review artifacts. Logical hashes canonicalize column order, natural-key
order and duplicate-key row tie-breakers; preserve value/null distinctions.

Repeat daily/20190625: {summary['repeat_consistency']}.
These captures reflect current observation of history, not event-day knowledge;
no Phase 1B data is eligible for historical strategy backtests.

## Secret / privacy audit

SECRET_SCAN: PASS for exact local token bytes in this batch's raw files, decoded
Parquet values, sidecars, local aggregate summary and review drafts. Token is only
read from local SecretStr settings; no secret printed, logged, serialized in metadata
or copied into Git. Local raw, default warehouse and private paths remain ignored.
No account, broker, balance, holding or personal execution data is used. Git staging
and exact-token scan must pass before review commit; CI gets no real token.

## Validation and CI

Local full-suite results and exact-commit GitHub CI evidence are appended after
verification. CI is synthetic, socket-blocked and offline after locked dependency
installation. Real probe is explicitly --live and never runs in GitHub Actions.

## Open questions / next gate

Review any aggregate DQ/permission/schema/coverage discrepancies before Phase 1C.
Unknown historical identity coverage and BSE code/calendar issues are not guessed.
HTTPS success, if observed, still does not establish an official support guarantee.
No production curated schema, history-wide backfill, strategy, backtest, broker,
orders or Phase 1C work. Stop after sanitized evidence push and exact-commit CI.
'''.encode('utf-8')
    draft_dir = root/'data/private/phase1b'/summary['batch_id']
    draft_md, draft_json = draft_dir/'review.md', draft_dir/'observed-schema.json'
    atomic_new_file(draft_md, lambda path:path.write_bytes(text))
    atomic_new_file(draft_json, lambda path:path.write_bytes(schema))
    if not secret_scan(token,[draft_md,draft_json]):
        raise ValueError('SECRET_SCAN: FAIL')
    destination = root/'docs/reviews'
    review = destination/f'{stamp}-phase1b-review.md'
    observed = destination/f'{stamp}-phase1b-observed-schema.json'
    atomic_new_file(review,lambda path:path.write_bytes(text))
    atomic_new_file(observed,lambda path:path.write_bytes(schema))
    return review, observed
