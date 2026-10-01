# Phase 1C.0 Identity Bootstrap

This phase creates identity governance from the accepted local Phase 1B captures.
It does not implement Phase 1C.1 slices or historical curation.

## Offline validation

```sh
scripts/uv run --offline --frozen pytest
scripts/uv run --offline --frozen astock doctor
scripts/uv run --offline --frozen astock data contracts --catalog v2
scripts/uv run --offline --frozen astock data identity specs
```

Python contract loading requires an explicit `catalog_version`. The historical
probe stays pinned to v1. Typed schemas and no-clobber publication helpers are
available for later reviewed curation; they do not download or curate market data.

## Evidence and bounded admission

Review the direct official BSE mapping table, pilot attachment, both switch
notices and exchange opening notice. Store the complete exact pair extract and
attachment locally under ignored `data/private/phase1c0/authority/`. A reviewed
`BSEEvidence` JSON records pinned URLs, retrieval time, pairs, six pilot pairs,
effective dates and evidence hashes. Never substitute search snippets or infer
pairs from digits. This local file is an operator-reviewed trust boundary.

```sh
scripts/uv run --offline --frozen astock data identity bootstrap \
  --authority data/private/phase1c0/authority/reviewed-evidence.json --live
```

`--live` permits exactly one mapping HTTP attempt, with TLS verification and no
retry. A durable no-clobber attempt marker consumes the budget before the POST;
failure needs review. Existing successful capture is reused on subsequent runs.
All 15 stock_basic probe partitions must already exist and verify against local
lineage. Missing raw evidence stops the operation without fetching a replacement.

A private anomaly audit precedes capture/admission. Pair-set disagreement prevents
admission. Validated identity/venue/quarantine rows are written in one transaction.
Unresolved identifiers stay verbatim, without IDs. Immutable review summaries
remain ignored locally; only sanitized aggregates belong in `docs/reviews/`.

## Later review gates

Provider delist-date interpretation remains open: no invented exclusive endpoint.
Changed admitted metadata needs review. Historical facts must resolve through
identity **and** venue boundaries and obey usage/availability restrictions before
Phase 1C.1 approval. This bootstrap does not promote valuations to strict PIT alpha.
