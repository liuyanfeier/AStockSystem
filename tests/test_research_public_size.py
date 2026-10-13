"""Public full-market metrics keep reconstructible provenance with bounded repetition."""
from copy import deepcopy
from hashlib import sha256
from astock.research.core import encoded
from astock.research.public_results import public_snapshot


def test_six_thousand_features_intern_source_hashes_without_mutating_input():
    hashes = [sha256(str(i).encode()).hexdigest() for i in range(260)]
    snapshot = dict(sources=[], features=[dict(code=str(i), return_20=.03, source_hashes=hashes[:])
                    for i in range(6000)], candidates=[dict(metrics=dict(source_hashes=hashes[:]))],
                    journal=dict(positions=[dict(private_note='PRIVATE_PERSONAL_RECORD')]))
    before = deepcopy(snapshot)
    result = public_snapshot(snapshot)
    assert snapshot == before
    assert len(result['source_hash_sets']) == 1
    for feature in result['features']:
        assert result['source_hash_sets'][feature['source_hash_set_id']] == sorted(hashes)
        assert feature['return_20'] == .03 and 'source_hashes' not in feature
    assert result['candidates'][0]['metrics']['source_hashes'] == hashes
    assert len(encoded(result)) < 10 * 1024 * 1024
    assert b'PRIVATE_PERSONAL_RECORD' not in encoded(result)


def test_manual_watch_source_description_and_journal_are_private():
    snapshot = dict(features=[dict(code='PROGRAM_POOL', source_hashes=['a' * 64])],
                    candidates=[dict(code='PROGRAM_CANDIDATE', metrics=dict(source_hashes=['a' * 64]))],
                    manual_cards=[dict(code='PRIVATE_MANUAL_CHOICE', note='PRIVATE_MANUAL_NOTE')],
                    journal=dict(positions=[dict(code='PRIVATE_HOLDING')],
                                 executions=['PRIVATE_EXECUTION'], pending_confirmation=['PRIVATE_EVENT']),
                    sources=[dict(dataset='daily', sha256='a' * 64, evidence_grade='USER_DECLARED',
                                  source='/Users/private/account-123 PRIVATE_THESIS',
                                  path='/Users/private/raw.json', request=dict(note='PRIVATE_REQUEST'),
                                  provider_ref='PRIVATE_ACCOUNT', evidence=[dict(path='/Users/private/claim', sha256='b' * 64)])])
    before = deepcopy(snapshot)
    result = public_snapshot(snapshot)
    body = encoded(result)
    assert b'PRIVATE_' not in body and b'/Users/' not in body and b'account-123' not in body
    assert result['manual_cards'] == [] and 'journal' not in result
    assert result['candidates'][0]['code'] == 'PROGRAM_CANDIDATE'
    assert result['sources'][0]['sha256'] == 'a' * 64
    assert result['sources'][0]['evidence_hashes'] == ['b' * 64]
    assert snapshot == before
