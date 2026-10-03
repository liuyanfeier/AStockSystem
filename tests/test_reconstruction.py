"""Offline synthetic publication/fault/identity approvals; no original DB access."""
import hashlib
import json
import shutil
from datetime import date,datetime,timezone,timedelta
from uuid import uuid4

import duckdb
import pytest

from astock.paths import get_project_root
from astock.data.raw_writer import migrate,RawWriter
from astock.data.audit import RequestParams
from astock.data.tushare_client import ProviderTable
from astock.data.receipt_migration import apply_receipt_integrity_upgrade
from astock.data.provider_identity import ListingEpisode,ExchangeCode,ProviderBinding,SourceObservation
from astock.data.reconstruction import (Approval,Context,Input,checksum,apply_reconstruction_schema,
    load_resolver,import_approved_cases,specs_hash,register_context,start_generation,publish_output,
    complete_generation,select_complete,compare_generations,generation_state,conserve,converted)
from astock.data.reconstruction_dq import load_policy,evidence_hash,audit_complete_generation,disposition_ledger

from test_slice_capture import slice_root

ROOT=get_project_root();NOW=datetime(2026,10,2,tzinfo=timezone.utc);DAY=date(2025,5,6)


@pytest.fixture
def environment(tmp_path):
    for directory in ('sql','config','docs'):
        shutil.copytree(ROOT/directory,tmp_path/directory)
    db=duckdb.connect(':memory:');migrate(db,tmp_path)
    apply_receipt_integrity_upgrade(tmp_path,db,verification_sha='a'*40)
    policy=load_policy(tmp_path)[1]
    approval=Approval(resolver_protocol="R2_RESOLVER_UTC_INSTANT_V2", time_integrity_addendum_hash=hashlib.sha256((ROOT / "docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md").read_bytes()).hexdigest(), review_ref='synthetic-independent-review',reviewed_sha='a'*40,
        design_hash=hashlib.sha256((tmp_path/'docs/remediation/phase1c1/r2-a-design-v1.md').read_bytes()).hexdigest(),
        policy_hash=policy,approved_case_set_hash=checksum(dict(episodes=[],codes=[],bindings=[])),approved_at=NOW,
        dq_evidence_hash=evidence_hash(dict(sessions=[],reference_exceptions=[],bse_transitions=[],source_dispositions=[])),
        publication_addendum_hash=hashlib.sha256((tmp_path/'docs/remediation/phase1c1/r2-a-design-v1-addendum-1.md').read_bytes()).hexdigest(),
        correction_addendum_hash=hashlib.sha256((tmp_path/'docs/remediation/phase1c1/r2-a-design-v1-addendum-3.md').read_bytes()).hexdigest(),
        disposition_addendum_hash=hashlib.sha256((tmp_path/'docs/remediation/phase1c1/r2-a-design-v1-addendum-2.md').read_bytes()).hexdigest())
    apply_reconstruction_schema(tmp_path,db,approval)
    specs=__import__('astock.data.curation',fromlist=['load_curation_specs']).load_curation_specs(tmp_path,spec_version='v2')
    inputs=[];raws=[]
    for dataset in ('daily','daily_basic'):
        run=uuid4()
        db.execute('''INSERT INTO ingestion_run(run_id,source,dataset,mode,started_at,status,code_commit,config_hash,provider_client_version)
            VALUES (?,'tushare',?,'AUDIT',?,'RUNNING',?,?,'1.0.0')''',[run,dataset,NOW-timedelta(days=1),'a'*40,'b'*64])
        spec=next(s for s in specs if s.dataset==dataset)
        fields=[f.source_column for f in spec.fields]
        base={f.source_column:dict(string='synthetic',date32='20250506',float64=10.0,int64=1)[f.logical_type] for f in spec.fields}
        base.update(ts_code='000001.SZ',change=0.0,pct_chg=0.0)
        unknown=dict(base,ts_code='T600018.SH')
        raw=RawWriter(tmp_path,db).write(run,dataset,0,
            ProviderTable(fields=fields,items=[[r[f] for f in fields] for r in (base,unknown)],retrieved_at=NOW-timedelta(hours=1)),
            RequestParams(trade_date=DAY))
        RawWriter(tmp_path,db).sidecar(run,dataset)
        inputs.append(Input(request_id=checksum(dataset),raw_object_id=raw.object_id,dataset=dataset,
            raw_hash=raw.sha256,raw_schema_hash=raw.schema_hash,row_count=2,is_output=True));raws.append(raw)
    episode=ListingEpisode(episode_id=uuid4(),security_id='synthetic-one',venue='SZSE',asset_type='STK',
        valid_from=date(2000,1,1),retrieved_at=NOW,available_at=NOW,evidence_ids=('synthetic-evidence',),approval_ref=approval.review_ref)
    code=ExchangeCode(code_id=uuid4(),episode_id=episode.episode_id,identifier='000001.SZ',valid_from=episode.valid_from,
        available_at=NOW,evidence_ids=('synthetic-official',),approval_ref=approval.review_ref)
    bindings=[ProviderBinding(binding_id=uuid4(),binding_version=1,dataset=i.dataset,native_identifier='000001.SZ',
        episode_id=episode.episode_id,representation_kind='EVENT_NATIVE',
        observations=(SourceObservation(raw_object_id=i.raw_object_id,raw_row_number=0,event_date=DAY),),
        first_observed_at=NOW-timedelta(hours=1),decision_at=NOW,available_at=NOW,evidence_ids=('synthetic-observation',),
        decision_status='APPROVED',approval_ref=approval.review_ref) for i in inputs]
    cases=dict(episodes=[episode.model_dump()],codes=[code.model_dump()],bindings=[b.model_dump() for b in bindings])
    approval=approval.model_copy(update=dict(approved_case_set_hash=checksum(cases)))
    import_approved_cases(tmp_path,db,cases,approval)
    evidence=dict(sessions=[],reference_exceptions=[],bse_transitions=[],source_dispositions=[])
    context=Context(resolver_protocol=approval.resolver_protocol, time_integrity_addendum_hash=approval.time_integrity_addendum_hash, parent_batch_id=uuid4(),parent_generation=0,parent_identity_hash='b'*64,parent_plan_hash='c'*64,
        resolver_hash=load_resolver(db).snapshot_hash,specs_hash=specs_hash(tmp_path),policy_hash=policy,
        design_hash=approval.design_hash,dq_evidence_hash=approval.dq_evidence_hash,publication_addendum_hash=approval.publication_addendum_hash,disposition_addendum_hash=approval.disposition_addendum_hash,correction_addendum_hash=approval.correction_addendum_hash,
        knowledge_as_of=NOW,implementation_sha='a'*40,approval=approval,inputs=tuple(inputs),fixture_only=True)
    context_id=register_context(tmp_path,db,context,allow_fixture=True)
    yield dict(root=tmp_path,db=db,approval=approval,cases=cases,context=context,context_id=context_id,
               inputs=inputs,episode=episode,evidence=evidence)
    db.close()


