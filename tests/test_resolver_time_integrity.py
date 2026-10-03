"""V2 resolver integrity across managed persistent SQL boundaries, synthetic only."""

import json
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from astock.data.audit import RequestParams
from astock.data.curation import load_curation_specs
from astock.data.provider_identity import (
    ExchangeCode, ListingEpisode, ProviderBinding, ProviderResolver, SourceObservation,
    RESOLVER_PROTOCOL, canonical_resolver_member,
)
from astock.data.raw_validation import sha256
from astock.data.raw_writer import RawWriter, migrate
from astock.data.receipt_migration import apply_receipt_integrity_upgrade
from astock.data.reconstruction import (
    Approval, Context, Input, apply_reconstruction_schema, checksum,
    compare_generations, complete_generation, get_context, import_approved_cases,
    load_context_resolver, load_resolver, publish_output, register_context,
    resolver_payload, select_complete, specs_hash, start_generation,
)
from astock.data.reconstruction_dq import evidence_hash, load_policy
from astock.data.tushare_client import ProviderTable, TushareClient
from astock.data.warehouse_lock import warehouse_connection

ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 10, 3, 3, 52, 23, 123456, timezone.utc)
OBS = (NOW - timedelta(hours=1)).astimezone(ZoneInfo('Asia/Shanghai'))
DAY = date(2025, 5, 6)
ZONES = ('Asia/Shanghai', 'UTC', 'America/New_York', 'Asia/Kathmandu')


