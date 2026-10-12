"""Closed synthetic proof chains; no real capture or provider authenticity claim."""
import copy
import hashlib
from pathlib import Path

import pytest

from astock.research.core import ResearchError, digest, encoded, read_json
from astock.research.evidence import APPROVAL_KEYS, CLAIM_KEYS, RESULT_KEYS
from astock.research.inputs import Bundle, SourceFile, load_bundle, records
from astock.research.store import ResearchStore
from astock.research.tushare import make_capture_bundle
from research_fixture import ASOF, approved_mock, fixture_plan, response


@pytest.fixture
def chain(tmp_path):
    """SYNTHETIC_PRODUCTION_SHAPE: simulate retained TLS records without transport.

    HUMAN/HTTPS labels here only exercise persisted contract validation in a
    test directory. They do not establish any actual authorization or market data.
    """
    plan = fixture_plan()
    destination = tmp_path / plan['destination']
    destination.mkdir(parents=True)
    (destination / 'plan.json').write_bytes(encoded(plan))
    approval = dict(protocol='RESEARCH_CAPTURE_APPROVAL_V1_1', plan_hash=digest(plan),
                    destination=str(destination), implementation_hash='a' * 64,
                    authorized_by='HUMAN', approved_at='2026-10-13T00:00:00+00:00',
                    expires_at='2026-10-14T00:00:00+00:00',
                    member_ids=[digest(m) for m in plan['members']], fixture_only=False,
                    execution_authorized=True)
    (destination / f'{digest(approval)}.approval.json').write_bytes(encoded(approval))
    for member in plan['members']:
        key = digest(member)
        body = encoded(response(plan, member))
        claim = dict(plan_hash=digest(plan), member=member,
                     claimed_at='2026-10-13T12:00:00+00:00', approval_hash=digest(approval))
        result = dict(member=member, claim_hash=digest(claim), state='COMPLETE', error=None,
                      transport='HTTPS_TLS', object=f'{key}.response.json',
                      sha256=hashlib.sha256(body).hexdigest(),
                      retrieved_at='2026-10-13T12:00:00+00:00', available_at=ASOF)
        for suffix, value in [('claim.json', encoded(claim)), ('result.json', encoded(result)), ('response.json', body)]:
            (destination / f'{key}.{suffix}').write_bytes(value)
    path = tmp_path / 'bundle.json'
    manifest = make_capture_bundle(destination, path)
    return path, manifest, destination


def proofs(spec):
    return {p['sha256']: Path(p['path']).read_bytes() for p in spec['evidence']}


def rewrite_proof(spec, keys, change):
    """Rehash all dependent test bytes so assertions exercise semantics, not just SHA."""
    by_keys = {frozenset(read_json(Path(p['path']))): p for p in spec['evidence']}
    proof = by_keys[frozenset(keys)]
    value = read_json(Path(proof['path']))
    change(value)
    Path(proof['path']).write_bytes(encoded(value))
    if keys == APPROVAL_KEYS:
        claim_proof = by_keys[frozenset(CLAIM_KEYS)]
        claim = read_json(Path(claim_proof['path']))
        claim['approval_hash'] = digest(value)
        Path(claim_proof['path']).write_bytes(encoded(claim))
    if keys in (APPROVAL_KEYS, CLAIM_KEYS):
        claim_proof = by_keys[frozenset(CLAIM_KEYS)]
        receipt_proof = by_keys[frozenset(RESULT_KEYS)]
        receipt = read_json(Path(receipt_proof['path']))
        receipt['claim_hash'] = hashlib.sha256(Path(claim_proof['path']).read_bytes()).hexdigest()
        Path(receipt_proof['path']).write_bytes(encoded(receipt))
    for p in spec['evidence']:
        p['sha256'] = hashlib.sha256(Path(p['path']).read_bytes()).hexdigest()


def test_manifest_grade_requires_proof_before_any_store_write(chain, tmp_path):
    path, manifest, _ = chain
    manifest['files'][0]['evidence'] = []
    path.write_bytes(encoded(manifest))
    store = ResearchStore(tmp_path / 'rejected' / 'research.duckdb')
    with pytest.raises(ValueError, match='CAPTURE_EVIDENCE_REQUIRED'):
        store.import_bundle(path)
    assert not store.path.parent.exists()


