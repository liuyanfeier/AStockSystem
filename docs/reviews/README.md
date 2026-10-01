# Review Artifacts

Commit lightweight human/AI review summaries and manifests in `docs/reviews/`.
Use descriptive date-prefixed names such as `YYYY-MM-DD-phase0-review.md`.
Existing Phase 0 acceptance evidence remains in `docs/phase0_report.md`.

A summary or manifest should identify the reviewed commit, scope, commands and
results, limitations/open questions, and artifact paths or checksums when relevant.
Do not include credentials, account details or raw market datasets. Append dated
corrections or add a new summary rather than rewriting historical conclusions.

Large/generated runtime reports remain under ignored `reports/`; raw, curated and
warehouse data remain ignored. Link or describe those artifacts in a small review
manifest when needed; do not force-add runtime output to Git for a review.

This is a storage/documentation policy only. No report generator, upload service,
artifact publisher or retention infrastructure is implemented.