def make_store(root, zone='Asia/Shanghai'):
    for name in ('sql', 'config', 'docs'):
        shutil.copytree(ROOT / name, root / name)
    path = root / 'data/warehouse/synthetic.duckdb'
    path.parent.mkdir(parents=True)
    with warehouse_connection(path) as db:
        db.execute("SET TimeZone='" + zone + "'")
        migrate(db, root)
        apply_receipt_integrity_upgrade(root, db, verification_sha='a' * 40)
        approval = Approval(
            resolver_protocol=RESOLVER_PROTOCOL,
            time_integrity_addendum_hash=sha256(root / 'docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md'),
            review_ref='synthetic-v2-review', reviewed_sha='a' * 40, approved_at=NOW,
            design_hash=sha256(root / 'docs/remediation/phase1c1/r2-a-design-v1.md'),
            policy_hash=load_policy(root)[1],
            approved_case_set_hash=checksum(dict(episodes=[], codes=[], bindings=[])),
            dq_evidence_hash=evidence_hash(dict(sessions=[], reference_exceptions=[], bse_transitions=[], source_dispositions=[])),
            publication_addendum_hash=sha256(root / 'docs/remediation/phase1c1/r2-a-design-v1-addendum-1.md'),
            disposition_addendum_hash=sha256(root / 'docs/remediation/phase1c1/r2-a-design-v1-addendum-2.md'),
            correction_addendum_hash=sha256(root / 'docs/remediation/phase1c1/r2-a-design-v1-addendum-3.md'),
        )
        assert apply_reconstruction_schema(root, db, approval) == 'UPGRADED'
        run = uuid4()
        db.execute("""INSERT INTO ingestion_run(run_id,source,dataset,mode,started_at,status,code_commit,config_hash,provider_client_version)
            VALUES (?,'tushare','daily','AUDIT',?,'RUNNING',?,?,'1.0.0')""", [run, OBS, 'a' * 40, 'b' * 64])
        spec = next(s for s in load_curation_specs(root, spec_version='v2') if s.dataset == 'daily')
        fields = [f.source_column for f in spec.fields]
        row = {f.source_column: dict(string='synthetic', date32='20250506', float64=10.0, int64=1)[f.logical_type] for f in spec.fields}
        row.update(ts_code='000001.SZ', change=0.0, pct_chg=0.0)
        raw = RawWriter(root, db).write(run, 'daily', 0, ProviderTable(
            fields=fields, items=[[row[f] for f in fields]] * 2, retrieved_at=OBS), RequestParams(trade_date=DAY))
        RawWriter(root, db).sidecar(run, 'daily')
        item = Input(request_id=checksum('synthetic-daily'), raw_object_id=raw.object_id, dataset='daily',
                     raw_hash=raw.sha256, raw_schema_hash=raw.schema_hash, row_count=2, is_output=True)
        episode = ListingEpisode(episode_id=uuid4(), security_id='synthetic-mixed-clock', venue='SZSE', asset_type='STK',
            valid_from=date(2000, 1, 1), published_at=None, retrieved_at=OBS, available_at=NOW,
            evidence_ids=('synthetic-episode',), approval_ref=approval.review_ref)
        code = ExchangeCode(code_id=uuid4(), episode_id=episode.episode_id, identifier='000001.SZ', valid_from=episode.valid_from,
            available_at=NOW.astimezone(ZoneInfo('Asia/Shanghai')), evidence_ids=('synthetic-code',), approval_ref=approval.review_ref)
        binding = ProviderBinding(binding_id=uuid4(), binding_version=1, dataset='daily', native_identifier='000001.SZ',
            episode_id=episode.episode_id, representation_kind='EVENT_NATIVE',
            observations=tuple(SourceObservation(raw_object_id=raw.object_id, raw_row_number=n, event_date=DAY) for n in range(2)),
            first_observed_at=OBS, decision_at=NOW, available_at=NOW.astimezone(ZoneInfo('Asia/Shanghai')),
            evidence_ids=('synthetic-binding',), decision_status='APPROVED', approval_ref=approval.review_ref)
        resolver = ProviderResolver([episode], [code], [binding])
        cases = dict(episodes=[episode.model_dump()], codes=[code.model_dump()], bindings=[binding.model_dump()])
        approval = approval.model_copy(update={'approved_case_set_hash': checksum(cases)})
        assert import_approved_cases(root, db, cases, approval) == resolver.snapshot_hash
        context = Context(parent_batch_id=uuid4(), parent_generation=0, parent_identity_hash='b' * 64, parent_plan_hash='c' * 64,
            resolver_hash=resolver.snapshot_hash, specs_hash=specs_hash(root), policy_hash=approval.policy_hash,
            design_hash=approval.design_hash, dq_evidence_hash=approval.dq_evidence_hash,
            publication_addendum_hash=approval.publication_addendum_hash, disposition_addendum_hash=approval.disposition_addendum_hash,
            correction_addendum_hash=approval.correction_addendum_hash, resolver_protocol=RESOLVER_PROTOCOL,
            time_integrity_addendum_hash=approval.time_integrity_addendum_hash, knowledge_as_of=NOW,
            implementation_sha='a' * 40, approval=approval, inputs=(item,), fixture_only=True)
        # Both instant changes and a stale v1-style digest must fail at initial registration.
        altered = binding.model_copy(update={'first_observed_at': OBS + timedelta(microseconds=1)})
        bad = context.model_copy(update={'resolver_hash': ProviderResolver([episode], [code], [altered]).snapshot_hash})
        with pytest.raises(ValueError, match='Resolver snapshot changed'):
            register_context(root, db, bad, allow_fixture=True)
        old = checksum(dict(episodes=[episode.model_dump(mode='json')], official_codes=[code.model_dump(mode='json')],
                            provider_bindings=[binding.model_dump(mode='json')]))
        assert old != resolver.snapshot_hash
        with pytest.raises(ValueError, match='Resolver snapshot changed'):
            register_context(root, db, context.model_copy(update={'resolver_hash': old}), allow_fixture=True)
        cid = register_context(root, db, context, allow_fixture=True)
        gen = publish(root, db, cid, context)
    return dict(root=root, path=path, context=context, cid=cid, gid=gen, resolver=resolver)


def publish(root, db, cid, context):
    gen = start_generation(db, cid, allow_fixture=True)
    for item in context.inputs:
        publish_output(root, db, cid, gen, item.request_id, allow_fixture=True)
    assert complete_generation(root, db, cid, gen, allow_fixture=True) == 'COMPLETE'
    return gen