def test_self_reported_raw_hash_and_arbitrary_proofs_do_not_grant_grade(chain):
    _, manifest, _ = chain
    spec = manifest['files'][0]
    body = Path(spec['path']).read_bytes()
    values = {}
    for index, p in enumerate(spec['evidence']):
        value = encoded({'unrelated': index})
        p['sha256'] = hashlib.sha256(value).hexdigest()
        values[p['sha256']] = value
    bundle = Bundle.model_validate(manifest)
    with pytest.raises(ResearchError, match='CAPTURE_EVIDENCE_ROLES'):
        records(bundle.files[0], body, bundle, evidence_bodies=values)


def test_direct_decoder_cannot_bypass_grade_validation(chain):
    _, manifest, _ = chain
    bundle = Bundle.model_validate(manifest)
    with pytest.raises(ResearchError, match='CAPTURE_EVIDENCE_REQUIRED'):
        records(bundle.files[0], Path(bundle.files[0].path).read_bytes(), bundle)


def test_native_file_cannot_claim_collector_grade(chain):
    _, manifest, _ = chain
    spec = manifest['files'][0]
    spec.update(format='csv', adapter='native-v1', request=None)
    with pytest.raises(ValueError, match='CAPTURE_EVIDENCE_REQUIRED'):
        SourceFile.model_validate(spec)


def test_modified_raw_with_self_reported_hash_is_rejected(chain):
    path, manifest, _ = chain
    spec = manifest['files'][0]
    value = read_json(Path(spec['path']))
    value['data']['items'][0][spec['request']['fields'].index('name')] = 'SYNTHETIC_CHANGED'
    Path(spec['path']).write_bytes(encoded(value))
    spec['sha256'] = digest(value)
    with pytest.raises(ResearchError, match='CAPTURE_RAW_BINDING'):
        load_bundle(path, manifest)


@pytest.mark.parametrize('role', [CLAIM_KEYS, APPROVAL_KEYS, RESULT_KEYS, None])
def test_missing_each_proof_is_rejected(chain, role):
    path, manifest, _ = chain
    spec = manifest['files'][0]
    proof = next(p for p in spec['evidence'] if
                 (set(read_json(Path(p['path']))) == role if role else read_json(Path(p['path'])).get('protocol') == 'RESEARCH_CAPTURE_V1_1'))
    Path(proof['path']).unlink()  # test-owned synthetic data only
    with pytest.raises(ResearchError, match='SOURCE_EVIDENCE_CHANGED'):
        load_bundle(path)


@pytest.mark.parametrize('keys,change,error', [
    (RESULT_KEYS, lambda v: v.update(state='FAILED'), 'CAPTURE_RECEIPT_BINDING'),
    (RESULT_KEYS, lambda v: v.update(transport='MOCK'), 'CAPTURE_RECEIPT_BINDING'),
    (RESULT_KEYS, lambda v: v.update(claim_hash='b'*64), 'CAPTURE_RECEIPT_BINDING'),
    (RESULT_KEYS, lambda v: v.update(sha256='b'*64), 'CAPTURE_RAW_BINDING'),
    (RESULT_KEYS, lambda v: v.update(object='../other.response.json'), 'CAPTURE_RAW_BINDING'),
    (CLAIM_KEYS, lambda v: v.update(plan_hash='b'*64), 'CAPTURE_AUTHORITY_BINDING'),
    (APPROVAL_KEYS, lambda v: v.update(execution_authorized=False), 'CAPTURE_APPROVAL_CONTRACT'),
    (APPROVAL_KEYS, lambda v: v.update(authorized_by='SYNTHETIC_TEST'), 'CAPTURE_AUTHORIZER'),
    (APPROVAL_KEYS, lambda v: v.update(expires_at='2026-10-12T00:00:00+00:00'), 'CAPTURE_AUTHORITY_TIME'),
    (APPROVAL_KEYS, lambda v: v.update(destination='/another/capture'), 'CAPTURE_DESTINATION_BINDING'),
])
def test_rehashed_tampered_receipts_still_rejected(chain, keys, change, error):
    path, manifest, _ = chain
    rewrite_proof(manifest['files'][0], keys, change)
    with pytest.raises(ResearchError, match=error):
        load_bundle(path, manifest)


