"""Spawned G2 fault/concurrency workers. Only parent-provided temporary synthetic roots."""

import os
import socket
from pathlib import Path
from uuid import UUID

import duckdb

from astock.data.warehouse_lock import warehouse_lock, warehouse_connection, WarehouseConnectionProxy


def deny_network():
    def deny(*args, **kwargs):
        raise AssertionError('Market/network access forbidden in G2 subprocess tests')
    socket.create_connection = socket.getaddrinfo = deny
    socket.socket.connect = socket.socket.connect_ex = deny


def lock_worker(pipe, path, mode):
    deny_network()
    try:
        if mode == 'native':
            # Deliberately uncooperative synthetic writer tests native fail-closed handling.
            owner = duckdb.connect(path)
            pipe.send({'event': 'READY'})
            pipe.recv()
            owner.close()
        else:
            try:
                with warehouse_lock(path, shared=mode == 'shared'):
                    pipe.send({'event': 'READY'})
                    command = pipe.recv()
                    if command == 'exception':
                        raise RuntimeError('synthetic lock-body failure')
            except RuntimeError:
                pipe.send({'event': 'RELEASED_AFTER_EXCEPTION'})
                pipe.recv()  # Remain alive: release must not depend on process exit.
            else:
                pipe.send({'event': 'RELEASED'})
    except Exception as error:
        pipe.send({'event': 'ERROR', 'code': getattr(error, 'code', type(error).__name__)})
    finally:
        pipe.close()


def contender(pipe, root, batch, action):
    deny_network()
    root = Path(root)
    calls = dict(constructed=0, fetched=0, claimed=0, preflight=0)
    from astock.data import slice_capture, slice_curate, slice_dq, bootstrap, probe
    from astock.data.tushare_client import TushareClient
    from astock.data.receipt_migration import apply_receipt_integrity_upgrade
    from astock.data.slice_plan import claim_request
    from test_slice_capture import settings
    def construction(*args, **kwargs):
        calls['constructed'] += 1
        raise AssertionError('Provider constructed before writer ownership')
    def fetch(*args, **kwargs):
        calls['fetched'] += 1
        raise AssertionError('Provider fetch must not run')
    def preflight(*args, **kwargs):
        calls['preflight'] += 1
        raise AssertionError('Preflight must not run without ownership')
    TushareClient.__init__ = construction
    TushareClient.fetch_slice = TushareClient.fetch = TushareClient.fetch_bse_mapping = fetch
    slice_capture.request_manifest = slice_curate.request_manifest = preflight
    slice_dq.identity_state = preflight
    bootstrap.load_curation_specs = probe.load_plan = preflight
    try:
        if action == 'capture':
            slice_capture.capture_slices(root, settings(), live=True, batch_id=UUID(batch), commit='a' * 40)
        elif action == 'curate':
            slice_curate.curate_slices(root, UUID(batch), commit='a' * 40)
        elif action == 'dq':
            slice_dq.dq_slices(root, UUID(batch))
        elif action == 'bootstrap':
            bootstrap.run_bootstrap(root, settings(), authority_path=root/'not-read.json')
        elif action == 'probe':
            probe.run_probe(root, settings())
        else:
            with warehouse_connection(root/'data/warehouse/astock.duckdb') as db:
                if action == 'upgrade':
                    apply_receipt_integrity_upgrade(root, db, verification_sha='a' * 40)
                elif action == 'claim':
                    calls['claimed'] += 1
                    claim_request(db, UUID(batch), 0)
                elif action == 'publish':
                    from astock.data.raw_writer import atomic_new_file
                    atomic_new_file(root/'data/private/publisher-should-not-run.json', lambda p: p.write_text('{}'))
                elif action == 'audit':
                    raise AssertionError('Use the actual read-only audit entry point')
        pipe.send({'event': 'UNEXPECTED_SUCCESS', **calls})
    except Exception as error:
        pipe.send({'event': 'BLOCKED', 'code': getattr(error, 'code', type(error).__name__), **calls})
    finally:
        pipe.close()


class CrashDB(WarehouseConnectionProxy):
    def __init__(self, db, pattern, after=False):
        super().__init__(db)
        self.db, self.pattern, self.after = db, pattern, after

    def execute(self, sql, *args):
        if self.pattern and self.pattern in sql and not self.after:
            os._exit(72)
        result = self.db.execute(sql, *args)
        if self.pattern and self.pattern in sql and self.after:
            os._exit(72)
        return result


