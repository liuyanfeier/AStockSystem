"""Append-only stopped-store continuation; production requires new matched licenses.

Startup exercises isolated closed mocks only. Future production entries are gated
by exact independent review/human evidence, original store/root and fresh consumption.
"""

import hashlib
import io
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import httpx
import pyarrow.parquet as pq
from pydantic import SecretStr

from astock.data import full_backfill_v1 as old
from astock.data import transport_diagnostics as diagnostics
from astock.data.receipt_integrity import serial
from astock.data.warehouse_lock import warehouse_connection

PROTOCOL = 'CAPTURE_CONTINUATION_V3'
SOURCE = 'src/astock/data/capture_continuation_v3.py'
DDL = 'sql/offline/capture_continuation_v3.sql'
DESIGN = 'docs/remediation/phase1c2-startup/continuation-v3-design.md'
DIAGNOSTICS = 'src/astock/data/transport_diagnostics.py'
OLD_TABLES = ('backfill_authorization', 'backfill_event', 'backfill_member',
              'backfill_pin', 'backfill_plan_member', 'backfill_receipt')
NEW_TABLES = ('continuation_attempt', 'continuation_authorization', 'continuation_baseline',
              'continuation_event', 'continuation_receipt')
Error = old.BackfillError


def pins(root: Path) -> dict:
    return dict(old.pins(root), **{p: old.sha256(root/p) for p in (SOURCE, DDL, DESIGN, DIAGNOSTICS)})


def rowsets(db, names=OLD_TABLES) -> dict:
    return {n: serial(db.execute('SELECT * FROM "'+n+'" ORDER BY ALL').fetchall()) for n in names}


def consumption(db) -> dict:
    result = {mid: [state for state, _, _ in old.events(db, mid)]
              for mid, in db.execute('SELECT member_id FROM backfill_member ORDER BY member_id').fetchall()}
    if 'continuation_event' in {n for n, _ in old.layout(db)}:
        for mid, in db.execute('SELECT member_id FROM continuation_attempt ORDER BY member_id').fetchall():
            if result[mid]:
                raise Error('CROSS_VERSION_DOUBLE_CONSUMPTION')
            result[mid] = [state for state, _, _ in events(db, mid)]
    return result


def evidence_hashes(store: Path) -> dict:
    return {str(p.relative_to(store)): old.sha256(p) for p in store.rglob('*')
            if p.is_file() and p.name in old.FILES}


def freeze_baseline(root: Path, db, store: Path, original_DB_hash: str, *, protected_history=None) -> dict:
    old.registry_validate(root, db, store)
    return dict(protocol=PROTOCOL, original_DB_hash=original_DB_hash,
                production_destination=str((root/old.DESTINATION).resolve()),
                legacy_pins=old.pins(root), legacy_rows=rowsets(db),
                legacy_files=evidence_hashes(store), consumption=consumption(db),
                protected_history=protected_history)


def protected_history_check(root: Path,baseline: dict) -> None:
    evidence=baseline.get('protected_history')
    if not isinstance(evidence,dict) or set(evidence)!={'path','sha256'}:
        raise Error('PROTECTED_HISTORY_REQUIRED')
    p=old.safe_path(root,root/evidence['path'],exists=True)
    if old.sha256(p)!=evidence['sha256']:raise Error('PROTECTED_MANIFEST_CHANGED')
    inventory=old.strict_json(p.read_bytes())
    original=root/'data/warehouse/astock.duckdb'
    metadata=root/'data/private/phase1c1-admission-metadata-live-v1/metadata.duckdb'
    if any(p.with_suffix('.duckdb.wal').exists() for p in (original,metadata)):
        raise Error('PROTECTED_ORIGINAL_WAL')
    with warehouse_connection(original,read_only=True),warehouse_connection(metadata,read_only=True):
        if old.sha256(original)!=inventory['original_hash'] or old.sha256(metadata)!=inventory['metadata_hash']:
            raise Error('PROTECTED_ORIGINAL_CHANGED')
        for rel,h in dict(inventory['files'],**inventory['accepted171']).items():
            # v3 changes only this DB's bytes; old content/source are separately pinned.
            if rel in {old.DESTINATION+'/capture.duckdb',old.DESTINATION+'/capture.duckdb.lock',old.DESTINATION+'/capture.duckdb.wal'}:continue
            if old.sha256(old.safe_path(root,root/rel,exists=True))!=h:
                raise Error('PROTECTED_HISTORY_CHANGED')


