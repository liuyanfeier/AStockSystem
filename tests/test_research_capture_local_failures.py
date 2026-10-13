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


@pytest.mark.parametrize('truncated', [True, False])
def test_continuation_cannot_consume_rest_after_truncation(tmp_path,truncated):
    from research_fixture import response
    plan=fixture_plan()
    def handler(member,count):
        value=response(plan,member)
        if truncated:value['data']['has_more']=True
        else:value['data']['items']*=member['row_cap']
        return httpx.Response(200,stream=BytesStream(encoded(value)))
    result,calls,_=approved_mock(tmp_path,plan,handler,continue_on_error=True)
    assert len(calls)==1 and result['stopped']=='FAILED' and result['unattempted']==38


def test_permission_errors_are_bounded(tmp_path):
    def handler(member,count):
        return httpx.Response(200,stream=BytesStream(encoded(dict(code=-2002,msg='SYNTHETIC permission',data=None))))
    result,calls,_=approved_mock(tmp_path,fixture_plan(),handler,continue_on_error=True)
    assert len(calls)==3 and result['stopped']=='PROTOCOL_CIRCUIT'


@pytest.mark.parametrize('code', ['PROVIDER_ROW_SHAPE', 'PROVIDER_NUMERIC_TYPE'])
def test_validation_protocol_errors_are_bounded(tmp_path, monkeypatch, code):
    from astock.research import acquisition
    from astock.research.core import ResearchError
    def reject(*args):
        raise ResearchError(code)
    monkeypatch.setattr(acquisition, 'payload_rows', reject)
    result, calls, destination = approved_mock(tmp_path, fixture_plan(), continue_on_error=True)
    assert len(calls) == 3 and result['stopped'] == 'PROTOCOL_CIRCUIT' and result['unattempted'] == 36
    assert result['failed_this_run'] == 3 and len(list(destination.glob('*.response.json'))) == 3


def test_repeated_compressed_responses_are_bounded(tmp_path):
    def handler(member, count):
        return httpx.Response(200, headers={'content-encoding': 'gzip'}, stream=BytesStream(b'SYNTHETIC'))
    result, calls, destination = approved_mock(tmp_path, fixture_plan(), handler, continue_on_error=True)
    assert len(calls) == 3 and result['stopped'] == 'PROTOCOL_CIRCUIT' and result['unattempted'] == 36
    assert result['failed_this_run'] == 3 and not list(destination.glob('*.response.json'))


@pytest.mark.parametrize('status,attempts,stop', [
    (401, 1, 'FAILED'), (403, 1, 'FAILED'), (429, 1, 'FAILED'),
    (500, 3, 'HTTP_CIRCUIT'), (503, 3, 'HTTP_CIRCUIT'),
])
def test_full_market_http_refusal_cannot_consume_299(tmp_path, status, attempts, stop):
    from market_fixture import plan
    from astock.research.acquisition import capture_status
    def handler(member, count):
        return httpx.Response(status, stream=BytesStream(b'SYNTHETIC_TEST_TOKEN_12345 private response'))
    result, calls, destination = approved_mock(tmp_path, plan(), handler, continue_on_error=True)
    assert len(calls) == attempts and result['stopped'] == stop
    assert result['unattempted'] == 299 - attempts
    assert capture_status(destination)['states']['FAILED'] == attempts
    assert len(list(destination.glob('*.claim.json'))) == attempts
    assert not list(destination.glob('*.response.json'))
    for receipt in destination.glob('*.result.json'):
        assert f'HTTP_{status}'.encode() in receipt.read_bytes()
        assert b'SYNTHETIC_TEST_TOKEN_12345' not in receipt.read_bytes()


@pytest.mark.parametrize('mixed', [False, True])
def test_full_market_transport_outage_is_bounded(tmp_path, mixed):
    from market_fixture import plan
    from astock.research.acquisition import capture_status
    def handler(member, count):
        error = httpx.ReadTimeout if mixed and count == 2 else httpx.ConnectError
        raise error('SYNTHETIC_TEST_TOKEN_12345 DNS/private host')
    result, calls, destination = approved_mock(tmp_path, plan(), handler, continue_on_error=True)
    assert len(calls) == 3 and result['stopped'] == 'TRANSPORT_CIRCUIT'
    assert result['unattempted'] == 296 and result['unknown_this_run'] == 3
    assert capture_status(destination)['states']['UNKNOWN'] == 3
    assert len(list(destination.glob('*.claim.json'))) == 3
    assert all(b'SYNTHETIC_TEST_TOKEN_12345' not in p.read_bytes() for p in destination.glob('*.result.json'))


def test_success_resets_http_and_transport_counters(tmp_path):
    plan = fixture_plan()
    def handler(member, count):
        if count in {1, 2, 4, 5}:
            return httpx.Response(503)
        if count in {7, 8, 10, 11}:
            raise httpx.ConnectError('SYNTHETIC private')
        return httpx.Response(200, stream=BytesStream(encoded(response(plan, member))))
    result, calls, _ = approved_mock(tmp_path, plan, handler, continue_on_error=True)
    assert len(calls) == 39 and result['stopped'] is None
    assert result['complete_this_run'] == 31


def test_body_cap_stops_continuation_without_publishing_partial_raw(tmp_path):
    plan = fixture_plan()
    def handler(member, count):
        return httpx.Response(200, stream=BytesStream(b'x' * (plan['max_body_bytes'] + 1)))
    result, calls, destination = approved_mock(tmp_path, plan, handler, continue_on_error=True)
    assert len(calls) == 1 and result['stopped'] == 'FAILED'
    assert not list(destination.glob('*.response.json'))


def test_destination_budget_blocks_call_before_claim(tmp_path, monkeypatch):
    from astock.research import acquisition
    from astock.research.core import ResearchError
    from market_fixture import plan
    p = plan()
    monkeypatch.setattr(acquisition, 'disk_bytes', lambda _: p['max_added_disk_bytes'])
    calls = []
    with pytest.raises(ResearchError, match='CAPTURE_DISK_BUDGET'):
        approved_mock(tmp_path, p, lambda member, count: calls.append(member), continue_on_error=True)
    assert not calls and not list((tmp_path / p['destination']).glob('*.claim.json'))
