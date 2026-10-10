"""Source-anchored version attacks and genuine executed-V2 compatibility, offline."""
from copy import deepcopy
from pathlib import Path
import json
import os
import shutil
import socket
import subprocess
import sys

import httpx
import pytest
from pydantic import SecretStr

from astock.phase1 import acquisition as a, contracts as c, domains as d, fixtures as f, pipeline as p, versions
from astock.phase1.core import PRODUCTION, Phase1Error, day, digest, encoded, file_hash, strict_json

ROOT = Path(__file__).resolve().parents[1]
EMPTY = dict(records=[], original_paths={}, original_hashes={})


@pytest.fixture(autouse=True)
def closed_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('REAL_NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


@pytest.fixture(scope='module')
def scoped_source(tmp_path_factory):
    destination = tmp_path_factory.mktemp('source-version') / 'fixture'
    member = c.request(ROOT, 'daily', dict(ts_code='000001.SZ', trade_date='20250102'))
    bar = f.row(ROOT, 'daily', ts_code='000001.SZ', trade_date='20250102')
    plan = a.make_plan(ROOT, destination, [member], EMPTY, fixture=True)
    result = a.run_batch(ROOT, destination, plan, EMPTY, token=SecretStr('closed-version'),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=encoded(f.response(member, [bar])))),
        clock=f.FixtureClock())
    assert result['status'] == 'RAW_BATCH_VALID'
    identifier = c.request(ROOT, 'security_identifiers', {}, metadata=dict(
        knowledge=f.proof('2024-12-31T00:00:00Z'), identifier_datasets={'000001.SZ': ['daily']}))
    row = f.row(ROOT, 'security_identifiers', security_id='S1', episode_id='E1', source='TUSHARE',
        identifier_type='PROVIDER_NATIVE', identifier='000001.SZ', exchange='SZSE', board='MAIN',
        list_status='L', valid_from='20000101', valid_to=None, evidence_source='FIXTURE_DATASET_SCOPE')
    episode = c.request(ROOT, 'listing_episodes', {}, metadata=dict(knowledge=f.proof('2024-12-31T00:00:00Z')))
    ep = f.row(ROOT, 'listing_episodes', security_id='S1', episode_id='E1', exchange='SZSE', board='MAIN',
        list_date='20000101', delist_date=None, valid_from='20000101', valid_to=None, evidence_source='FIXTURE_EPISODE')
    p.import_evidence(ROOT, destination, [dict(namespace='FIXTURE', request=m, response=f.response(m, [r]),
        retrieved_at='2025-06-01T00:00:00Z', evidence='SYNTHETIC_NOT_LEGAL_EVIDENCE') for m, r in [(identifier, row), (episode, ep)]])
    p.build(ROOT, destination)
    return destination


