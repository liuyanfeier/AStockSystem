import hashlib,json,shutil,socket,tempfile
from pathlib import Path
from collections import Counter
from datetime import date,datetime,timezone,timedelta
from uuid import uuid4
import duckdb,httpx
from astock.data.raw_writer import migrate,RawWriter
from astock.data.audit import RequestParams
from astock.data.tushare_client import ProviderTable,TushareClient
from astock.data.receipt_migration import apply_receipt_integrity_upgrade
from astock.data.provider_identity import ListingEpisode,ExchangeCode,ProviderBinding,SourceObservation
from astock.data.curation import load_curation_specs
from astock.data.reconstruction import Approval,Context,Input,checksum,apply_reconstruction_schema,import_approved_cases,load_resolver,specs_hash,register_context,start_generation,publish_output,complete_generation,select_complete
from astock.data.reconstruction_dq import load_policy,evidence_hash,audit_complete_generation
ROOT=Path('/Users/yanliu/Documents/AStockSystem');WORK=Path(__file__).parent
NOW=datetime(2026,10,3,tzinfo=timezone.utc);DAY=date(2025,5,6);OBS=NOW-timedelta(hours=1)
spies=Counter()
def deny(key):
 def f(*a,**k):spies[key]+=1;raise AssertionError('FORBIDDEN_'+key)
 return f
TushareClient.__init__=deny('provider');httpx.Client.request=httpx.AsyncClient.request=deny('http')
socket.create_connection=socket.getaddrinfo=socket.socket.connect=socket.socket.connect_ex=deny('socket')

def build(days,empty_factor=False):
 root=Path(tempfile.mkdtemp(prefix='r2a-probe-',dir=WORK))
 for name in ('sql','config','docs'):shutil.copytree(ROOT/name,root/name)
 db=duckdb.connect(':memory:');migrate(db,root);apply_receipt_integrity_upgrade(root,db,verification_sha='a'*40)
 ep=ListingEpisode(episode_id=uuid4(),security_id='synthetic-dq-security',venue='SZSE',asset_type='STK',valid_from=date(2000,1,1),retrieved_at=NOW,available_at=NOW,evidence_ids=('synthetic-proof',),approval_ref='synthetic-independent-review')
 code=ExchangeCode(code_id=uuid4(),episode_id=ep.episode_id,identifier='000001.SZ',valid_from=ep.valid_from,available_at=NOW,evidence_ids=('synthetic-code',),approval_ref=ep.approval_ref)
 sessions=[dict(venue='SZSE',episode_id=str(ep.episode_id),event_date=DAY+timedelta(days=n),previous_session=DAY+timedelta(days=n-1),certified=True,evidence_venue='SZSE',evidence_ref='synthetic-calendar') for n in range(days)]
 evidence=dict(sessions=sessions,reference_exceptions=[],bse_transitions=[],source_dispositions=[])
 approval=Approval(review_ref=ep.approval_ref,reviewed_sha='a'*40,approved_at=NOW,design_hash=hashlib.sha256((root/'docs/remediation/phase1c1/r2-a-design-v1.md').read_bytes()).hexdigest(),policy_hash=load_policy(root)[1],approved_case_set_hash=checksum(dict(episodes=[],codes=[],bindings=[])),dq_evidence_hash=evidence_hash(evidence),publication_addendum_hash=hashlib.sha256((root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-1.md').read_bytes()).hexdigest(),disposition_addendum_hash=hashlib.sha256((root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-2.md').read_bytes()).hexdigest())
 apply_reconstruction_schema(root,db,approval)
 inputs=[];scopes={};specs=load_curation_specs(root,spec_version='v2')
 for n in range(days):
  day=DAY+timedelta(days=n);close=10.0 if n==0 else 11.0;pre_close=10.0 if n<2 else 11.0
  for spec in specs:
   dataset=spec.dataset;run=uuid4()
   db.execute("INSERT INTO ingestion_run(run_id,source,dataset,mode,started_at,status,code_commit,config_hash,provider_client_version) VALUES (?,'tushare',?,'AUDIT',?,'RUNNING',?,?,'1.0.0')",[run,dataset,OBS,'a'*40,'b'*64])
   fields=[f.source_column for f in spec.fields]
   base={f.source_column:dict(string='synthetic',date32=day.strftime('%Y%m%d'),float64=10.0,int64=1)[f.logical_type] for f in spec.fields}
   base.update(open=close,high=12.0,low=9.0,ts_code='000001.SZ',asset_type='STK',exchange='SZSE',close=close,pre_close=pre_close,pct_chg=0.0,change=0.0,adj_factor=1.0)
   items=[] if dataset in ('stock_st','suspend_d') or (dataset=='adj_factor' and empty_factor) else [[base[f] for f in fields]]
   raw=RawWriter(root,db).write(run,dataset,0,ProviderTable(fields=fields,items=items,retrieved_at=OBS),RequestParams(trade_date=day));RawWriter(root,db).sidecar(run,dataset)
   inputs.append(Input(request_id=checksum((dataset,day)),raw_object_id=raw.object_id,dataset=dataset,raw_hash=raw.sha256,raw_schema_hash=raw.schema_hash,row_count=len(items),is_output=True))
   if items:scopes.setdefault(dataset,[]).append(SourceObservation(raw_object_id=raw.object_id,raw_row_number=0,event_date=day))
 bindings=[ProviderBinding(binding_id=uuid4(),binding_version=1,dataset=dataset,native_identifier='000001.SZ',episode_id=ep.episode_id,representation_kind='EVENT_NATIVE',observations=tuple(observations),first_observed_at=OBS,decision_at=NOW,available_at=NOW,evidence_ids=('synthetic-capture',),decision_status='APPROVED',approval_ref=ep.approval_ref) for dataset,observations in scopes.items()]
 cases=dict(episodes=[ep.model_dump()],codes=[code.model_dump()],bindings=[b.model_dump() for b in bindings]);approval=approval.model_copy(update={'approved_case_set_hash':checksum(cases)})
 import_approved_cases(root,db,cases,approval)
 context=Context(parent_batch_id=uuid4(),parent_generation=0,parent_identity_hash='b'*64,parent_plan_hash='c'*64,resolver_hash=load_resolver(db).snapshot_hash,specs_hash=specs_hash(root),policy_hash=approval.policy_hash,design_hash=approval.design_hash,dq_evidence_hash=approval.dq_evidence_hash,publication_addendum_hash=approval.publication_addendum_hash,disposition_addendum_hash=approval.disposition_addendum_hash,knowledge_as_of=NOW,implementation_sha='a'*40,approval=approval,inputs=tuple(inputs),fixture_only=True)
 cid=register_context(root,db,context,allow_fixture=True);gid=start_generation(db,cid,allow_fixture=True)
 for item in inputs:publish_output(root,db,cid,gid,item.request_id,allow_fixture=True)
 complete_generation(root,db,cid,gid,allow_fixture=True)
 return dict(root=root,db=db,cid=cid,gid=gid,approval=approval,evidence=evidence,bindings=bindings,context=context,inputs=inputs)

