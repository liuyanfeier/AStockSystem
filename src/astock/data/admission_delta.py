"""Exact incremental approvals; retain existing v2 resolver metadata unchanged."""

from datetime import date, datetime

from astock.data.provider_identity import (
    ProviderResolver, ListingEpisode, ExchangeCode, ProviderBinding, canonical_resolver_member,
)
from astock.data.reconstruction import Approval, checksum, import_approved_cases, load_resolver, raw_capture
from astock.data.raw_validation import sha256
from astock.data.warehouse_lock import require_writer


def import_delta(root, db, delta, approval: Approval) -> dict:
    require_writer(db)
    approval = Approval.model_validate(approval)
    if checksum(delta) != approval.approved_case_set_hash:
        raise ValueError('Delta differs from exact approval')
    if sha256(root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md') != approval.time_integrity_addendum_hash:
        raise ValueError('Time integrity design differs from approval')
    if set(delta) != {'episodes','codes','bindings'} or not any(delta.values()):
        raise ValueError('Nonempty delta with exact fields required')
    old = load_resolver(db)
    sections = [(ListingEpisode, old.episodes, 'episodes', 'episode_id'),
                (ExchangeCode, old.codes, 'codes', 'code_id'),
                (ProviderBinding, old.bindings, 'bindings', 'binding_id')]
    present, missing = 0, 0
    merged = []
    for model, current, field, key in sections:
        additions = [model.model_validate(r) for r in delta[field]]
        if len({getattr(m,key) for m in additions}) != len(additions):
            raise ValueError('Duplicate delta member')
        by_id = {getattr(m,key):m for m in current}
        for member in additions:
            if member.approval_ref != approval.review_ref or member.available_at < approval.approved_at:
                raise ValueError('Delta approval metadata differs')
            if isinstance(member, ProviderBinding) and (member.decision_status != 'APPROVED' or member.decision_at < approval.approved_at):
                raise ValueError('Unapproved delta binding')
            existing = by_id.get(getattr(member,key))
            if existing:
                if canonical_resolver_member(existing) != canonical_resolver_member(member):
                    raise ValueError('Existing member conflicts with delta')
                present += 1
            else:
                missing += 1
        merged.append([*current, *(m for m in additions if getattr(m,key) not in by_id)])
    if present and missing:
        raise ValueError('Partial delta cannot be resumed as new approval')
    candidate = ProviderResolver(*merged)
    if present:
        # An idempotent repeat is still an exact raw-integrity check.
        cache = {}
        for value in delta['bindings']:
            binding = ProviderBinding.model_validate(value)
            observed = []
            for observation in binding.observations:
                capture = raw_capture(root, db, observation.raw_object_id, cache)
                table, manifest = capture['arrow'], capture['manifest']
                if manifest['dataset'] != binding.dataset or observation.raw_row_number >= table.num_rows:
                    raise ValueError('Repeated delta source differs')
                row = table.slice(observation.raw_row_number, 1).to_pylist()[0]
                event = row['trade_date']
                event = date.fromisoformat(event) if isinstance(event, str) and '-' in event else (
                    datetime.strptime(event, '%Y%m%d').date() if isinstance(event, str) else event)
                if row['ts_code'] != binding.native_identifier or event != observation.event_date:
                    raise ValueError('Repeated delta source differs')
                observed.append(manifest['retrieved_at'])
            if binding.first_observed_at != min(observed):
                raise ValueError('Repeated delta first capture differs')
        return dict(status='ALREADY_VALID', resolver_hash=candidate.snapshot_hash)
    # The core verifies complete SQL readback before COMMIT, including direct callers.
    return dict(status='IMPORTED', resolver_hash=import_approved_cases(root, db, delta, approval))
