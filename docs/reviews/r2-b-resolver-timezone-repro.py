"""Synthetic proof of the B rehearsal blocker; memory DB only, no approvals/APIs.

Run with project-local Python: uv run --offline --frozen python
docs/reviews/r2-b-resolver-timezone-repro.py
"""
import json
from datetime import date, datetime, timezone
from uuid import UUID

import duckdb

from astock.data.provider_identity import (
    ExchangeCode, ListingEpisode, ProviderBinding, ProviderResolver, SourceObservation,
)


def main():
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    observed = datetime.fromisoformat('2026-01-01T12:00:00+08:00')
    episode_id = UUID('00000000-0000-0000-0000-000000000001')
    episode = ListingEpisode(
        episode_id=episode_id, security_id='synthetic-timezone-only', venue='SZSE',
        asset_type='STK', valid_from=date(2000, 1, 1), retrieved_at=now,
        available_at=now, evidence_ids=('synthetic',),
        approval_ref='synthetic-not-production-approval',
    )
    code = ExchangeCode(
        code_id=UUID('00000000-0000-0000-0000-000000000002'),
        episode_id=episode_id, identifier='000001.SZ', valid_from=episode.valid_from,
        available_at=now, evidence_ids=('synthetic',), approval_ref=episode.approval_ref,
    )
    binding = ProviderBinding(
        binding_id=UUID('00000000-0000-0000-0000-000000000003'), binding_version=1,
        dataset='daily', native_identifier='000001.SZ', episode_id=episode_id,
        representation_kind='EVENT_NATIVE', first_observed_at=observed,
        decision_at=now, available_at=now, evidence_ids=('synthetic',),
        decision_status='PROPOSED', approval_ref=None,
        observations=(SourceObservation(
            raw_object_id=UUID('00000000-0000-0000-0000-000000000004'),
            raw_row_number=0, event_date=date(2025, 1, 2),
        ),),
    )
    original = ProviderResolver([episode], [code], [binding])
    models = (episode, code, binding)
    results = []
    with duckdb.connect(':memory:') as db:
        db.execute('CREATE TABLE clocks (name VARCHAR PRIMARY KEY, value TIMESTAMPTZ)')
        for number, model in enumerate(models):
            for field, value in model.model_dump().items():
                if isinstance(value, datetime):
                    db.execute('INSERT INTO clocks VALUES (?,?)', [f'{number}:{field}', value])
        for zone in ('Asia/Shanghai', 'UTC'):
            db.execute("SET TimeZone='" + zone + "'")
            rows = dict(db.execute('SELECT name,value FROM clocks').fetchall())
            read_back = []
            for number, model in enumerate(models):
                value = model.model_dump()
                for field in value:
                    if f'{number}:{field}' in rows:
                        value[field] = rows[f'{number}:{field}']
                read_back.append(value)
            actual = ProviderResolver([read_back[0]], [read_back[1]], [read_back[2]])
            same = (original.episodes == actual.episodes and original.codes == actual.codes
                    and original.bindings == actual.bindings)
            assert same, 'This proof must preserve instants and all semantic fields'
            assert actual.snapshot_hash != original.snapshot_hash, 'Expected reviewed-code blocker'
            results.append(dict(timezone=zone, semantic_models_equal=same,
                                input_hash=original.snapshot_hash, read_back_hash=actual.snapshot_hash))
    print(json.dumps(dict(status='BLOCKER_REPRODUCED', synthetic_only=True,
                          real_approvals=0, market_requests=0, results=results), sort_keys=True))


if __name__ == '__main__':
    main()