missing=build(1,empty_factor=True)
a=audit_complete_generation(missing['root'],missing['db'],missing['cid'],missing['gid'],evidence=missing['evidence'],allow_fixture=True)
assert a['findings']==0 and a['local_status']==a['batch_gate_status']=='PASS'
result={'missing_factor':dict(daily_resolved_rows=1,adj_factor_source_rows=0,audit_findings=a['findings'],local_status=a['local_status'],batch_gate_status=a['batch_gate_status'])}
missing['db'].close()

math=build(3)
b=audit_complete_generation(math['root'],math['db'],math['cid'],math['gid'],evidence=math['evidence'],allow_fixture=True)
observed=[json.loads(r[0]) for r in math['db'].execute('SELECT payload FROM reconstruction_finding_observation').fetchall()]
quality={next(i.dataset+':'+(DAY+timedelta(days=n)).isoformat() for n in range(3) for i in math['inputs'] if i.request_id==request and i.request_id==checksum((i.dataset,DAY+timedelta(days=n)))):status for request,status in math['db'].execute('SELECT request_id,local_status FROM reconstruction_output_quality WHERE audit_id=?',[b['audit_id']]).fetchall()}
assert b['causal']['causal_mismatch']==1 and b['causal']['factor_mismatch']==1
assert quality['daily:2025-05-07']=='PASS' and quality['daily:2025-05-08']=='BLOCKED'
result['misdated_math_findings']=dict(actual_bad_pair_date='2025-05-07',emitted=[dict(rule=f['rule'],event_date=f['event_date']) for f in observed],daily_quality={k:v for k,v in quality.items() if k.startswith('daily:')})
math['db'].close()

version=build(1)
old=next(b for b in version['bindings'] if b.dataset=='daily');later=NOW+timedelta(days=1)
new=old.model_copy(update=dict(binding_id=uuid4(),binding_version=2,supersedes_binding_id=old.binding_id,decision_at=later,available_at=later))
cases=dict(episodes=[],codes=[],bindings=[new.model_dump()]);approval=version['approval'].model_copy(update={'approved_case_set_hash':checksum(cases),'approved_at':later})
import_approved_cases(version['root'],version['db'],cases,approval)
resolver=load_resolver(version['db']);o=old.observations[0]
hit=resolver.resolve(provider='tushare',dataset='daily',native_identifier=old.native_identifier,event_date=o.event_date,raw_object_id=o.raw_object_id,raw_row_number=o.raw_row_number,knowledge_as_of=NOW)
assert hit.binding_id==old.binding_id and hit.reason is None
try:select_complete(version['root'],version['db'],version['cid'],version['gid'],allow_fixture=True)
except ValueError as error:failure=str(error)
else:raise AssertionError('Expected old frozen context invalidated')
assert failure=='Design/resolver snapshot changed'
result['appended_version_invalidates_frozen_context']=dict(old_knowledge_resolves_original_binding=True,old_complete_selection_error=failure)
version['db'].close()
assert all(v==0 for v in spies.values())
result['market_calls']=dict(provider=spies['provider'],http=spies['http'],socket=spies['socket'])
(WORK/'r2a-independent-repros.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
