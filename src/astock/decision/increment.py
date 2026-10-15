"""Link immutable component stores read-only instead of copying the old price window."""
from typing import Callable
from astock.research.store import ResearchStore


class LinkedResearchStore(ResearchStore):
    def __init__(self, primary: ResearchStore, components: dict[str, ResearchStore]):
        super().__init__(primary.path)
        self.primary = primary
        self.components = components

    def snapshot(self, bundle_id: str, as_of: str):
        owner = self.components.get(bundle_id, self.primary)
        return owner.snapshot(bundle_id, as_of)


def market_context(primary, bundle: str, as_of: str, parameters, components=None, owners=None, revisions=None,
                   *, snapshot_consumer: Callable[[dict, dict], None] | None = None):
    from astock.research.service import analyze
    from astock.decision.snapshots import MarketSnapshot
    store = LinkedResearchStore(primary, owners or {})
    members = components or []
    memberships = []
    def consume(manifest: dict, rows: dict) -> None:
        memberships.extend({k:r[k] for k in ('code','industry_code','source_hash')}
                           for r in rows.get('industry_membership', []))
        if snapshot_consumer is not None:
            snapshot_consumer(manifest, rows)
    snapshot = MarketSnapshot.from_analysis(analyze(
        store, bundle, as_of, parameters, radar=True, components=members,
        revisions=revisions or {}, include_journal=False,
        snapshot_consumer=consume)).model_dump(mode='json')
    return snapshot, memberships