def rewrite_generation(db, descriptors):
    """Attacker recomputes all SQL hashes with a registered alternate adapter."""
    all_facts, quality = {}, {}
    for descriptor in descriptors:
        cs, ds = versions.adapters(ROOT, descriptor['transform_pins'])
        decoded = cs.decode(ROOT, descriptor['request'], Path(descriptor['body_path']).read_bytes())
        facts, findings = ds.facts(ROOT, descriptor['request'], decoded['rows'], descriptor['source'])
        all_facts.update({fact['fact_hash']: fact for fact in facts})
        for finding in findings:
            q = dict(finding, event_date=day(finding['event_date']).isoformat() if finding['event_date'] else None,
                     source_object=descriptor['object_id'])
            quality[digest(q)] = q
    manifest = dict(protocol='PHASE1_INTEGRATED_V2', namespace='FIXTURE', pins=a.pins(ROOT),
        objects=[{k: v for k, v in x.items() if k not in ('body_path', 'source_path')} for x in descriptors])
    gh = digest(manifest)
    # DuckDB requires referenced lineage deletion to commit before parent deletion.
    a.transaction(db, lambda: db.execute('DELETE FROM p1_lineage'))
    def change():
        for table in ('p1_generation', 'p1_fact', 'p1_quality'):
            db.execute('DELETE FROM ' + table)
        db.execute("UPDATE p1_meta SET payload=? WHERE key='generation_inputs'", [encoded(descriptors).decode()])
        for fact in all_facts.values():
            keys = ['fact_hash','dataset','domain','series_key','entity','event_date','valid_from','valid_to',
                    'published_at','available_at','retrieved_at','precision','knowledge_basis','source_object','source_row']
            values = [fact[k] for k in keys] + [encoded(fact['payload']).decode(), fact['eligibility']]
            db.execute('INSERT INTO p1_fact VALUES (' + ','.join('?' for _ in values) + ')', values)
        db.execute('INSERT INTO p1_generation VALUES (?,?,?,?,?)', [gh, encoded(manifest).decode(),
            digest([all_facts[h] for h in sorted(all_facts)]), 'FIXTURE', '2025-06-01T00:00:00Z'])
        for h in all_facts:
            db.execute('INSERT INTO p1_lineage VALUES (?,?)', [gh, h])
        for h, q in quality.items():
            db.execute('INSERT INTO p1_quality VALUES (?,?,?,?,?,?,?)', [h, q['dataset'], q['entity'],
                q['event_date'], q['reason'], q['source_object'], encoded(q).decode()])
    a.transaction(db, change)
    return list(all_facts.values())


@pytest.mark.parametrize('kind', ['CAPTURE', 'DOCUMENT_FACT'])
@pytest.mark.parametrize('replacement', ['V1', 'V2_5672'])
def test_self_consistent_registered_transform_substitution_rejected(scoped_source, tmp_path, kind, replacement):
    destination = tmp_path / 'derived'
    p.build(ROOT, destination, source_destination=scoped_source)
    with a.store(ROOT, destination, read_only=True) as db:
        descriptors = strict_json(db.execute("SELECT payload FROM p1_meta WHERE key='generation_inputs'").fetchone()[0].encode())
    target = next(x for x in descriptors if x['kind'] == kind and (kind == 'CAPTURE' or x['request']['dataset'] == 'security_identifiers'))
    original_files = {x['body_path']: file_hash(Path(x['body_path'])) for x in descriptors}
    original_files.update({x['source_path']: file_hash(Path(x['source_path'])) for x in descriptors})
    target['transform_pins'] = (versions.v1_registry(ROOT) if replacement == 'V1' else versions.v2_registry(ROOT))['pins']
    with a.store(ROOT, destination) as db:
        forged = rewrite_generation(db, descriptors)
    if kind == 'DOCUMENT_FACT' and replacement == 'V1':
        assert next(x for x in forged if x['dataset'] == 'security_identifiers')['payload'].get('datasets') is None
    before = file_hash(destination / 'catalog.duckdb')
    with a.store(ROOT, destination, read_only=True) as db:
        for check in (lambda: p.verify_generation_inputs(ROOT, destination, db), lambda: p.validate_lineage(db)):
            with pytest.raises(Phase1Error, match='SOURCE_TRANSFORM_BINDING_CHANGED'):
                check()
    for check in (lambda: p.query(ROOT, destination, 'S1', '2025-01-02', '2025-06-02T00:00:00Z'),
                  lambda: p.coverage(ROOT, destination), lambda: p.build(ROOT, destination),
                  lambda: p.build(ROOT, tmp_path / 'new-derived', source_destination=destination)):
        with pytest.raises(Phase1Error, match='SOURCE_TRANSFORM_BINDING_CHANGED'):
            check()
    assert file_hash(destination / 'catalog.duckdb') == before
    assert all(file_hash(Path(name)) == checksum for name, checksum in original_files.items())


