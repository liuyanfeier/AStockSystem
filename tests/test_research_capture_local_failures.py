"""Local failure never licenses another HTTP attempt; immutable history survives."""
import httpx
import pytest
from research_fixture import fixture_plan, approved_mock, response, BytesStream
from astock.research.core import encoded

@pytest.mark.parametrize('error', [OSError('SYNTHETIC_PRIVATE_CONTEXT'), RuntimeError('SYNTHETIC_PRIVATE_CONTEXT')])
def test_publication_fault_stops_continuing_capture(tmp_path, monkeypatch, error):
    from astock.research import acquisition
    publish = acquisition.publish_bytes
    def fail_raw(path, body):
        if path.name.endswith('.response.json'):
            raise error
        publish(path, body)
    monkeypatch.setattr(acquisition, 'publish_bytes', fail_raw)
    result, calls, destination = approved_mock(tmp_path, fixture_plan(), continue_on_error=True)
    assert len(calls) == 1 and result['unattempted'] == 38 and result['stopped'] == 'UNKNOWN'
    assert len(list(destination.glob('*.claim.json'))) == len(list(destination.glob('*.result.json'))) == 1
    assert all(b'SYNTHETIC_PRIVATE_CONTEXT' not in p.read_bytes() for p in destination.glob('*.result.json'))


def test_unknown_validation_fault_stops_continuing_capture(tmp_path, monkeypatch):
    from astock.research import acquisition
    def fail(*args):
        raise RuntimeError('SYNTHETIC_PRIVATE_CONTEXT')
    monkeypatch.setattr(acquisition, 'payload_rows', fail)
    result, calls, destination = approved_mock(tmp_path, fixture_plan(), continue_on_error=True)
    assert len(calls) == 1 and result['stopped'] == 'UNKNOWN'
    assert len(list(destination.glob('*.response.json'))) == 1


def test_three_identical_protocol_errors_open_circuit(tmp_path):
    def bad(member, count):
        return httpx.Response(200, stream=BytesStream(encoded({'unexpected': 'SYNTHETIC_SCHEMA'})))
    result, calls, destination = approved_mock(tmp_path, fixture_plan(), bad, continue_on_error=True)
    assert len(calls) == 3 and result['stopped'] == 'PROTOCOL_CIRCUIT' and result['unattempted'] == 36
    assert len(list(destination.glob('*.claim.json'))) == 3
    assert len(list(destination.glob('*.response.json'))) == 3
