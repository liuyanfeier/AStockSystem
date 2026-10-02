# Phase 1C.1-R1 — Human-authorized batch revision

2026-10-02 · Base `26004ac573d6f66fe14cc63bb87b37543109cf22`.

The user explicitly authorized a single delivery containing:

1. Fix both G2 P2 findings: late unmanaged connection admission and inherited
   lock descriptors when another thread/context forks.
2. Check related connection/proxy/cursor, context/thread, fork, exception and
   process-death boundaries; fix defects within that scope and add regressions.
3. After engineering self-checks, verify a backup, migrate an isolated copy and
   accept existing 133 receipts, 181 raw, 252 old curated and frozen identity offline.

This supersedes this batch's intermediate stop/review prerequisites in the retained
R1 prompts and independent G2 review. It does not turn CHANGES_REQUIRED into PASS.
Multiple focused commits may be delivered together; failures within scope are
fixed and rechecked without a new permission request. Stop at batch completion or
a blocker that genuinely needs the user.

Hard limits remain: zero new market requests; no real capture/resume/replay;
original warehouse read-only, no original 007 or binding/audit writes; preserve
raw, curated, lineage, old receipts/attempts/timestamps and frozen identity.
Missing or contradictory evidence is recorded BLOCKED, never guessed or repaired.
No R2, Phase1C.2 or trading/research implementation.

Keep old specifications and historical reviews unchanged. Final delivery includes
problem-closure evidence, backup/copy acceptance, preservation, pending original
deployment, full self-check and final exact-SHA CI. Author checks and copy acceptance
are distinct from an independent review and do not establish R1 FINAL PASS.