@pytest.mark.parametrize('dataset', sorted(c.FINANCIAL))
def test_source_dataset_scope_survives_and_blocks_other_financial_domains(scoped_source, dataset):
    with a.store(ROOT, scoped_source, read_only=True) as db:
        p.verify_generation_inputs(ROOT, scoped_source, db)
        rows = p.fact_rows(db)
    assert d.resolve(rows, '000001.SZ', '2025-01-02', '2025-06-02T00:00:00Z', source='TUSHARE', dataset='daily')['status'] == 'RESOLVED'
    assert d.resolve(rows, '000001.SZ', '2025-01-02', '2025-06-02T00:00:00Z', source='TUSHARE', dataset=dataset)['status'] == 'EVIDENCE_REQUIRED'
    assert d.resolve(rows, '000001.SZ', '2025-01-02', '2025-06-02T00:00:00Z', source='OTHER_PROVIDER', dataset='daily')['status'] == 'EVIDENCE_REQUIRED'


@pytest.mark.parametrize('mutation', ['missing', 'null', 'unknown', 'v1_protocol_without_pins'])
def test_v2_document_source_cannot_fallback(scoped_source, tmp_path, mutation):
    with a.store(ROOT, scoped_source, read_only=True) as db:
        original = next(x for x in p.inputs(ROOT, scoped_source, db) if x['request']['dataset'] == 'security_identifiers')
    descriptor = deepcopy(original)
    directory = tmp_path / 'standalone' / 'evidence' / descriptor['object_id']
    shutil.copytree(Path(descriptor['body_path']).parent, directory)
    descriptor['body_path'] = str(directory / 'response.body')
    descriptor['source_path'] = str(directory / 'source.json')
    if mutation in ('missing', 'v1_protocol_without_pins'):
        descriptor['source'].pop('transform_pins')
        if mutation == 'v1_protocol_without_pins':
            descriptor['source']['protocol'] = 'PHASE1_INTEGRATED_V1'
    else:
        descriptor['source']['transform_pins'] = None if mutation == 'null' else {'unknown': 'a' * 64}
    Path(descriptor['source_path']).write_bytes(encoded(descriptor['source']))
    descriptor['source_hash'] = file_hash(Path(descriptor['source_path']))
    with pytest.raises((Phase1Error, FileNotFoundError)):
        p.source_decode(ROOT, descriptor)


def copy_runtime(repository, target):
    for name in a.pins(repository):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repository / name, path)
    for registry in (versions.v1_registry(repository), versions.v2_registry(repository)):
        for name in registry['pins']:
            path = target / registry['archive'] / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(repository / registry['archive'] / name, path)


def test_cached_archive_dispatch_still_rehashes_every_frozen_file(tmp_path):
    copy_runtime(ROOT, tmp_path)
    registry = versions.v2_registry(tmp_path)
    pins = registry['pins']
    first = versions.adapters(tmp_path, pins)
    assert versions.adapters(tmp_path, pins) == first
    path = tmp_path / registry['archive'] / 'src/astock/phase1/domains.py'
    path.write_bytes(path.read_bytes() + b'\n# unexpected archive mutation\n')
    with pytest.raises(Phase1Error, match='FROZEN_ADAPTER_CHANGED'):
        versions.adapters(tmp_path, pins)


@pytest.fixture(scope='module')
def genuine_v2_production(tmp_path_factory):
    base = tmp_path_factory.mktemp('genuine-5672')
    execution_root = base / 'execution'
    v2 = versions.v2_registry(ROOT)
    for name in v2['pins']:
        path = execution_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / v2['archive'] / name, path)
    v1 = versions.v1_registry(ROOT)
    for name in v1['pins']:
        path = execution_root / v1['archive'] / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / v1['archive'] / name, path)
    path = execution_root / 'sql/offline/phase1_integrated_v1.sql'
    shutil.copyfile(ROOT / 'sql/offline/phase1_integrated_v1.sql', path)
    (execution_root / 'src/astock/__init__.py').write_text('__path__.append(' + repr(str(ROOT / 'src/astock')) + ')\n')
    test_root = base / 'production'
    script = "import socket; deny=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN')); socket.socket.connect=deny; socket.getaddrinfo=deny; from pathlib import Path; from astock.phase1.production_fixture import rehearsal; import json; print(json.dumps(rehearsal(Path(" + repr(str(execution_root)) + "),Path(" + repr(str(test_root)) + "))))"
    result = subprocess.run([sys.executable, '-c', script], cwd=execution_root, check=True, capture_output=True,
        env=dict(os.environ, PYTHONPATH=str(execution_root / 'src'), PYTHONDONTWRITEBYTECODE='1', TUSHARE_TOKEN=''))
    accepted = json.loads(result.stdout)
    assert accepted['closed_mock_calls'] == 35 and accepted['correction_increment']['facts'] == 71
    copy_runtime(ROOT, test_root)
    # A changed current catalog hash must not force historical sources to adopt it.
    catalog = test_root / c.CATALOG
    catalog.write_bytes(catalog.read_bytes() + b'\n# isolated future catalog revision\n')
    return test_root, accepted