@pytest.mark.parametrize('change,error', [
    (lambda b: b['files'][0].update(source='Another provider'), 'CAPTURE_PROVIDER_BINDING'),
    (lambda b: b['files'][0].update(retrieved_at='2026-10-13T11:00:00+00:00'), 'CAPTURE_SOURCE_TIME_BINDING'),
    (lambda b: b['files'][0].update(available_at='2026-10-13T11:00:00+00:00', retrieved_at='2026-10-13T11:00:00+00:00'), 'CAPTURE_SOURCE_TIME_BINDING'),
    (lambda b: b.update(universe_scope='PROVIDER_SAMPLE'), 'CAPTURE_SCOPE_BINDING'),
    (lambda b: b.update(window_start='2026-04-02'), 'CAPTURE_SCOPE_BINDING'),
])
def test_manifest_cannot_relabel_captured_time_or_scope(chain, change, error):
    path, manifest, _ = chain
    change(manifest)
    with pytest.raises(ResearchError, match=error):
        load_bundle(path, manifest)


def test_mock_cannot_be_promoted_to_local_capture_bound(tmp_path):
    _, _, destination = approved_mock(tmp_path, fixture_plan())
    path = tmp_path / 'mock-bundle.json'
    manifest = make_capture_bundle(destination, path)
    manifest['files'][0]['evidence_grade'] = 'LOCAL_CAPTURE_BOUND'
    with pytest.raises(ResearchError, match='CAPTURE_GRADE_MISMATCH'):
        load_bundle(path, manifest)
    _, inputs = load_bundle(path)
    assert all(row['evidence_grade'] == 'SYNTHETIC' for _, _, rows in inputs for row in rows)


def test_valid_chain_rebuilds_from_retained_proofs_without_original_paths(chain, tmp_path):
    path, manifest, destination = chain
    # Evidence role order and historical source implementation pin need not match
    # today's collector. Conservative delayed availability is allowed.
    manifest['files'][0]['evidence'].reverse()
    manifest['files'][0]['available_at'] = '2026-10-14T20:00:00+08:00'
    path.write_bytes(encoded(manifest))
    store = ResearchStore(tmp_path / 'store' / 'research.duckdb')
    bid = store.import_bundle(path)
    original = store.snapshot(bid, '2026-10-14T20:00:00+08:00')
    assert all(row['evidence_grade'] == 'LOCAL_CAPTURE_BOUND' for rows in original[1].values() for row in rows)
    destination.rename(destination.with_name('retained-source-relocated'))
    assert store.snapshot(bid, '2026-10-14T20:00:00+08:00') == original


def test_retained_proof_hash_tamper_is_rejected_even_before_asof(chain, tmp_path):
    path, manifest, _ = chain
    store = ResearchStore(tmp_path / 'store' / 'research.duckdb')
    bid = store.import_bundle(path)
    proof = manifest['files'][0]['evidence'][0]
    (store.path.parent / 'raw' / proof['sha256']).write_bytes(b'{}')
    with pytest.raises(ResearchError, match='RETAINED_SOURCE_CHANGED'):
        store.snapshot(bid, '2026-10-01T00:00:00+08:00')


def test_stored_forged_grade_rejected_despite_consistent_manifest_id(chain, tmp_path):
    from astock.data.warehouse_lock import warehouse_connection
    path, manifest, _ = chain
    store = ResearchStore(tmp_path / 'store' / 'research.duckdb')
    original_id = store.import_bundle(path)
    retained, _ = store.snapshot(original_id, ASOF)
    # Production-shaped corruption: recompute manifest ID and retain byte hashes,
    # then break semantic receipt binding. Snapshot must not trust SQL or its ID.
    forged = copy.deepcopy(retained)
    forged['files'][0]['request']['params']['ts_code'] = forged['universe'][1]
    bid = digest(forged)
    with warehouse_connection(store.path) as db:
        db.execute('INSERT INTO research_bundle VALUES (?,?)', [bid, encoded(forged).decode()])
    with pytest.raises(ResearchError, match='CAPTURE_RECEIPT_BINDING'):
        store.snapshot(bid, '2026-10-01T00:00:00+08:00')