def upgrade_copy(root: Path, db, store: Path, baseline: dict) -> dict:
    old.owner(db, store)
    if store.resolve() == (root/old.DESTINATION).resolve():
        raise Error('PRODUCTION_UPGRADE_NOT_EXPOSED')
    tables = {n for n, _ in old.layout(db)}
    if tables == set(OLD_TABLES):
        if freeze_baseline(root, db, store, baseline['original_DB_hash'],protected_history=baseline.get('protected_history')) != baseline:
            raise Error('ISOLATED_BASELINE_CHANGED')
        expected_hash = old.checksum(baseline)
        def append():
            db.execute((root/DDL).read_text())
            db.execute('INSERT INTO continuation_baseline VALUES (?,?)',
                       [expected_hash, old.canonical_json(baseline).decode()])
        old.transaction(db, append)
    elif tables != set(OLD_TABLES+NEW_TABLES):
        raise Error('UNEXPECTED_CANDIDATE_SCHEMA')
    baseline_check(root, db, store, baseline)
    return dict(status='CANDIDATE_UPGRADE_VALID', old_tables=6, new_tables=5,
                old_history_unchanged=True, production_deployed=False)


def upgrade_production(root: Path,db,store: Path,baseline: dict,app: dict,review: dict,human: dict,*,live=False) -> dict:
    old.owner(db,store)
    if not live or store.resolve()!=(root/old.DESTINATION).resolve():
        raise Error('MATCHED_PRODUCTION_UPGRADE_REQUIRED')
    authorize(root,db,baseline,app,review,human,fixture=False,archived=False)
    protected_history_check(root,baseline)
    if set(n for n,_ in old.layout(db))==set(OLD_TABLES):
        if (old.sha256(store/'capture.duckdb')!=baseline['original_DB_hash']
                or freeze_baseline(root,db,store,baseline['original_DB_hash'],protected_history=baseline.get('protected_history'))!=baseline):
            raise Error('CURRENT_PRODUCTION_BASELINE_CHANGED')
        def append():
            db.execute((root/DDL).read_text())
            db.execute('INSERT INTO continuation_baseline VALUES (?,?)',
                       [old.checksum(baseline),old.canonical_json(baseline).decode()])
            baseline_check(root,db,store,baseline)
        old.transaction(db,append)
    baseline_check(root,db,store,baseline)
    return dict(status='APPEND_ONLY_UPGRADE_VALID',old_history_unchanged=True)


def baseline_check(root: Path, db, store: Path, baseline: dict) -> None:
    with duckdb.connect(':memory:') as expected:
        expected.execute((root/old.DDL).read_text())
        expected.execute((root/DDL).read_text())
        if old.layout(db)!=old.layout(expected):
            raise Error('CONTINUATION_SCHEMA_CHANGED')
    if (baseline['protocol'] != PROTOCOL or baseline['legacy_pins'] != old.pins(root)
            or baseline['production_destination'] != str((root/old.DESTINATION).resolve())
            or rowsets(db) != baseline['legacy_rows']
            or any(old.sha256(old.safe_path(store,store/p,exists=True)) != h
                   for p, h in baseline['legacy_files'].items())):
        raise Error('LEGACY_BASELINE_CHANGED')
    stored = db.execute('SELECT baseline_hash,payload FROM continuation_baseline').fetchall()
    if stored != [(old.checksum(baseline), old.canonical_json(baseline).decode())]:
        raise Error('BASELINE_PIN_CHANGED')


def application(root: Path, db, baseline: dict, *, fixture=False, dependencies=None) -> dict:
    history = consumption(db); dependencies = dependencies or {}
    members = []
    # Origin plan order is authoritative, not arbitrary SQL member order.
    for ph, payload in db.execute('SELECT plan_hash,payload FROM backfill_pin ORDER BY plan_hash').fetchall():
        for request in json.loads(payload)['requests']:
            mid = request['member_id']
            if history[mid]:
                continue
            obj, origin = db.execute('SELECT object_id,origin_plan FROM backfill_member WHERE member_id=?', [mid]).fetchone()
            if origin != ph or any(m['member_id']==mid for m in members):
                continue
            members.append(dict(member_id=mid, object_id=str(obj), origin_plan=origin,
                                request=request, dependencies=dependencies.get(mid, []), admission='RAW_ONLY'))
    return dict(protocol=PROTOCOL, namespace='FIXTURE' if fixture else 'PROPOSED',
                execution_license=False, baseline_hash=old.checksum(baseline),
                baseline_consumption_hash=old.checksum(baseline['consumption']),
                consumption_hash=old.checksum(history), production_destination=baseline['production_destination'],
                members=members, membership_hash=old.checksum(members), pins=pins(root),
                budget=len(members), max_attempts=1, call_start_spacing_seconds=1.25,
                research_admitted=False)


