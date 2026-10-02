# Phase 1C.1-R1-G2 — Review remediation and lifecycle self-check

2026-10-02 · AUTHOR_SELF_CHECK_COMPLETE · independent re-review pending.

Base: `26004ac573d6f66fe14cc63bb87b37543109cf22`. Both P2 findings in the
[retained independent review](2026-10-02-phase1c1-r1-g2-independent-review.md)
are accepted. The [human batch revision](2026-10-02-phase1c1-r1-batch-authorization.md)
permits these fixes followed by G3 isolated-copy acceptance before one review.
No author-created independent PASS is asserted; R2/Phase1C.2 remain closed.

## Finding closure evidence

| Finding | Fix and executable evidence |
|---|---|
| Late unmanaged connection admission | Managed disk handles bind their original guard/scope, process and thread. Actual native-connect-before-lock tests reject require/claim/raw/migration and an explicit proxy. All eleven helper negative cases now run both without ownership and with late same-path ownership; prior rows/files remain identical. |
| Fork from another thread/context leaks descriptors | Process-wide registry covers all lock fds from open through close, synchronized by before/parent/child fork hooks. Child closes inherited copies without LOCK_UN. Both another-thread and empty-context forks prove parent remains BUSY while owned, new owner succeeds after parent release while child lives, and child independently acquires afterward. Stable inode retained. |

Related self-check closed stale copied-ContextVar guard reuse and unscoped duplicate
cursors. Execute results stay scoped; root/early close invalidates all cursors and
proxies, closes every native cursor before lock release, while cursor-only close
leaves the root valid. Foreign threads/copied foreign contexts, ended scopes and
fork children reject native execution. Reacquiring a lock cannot revive a handle.
Memory-only native databases remain supported; attached disk and fabricated/empty
PRAGMA proxies cannot bypass helper admission. Fault adapters use an explicit base
handle and retain existing rollback/death assertions.

## Author verification

Full local suite: **480 passed, 1 warning in 239.23s**; 38 additional regressions
over G2's 442. The warning is Python's multithreaded-fork deprecation warning in
the intentional cross-thread fork test; that bounded pipe-synchronized test passed.
All existing claim/finalize rollback, native lock, exception/kill release, aliases,
shared readers, publication exclusion and secret/denied-network tests remain.
Locked offline sync, token-NO doctor, contracts v1/v2, probe/identity/slice plans
and specifications passed before progressing to copy acceptance. Focused boundary
and retained fault suite: **116 passed, 1 warning in 43.08s**. A cross-context exit
reports a stable error but still closes the OS descriptor and invalidates handles;
the two additional regressions prove no stranded ownership on that exception path.

No dependencies, SQL001–007, configuration, old review/specification, original
receipt/attempt/timestamp, market object or frozen identity are rewritten.
Network tests use temporary synthetic storage only. Native private attributes and
arbitrary manual SQL are trusted application internals, not an adversarial sandbox.
The fd registry supplies cleanup, never cross-thread ownership authorization.

## Batched handoff

The focused fix commit establishes the implementation SHA for G3. The subsequent
G3 candidate report records isolated acceptance separately from the pending
original deployment. Final artifact SHA/current-SHA CI are supplied in the user
handoff. This report is author problem-closure evidence, not independent acceptance.
