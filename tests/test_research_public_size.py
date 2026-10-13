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