def validate_application(root: Path, db, baseline: dict, app: dict, *, archived=False) -> None:
    if baseline['production_destination']!=str((root/old.DESTINATION).resolve()):
        raise Error('CANONICAL_ROOT_CHANGED')
    expected = application(root, db, baseline, fixture=app.get('namespace')=='FIXTURE',
                           dependencies={m['member_id']: m['dependencies'] for m in app.get('members', [])})
    # Consumption evolves after this exact application is registered, but its baseline
    # and origin descriptors do not. Never recompute or reorder signed membership.
    if archived:
        expected.update(members=app['members'], membership_hash=old.checksum(app['members']),
                        budget=app['budget'], consumption_hash=app['consumption_hash'])
    if app != expected or not app['members'] or app['budget'] != len(app['members']):
        raise Error('EXACT_APPLICATION_CHANGED')
    ids = [m['member_id'] for m in app['members']]
    if len(ids) != len(set(ids)):
        raise Error('DUPLICATE_CONTINUATION_MEMBER')
    for m in app['members']:
        row = db.execute('SELECT object_id,origin_plan,payload FROM backfill_member WHERE member_id=?', [m['member_id']]).fetchone()
        if (row is None or (str(row[0]), row[1], json.loads(row[2])) !=
                (m['object_id'], m['origin_plan'], m['request']) or old.logical_id(m['request']) != m['member_id']
                or baseline['consumption'][m['member_id']] or m['admission'] != 'RAW_ONLY'
                or not isinstance(m['dependencies'], list) or len(m['dependencies']) != len(set(m['dependencies']))
                or any(dep not in baseline['consumption'] or dep == m['member_id'] for dep in m['dependencies'])):
            raise Error('ORIGIN_OR_CONSUMED_MEMBER_CHANGED')


def authorize(root: Path, db, baseline: dict, app: dict, review: dict, human: dict,
              *, fixture: bool, archived=False) -> None:
    validate_application(root, db, baseline, app, archived=archived)
    base = dict(protocol=PROTOCOL, application_hash=old.checksum(app),
                namespace='FIXTURE' if fixture else 'PRODUCTION', pins=app['pins'],
                baseline_hash=app['baseline_hash'], membership_hash=app['membership_hash'],
                production_destination=app['production_destination'], budget=app['budget'])
    if (not isinstance(review, dict) or set(review) != set(base)|{
            'implementation_sha', 'review_ref', 'reviewed_at', 'execution_license', 'human_evidence'}
            or any(review.get(k)!=v for k,v in base.items()) or review['execution_license'] is not True
            or app['namespace'] != ('FIXTURE' if fixture else 'PROPOSED')):
        raise Error('MATCHED_CONTINUATION_REVIEW_REQUIRED')
    if (not isinstance(human, dict) or set(human) != {'protocol', 'review_hash', 'instruction_ref',
            'authorization_ref', 'authorized_at', 'execution_license'} or human['protocol'] != PROTOCOL
            or human['review_hash'] != old.checksum(review) or human['execution_license'] is not True
            or human['instruction_ref'] != review['human_evidence']):
        raise Error('MATCHED_ACTUAL_HUMAN_REQUIRED')
    if not old.instant(review['reviewed_at']) <= old.instant(human['authorized_at']) <= datetime.now(timezone.utc):
        raise Error('CONTINUATION_TIME_INVALID')
    if fixture:
        if not all(isinstance(v,str) and v.startswith('FIXTURE:') for v in
                   (review['review_ref'], human['authorization_ref'], review['human_evidence'])):
            raise Error('FIXTURE_LICENSE_REQUIRED')
    else:
        if any(json.loads(db.execute('SELECT payload FROM backfill_pin WHERE plan_hash=?',
                    [m['origin_plan']]).fetchone()[0])['namespace']!='PRODUCTION' for m in app['members']):
            raise Error('PRODUCTION_LEGACY_ORIGIN_REQUIRED')
        evidence = review['human_evidence']
        if not isinstance(evidence, dict) or set(evidence)!={'path','sha256'}:
            raise Error('ACTUAL_HUMAN_BYTES_REQUIRED')
        path=old.safe_path(root,root/evidence['path'],exists=True)
        instruction=old.strict_json(path.read_bytes())
        if (old.sha256(path)!=evidence['sha256'] or instruction.get('source')!='DIRECT_USER'
                or instruction.get('kind')!='ACTUAL_USER_INSTRUCTION'
                or instruction.get('scope')!='EXACT_CONTINUATION_EXECUTION'
                or instruction.get('application_hash')!=old.checksum(app)
                or not instruction.get('instruction')
                or any(not isinstance(v,str) or not v or any(x in v for x in ('FIXTURE','PROPOSED'))
                       for v in (review['review_ref'],human['authorization_ref']))):
            raise Error('ACTUAL_EXECUTION_INSTRUCTION_REQUIRED')
        if not archived and (review['implementation_sha']!=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
                or subprocess.check_output(['git','status','--porcelain'],cwd=root)):
            raise Error('CLEAN_REVIEWED_IMPLEMENTATION_REQUIRED')


