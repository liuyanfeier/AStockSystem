import json
from datetime import datetime, timezone
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from astock.data.audit import (
    MockProviderTransport, RawObjectManifest, RequestParams, SafeError,
    TransportConfig, redact_request_params,
)


SECRET = 'synthetic-sensitive-value-not-a-real-credential'
RUN = UUID('00000000-0000-0000-0000-000000000001')


@pytest.mark.parametrize('url', [
    'http://api.tushare.pro', 'ftp://api.tushare.pro', '//api.tushare.pro',
    'https://user:password@api.tushare.pro', 'https://api.tushare.pro?token=x',
    'https://api.tushare.pro#fragment', 'https://',
])
def test_transport_rejects_insecure_or_secret_bearing_url(url):
    with pytest.raises(ValidationError):
        TransportConfig(endpoint=url)


@pytest.mark.parametrize('target', ['http://api.tushare.pro', 'https://other.example'])
@pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
def test_mock_transport_rejects_every_redirect_without_following(target, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={'Location': target})

    client = MockProviderTransport(TransportConfig(), httpx.MockTransport(handler))
    error = client.probe('stock_basic', RequestParams())
    assert error.category == 'REDIRECT'
    assert len(calls) == 1
    assert calls[0].url.scheme == 'https'
    assert json.loads(calls[0].content)['token'] == ''
    assert target not in error.model_dump_json()


def test_real_network_transport_cannot_be_constructed():
    with pytest.raises(TypeError, match='MockTransport'):
        MockProviderTransport(TransportConfig(), object())


def test_params_redaction_drops_nested_secrets_and_invalid_allowed_values():
    clean = redact_request_params({
        'token': SECRET, 'Authorization': SECRET, 'password': SECRET,
        'nested': {'TUSHARE_TOKEN': SECRET}, 'ts_code': SECRET,
        'trade_date': '2024-01-03', 'list_status': 'D', 'start_date': {'token': SECRET},
    })
    assert clean == {'trade_date': '2024-01-03', 'list_status': 'D'}
    assert SECRET not in json.dumps(clean)


def test_errors_do_not_echo_provider_message_or_http_exception():
    for handler in (
        lambda request: httpx.Response(200, json={'code': 40101, 'msg': SECRET}),
        lambda request: httpx.Response(200, content=SECRET),
        lambda request: httpx.Response(500, text=SECRET),
        lambda request: httpx.Response(200, json={'code': SECRET}),
    ):
        error = MockProviderTransport(TransportConfig(), httpx.MockTransport(handler)).probe(
            'daily', RequestParams())
        assert error is not None
        assert SECRET not in repr(error) + error.model_dump_json()

    def failure(request):
        raise httpx.ConnectError(SECRET, request=request)

    error = MockProviderTransport(TransportConfig(), httpx.MockTransport(failure)).probe(
        'daily', RequestParams())
    assert error.category == 'TRANSPORT'
    assert SECRET not in error.model_dump_json()
    with pytest.raises(ValidationError):
        SafeError(category='AUTH', message=SECRET)


def manifest_values():
    return dict(object_id=UUID('00000000-0000-0000-0000-000000000002'), run_id=RUN,
                dataset='daily', relative_path=f'data/raw/tushare/daily/run_id={RUN}/part-000.parquet',
                sha256='a' * 64, schema_hash='b' * 64,
                retrieved_at=datetime(2024, 1, 3, tzinfo=timezone.utc), row_count=0,
                request_params=RequestParams.model_validate(redact_request_params({'token': SECRET})))


def test_manifest_can_serialize_only_public_typed_metadata():
    manifest = RawObjectManifest(**manifest_values())
    assert SECRET not in manifest.model_dump_json()
    assert 'token' not in manifest.model_dump_json()
    assert manifest.request_params.public_dict() == {}
    assert json.loads(manifest.model_dump_json())['request_params'] == {}


@pytest.mark.parametrize('change', [
    {'sha256': 'not-a-checksum'}, {'schema_hash': 'a' * 63}, {'row_count': -1},
    {'relative_path': '/tmp/part-000.parquet'}, {'relative_path': '../private/file.parquet'},
    {'relative_path': 'data/raw/tushare/daily/run_id=wrong/part-000.parquet'},
    {'retrieved_at': '2024-01-03T00:00:00'}, {'request_params': {'token': SECRET}},
    {'request_params': {'ts_code': SECRET}}, {'min_event_date': '2024-01-03'},
    {'min_event_date': '2024-01-04', 'max_event_date': '2024-01-03'},
])
def test_manifest_rejects_unsafe_or_inconsistent_metadata(change):
    with pytest.raises(ValidationError):
        RawObjectManifest(**(manifest_values() | change))