def test_executed_v2_read_only_reproof_rebuild_increment_and_policy_tamper(genuine_v2_production, tmp_path):
    root, original = genuine_v2_production
    source = root / PRODUCTION
    before = file_hash(source / 'catalog.duckdb')
    with a.store(root, source, read_only=True) as db:
        assert a.audit(root, source, db)['checked'] == 35
        p.verify_generation_inputs(root, source, db)
        assert p.validate_lineage(db)['facts'] == 71
        descriptors = p.inputs(root, source, db)
        assert all(x['transform_pins'] == versions.v2_registry(root)['pins'] for x in descriptors)
        old_generations = db.execute('SELECT * FROM p1_generation').fetchall()
    first = p.build(root, root / 'new-derived-a', source_destination=source)
    second = p.build(root, root / 'new-derived-b', source_destination=source)
    assert first['logical_content_hash'] == second['logical_content_hash'] == original['correction_increment']['logical_content_hash']
    assert len(p.query(root, root / 'new-derived-a', 'S1', '2025-05-15', '2025-05-15T10:00:00Z')['domains']['financial']) == 4
    assert p.build(root, root / 'new-derived-a')['status'] == 'ALREADY_VALID'
    assert file_hash(source / 'catalog.duckdb') == before
    # A reviewed new interpretation appends a separate current-version source.
    descriptor = next(x for x in descriptors if x['kind'] == 'DOCUMENT_FACT' and x['request']['dataset'] == 'security_status')
    package = strict_json((Path(descriptor['source_path']).parent / 'package.json').read_bytes())
    package['retrieved_at'] = '2025-06-06T00:00:00Z'
    proof = package['request']['metadata']['knowledge']
    proof.update(published_at='2025-06-05T00:00:00Z', available_at='2025-06-05T00:00:00Z')
    rows = c.decode(root, package['request'], encoded(package['response']))['rows']
    package['response'] = f.response(package['request'], [dict(rows[0], state_value='NORMAL')])
    review = dict(descriptor['source']['approval'], pins=a.pins(root), packages_hash=digest([package]))
    human = dict(descriptor['source']['human'], review_hash=digest(review))
    changed = dict(review, pins={'unknown': 'a' * 64})
    from astock.phase1.fact_admission import authorize
    with pytest.raises(Phase1Error, match='UNREGISTERED'):
        authorize(root, source, [package], changed, human, runtime=False)
    p.import_evidence(root, source, [package], fixture=False, approval=review, human=human)
    built = p.build(root, source)
    a_result = p.build(root, root / 'new-derived-a', source_destination=source)
    b_result = p.build(root, root / 'new-derived-b', source_destination=source)
    assert built['logical_content_hash'] == a_result['logical_content_hash'] == b_result['logical_content_hash']
    assert p.build(root, root / 'new-derived-a')['status'] == 'ALREADY_VALID'
    with a.store(root, source, read_only=True) as db:
        assert all(g in db.execute('SELECT * FROM p1_generation').fetchall() for g in old_generations)
        p.verify_generation_inputs(root, source, db)
    p.coverage(root, root / 'new-derived-a')