def events(db, mid: str) -> list:
    return db.execute('SELECT state,recorded_at,payload FROM continuation_event WHERE member_id=? ORDER BY ordinal', [mid]).fetchall()


def event(db, mid: str, state: str, clock, payload: dict) -> str:
    history=events(db,mid); previous=history[-1][0] if history else None
    if state not in {None:{'CLAIMED'},'CLAIMED':{'CALL_ENTERED','UNCERTAIN'},
                     'CALL_ENTERED':{'COMPLETE','RAW_RETAINED','FAILED','UNCERTAIN'}}.get(previous,set()):
        raise Error('CONTINUATION_TERMINAL_NO_RESEND')
    at=old.stamp(clock)
    if history and old.instant(at)<old.instant(history[-1][1]):
        raise Error('CONTINUATION_CLOCK_ROLLBACK')
    db.execute('INSERT INTO continuation_event VALUES (?,?,?,?,?)',
               [mid,len(history),state,at,old.canonical_json(payload).decode()])
    return at


def audit(root: Path, db, store: Path, baseline: dict) -> None:
    baseline_check(root,db,store,baseline)
    allowed={'capture.duckdb','capture.duckdb.lock','capture.duckdb.wal'}|{v[0] for v in db.execute('SELECT member_id FROM backfill_member').fetchall()}
    if any(p.name not in allowed for p in store.iterdir()):raise Error('ORPHAN_CONTINUATION_STORE_FILE')
    for mid, in db.execute('SELECT member_id FROM backfill_member').fetchall():
        directory=old.safe_path(store,store/mid)
        if directory.exists() and not old.events(db,mid) and not events(db,mid):
            raise Error('ORPHAN_UNCLAIMED_CONTINUATION_MEMBER')
    licenses={}
    for aid,av,rv,hv,registered_at in db.execute('SELECT * FROM continuation_authorization').fetchall():
        app,review,human=(json.loads(v) for v in (av,rv,hv))
        if aid!=old.checksum(dict(application=app,review=review,human=human)):
            raise Error('APPENDED_AUTHORIZATION_CHANGED')
        authorize(root,db,baseline,app,review,human,fixture=app['namespace']=='FIXTURE',archived=True)
        if old.instant(registered_at)<old.instant(human['authorized_at']):raise Error('AUTHORIZATION_REGISTRATION_TIME_CHANGED')
        licenses[aid]=(app,review,human)
    consumption(db)
    for mid,obj,origin,aid,claimed in db.execute('SELECT * FROM continuation_attempt').fetchall():
        if aid not in licenses:
            raise Error('ATTEMPT_LICENSE_MISSING')
        app,_,_=licenses[aid]; selected=[m for m in app['members'] if m['member_id']==mid]
        if len(selected)!=1 or (str(obj),origin)!=(selected[0]['object_id'],selected[0]['origin_plan']):
            raise Error('ATTEMPT_ORIGIN_CHANGED')
        h=events(db,mid);states=[e[0] for e in h]
        if states not in (['CLAIMED'],['CLAIMED','CALL_ENTERED'],['CLAIMED','UNCERTAIN'],
                          ['CLAIMED','CALL_ENTERED','COMPLETE'],['CLAIMED','CALL_ENTERED','RAW_RETAINED'],
                          ['CLAIMED','CALL_ENTERED','FAILED'],['CLAIMED','CALL_ENTERED','UNCERTAIN']):
            raise Error('CONTINUATION_EVENT_HISTORY_CHANGED')
        if h[0][1]!=claimed or [old.instant(e[1]) for e in h]!=sorted(old.instant(e[1]) for e in h):
            raise Error('CONTINUATION_TIME_ORDER_CHANGED')
        ordinals=[v[0] for v in db.execute('SELECT ordinal FROM continuation_event WHERE member_id=? ORDER BY ordinal',[mid]).fetchall()]
        if ordinals!=list(range(len(h))) or any(json.loads(e[2]).get('authorization_id')!=aid for e in h):
            raise Error('EVENT_ATTEMPT_BINDING_CHANGED')
        if len(h)>1 and h[1][0]=='CALL_ENTERED':
            call=json.loads(h[1][2])
            if (set(call)!={'authorization_id','wall','monotonic','boot'} or call['wall']!=h[1][1]
                    or type(call['monotonic']) not in (int,float) or not math.isfinite(call['monotonic'])
                    or call['monotonic']<0 or not isinstance(call['boot'],str)):
                raise Error('DURABLE_NEW_CALL_CHANGED')
        if db.execute('SELECT count(*) FROM continuation_attempt WHERE authorization_id=?',[aid]).fetchone()[0]>app['budget']:
            raise Error('CONTINUATION_BUDGET_CHANGED')
        if states[-1] in ('COMPLETE','RAW_RETAINED'):
            physical_validate(root,db,store,mid)
        elif db.execute('SELECT 1 FROM continuation_receipt WHERE member_id=?',[mid]).fetchone():
            raise Error('NONCOMPLETE_RECEIPT')
    if db.execute('SELECT member_id FROM continuation_event EXCEPT SELECT member_id FROM continuation_attempt').fetchall():
        raise Error('ORPHAN_CONTINUATION_EVENT')


