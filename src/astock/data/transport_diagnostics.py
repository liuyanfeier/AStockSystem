"""Allowlisted observations; never serialize request or exception content."""

import socket
import ssl
import time
from datetime import datetime, timezone

import certifi
import httpx

HOST = 'api.tushare.pro'
PORT = 443
ERROR_TYPES = (
    (ssl.SSLCertVerificationError, 'TLS_CERTIFICATE_VERIFICATION'),
    (ssl.SSLError, 'TLS_ERROR'),
    (socket.gaierror, 'DNS_ERROR'),
    (httpx.ConnectTimeout, 'CONNECT_TIMEOUT'),
    (httpx.ConnectError, 'CONNECT_ERROR'),
    (httpx.ReadTimeout, 'READ_TIMEOUT'),
    (httpx.ReadError, 'READ_ERROR'),
    (httpx.RemoteProtocolError, 'REMOTE_PROTOCOL_ERROR'),
    (TimeoutError, 'TIMEOUT'),
    (PermissionError, 'PERMISSION_DENIED'),
    (ConnectionError, 'CONNECTION_ERROR'),
    (OSError, 'OS_ERROR'),
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def error_type(error: BaseException | None) -> str:
    if error is None:
        return 'NONE'
    return next((label for kind, label in ERROR_TYPES if isinstance(error, kind)), 'OTHER_EXCEPTION')


def observation(*, phase: str, started_at: str, ended_at: str, headers_received: bool,
                body_bytes: int, eof: bool, error: BaseException | None = None) -> dict:
    if (phase not in ('DNS', 'TCP', 'TLS', 'AWAIT_HEADERS', 'READ_BODY', 'COMPLETE')
            or type(headers_received) is not bool or type(eof) is not bool
            or type(body_bytes) is not int or body_bytes < 0):
        raise ValueError('DIAGNOSTIC_SCHEMA_INVALID')
    first = datetime.fromisoformat(started_at); last = datetime.fromisoformat(ended_at)
    if first.utcoffset() is None or last.utcoffset() is None or last < first:
        raise ValueError('DIAGNOSTIC_TIME_INVALID')
    return dict(protocol='SAFE_TRANSPORT_OBSERVATION_V1', phase=phase,
                started_at=first.astimezone(timezone.utc).isoformat(),
                ended_at=last.astimezone(timezone.utc).isoformat(),
                duration_seconds=(last-first).total_seconds(), error_type=error_type(error),
                headers_received=headers_received, body_bytes=body_bytes, eof=eof,
                endpoint_host=HOST, port=PORT, route_mode='DIRECT_TRUST_ENV_FALSE',
                TLS_verify=True, historical_delivery='UNKNOWN_PAST_TRANSPORT_REASON')


def connection_probe(record) -> dict:
    """Caller owns an exclusive one-shot ledger; no HTTP and no credentials.

    record persists CALL_ENTERED before each stage. Single getaddrinfo, first address
    only, one TCP socket, same socket for one verified TLS handshake. Never retries.
    """
    results = []; raw = None; wrapped = None
    phase = 'DNS'; started = utc(); tick = time.monotonic()
    record(dict(state='CALL_ENTERED', phase=phase, started_at=started))
    try:
        addresses = socket.getaddrinfo(HOST, PORT, type=socket.SOCK_STREAM)
        if not addresses:
            raise socket.gaierror()
        result = observation(phase=phase, started_at=started, ended_at=utc(),
                             headers_received=False, body_bytes=0, eof=False)
        result.update(state='SUCCESS', monotonic_duration=time.monotonic()-tick,
                      resolved_address_count=len(addresses))
        results.append(result); record(result)
        phase = 'TCP'; started = utc(); tick = time.monotonic()
        record(dict(state='CALL_ENTERED', phase=phase, started_at=started))
        family, kind, proto, _, address = addresses[0]
        raw = socket.socket(family, kind, proto); raw.settimeout(10)
        raw.connect(address)
        result = observation(phase=phase, started_at=started, ended_at=utc(),
                             headers_received=False, body_bytes=0, eof=False)
        result.update(state='SUCCESS', monotonic_duration=time.monotonic()-tick)
        results.append(result); record(result)
        phase = 'TLS'; started = utc(); tick = time.monotonic()
        record(dict(state='CALL_ENTERED', phase=phase, started_at=started))
        context = ssl.create_default_context(cafile=certifi.where())
        wrapped = context.wrap_socket(raw, server_hostname=HOST, do_handshake_on_connect=False)
        wrapped.do_handshake()
        result = observation(phase=phase, started_at=started, ended_at=utc(),
                             headers_received=False, body_bytes=0, eof=False)
        result.update(state='SUCCESS', monotonic_duration=time.monotonic()-tick)
        results.append(result); record(result)
    except Exception as error:
        result = observation(phase=phase, started_at=started, ended_at=utc(),
                             headers_received=False, body_bytes=0, eof=False, error=error)
        result.update(state='FAILED_NO_RETRY', monotonic_duration=time.monotonic()-tick)
        results.append(result); record(result)
    finally:
        if wrapped is not None:
            wrapped.close()
        elif raw is not None:
            raw.close()
    return dict(status='CONNECTED_TLS_NO_HTTP' if results[-1]['state']=='SUCCESS'
                and results[-1]['phase']=='TLS' else 'DIAGNOSTIC_STOPPED_NO_RETRY',
                phases=results, DNS_calls=1, TCP_calls=int(any(r['phase']=='TCP' for r in results)),
                TLS_calls=int(any(r['phase']=='TLS' for r in results)),
                TCP_connections=int(any(r['phase']=='TCP' for r in results)), HTTP_calls=0,
                token_sent=False, historical_reason='UNKNOWN_PAST_TRANSPORT_REASON')