def generation(env):return start_generation(env['db'],env['context_id'],allow_fixture=True)


def publish(env,gen,i=0,**kwargs):
    return publish_output(env['root'],env['db'],env['context_id'],gen,env['inputs'][i].request_id,allow_fixture=True,**kwargs)


def finish(env,gen,**kwargs):
    return complete_generation(env['root'],env['db'],env['context_id'],gen,allow_fixture=True,**kwargs)


def complete(env):
    gen=generation(env)
    for i in range(len(env['inputs'])):publish(env,gen,i)
    finish(env,gen);return gen


def snapshot(db):
    tables=[r[0] for r in db.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name").fetchall()]
    return {t:db.execute(f'SELECT * FROM {t} ORDER BY ALL').fetchall() for t in tables}


def test_additive_schema_repeat_and_legacy_immutable(environment):
    e=environment;before=snapshot(e['db'])
    assert apply_reconstruction_schema(e['root'],e['db'],e['approval'])=='ALREADY_VALID'
    assert snapshot(e['db'])==before
    assert e['db'].execute('SELECT version FROM schema_version ORDER BY version').fetchall()==[(v,) for v in range(1,11)]
    migrate(e['db'],e['root'])
    assert snapshot(e['db'])==before


def test_explicit_fixture_cannot_be_admitted_as_production(environment):
    e=environment
    with pytest.raises(ValueError,match='Fixture'):register_context(e['root'],e['db'],e['context'])
    with pytest.raises(ValueError,match='Fixture'):start_generation(e['db'],e['context_id'])
    gen=complete(e)
    with pytest.raises(ValueError,match='Fixture'):select_complete(e['root'],e['db'],e['context_id'],gen)
    with pytest.raises(ValueError,match='133'):Context.model_validate(e['context'].model_dump()|dict(fixture_only=False))


@pytest.mark.parametrize('point',['FILE','LINEAGE','DB','REGISTERED'])
def test_partial_crashes_reconcile_independently_then_complete(environment,point):
    e=environment;gen=generation(e);before=snapshot(e['db'])
    def fault(where):
        if where==point:raise RuntimeError('synthetic boundary')
    with pytest.raises(RuntimeError):publish(e,gen,fault=fault)
    if point!='REGISTERED':assert snapshot(e['db'])==before
    else:assert e['db'].execute('SELECT count(*) FROM derivation_output').fetchone()==(1,)
    assert publish(e,gen) in ('PUBLISHED','ALREADY_VALID')
    publish(e,gen,1);assert finish(e,gen)=='COMPLETE'
    assert e['db'].execute('SELECT count(*) FROM derivation_row_quarantine').fetchone()==(2,)
    assert len(select_complete(e['root'],e['db'],e['context_id'],gen,allow_fixture=True)[1])==2


@pytest.mark.parametrize('kind',['file','lineage'])
def test_corrupt_orphan_never_overwritten_or_deleted(environment,kind):
    e=environment;gen=generation(e)
    def fault(where):
        if where=='LINEAGE':raise RuntimeError('orphan')
    with pytest.raises(RuntimeError):publish(e,gen,fault=fault)
    path=next((e['root']/'data/curated/reconstruction').rglob('*.parquet' if kind=='file' else '*.lineage.json'))
    path.write_bytes(b'corrupt synthetic orphan')
    with pytest.raises(ValueError,match='Corrupt orphan'):publish(e,gen)
    assert path.read_bytes()==b'corrupt synthetic orphan'
    assert e['db'].execute('SELECT count(*) FROM derivation_output').fetchone()==(0,)
    assert generation_state(e['db'],e['context_id'],gen)=='BLOCKED'
    with pytest.raises(ValueError,match='blocked'):publish(e,gen)


def test_promotion_fault_is_atomic_and_repeat_does_not_retime(environment):
    e=environment;gen=generation(e)
    for i in range(2):publish(e,gen,i)
    before=snapshot(e['db'])
    def fail(_):raise RuntimeError('synthetic promotion')
    with pytest.raises(RuntimeError):finish(e,gen,fault=fail)
    assert snapshot(e['db'])==before and generation_state(e['db'],e['context_id'],gen)=='BUILDING'
    finish(e,gen);before=snapshot(e['db'])
    assert finish(e,gen)=='ALREADY_VALID'
    assert publish(e,gen)=='ALREADY_VALID'
    assert snapshot(e['db'])==before


def test_partial_generation_unknown_context_and_explicit_selection(environment):
    e=environment;gen=generation(e);publish(e,gen)
    with pytest.raises(ValueError,match='Partial'):finish(e,gen)
    with pytest.raises(ValueError,match='COMPLETE'):select_complete(e['root'],e['db'],e['context_id'],gen,allow_fixture=True)
    with pytest.raises(ValueError,match='Unknown'):select_complete(e['root'],e['db'],uuid4(),gen,allow_fixture=True)
    good=complete(e);bad=generation(e)
    assert len(select_complete(e['root'],e['db'],e['context_id'],good,allow_fixture=True)[1])==2
    with pytest.raises(ValueError,match='COMPLETE'):select_complete(e['root'],e['db'],e['context_id'],bad,allow_fixture=True)


def test_same_context_rebuild_schema_units_sources_and_quarantine(environment):
    e=environment;left=complete(e);right=complete(e)
    assert compare_generations(e['root'],e['db'],e['context_id'],left,right,allow_fixture=True)['outputs']==2
    table,q=converted(e['root'],e['db'],e['context'],e['inputs'][0])
    assert table['ts_code'].to_pylist()==['000001.SZ'] and q[0]['provider_identifier']=='T600018.SH'
    assert table['raw_row_number'].to_pylist()==[0] and q[0]['raw_row_number']==1
    assert table.schema.metadata[b'identity_basis']==b'CURRENT_RECONSTRUCTION'
    assert table['retrieved_at'].to_pylist()==table['available_at'].to_pylist()
    assert table['binding_available_at'].to_pylist()[0]>table['available_at'].to_pylist()[0]
    with pytest.raises(ValueError,match='conservation'):conserve(table,q+q,e['inputs'][0])
    with pytest.raises(ValueError,match='conservation'):conserve(table,[],e['inputs'][0])


def test_exact_quarantine_raw_fk_and_row_mutation_detected(environment):
    e=environment;gen=complete(e);db=e['db']
    with pytest.raises(duckdb.Error):db.execute('UPDATE derivation_row_quarantine SET raw_object_id=?',[uuid4()])
    db.execute('UPDATE derivation_row_quarantine SET raw_row_number=99 WHERE request_id=?',[e['inputs'][0].request_id])
    with pytest.raises(ValueError,match='Quarantine'):select_complete(e['root'],db,e['context_id'],gen,allow_fixture=True)


@pytest.mark.parametrize('field',['policy_hash','resolver_hash','design_hash','specs_hash','dq_evidence_hash','implementation_sha'])
def test_changed_context_pins_rejected(environment,field):
    e=environment;changed=e['context'].model_dump()|{field:('f'*40 if field=='implementation_sha' else 'f'*64)}
    with pytest.raises(ValueError):register_context(e['root'],e['db'],Context.model_validate(changed),allow_fixture=True)


def test_dq_audits_append_and_local_status_separate_from_batch(environment):
    e=environment;gen=complete(e);db=e['db'];legacy={k:v for k,v in snapshot(db).items() if not k.startswith('reconstruction_')}
    def run(**kwargs):return audit_complete_generation(e['root'],db,e['context_id'],gen,evidence=e['evidence'],allow_fixture=True,**kwargs)
    a=run();before=snapshot(db)
    b=run(supersedes=a['audit_id'])
    assert a['audit_id']!=b['audit_id'] and a['finding_set_hash']==b['finding_set_hash']
    for table,rows in before.items():
        if table.startswith('reconstruction_'):assert set(map(str,rows))<=set(map(str,snapshot(db)[table]))
    assert {k:v for k,v in snapshot(db).items() if k in legacy}==legacy
    assert a['batch_gate_status']=='BLOCKED' # unknown sessions and retained unknown native
    assert db.execute('SELECT count(*) FROM reconstruction_quality_audit').fetchone()==(2,)
    with pytest.raises(ValueError,match='Supersedes'):run(supersedes=uuid4())
    changed=dict(e['evidence'],sessions=[dict(venue='SZSE',episode_id=str(e['episode'].episode_id),event_date=DAY,
        previous_session=DAY-timedelta(days=1),certified=True,evidence_ref='fake',evidence_venue='SZSE')])
    with pytest.raises(ValueError,match='evidence'):audit_complete_generation(e['root'],db,e['context_id'],gen,evidence=changed,allow_fixture=True)


def test_dq_rejects_partial_and_evidence_no_implicit_disposition(environment):
    e=environment;gen=generation(e)
    with pytest.raises(ValueError,match='COMPLETE'):audit_complete_generation(e['root'],e['db'],e['context_id'],gen,evidence=e['evidence'],allow_fixture=True)
    old=[dict(finding_key='old',severity='ERROR')];new=[dict(finding_key='new',severity='REVIEW')]
    ledger=disposition_ledger(old,new)
    assert [r['disposition'] for r in ledger]==['EVIDENCE_REQUIRED','NEW_FINDING']
    with pytest.raises(ValueError):disposition_ledger(old,new,[dict(finding_key='old',decision='RESOLVED')])


@pytest.mark.parametrize('change',['hash','ordinal','native','dataset','status','knowledge'])
def test_exact_case_approval_and_source_scope_validation(environment,change):
    from copy import deepcopy
    e=environment;case=deepcopy(e['cases']);b=case['bindings'][0]
    if change=='hash':approval=e['approval']
    else:
        if change=='ordinal':b['observations'][0]['raw_row_number']=99
        if change=='native':b['native_identifier']='000002.SZ'
        if change=='dataset':b['dataset']='stock_st'
        if change=='status':b['decision_status']='PROPOSED'
        if change=='knowledge':b['decision_at']=NOW-timedelta(days=2)
        approval=e['approval'].model_copy(update={'approved_case_set_hash':checksum(case)})
    if change=='hash':case['bindings'][0]['native_identifier']='000003.SZ'
    before=snapshot(e['db'])
    with pytest.raises(ValueError):import_approved_cases(e['root'],e['db'],case,approval)
    assert snapshot(e['db'])==before


def publication_worker(root,context_id,generation_id,request_id,gate,queue):
    from pathlib import Path
    from astock.data.warehouse_lock import warehouse_connection
    try:
        gate.wait(10)
        with warehouse_connection(Path(root)/'data/warehouse/concurrency.duckdb',wait_seconds=5) as db:
            result=publish_output(Path(root),db,context_id,generation_id,request_id,allow_fixture=True)
        queue.put(result)
    except BaseException as exc:queue.put(type(exc).__name__)


def test_two_process_publishers_serialize_and_resume_exact_once(environment):
    import multiprocessing
    from astock.data.warehouse_lock import warehouse_connection
    e=environment;gen=generation(e)
    destination=e['root']/'data/warehouse/concurrency.duckdb';destination.parent.mkdir(parents=True,exist_ok=True)
    # Build an independent physical synthetic store in FK order. Native COPY/
    # EXPORT cannot currently preserve this populated FK graph reliably.
    with warehouse_connection(destination) as db:
        migrate(db,e['root']);apply_receipt_integrity_upgrade(e['root'],db,verification_sha='a'*40)
        apply_reconstruction_schema(e['root'],db,e['approval'])
        for table in ('ingestion_run','raw_object_manifest','listing_episode','official_exchange_code',
                      'provider_native_binding','provider_binding_observation','derivation_context','derivation_input','derivation_resolver_snapshot',
                      'derivation_generation','derivation_generation_event'):
            result=e['db'].execute(f'SELECT * FROM {table} ORDER BY ALL');rows=result.fetchall()
            placeholders=','.join('?' for _ in result.description)
            for row in rows:db.execute(f'INSERT INTO {table} VALUES ({placeholders})',list(row))
    mp=multiprocessing.get_context('spawn');gate=mp.Event();queue=mp.Queue()
    workers=[mp.Process(target=publication_worker,args=(str(e['root']),e['context_id'],gen,e['inputs'][0].request_id,gate,queue)) for _ in range(2)]
    for worker in workers:worker.start()
    gate.set()
    results=[queue.get(timeout=25) for _ in workers]
    for worker in workers:worker.join(10);assert worker.exitcode==0
    assert sorted(results)==['ALREADY_VALID','PUBLISHED']
    with warehouse_connection(destination) as db:
        assert db.execute('SELECT count(*) FROM derivation_output').fetchone()==(1,)
        assert db.execute('SELECT count(*) FROM derivation_row_quarantine').fetchone()==(1,)


@pytest.mark.parametrize('point',['008_r2_provider_identity','009_r2_derivation_publication','010_r2_append_only_quality'])
def test_schema_owner_transaction_rolls_back_partial_ddl(environment,point):
    from astock.data.warehouse_lock import WarehouseConnectionProxy
    e=environment
    # Independent fresh synthetic schema001–007, never drop an established generation.
    with duckdb.connect(':memory:') as db:
        migrate(db,e['root']);apply_receipt_integrity_upgrade(e['root'],db,verification_sha='a'*40)
        before=snapshot(db)
        class Fault(WarehouseConnectionProxy):
            def execute(self,sql,*args):
                if sql.startswith('CREATE TABLE listing_episode') or sql.startswith('-- Explicit') or sql.startswith('-- Append-only'):
                    if point.split('_',1)[0] in ('008','009','010'):
                        target={'008':'listing_episode','009':'derivation_context','010':'reconstruction_quality_audit'}[point[:3]]
                        if f'CREATE TABLE {target}' in sql:raise RuntimeError('synthetic migration')
                return db.execute(sql,*args)
        with pytest.raises(RuntimeError):apply_reconstruction_schema(e['root'],Fault(db),e['approval'])
        assert snapshot(db)==before
        assert apply_reconstruction_schema(e['root'],db,e['approval'])=='UPGRADED'


def test_quarantine_only_audit_survives_exact_foreign_key(environment):
    e=environment;gen=complete(e)
    # Existing proposal remains inactive at older knowledge cutoff; not an implicit historical backdate.
    context=e['context'].model_copy(update={'knowledge_as_of':NOW-timedelta(microseconds=1)})
    with pytest.raises(ValueError,match='knowledge'):register_context(e['root'],e['db'],context,allow_fixture=True)
    result=audit_complete_generation(e['root'],e['db'],e['context_id'],gen,evidence=e['evidence'],allow_fixture=True)
    assert result['findings']>=3


@pytest.mark.parametrize('tamper',['none','request_pair','parent_generation'])
def test_production_shape_requires_r1_exact133_and_parent126(slice_root,tamper):
    """Production admission path on a fully synthetic133-request temporary store."""
    from test_slice_capture import settings
    from test_slice_curate import MarketClient
    from astock.data.slice_capture import capture_slices,identity_state
    from astock.data.slice_curate import curate_slices
    from astock.data.warehouse_lock import warehouse_connection
    from astock.data.raw_validation import rows_dict
    shutil.copytree(ROOT/'docs',slice_root/'docs')
    capture=capture_slices(slice_root,settings(),live=True,client=MarketClient(),commit='a'*40)
    batch=__import__('uuid').UUID(capture['batch_id']);curate_slices(slice_root,batch,commit='a'*40)
    with warehouse_connection(slice_root/'data/warehouse/astock.duckdb') as db:
        at=datetime.now(timezone.utc);evidence=dict(sessions=[],reference_exceptions=[],bse_transitions=[],source_dispositions=[])
        approval=Approval(resolver_protocol="R2_RESOLVER_UTC_INSTANT_V2", time_integrity_addendum_hash=hashlib.sha256((ROOT / "docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md").read_bytes()).hexdigest(), review_ref='synthetic-full-plan-review',reviewed_sha='a'*40,
            design_hash=hashlib.sha256((slice_root/'docs/remediation/phase1c1/r2-a-design-v1.md').read_bytes()).hexdigest(),
            policy_hash=load_policy(slice_root)[1],approved_case_set_hash=checksum(dict(episodes=[],codes=[],bindings=[])),
            dq_evidence_hash=evidence_hash(evidence),publication_addendum_hash=hashlib.sha256((slice_root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-1.md').read_bytes()).hexdigest(),
            correction_addendum_hash=hashlib.sha256((slice_root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-3.md').read_bytes()).hexdigest(),
            disposition_addendum_hash=hashlib.sha256((slice_root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-2.md').read_bytes()).hexdigest(),approved_at=at)
        apply_reconstruction_schema(slice_root,db,approval)
        old={k:v for k,v in snapshot(db).items() if not k.startswith(('derivation_','reconstruction_'))}
        requests=rows_dict(db,'SELECT r.request_id,m.* FROM slice_request r JOIN raw_object_manifest m ON r.object_id=m.object_id WHERE batch_id=? ORDER BY ordinal',[batch])
        inputs=[Input(request_id=r['request_id'],raw_object_id=r['object_id'],dataset=r['dataset'],raw_hash=r['sha256'],
            raw_schema_hash=r['schema_hash'],row_count=r['row_count'],is_output=r['dataset']!='trade_cal') for r in requests]
        frozen=db.execute('SELECT identity_snapshot_hash,plan_hash FROM slice_batch WHERE batch_id=?',[batch]).fetchone()
        context=Context(resolver_protocol=approval.resolver_protocol, time_integrity_addendum_hash=approval.time_integrity_addendum_hash, parent_batch_id=batch,parent_generation=0,parent_identity_hash=frozen[0],parent_plan_hash=frozen[1],
            resolver_hash=load_resolver(db).snapshot_hash,specs_hash=specs_hash(slice_root),policy_hash=approval.policy_hash,
            design_hash=approval.design_hash,publication_addendum_hash=approval.publication_addendum_hash,disposition_addendum_hash=approval.disposition_addendum_hash,correction_addendum_hash=approval.correction_addendum_hash,
            dq_evidence_hash=approval.dq_evidence_hash,knowledge_as_of=at,implementation_sha='a'*40,approval=approval,inputs=tuple(inputs))
        if tamper=='request_pair':
            inputs[0]=inputs[0].model_copy(update={'request_id':'f'*64});context=context.model_copy(update={'inputs':tuple(inputs)})
        if tamper=='parent_generation':context=context.model_copy(update={'parent_generation':99})
        if tamper!='none':
            with pytest.raises(ValueError):register_context(slice_root,db,context)
        else:
            cid=register_context(slice_root,db,context);gen=start_generation(db,cid)
            publish_output(slice_root,db,cid,gen,next(i.request_id for i in inputs if i.dataset=='daily'))
            with pytest.raises(ValueError,match='Partial'):complete_generation(slice_root,db,cid,gen)
        assert {k:v for k,v in snapshot(db).items() if k in old}==old


def test_schema_missing_checks_or_shadow_rejected(environment):
    from astock.data.reconstruction import require_reconstruction_schema
    e=environment;db=e['db']
    db.execute('ALTER TABLE derivation_context ADD COLUMN unreviewed INTEGER')
    with pytest.raises(ValueError,match='schema'):require_reconstruction_schema(db)


def test_binding_first_observation_is_earliest_capture_not_every_capture(environment):
    e=environment;db=e['db'];run=uuid4();at=NOW+timedelta(hours=1)
    db.execute('''INSERT INTO ingestion_run(run_id,source,dataset,mode,started_at,status,code_commit,config_hash,provider_client_version)
        VALUES (?,'tushare','daily','AUDIT',?,'RUNNING',?,?,'1.0.0')''',[run,at,'a'*40,'b'*64])
    from astock.data.reconstruction import raw_capture
    original=raw_capture(e['root'],db,e['inputs'][0].raw_object_id)['arrow']
    table=ProviderTable(fields=original.column_names,items=[list(original.to_pylist()[0].values())],retrieved_at=at)
    raw=RawWriter(e['root'],db).write(run,'daily',0,table,RequestParams(trade_date=DAY));RawWriter(e['root'],db).sidecar(run,'daily')
    b=ProviderBinding.model_validate(e['cases']['bindings'][0])
    new=b.model_copy(update=dict(binding_id=uuid4(),binding_version=2,supersedes_binding_id=b.binding_id,
        observations=(*b.observations,SourceObservation(raw_object_id=raw.object_id,raw_row_number=0,event_date=DAY)),
        decision_at=at,available_at=at))
    cases=dict(episodes=[],codes=[],bindings=[new.model_dump()])
    approval=e['approval'].model_copy(update={'approved_case_set_hash':checksum(cases)})
    import_approved_cases(e['root'],db,cases,approval)
    resolved=load_resolver(db).resolve(provider='tushare',dataset='daily',native_identifier='000001.SZ',event_date=DAY,
        raw_object_id=raw.object_id,raw_row_number=0,knowledge_as_of=at)
    assert resolved.reason is None and resolved.binding_id==new.binding_id


@pytest.mark.parametrize('change',['none','ordinal','approval','evidence','dataset'])
def test_approved_out_of_scope_retains_quarantine_without_guessed_identity(environment,change):
    e=environment
    disposition=dict(dataset='daily_basic',event_date=DAY,raw_object_id=str(e['inputs'][1].raw_object_id),raw_row_number=1,
        decision='APPROVED_OUT_OF_SCOPE',approval_ref=e['approval'].review_ref,case_ref='synthetic-case-outside',evidence_ids=['synthetic-scope-proof'])
    if change=='ordinal':disposition['raw_row_number']=99
    if change=='approval':disposition['approval_ref']='author-proposal'
    if change=='evidence':disposition['evidence_ids']=[]
    if change=='dataset':disposition['dataset']='daily'
    evidence=dict(e['evidence'],source_dispositions=[disposition])
    approval=e['approval'].model_copy(update={'dq_evidence_hash':evidence_hash(evidence)})
    context=e['context'].model_copy(update={'approval':approval,'dq_evidence_hash':approval.dq_evidence_hash})
    cid=register_context(e['root'],e['db'],context,allow_fixture=True);gen=start_generation(e['db'],cid,allow_fixture=True)
    for input in context.inputs:publish_output(e['root'],e['db'],cid,gen,input.request_id,allow_fixture=True)
    complete_generation(e['root'],e['db'],cid,gen,allow_fixture=True)
    def run():return audit_complete_generation(e['root'],e['db'],cid,gen,evidence=evidence,allow_fixture=True)
    if change!='none':
        with pytest.raises(ValueError):run()
    else:
        run()
        rows=e['db'].execute('SELECT payload FROM reconstruction_finding_observation WHERE raw_object_id=?',[e['inputs'][1].raw_object_id]).fetchall()
        scoped=[json.loads(r[0]) for r in rows if json.loads(r[0])['raw_row_number']==1]
        assert scoped[0]['decision']=='OUT_OF_SCOPE' and scoped[0]['blocking'] is False
        assert e['db'].execute('SELECT count(*) FROM derivation_row_quarantine WHERE generation_id=?',[gen]).fetchone()==(2,)