def artifacts(root: Path, db, mid: str, body: bytes, source: dict) -> tuple:
    request=source['member'];table=old.decoded_table(root,request,body,source['retrieved_at'])
    catalog=json.loads((root/old.CATALOG).read_bytes())[request['dataset']]
    completeness='CONTRACT_AND_WINDOW' if catalog['max_rows'] is not None or request['dataset']=='trade_cal' else 'RAW_UNCERTIFIED'
    buf=io.BytesIO();pq.write_table(table,buf);typed=buf.getvalue()
    manifest=dict(protocol=PROTOCOL,member_id=mid,object_id=source['object_id'],body_hash=hashlib.sha256(body).hexdigest(),
                  source_hash=old.checksum(source),typed_hash=hashlib.sha256(typed).hexdigest(),
                  rows=table.num_rows,schema_hash=hashlib.sha256(table.schema.serialize().to_pybytes()).hexdigest(),
                  completeness=completeness,leading_previous_certified=False,research_admitted=False,
                  authorization_id=source['authorization_id'],origin_plan=source['origin_plan'])
    sidecar=dict(protocol=PROTOCOL,member_id=mid,manifest_hash=old.checksum(manifest),
                 authorization_id=source['authorization_id'],origin_plan=source['origin_plan'])
    return table,typed,manifest,sidecar


def cross_window(db,store: Path,member: dict,table) -> None:
    old.calendar_cross_window(db,store,member,table)
    if member['dataset']!='trade_cal':return
    p=member['params'];current=sorted(table.to_pylist(),key=lambda r:r['cal_date'])
    from datetime import timedelta
    def adjacent(end,start):return datetime.strptime(end,'%Y%m%d')+timedelta(days=1)==datetime.strptime(start,'%Y%m%d')
    for mid, in db.execute("SELECT member_id FROM continuation_receipt WHERE completeness='CONTRACT_AND_WINDOW'").fetchall():
        if mid==member['member_id']:continue
        other=json.loads(db.execute('SELECT payload FROM backfill_member WHERE member_id=?',[mid]).fetchone()[0])
        q=other['params']
        if other['dataset']!='trade_cal' or q['exchange']!=p['exchange']:continue
        rows=sorted(pq.read_table(store/mid/'typed.parquet').to_pylist(),key=lambda r:r['cal_date'])
        for past,future in [(rows,current)] if adjacent(q['end_date'],p['start_date']) else [(current,rows)] if adjacent(p['end_date'],q['start_date']) else []:
            last=past[-1];previous=last['cal_date'] if last['is_open']==1 else last['pretrade_date']
            if future[0]['pretrade_date']!=previous:raise Error('NEW_CROSS_WINDOW_PREVIOUS_CONFLICT')


