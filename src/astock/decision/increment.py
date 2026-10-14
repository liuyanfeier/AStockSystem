"""Link immutable component stores read-only instead of copying the old price window."""
from astock.research.core import require
from astock.research.store import ResearchStore


class LinkedResearchStore(ResearchStore):
    def __init__(self, primary: ResearchStore, components: dict[str, ResearchStore]):
        super().__init__(primary.path)
        self.primary = primary
        self.components = components

    def snapshot(self, bundle_id: str, as_of: str):
        owner = self.components.get(bundle_id, self.primary)
        return owner.snapshot(bundle_id, as_of)


def market_context(primary, bundle: str, as_of: str, parameters, components=None, owners=None, revisions=None):
    from astock.research.increment import compose
    from astock.research.service import analyze
    from astock.research.public_results import public_snapshot
    store = LinkedResearchStore(primary, owners or {})
    members = components or []
    snapshot = public_snapshot(analyze(store, bundle, as_of, parameters, radar=True,
                                       components=members, revisions=revisions or {}))
    if members:
        _, rows = compose(store, [bundle,*members], as_of, revisions or {})
    else:
        _, rows = store.snapshot(bundle, as_of)
    return snapshot, [{k:r[k] for k in ('code','industry_code','source_hash')} for r in rows.get('industry_membership',[])]