@pytest.fixture
def store(tmp_path, monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('No provider client allowed in time integrity regressions')
    monkeypatch.setattr(TushareClient, '__init__', reject)
    return make_store(tmp_path)


@pytest.mark.parametrize('write_zone', ('Asia/Shanghai', 'UTC'))
def test_register_reopen_select_and_independent_rebuild_across_timezones(tmp_path, write_zone):
    env = make_store(tmp_path, write_zone)
    expected = resolver_payload(env['resolver'])
    assert expected['episodes'][0]['published_at'] is None
    assert expected['provider_bindings'][0]['first_observed_at'].endswith('.123456Z')
    for zone in ZONES:
        # A new managed connection, not only a changed Python/in-memory timezone.
        with warehouse_connection(env['path']) as db:
            db.execute("SET TimeZone='" + zone + "'")
            live = load_resolver(db)
            context = get_context(db, env['cid'])
            assert live.snapshot_hash == context.resolver_hash == env['resolver'].snapshot_hash
            assert resolver_payload(live) == expected
            pinned = load_context_resolver(db, context)
            assert resolver_payload(pinned) == expected
            roundtrip = json.loads(json.dumps(expected))
            rebuilt = ProviderResolver(roundtrip['episodes'], roundtrip['official_codes'], roundtrip['provider_bindings'])
            assert resolver_payload(rebuilt) == expected and rebuilt.snapshot_hash == live.snapshot_hash
            assert register_context(env['root'], db, context, allow_fixture=True) == env['cid']
            assert len(select_complete(env['root'], db, env['cid'], env['gid'], allow_fixture=True)[1]) == 1
            new_gen = publish(env['root'], db, env['cid'], context)
            assert compare_generations(env['root'], db, env['cid'], env['gid'], new_gen, allow_fixture=True)['logical_schema_source_match']


@pytest.mark.parametrize('kind,field', (
    ('episodes', 'published_at'), ('episodes', 'retrieved_at'), ('episodes', 'available_at'),
    ('codes', 'available_at'), ('bindings', 'first_observed_at'),
    ('bindings', 'decision_at'), ('bindings', 'available_at'),
))
def test_explicit_clock_fields_reject_naive_and_preserve_microseconds(store, kind, field):
    original = getattr(store['resolver'], kind)[0]
    value = NOW if field != 'retrieved_at' else OBS
    member = original.model_copy(update={field: value})
    offset = member.model_copy(update={field: value.astimezone(ZoneInfo('Asia/Kathmandu'))})
    assert canonical_resolver_member(member) == canonical_resolver_member(offset)
    changed = member.model_copy(update={field: value + timedelta(microseconds=1)})
    assert canonical_resolver_member(member) != canonical_resolver_member(changed)
    naive = member.model_copy(update={field: datetime(2026, 1, 1)})
    with pytest.raises(ValueError, match='timezone-aware'):
        canonical_resolver_member(naive)


@pytest.mark.parametrize('change', ('instant', 'native', 'security_id', 'code_start', 'approval_ref', 'ordinal'))
def test_digest_retains_material_identity_and_source_semantics(store, change):
    resolver = store['resolver']
    episode, code, binding = resolver.episodes[0], resolver.codes[0], resolver.bindings[0]
    if change == 'instant':
        binding = binding.model_copy(update={'first_observed_at': OBS + timedelta(microseconds=1)})
    elif change == 'native':
        binding = binding.model_copy(update={'native_identifier': '000002.SZ'})
    elif change == 'security_id':
        episode = episode.model_copy(update={'security_id': 'another-security'})
    elif change == 'code_start':
        code = code.model_copy(update={'valid_from': code.valid_from + timedelta(days=1)})
    elif change == 'approval_ref':
        binding = binding.model_copy(update={'approval_ref': 'another-review'})
    else:
        observation = binding.observations[0].model_copy(update={'raw_row_number': 99})
        binding = binding.model_copy(update={'observations': (observation, *binding.observations[1:])})
    changed = ProviderResolver([episode], [code], [binding])
    assert changed.snapshot_hash != resolver.snapshot_hash


@pytest.mark.parametrize('change', (
    'instant', 'native', 'dataset', 'scope_event', 'scope_raw', 'ordinal', 'security',
    'episode', 'code_interval', 'evidence', 'approval', 'status', 'version', 'observation_order',
))
def test_material_changes_rejected_after_reopen(store, change):
    with warehouse_connection(store['path']) as db:
        db.execute("SET TimeZone='UTC'")
        if change == 'instant':
            db.execute("UPDATE provider_native_binding SET first_observed_at=first_observed_at+INTERVAL 1 MICROSECOND")
        elif change in ('native', 'dataset', 'evidence', 'approval', 'status', 'version'):
            field, value = {'native': ('native_identifier', '000002.SZ'), 'dataset': ('dataset', 'daily_basic'),
                'evidence': ('evidence_ids', '["different"]'), 'approval': ('approval_ref', 'other-review'),
                'status': ('decision_status', 'PROPOSED'), 'version': ('binding_version', 2)}[change]
            db.execute(f'UPDATE provider_native_binding SET {field}=?', [value])
        elif change == 'security':
            db.execute("UPDATE listing_episode SET security_id='changed'")
        elif change == 'code_interval':
            db.execute("UPDATE official_exchange_code SET valid_from=valid_from+INTERVAL 1 DAY")
        elif change in ('scope_event', 'ordinal'):
            field, value = ('event_date', DAY + timedelta(days=1)) if change == 'scope_event' else ('raw_row_number', 99)
            db.execute(f'UPDATE provider_binding_observation SET {field}=? WHERE raw_row_number=0', [value])
        else:
            payload = json.loads(db.execute('SELECT payload FROM derivation_resolver_snapshot').fetchone()[0])
            if change == 'scope_raw':
                payload['provider_bindings'][0]['observations'][0]['raw_object_id'] = str(uuid4())
            elif change == 'episode':
                payload['episodes'][0]['episode_id'] = str(uuid4())
            else:
                payload['provider_bindings'][0]['observations'].reverse()
            db.execute('UPDATE derivation_resolver_snapshot SET payload=?', [json.dumps(payload)])
    with warehouse_connection(store['path'], read_only=True) as db:
        db.execute("SET TimeZone='Asia/Kathmandu'")
        with pytest.raises(ValueError):
            select_complete(store['root'], db, store['cid'], store['gid'], allow_fixture=True)


@pytest.mark.parametrize('missing', ('code', 'observation', 'snapshot'))
def test_missing_members_and_snapshot_fail_after_reopen(store, missing):
    with warehouse_connection(store['path']) as db:
        table = {'code': 'official_exchange_code', 'observation': 'provider_binding_observation', 'snapshot': 'derivation_resolver_snapshot'}[missing]
        db.execute(f'DELETE FROM {table}')
    with warehouse_connection(store['path'], read_only=True) as db:
        with pytest.raises(ValueError):
            select_complete(store['root'], db, store['cid'], store['gid'], allow_fixture=True)


def test_v1_approval_context_and_changed_design_are_not_implicitly_admitted(store):
    context = store['context']
    old = context.approval.model_dump(exclude={'resolver_protocol', 'time_integrity_addendum_hash'})
    with pytest.raises(ValidationError):
        Approval.model_validate(old)
    old_context = context.model_dump(exclude={'resolver_protocol', 'time_integrity_addendum_hash'})
    with pytest.raises(ValidationError):
        Context.model_validate(old_context)
    with warehouse_connection(store['path']) as db:
        bad = context.approval.model_copy(update={'time_integrity_addendum_hash': 'f' * 64})
        with pytest.raises(ValueError, match='Time integrity design'):
            apply_reconstruction_schema(store['root'], db, bad)
        with pytest.raises(ValueError, match='Time integrity design'):
            import_approved_cases(store['root'], db, dict(episodes=[], codes=[], bindings=[]), bad)
        wrong = context.model_copy(update={'time_integrity_addendum_hash': 'f' * 64})
        with pytest.raises(ValueError, match='time integrity'):
            register_context(store['root'], db, wrong, allow_fixture=True)