def physical_validate(root: Path, db, store: Path, mid: str) -> dict:
    directory=old.safe_path(store,store/mid)
    if not directory.is_dir() or {p.name for p in directory.iterdir()}!=old.FILES:
        raise Error('CONTINUATION_FILE_MEMBERSHIP_CHANGED')
    paths={n:old.safe_path(store,directory/n,exists=True) for n in old.FILES}
    body=paths['response.body'].read_bytes();source=old.strict_json(paths['http-source.json'].read_bytes())
    row=db.execute('SELECT object_id,origin_plan,authorization_id,claimed_at FROM continuation_attempt WHERE member_id=?',[mid]).fetchone()
    h=events(db,mid)
    if row is None or len(h)!=3 or h[1][0]!='CALL_ENTERED':
        raise Error('EXACT_NEW_CALL_REQUIRED')
    obj,origin,aid,claimed=row
    app,review,human=(json.loads(v) for v in db.execute('SELECT application,review,human FROM continuation_authorization WHERE authorization_id=?',[aid]).fetchone())
    member=next(m['request'] for m in app['members'] if m['member_id']==mid)
    expected={'protocol','member','object_id','origin_plan','authorization_id','review_hash','human_hash',
              'claimed_at','call_entered_at','retrieved_at','available_at','http_status','content_length',
              'content_encoding','body_hash','body_bytes','complete_body','fixture_only','diagnostic'}
    if (set(source)!=expected or source['protocol']!=PROTOCOL or source['member']!=member
            or source['object_id']!=str(obj) or source['origin_plan']!=origin or source['authorization_id']!=aid
            or source['review_hash']!=old.checksum(review) or source['human_hash']!=old.checksum(human)
            or source['claimed_at']!=claimed or source['call_entered_at']!=h[1][1]
            or source['body_hash']!=old.sha256(paths['response.body']) or source['body_bytes']!=len(body)
            or source['fixture_only'] is not (app['namespace']=='FIXTURE') or source['complete_body'] is not True
            or source['http_status']!=200 or source['content_encoding'] not in ('','identity')
            or source['content_length'] is not None and source['content_length']!=len(body)):
        raise Error('CONTINUATION_SOURCE_BINDING_CHANGED')
    times=[old.instant(source[k]) for k in ('claimed_at','call_entered_at','retrieved_at','available_at')]
    if times!=sorted(times):raise Error('CONTINUATION_SOURCE_TIME_CHANGED')
    diagnostic=source['diagnostic']
    if diagnostic!=diagnostics.observation(phase='COMPLETE',started_at=diagnostic['started_at'],
            ended_at=diagnostic['ended_at'],headers_received=True,body_bytes=len(body),eof=True):
        raise Error('UNSAFE_SOURCE_DIAGNOSTIC')
    table,typed,manifest,sidecar=artifacts(root,db,mid,body,source)
    cross_window(db,store,member,table)
    for n,b in [('typed.parquet',typed),('manifest.json',old.canonical_json(manifest)),('sidecar.json',old.canonical_json(sidecar))]:
        if paths[n].read_bytes()!=b:raise Error('CONTINUATION_PHYSICAL_BYTES_CHANGED')
    receipt=db.execute('SELECT manifest_hash,source_hash,completed_at,completeness FROM continuation_receipt WHERE member_id=?',[mid]).fetchone()
    expected_state='COMPLETE' if manifest['completeness']=='CONTRACT_AND_WINDOW' else 'RAW_RETAINED'
    if (receipt is None or receipt[:2]!=(old.checksum(manifest),old.checksum(source))
            or receipt[3]!=manifest['completeness'] or h[-1][0]!=expected_state
            or not times[-1]<=old.instant(receipt[2])<=old.instant(h[-1][1])
            or json.loads(h[-1][2])!=dict(authorization_id=aid,manifest_hash=old.checksum(manifest),source_hash=old.checksum(source))):
        raise Error('CONTINUATION_RECEIPT_CHANGED')
    return dict(status='ALREADY_VALID',completeness=manifest['completeness'],research_admitted=False)


def capture_mock(root: Path, db, store: Path, baseline: dict, app: dict, review: dict,
                 human: dict, mid: str, token: SecretStr, *, transport, clock=None, fault=lambda stage:None) -> dict:
    return _capture(root,db,store,baseline,app,review,human,mid,token,fixture=True,
                    live=True,transport=transport,clock=clock,fault=fault)


def capture_production(root: Path,db,store: Path,baseline: dict,app: dict,review: dict,
                       human: dict,mid: str,token: SecretStr,*,live=False,clock=None) -> dict:
    return _capture(root,db,store,baseline,app,review,human,mid,token,fixture=False,
                    live=live,transport=None,clock=clock)


