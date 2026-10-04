"""Managed synthetic import rollback, persistent order and v2 compatibility."""
import copy
from datetime import timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest

from astock.data import reconstruction
from astock.data.admission_delta import import_delta
from astock.data.audit import RequestParams
from astock.data.curation import load_curation_specs
from astock.data.provider_identity import ProviderResolver, SourceObservation
from astock.data.raw_writer import RawWriter
from astock.data.reconstruction import checksum, import_approved_cases, load_resolver, resolver_payload
from astock.data.tushare_client import ProviderTable, TushareClient
from astock.data.warehouse_lock import WarehouseConnectionProxy, warehouse_connection
from test_resolver_time_integrity import DAY, NOW, OBS, ZONES, make_store

TABLES = ('listing_episode', 'official_exchange_code', 'provider_native_binding',
          'provider_binding_observation')


@pytest.fixture(autouse=True)
def reject_provider(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('Synthetic import regressions cannot create a provider client')
    monkeypatch.setattr(TushareClient, '__init__', reject)


def rows(db):
    return {table: db.execute('SELECT * FROM ' + table + ' ORDER BY ALL').fetchall()
            for table in TABLES}


def successor(env, reverse=False):
    old = env['resolver'].bindings[0]
    observations = old.observations[::-1] if reverse else old.observations
    new = old.model_copy(update=dict(binding_id=uuid4(), binding_version=2,
        supersedes_binding_id=old.binding_id, observations=observations,
        decision_at=NOW + timedelta(days=1), available_at=NOW + timedelta(days=1),
        approval_ref='synthetic-independent-atomicity'))
    delta = dict(episodes=[], codes=[], bindings=[new.model_dump(mode='json')])
    approval = env['context'].approval.model_copy(update=dict(review_ref=new.approval_ref,
        approved_at=new.decision_at, approved_case_set_hash=checksum(delta)))
    return delta, approval


def full_delta(env, db):
    """Two actual raw objects plus all four kinds of new identity record."""
    spec = next(s for s in load_curation_specs(env['root'], spec_version='v2') if s.dataset == 'daily')
    fields = [f.source_column for f in spec.fields]
    value = {f.source_column: dict(string='synthetic', date32='20250506', float64=10.0,
                                 int64=1)[f.logical_type] for f in spec.fields}
    value.update(ts_code='000002.SZ', change=0.0, pct_chg=0.0)
    observations = []
    for _ in range(2):
        run = uuid4()
        db.execute("""INSERT INTO ingestion_run(run_id,source,dataset,mode,started_at,status,
            code_commit,config_hash,provider_client_version)
            VALUES (?,'tushare','daily','AUDIT',?,'RUNNING',?,?,'1.0.0')""",
            [run, OBS, 'a' * 40, 'b' * 64])
        raw = RawWriter(env['root'], db).write(run, 'daily', 0,
            ProviderTable(fields=fields, items=[[value[f] for f in fields]] * 2,
                          retrieved_at=OBS), RequestParams(trade_date=DAY))
        RawWriter(env['root'], db).sidecar(run, 'daily')
        observations.extend(SourceObservation(raw_object_id=raw.object_id,
            raw_row_number=n, event_date=DAY) for n in (0, 1))
    observations.sort(key=lambda o: (o.raw_object_id.int, o.raw_row_number, o.event_date))
    instant = NOW + timedelta(days=1)
    ref = 'synthetic-independent-full-delta'
    episode = env['resolver'].episodes[0].model_copy(update=dict(episode_id=uuid4(),
        security_id='synthetic-second-instrument', available_at=instant, approval_ref=ref))
    code = env['resolver'].codes[0].model_copy(update=dict(code_id=uuid4(),
        episode_id=episode.episode_id, identifier='000002.SZ',
        available_at=instant.astimezone(ZoneInfo('Asia/Kathmandu')), approval_ref=ref))
    binding = env['resolver'].bindings[0].model_copy(update=dict(binding_id=uuid4(),
        episode_id=episode.episode_id, native_identifier='000002.SZ', observations=tuple(observations),
        decision_at=instant.astimezone(ZoneInfo('America/New_York')),
        available_at=instant, approval_ref=ref))
    delta = dict(episodes=[episode.model_dump(mode='json')], codes=[code.model_dump(mode='json')],
                 bindings=[binding.model_dump(mode='json')])
    approval = env['context'].approval.model_copy(update=dict(review_ref=ref,
        approved_at=instant, approved_case_set_hash=checksum(delta)))
    return delta, approval


def call(route, env, db, delta, approval):
    return (import_delta if route == 'delta' else import_approved_cases)(env['root'], db, delta, approval)


class NoInsert(WarehouseConnectionProxy):
    def execute(self, sql, *args, **kwargs):
        if sql.lstrip().upper().startswith('INSERT'):
            raise AssertionError('Unroundtrippable order reached INSERT')
        return super().execute(sql, *args, **kwargs)


@pytest.mark.parametrize('route', ('core', 'delta'))
def test_reversed_real_observations_rejected_before_insert_and_reopen(tmp_path, route):
    env = make_store(tmp_path)
    delta, approval = successor(env, reverse=True)
    with warehouse_connection(env['path']) as db:
        before = rows(db)
        with pytest.raises(ValueError, match='persistent SQL order'):
            call(route, env, NoInsert(db), delta, approval)
        assert rows(db) == before
    with warehouse_connection(env['path'], read_only=True) as db:
        assert rows(db) == before


@pytest.mark.parametrize('route', ('core', 'delta'))
@pytest.mark.parametrize('failure', ('hash', 'readback'))
def test_postinsert_fault_rolls_back_all_identity_rowsets(tmp_path, monkeypatch, route, failure):
    env = make_store(tmp_path)
    with warehouse_connection(env['path']) as db:
        delta, approval = full_delta(env, db)
        before = rows(db)
        original = reconstruction.load_resolver
        observed_insert = []
        def fail_after_insert(handle):
            actual = original(handle)
            if len(actual.episodes) == 2:
                assert handle.execute('SELECT count(*) FROM provider_binding_observation').fetchone()[0] == 6
                observed_insert.append(True)
                if failure == 'readback':
                    raise RuntimeError('injected SQL readback failure')
                changed = actual.episodes[-1].model_copy(update={'evidence_ids': ('injected-mismatch',)})
                return ProviderResolver([*actual.episodes[:-1], changed], actual.codes, actual.bindings)
            return actual
        with monkeypatch.context() as patch:
            patch.setattr(reconstruction, 'load_resolver', fail_after_insert)
            with pytest.raises((RuntimeError, ValueError), match='readback failure|Imported merged snapshot differs'):
                call(route, env, db, delta, approval)
        assert observed_insert
        assert rows(db) == before
    with warehouse_connection(env['path'], read_only=True) as db:
        assert rows(db) == before
    # Rollback leaves the same exact new delta usable; no partial identity remains.
    with warehouse_connection(env['path']) as db:
        call(route, env, db, delta, approval)
        assert db.execute('SELECT count(*) FROM listing_episode').fetchone()[0] == 2


@pytest.mark.parametrize('zone', ZONES)
def test_persistent_order_import_repeat_and_reopen_preserve_v2(tmp_path, zone):
    env = make_store(tmp_path, zone)
    old = resolver_payload(env['resolver'])
    with warehouse_connection(env['path']) as db:
        db.execute("SET TimeZone='" + zone + "'")
        delta, approval = full_delta(env, db)
        expected = ProviderResolver([*env['resolver'].episodes, *delta['episodes']],
            [*env['resolver'].codes, *delta['codes']], [*env['resolver'].bindings, *delta['bindings']])
        assert import_delta(env['root'], db, delta, approval) == dict(status='IMPORTED', resolver_hash=expected.snapshot_hash)
        assert resolver_payload(load_resolver(db)) == resolver_payload(expected)
        original_rows = rows(db)
    for read_zone in ZONES:
        with warehouse_connection(env['path']) as db:
            db.execute("SET TimeZone='" + read_zone + "'")
            assert resolver_payload(load_resolver(db)) == resolver_payload(expected)
            assert import_delta(env['root'], db, delta, approval) == dict(status='ALREADY_VALID', resolver_hash=expected.snapshot_hash)
            assert rows(db) == original_rows
            live = resolver_payload(load_resolver(db))
            for section, key in [('episodes', 'episode_id'), ('official_codes', 'code_id'),
                                 ('provider_bindings', 'binding_id')]:
                by_id = {m[key]: m for m in live[section]}
                assert all(by_id[m[key]] == m for m in old[section])
            assert live['episodes'][0]['published_at'] is None
            assert all(b['first_observed_at'].endswith('.123456Z') for b in live['provider_bindings'])


def test_uuid_integer_ordinal_date_order_matches_duckdb(tmp_path):
    env = make_store(tmp_path)
    ids = [UUID(x) for x in ('ffffffff-ffff-ffff-ffff-ffffffffffff',
        '80000000-0000-0000-0000-000000000000', '7fffffff-ffff-ffff-ffff-ffffffffffff',
        '00000000-0000-0000-0000-000000000001')]
    values = [(u, n, DAY + timedelta(days=d)) for u in ids for n in (10, 2, 1) for d in (1, 0)]
    with warehouse_connection(env['path'], read_only=True) as db:
        sql = 'SELECT * FROM (VALUES ' + ','.join('(CAST(? AS UUID),CAST(? AS BIGINT),CAST(? AS DATE))' for _ in values) + ') ORDER BY ALL'
        actual = db.execute(sql, [v for row in values for v in row]).fetchall()
    assert actual == sorted(values, key=lambda row: (row[0].int, row[1], row[2]))


@pytest.mark.parametrize('route', ('core', 'delta'))
@pytest.mark.parametrize('tamper', ('approval', 'ordinal', 'FK'))
def test_existing_approval_and_raw_controls_still_fail_closed(tmp_path, route, tamper):
    env = make_store(tmp_path)
    delta, approval = successor(env)
    if tamper != 'approval':
        delta = copy.deepcopy(delta)
        if tamper == 'ordinal':delta['bindings'][0]['observations'][1]['raw_row_number'] = 999
        else:delta['bindings'][0]['observations'] = [dict(delta['bindings'][0]['observations'][0], raw_object_id=str(uuid4()))]
        approval = approval.model_copy(update={'approved_case_set_hash': checksum(delta)})
    else:approval = approval.model_copy(update={'approved_case_set_hash': 'f' * 64})
    with warehouse_connection(env['path']) as db:
        before = rows(db)
        with pytest.raises(ValueError):call(route, env, db, delta, approval)
        assert rows(db) == before
