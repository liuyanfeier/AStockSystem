"""Explicit continuing authorization; durable failures and secret guards stay intact."""
import hashlib

import httpx
import pytest

from astock.research.acquisition import capture_status, read_capture, safe_exception_code
from astock.research.core import ResearchError, encoded
from astock.research.store import ResearchStore
from astock.research.tushare import make_capture_bundle
from research_fixture import ASOF, BytesStream, approved_mock, fixture_plan, response


@pytest.mark.parametrize('error,code', [
    (httpx.ReadTimeout('secret request body'), 'TRANSPORT_TIMEOUT'),
    (httpx.ConnectError('secret request body'), 'TRANSPORT_CONNECT_ERROR'),
    (httpx.RemoteProtocolError('secret request body'), 'TRANSPORT_REMOTE_PROTOCOL_ERROR'),
    (httpx.ReadError('secret request body'), 'TRANSPORT_ERROR'),
    (httpx.StreamConsumed(), 'CAPTURE_STREAM_CONSUMED'),
    (OSError('secret request body'), 'CAPTURE_OS_ERROR'),
    (ValueError('secret request body'), 'CAPTURE_INTERNAL_ERROR'),
])
def test_exception_categories_never_include_native_messages(error, code):
    assert safe_exception_code(error) == code


def test_continue_consumes_other_members_without_rewriting_failed_attempts(tmp_path):
    plan = fixture_plan()
    def handler(member, count):
        if count == 1:
            raise httpx.ReadTimeout('SYNTHETIC_TEST_TOKEN_12345')
        value = response(plan, member)
        if count == 2:
            value['code'] = -2002
        return httpx.Response(200, stream=BytesStream(encoded(value)))
    result, calls, destination = approved_mock(tmp_path, plan, handler, continue_on_error=True)
    assert len(calls) == 39 and result['stopped'] is None and result['unattempted'] == 0
    assert result['complete_this_run'] == 37 and result['failed_this_run'] == result['unknown_this_run'] == 1
    assert capture_status(destination)['states'] == dict(COMPLETE=37, FAILED=1, UNKNOWN=1, UNATTEMPTED=0)
    assert len(read_capture(destination)[1]) == 37
    old = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir() if p.is_file()}
    with pytest.raises(ResearchError, match='APPROVAL_UNATTEMPTED_MEMBERS'):
        approved_mock(tmp_path, plan, continue_on_error=True)
    assert old == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir() if p.is_file()}
    assert all(b'SYNTHETIC_TEST_TOKEN_12345' not in p.read_bytes() for p in destination.glob('*.result.json'))


def test_continuing_approval_verifies_through_retained_store(tmp_path):
    result, _, destination = approved_mock(tmp_path, fixture_plan(), continue_on_error=True)
    assert result['complete_this_run'] == 39
    manifest = make_capture_bundle(destination)
    from astock.research.core import digest
    store = ResearchStore(destination / 'research.duckdb')
    bundle = store.import_bundle(destination / f'{digest(manifest)}.bundle.json')
    retained, rows = store.snapshot(bundle, ASOF)
    assert all(f['evidence_grade'] == 'SYNTHETIC' for f in retained['files'])
    assert rows['daily']


@pytest.mark.parametrize('policy', [1, 'yes', []])
def test_continuation_requires_actual_boolean(tmp_path, policy):
    with pytest.raises(ResearchError, match='CAPTURE_CONTINUATION_POLICY'):
        approved_mock(tmp_path, fixture_plan(), continue_on_error=policy)
    assert not (tmp_path / fixture_plan()['destination']).exists()


def test_continuing_mode_still_stops_on_credential_in_response(tmp_path):
    plan = fixture_plan()
    def handler(member, count):
        value = response(plan, member)
        value['msg'] = 'SYNTHETIC_TEST_TOKEN_12345'
        return httpx.Response(200, stream=BytesStream(encoded(value)))
    result, calls, destination = approved_mock(tmp_path, plan, handler, continue_on_error=True)
    assert len(calls) == 1 and result['stopped'] == 'FAILED' and result['unattempted'] == 38
    assert not list(destination.glob('*.response.json'))


def test_rejected_schema_bytes_are_preserved_without_admission(tmp_path):
    plan = fixture_plan()
    body = encoded({'code': 0, 'unexpected': 'SYNTHETIC_PROVIDER_METADATA'})
    def handler(member, count):
        return httpx.Response(200, stream=BytesStream(body))
    result, _, destination = approved_mock(tmp_path, plan, handler)
    assert result['complete_this_run'] == 0 and result['failed_this_run'] == 1
    _, receipts = read_capture(destination)
    assert receipts == []
    saved = list(destination.glob('*.response.json'))
    assert len(saved) == 1 and saved[0].read_bytes() == body
    with pytest.raises(Exception):
        make_capture_bundle(destination)
    saved[0].write_bytes(body + b' ')
    with pytest.raises(ResearchError, match='CAPTURE_OBJECT_CHANGED'):
        read_capture(destination)


def test_actual_optional_metadata_does_not_replace_item_rows():
    from astock.research.tushare import decode_response
    plan = fixture_plan()
    member = plan['members'][0]
    value = response(plan, member)
    value['detail'] = 'SYNTHETIC_METADATA'
    value['data']['count'] = 0  # real observed shape; count is not coverage
    rows = decode_response(encoded(value), member)
    assert len(rows) == 1 and rows[0]['ts_code'] == member['params']['ts_code']
    value['data']['has_more'] = True
    with pytest.raises(ResearchError, match='PROVIDER_TRUNCATED'):
        decode_response(encoded(value), member)


@pytest.mark.parametrize('field,value,code', [
    ('detail', {}, 'PROVIDER_METADATA_TYPE'),
    ('count', True, 'PROVIDER_COUNT_TYPE'),
    ('count', -1, 'PROVIDER_COUNT_TYPE'),
    ('count', '1', 'PROVIDER_COUNT_TYPE'),
])
def test_optional_metadata_remains_strict(field, value, code):
    from astock.research.tushare import decode_response
    plan = fixture_plan()
    member = plan['members'][0]
    payload = response(plan, member)
    (payload if field == 'detail' else payload['data'])[field] = value
    with pytest.raises(ResearchError, match=code):
        decode_response(encoded(payload), member)