def _capture(root: Path, db, store: Path, baseline: dict, app: dict, review: dict,
             human: dict,mid: str,token: SecretStr,*,fixture: bool,live: bool,
             transport,clock=None,fault=lambda stage:None) -> dict:
    old.owner(db,store)
    if (not live or not isinstance(token,SecretStr) or not token.get_secret_value()
            or fixture and (store.resolve()==(root/old.DESTINATION).resolve()
                or type(transport) is not httpx.MockTransport or not token.get_secret_value().startswith('closed-'))
            or not fixture and (store.resolve()!=(root/old.DESTINATION).resolve() or transport is not None)):
        raise Error('ISOLATED_CLOSED_MOCK_REQUIRED')
    clock=clock or old.Clock();audit(root,db,store,baseline)
    aid=old.checksum(dict(application=app,review=review,human=human))
    registered=db.execute('SELECT 1 FROM continuation_authorization WHERE authorization_id=?',[aid]).fetchone()
    authorize(root,db,baseline,app,review,human,fixture=fixture,archived=bool(registered))
    selected=[m for m in app['members'] if m['member_id']==mid]
    if len(selected)!=1:raise Error('MEMBER_NOT_APPROVED')
    m=selected[0];h=events(db,mid)
    if h:
        if h[-1][0] in ('COMPLETE','RAW_RETAINED'):return physical_validate(root,db,store,mid)
        raise Error('CONSUMED_NEW_MEMBER_NO_RESEND')
    if not fixture:
        if (review['implementation_sha']!=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
                or subprocess.check_output(['git','status','--porcelain'],cwd=root)):
            raise Error('CLEAN_REVIEWED_IMPLEMENTATION_REQUIRED')
        protected_history_check(root,baseline)
    if any(states and states[-1] not in ('COMPLETE','RAW_RETAINED') for _,states in
           [(v[0],[e[0] for e in events(db,v[0])]) for v in db.execute('SELECT member_id FROM continuation_attempt').fetchall()]):
        raise Error('NEW_UNCERTAIN_STOPS_BATCH')
    current=consumption(db)
    if current[mid]:raise Error('CONSUMED_LOGICAL_MEMBER_NO_RESEND')
    next_member=next((m['member_id'] for m in app['members'] if not current[m['member_id']]),None)
    if mid!=next_member:raise Error('APPROVED_EXECUTION_ORDER_REQUIRED')
    for dep in m['dependencies']:
        if not current[dep] or current[dep][-1]!='COMPLETE':raise Error('DEPENDENCY_NOT_COMPLETE')
    directory=old.safe_path(store,store/mid)
    if directory.exists():raise Error('ORPHAN_BEFORE_NEW_CLAIM')
    # Both versions' durable start times count for spacing.
    old.pace(db,clock)
    starts=[(old.instant(at),json.loads(payload)) for at,payload in db.execute("SELECT recorded_at,payload FROM continuation_event WHERE state='CALL_ENTERED'").fetchall()]
    if starts:
        last,call=max(starts,key=lambda x:x[0]);delta=(clock.utc()-last).total_seconds()
        if delta<0:raise Error('CONTINUATION_CLOCK_ROLLBACK')
        mono=clock.monotonic()-call['monotonic'] if clock.boot()==call['boot'] else 0
        if mono<0:raise Error('CONTINUATION_MONOTONIC_ROLLBACK')
        clock.sleep(max(0,1.25-delta,1.25-mono))
        if (clock.utc()-last).total_seconds()<1.25 or clock.boot()==call['boot'] and clock.monotonic()-call['monotonic']<1.25:
            raise Error('CONTINUATION_PACING_FAILED')
    def claim():
        at=old.stamp(clock)
        if old.instant(at)<old.instant(human['authorized_at']):
            raise Error('CLAIM_BEFORE_ACTUAL_AUTHORIZATION')
        if not registered:
            db.execute('INSERT INTO continuation_authorization VALUES (?,?,?,?,?)',[aid,
                       old.canonical_json(app).decode(),old.canonical_json(review).decode(),
                       old.canonical_json(human).decode(),at])
        if db.execute('SELECT count(*) FROM continuation_attempt WHERE authorization_id=?',[aid]).fetchone()[0]>=app['budget']:
            raise Error('CONTINUATION_BUDGET_EXHAUSTED')
        db.execute('INSERT INTO continuation_attempt VALUES (?,?,?,?,?)',[mid,m['object_id'],m['origin_plan'],aid,at])
        # same timestamp: attempt binding and budget consumed in one transaction
        db.execute('INSERT INTO continuation_event VALUES (?,?,?,?,?)',[mid,0,'CLAIMED',at,old.canonical_json(dict(authorization_id=aid)).decode()])
        return at
    claimed=old.transaction(db,claim);fault('after_claim')
    def enter():
        at=old.stamp(clock)
        if old.instant(at)<old.instant(claimed):
            raise Error('CALL_BEFORE_DURABLE_CLAIM')
        db.execute('INSERT INTO continuation_event VALUES (?,?,?,?,?)',[mid,1,'CALL_ENTERED',at,
                   old.canonical_json(dict(authorization_id=aid,wall=at,monotonic=clock.monotonic(),boot=clock.boot())).decode()])
        return at
    entered=old.transaction(db,enter)
    fault('after_call_entered')
    started=diagnostics.utc();phase='AWAIT_HEADERS';received=False;body=b'';eof=False
    try:
        with httpx.Client(transport=transport if fixture else httpx.HTTPTransport(retries=0,verify=True,trust_env=False),
                          verify=True,trust_env=False,follow_redirects=False,timeout=20) as client:
            with client.stream('POST',old.ENDPOINT,headers={'Accept-Encoding':'identity'},json=dict(
                    api_name=m['request']['dataset'],params=m['request']['params'],
                    fields=','.join(m['request']['fields']),token=token.get_secret_value())) as response:
                received=True;phase='READ_BODY'
                if response.is_stream_consumed:body=response.content
                else:
                    for chunk in response.iter_raw():body+=chunk
                eof=True
    except Exception as error:
        safe=diagnostics.observation(phase=phase,started_at=started,ended_at=diagnostics.utc(),
                                    headers_received=received,body_bytes=len(body),eof=eof,error=error)
        old.transaction(db,lambda:event(db,mid,'UNCERTAIN',clock,dict(authorization_id=aid,diagnostic=safe)))
        raise Error('NEW_TRANSPORT_UNKNOWN_NO_RESEND') from None
    safe=diagnostics.observation(phase='COMPLETE',started_at=started,ended_at=diagnostics.utc(),
                                headers_received=True,body_bytes=len(body),eof=True)
    if old.secret_present(body,token.get_secret_value()):
        old.transaction(db,lambda:event(db,mid,'FAILED',clock,dict(authorization_id=aid,reason='UNSAFE_BODY_SUPPRESSED',diagnostic=safe)))
        raise Error('UNSAFE_BODY_SUPPRESSED')
    length=response.headers.get('content-length')
    source=dict(protocol=PROTOCOL,member=m['request'],object_id=m['object_id'],origin_plan=m['origin_plan'],
                authorization_id=aid,review_hash=old.checksum(review),human_hash=old.checksum(human),
                claimed_at=claimed,call_entered_at=entered,retrieved_at=old.stamp(clock),available_at=old.stamp(clock),
                http_status=response.status_code,content_length=int(length) if length and length.isdecimal() else -1 if length else None,
                content_encoding=response.headers.get('content-encoding','') if response.headers.get('content-encoding','') in ('','identity') else 'UNSUPPORTED',body_hash=hashlib.sha256(body).hexdigest(),
                body_bytes=len(body),complete_body=True,fixture_only=fixture,diagnostic=safe)
    directory.mkdir();old.publish(directory/'response.body',body);fault('after_body')
    old.publish(directory/'http-source.json',old.canonical_json(source));fault('after_source')
    try:
        if (source['http_status']!=200 or source['content_encoding'] not in ('','identity')
                or source['content_length'] is not None and source['content_length']!=len(body)):
            raise Error('HTTP_OR_TRUNCATION')
        table,typed,manifest,sidecar=artifacts(root,db,mid,body,source)
        cross_window(db,store,m['request'],table)
    except (ValueError,TypeError,KeyError,UnicodeError):
        old.transaction(db,lambda:event(db,mid,'FAILED',clock,dict(authorization_id=aid,reason='HTTP_OR_CONTRACT_STOPPED')))
        raise Error('HTTP_OR_CONTRACT_STOPPED') from None
    for n,b in [('typed.parquet',typed),('manifest.json',old.canonical_json(manifest)),('sidecar.json',old.canonical_json(sidecar))]:
        old.publish(directory/n,b);fault('after_'+n.split('.')[0])
    status='COMPLETE' if manifest['completeness']=='CONTRACT_AND_WINDOW' else 'RAW_RETAINED'
    def complete():
        db.execute('INSERT INTO continuation_receipt VALUES (?,?,?,?,?)',[mid,old.checksum(manifest),old.checksum(source),old.stamp(clock),manifest['completeness']])
        fault('after_registration')
        event(db,mid,status,clock,dict(authorization_id=aid,manifest_hash=old.checksum(manifest),source_hash=old.checksum(source)))
        fault('after_promotion')
        physical_validate(root,db,store,mid)
    old.transaction(db,complete)
    return dict(status=status,research_admitted=False,completeness=manifest['completeness'])