def crash_worker(root, batch, action, pattern='', after=False):
    deny_network()
    from astock.data.audit import RequestParams
    from astock.data.contracts import load_contracts
    from astock.data.raw_writer import RawWriter
    from astock.data.receipt_integrity import batch_requests
    from astock.data.slice_plan import claim_request
    from astock.data.slice_capture import finalize_receipt, publish_capture_metadata
    from test_slice_capture import SyntheticCaptureClient
    root = Path(root)
    with warehouse_connection(root/'data/warehouse/astock.duckdb') as db:
        fault = CrashDB(db, pattern, after)
        if action == 'claim':
            claim_request(fault, UUID(batch), 1)
        elif action == 'finalize':
            req = batch_requests(db, UUID(batch))[1]
            contract = next(c for c in load_contracts(root, catalog_version='v2') if c.dataset == 'daily')
            finalize_receipt(root, fault, req, contract, verification_sha='a' * 40)
        else:
            req = batch_requests(db, UUID(batch))[1]
            contract = next(c for c in load_contracts(root, catalog_version='v2') if c.dataset == 'daily')
            params = RequestParams.model_validate_json(req['request_params'])
            table = SyntheticCaptureClient().fetch_slice(contract, params)
            raw = RawWriter(root, fault).write(req['run_id'], req['dataset'], 0, table, params)
            if action == 'metadata':
                publish_capture_metadata(root, db, req, contract,
                    dict(object_id=str(raw.object_id), relative_path=raw.relative_path, sha256=raw.sha256))
        os._exit(73)  # Crash after the requested committed stage, before the next action.


def capture_owner(pipe, root, batch):
    deny_network()
    from astock.data.slice_capture import capture_slices
    from test_slice_capture import settings, SyntheticCaptureClient
    root = Path(root)
    class PausedClient(SyntheticCaptureClient):
        def fetch_slice(self, contract, params):
            # A second connection sees the committed claim before synthetic fetch.
            with warehouse_connection(root/'data/warehouse/astock.duckdb') as observer:
                attempts, count = observer.execute('''SELECT sum(s.attempts),sum(r.request_count)
                    FROM slice_request s JOIN ingestion_run r USING(run_id)''').fetchone()
            pipe.send({'event': 'FETCH_ENTERED', 'attempts': attempts, 'request_count': count})
            pipe.recv()
            return super().fetch_slice(contract, params)
    client = PausedClient()
    try:
        result = capture_slices(root, settings(), live=True, batch_id=UUID(batch), stop_after=1,
                                client=client, commit='a' * 40)
        pipe.send({'event': 'FINISHED', 'result': result, 'fetched': len(client.calls)})
    except Exception as error:
        pipe.send({'event': 'ERROR', 'code': getattr(error, 'code', type(error).__name__)})
    finally:
        pipe.close()


def publication_owner(pipe, root, batch):
    deny_network()
    from astock.data import raw_writer
    from astock.data.audit import RequestParams
    from astock.data.contracts import load_contracts
    from astock.data.receipt_integrity import batch_requests
    from astock.data.slice_plan import claim_request
    from astock.data.slice_capture import finalize_receipt, publish_capture_metadata
    from test_slice_capture import SyntheticCaptureClient
    root = Path(root)
    original = raw_writer.atomic_new_file
    def paused(path, write):
        if path.name != 'part-000.parquet': return original(path, write)
        def callback(temporary):
            write(temporary)
            pipe.send({'event': 'PUBLICATION_PAUSED'})
            pipe.recv()
        return original(path, callback)
    raw_writer.atomic_new_file = paused
    try:
        with warehouse_connection(root/'data/warehouse/astock.duckdb') as db:
            claim_request(db, UUID(batch), 1)
            req = batch_requests(db, UUID(batch))[1]
            contract = next(c for c in load_contracts(root, catalog_version='v2') if c.dataset == 'daily')
            params = RequestParams.model_validate_json(req['request_params'])
            raw = raw_writer.RawWriter(root, db).write(req['run_id'], 'daily', 0,
                SyntheticCaptureClient().fetch_slice(contract, params), params)
            publish_capture_metadata(root, db, req, contract,
                dict(object_id=str(raw.object_id), relative_path=raw.relative_path, sha256=raw.sha256))
            finalize_receipt(root, db, req, contract, verification_sha='a' * 40)
        pipe.send({'event': 'FINISHED'})
    except Exception as error:
        pipe.send({'event': 'ERROR', 'code': getattr(error, 'code', type(error).__name__)})
    finally:
        pipe.close()
