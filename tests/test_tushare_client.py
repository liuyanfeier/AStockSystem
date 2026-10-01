import json
import ssl
from datetime import date

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from astock.data.audit import RequestParams, TransportConfig
from astock.data.contracts import load_contracts, require_https
from astock.data.tushare_client import ProviderFailure, TushareClient
from astock.paths import get_project_root


SECRET = 'synthetic-real-path-token-not-an-actual-credential'
CONTRACT = {c.dataset:c for c in load_contracts(get_project_root(), catalog_version="v1")}['trade_cal']


def make_client(handler):
    clock = [0.0]
    waits = []
    def sleep(seconds):
        waits.append(seconds)
        clock[0] += seconds
    return TushareClient(SecretStr(SECRET), transport=httpx.MockTransport(handler),
                         clock=lambda:clock[0], sleep=sleep), waits


def success():
    return httpx.Response(200, json={'code':0,'data':{'fields':CONTRACT.required_fields,
        'items':[['SSE','20260930',1,'20260929']]}})


@pytest.mark.parametrize('url', ['https://evil.example','https://api.tushare.pro:444',
    'https://api.tushare.pro/dataapi','https://api.tushare.pro?','https://api.tushare.pro#',
    'https://@api.tushare.pro','http://api.tushare.pro','https://api.tushare.pro.evil.example',
    'https://api.tushare.pro./','https://127.0.0.1'])
def test_exact_pinning(url):
    with pytest.raises(ValueError):
        require_https(url)
    with pytest.raises(ValidationError):
        TransportConfig(endpoint=url)
    with pytest.raises(ValueError):
        TushareClient(SecretStr(SECRET), endpoint=url)


@pytest.mark.parametrize('url', ['https://api.tushare.pro','https://api.tushare.pro/',
                               'https://api.tushare.pro:443/'])
def test_only_pinned_origin_accepted(url):
    assert require_https(url) == 'https://api.tushare.pro'


def test_explicit_fields_wire_date_and_redacted_client():
    seen=[]
    def handler(request):
        seen.append(json.loads(request.content))
        assert str(request.url)=='https://api.tushare.pro'
        return success()
    client,_=make_client(handler)
    result=client.fetch(CONTRACT,RequestParams(trade_date=date(2026,9,30)))
    assert seen[0]['params']['trade_date']=='20260930'
    assert seen[0]['fields']==','.join(CONTRACT.required_fields)
    assert seen[0]['token']==SECRET
    assert SECRET not in repr(client)+result.model_dump_json()


@pytest.mark.parametrize('code,category', [(2002,'PERMISSION'),(40101,'AUTH'),(-1,'PROVIDER')])
def test_safe_codes_no_retry(code, category):
    client,_=make_client(lambda r:httpx.Response(200,json={'code':code,'msg':SECRET,'data':None}))
    with pytest.raises(ProviderFailure) as exc:
        client.fetch(CONTRACT,RequestParams())
    assert exc.value.error.category==category
    assert client.request_count==1
    assert SECRET not in str(exc.value)+repr(exc.value)+exc.value.error.model_dump_json()


@pytest.mark.parametrize('code',[301,302,303,307,308])
def test_redirect_never_followed_or_retried(code):
    client,_=make_client(lambda r:httpx.Response(code,headers={'Location':'http://evil.example'}))
    with pytest.raises(ProviderFailure) as exc:
        client.fetch(CONTRACT,RequestParams())
    assert exc.value.error.category=='REDIRECT'
    assert client.request_count==1


@pytest.mark.parametrize('data', [None,[],{}, {'fields':['exchange','exchange'],'items':[]},
    {'fields':CONTRACT.required_fields,'items':[['SSE']]},
    {'fields':['extra'],'items':[]}, {'fields':CONTRACT.required_fields,'items':[[{},None,None,None]]},
    {'fields':CONTRACT.required_fields,'items':[[SECRET,None,None,None]]}])
def test_invalid_responses_fail_closed(data):
    client,_=make_client(lambda r:httpx.Response(200,json={'code':0,'data':data,'msg':SECRET}))
    with pytest.raises(ProviderFailure) as exc:
        client.fetch(CONTRACT,RequestParams())
    assert exc.value.error.category=='INVALID_RESPONSE'
    assert client.request_count==1
    assert SECRET not in str(exc.value)


@pytest.mark.parametrize('transient', ['connect','connect_timeout','read_timeout','500'])
def test_one_transient_retry_and_pacing(transient):
    calls=[]
    def handler(request):
        calls.append(request)
        if len(calls)==1:
            if transient=='500':return httpx.Response(500,text=SECRET)
            kind={'connect':httpx.ConnectError,'connect_timeout':httpx.ConnectTimeout,
                  'read_timeout':httpx.ReadTimeout}[transient]
            raise kind(SECRET,request=request)
        return success()
    client,waits=make_client(handler)
    client.fetch(CONTRACT,RequestParams())
    client.fetch(CONTRACT,RequestParams())
    assert client.request_count==3
    assert waits==[1.25,1.25]


def test_tls_failure_never_retried():
    def handler(request):
        try:raise ssl.SSLCertVerificationError('synthetic certificate failure')
        except ssl.SSLError as cause:raise httpx.ConnectError(SECRET,request=request) from cause
    client,_=make_client(handler)
    with pytest.raises(ProviderFailure):client.fetch(CONTRACT,RequestParams())
    assert client.request_count==1


def test_exhausted_transient_has_only_two_attempts():
    client,_=make_client(lambda r:httpx.Response(503,text=SECRET))
    with pytest.raises(ProviderFailure):client.fetch(CONTRACT,RequestParams())
    assert client.request_count==2


def test_index_endpoints_cannot_be_probed():
    client,_=make_client(lambda r:success())
    contract={c.dataset:c for c in load_contracts(get_project_root(), catalog_version="v1")}['index_daily']
    with pytest.raises(ValueError):client.fetch(contract,RequestParams())
    assert client.request_count==0
