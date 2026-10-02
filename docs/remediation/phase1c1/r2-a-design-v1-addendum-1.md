# R2-A design v1 addendum 1

2026-10-02, before implementation of the complete-generation DQ runner. The
frozen v1 remains byte-identical. Context additionally pins an approved
`dq_evidence_hash`: canonical session records, exact approved reference exceptions
and BSE transition cases. Approval pins this digest too. A runner must reject
changed evidence, including a caller changing calendar certification. Missing
records stay NOT_CERTIFIED; a frozen hash does not certify their authority.

Request IDs retain the existing 64-character plan digests, not UUIDs. Contexts
also pin this addendum hash. Generation quarantine is part of independently
recomputed lineage. Files preceding DB commit may survive faults, but are admitted
only after independently matching bytes, lineage and the exact input row set.
