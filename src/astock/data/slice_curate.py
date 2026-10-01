"""Exact historical identity joins and append-only, explicitly typed slice outputs."""

import hashlib
import json
import math
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.curation import load_curation_specs, digest, publish_curated_bytes, input_manifest_hash
from astock.data.identity import _known_versions, is_normalized_ashare_identifier
from astock.data.probe_audit import canonical_json, records
from astock.data.raw_writer import atomic_new_file, verify_batch
from astock.data.slice_capture import (SliceStop, identity_state, implementation_commit,
                                      batch_requests, _object_table, validate_capture, validate_requests)
from astock.data.slice_plan import request_manifest

OUTPUTS = dict(daily='daily_bar', daily_basic='daily_basic_snapshot',
               adj_factor='adjustment_factor_observed', suspend_d='suspension_daily',
               stock_st='risk_warning_daily', stk_limit='price_limit_daily')


class FrozenResolver:
    def __init__(self, history, venues, as_of):
        self.index=defaultdict(list)
        for row in _known_versions(history.rows,as_of):
            if row.source=='tushare' and row.identifier_type=='ts_code':
                self.index[row.identifier].append(row)
        self.venues=defaultdict(list)
        latest={}
        for v in venues:
            if v['available_at']<=as_of:
                key=(v['security_id'],v['venue'],v['effective_from'])
                if key not in latest or v['available_at']>latest[key]['available_at']:latest[key]=v
        for v in latest.values():self.venues[v['security_id']].append(v)

    def resolve(self, identifier, event, *, provider_exchange=None):
        if not is_normalized_ashare_identifier(identifier):return None,'NON_NORMALIZED_IDENTIFIER'
        candidates=self.index.get(identifier,[])
        if not candidates:return None,'NO_IDENTIFIER_MAPPING'
        hits=[r for r in candidates if r.valid_from<=event and (r.valid_to is None or event<r.valid_to)]
        if not hits:
            if any(r.exchange=='BSE' for r in candidates) and event<date(2021,11,15):return None,'PRE_BSE_LEGACY'
            return None,'OUTSIDE_IDENTIFIER_INTERVAL'
        if len(hits)!=1:raise SliceStop('AMBIGUOUS_IDENTIFIER')
        row=hits[0]
        if provider_exchange is not None and provider_exchange!=row.exchange:raise SliceStop('PROVIDER_MAPPING_CONFLICT')
        venue=[v for v in self.venues[row.security_id] if v['venue']==row.exchange
               and v['effective_from']<=event and (v['effective_to'] is None or event<v['effective_to'])]
        if len(venue)!=1:raise SliceStop('VENUE_IDENTITY_CONFLICT')
        return row.security_id,None


def cast_field(value, field):
    if value is None:
        if field.nullable_policy=='FORBID':raise SliceStop('SCHEMA')
        return None
    kind=field.logical_type
    if kind=='string' and isinstance(value,str):return value
    if kind=='date32' and isinstance(value,str) and len(value)==8 and value.isdigit():
        try:return date.fromisoformat(f'{value[:4]}-{value[4:6]}-{value[6:]}')
        except ValueError:pass
    if kind=='float64' and type(value) in (int,float) and math.isfinite(value):
        if type(value)==int and abs(value)>2**53:raise SliceStop('SCHEMA')
        return float(value)
    if kind=='int64' and type(value)==int and -(2**63)<=value<2**63:return value
    raise SliceStop('SCHEMA')


def output_schema(spec):
    fields=list(spec.arrow_schema())+[
        pa.field('security_id',pa.string(),nullable=False),
        pa.field('raw_object_id',pa.string(),nullable=False),
        pa.field('raw_row_number',pa.int64(),nullable=False),
        pa.field('retrieved_at',pa.timestamp('us',tz='UTC'),nullable=False),
        pa.field('available_at',pa.timestamp('us',tz='UTC'),nullable=False)]
    return pa.schema(fields,metadata={'output_name':OUTPUTS[spec.dataset],
        'spec_version':spec.spec_version,'availability_basis':'OBSERVED_CAPTURE',
        'identity_basis':'CURRENT_RECONSTRUCTION','research_usage':spec.research_usage})


def logical_hash(table):
    def serial(row):
        return {k:v.isoformat() if isinstance(v,(date,datetime)) else v for k,v in row.items()}
    # Schema bytes retain field units and usage without JSON bytes coercion.
    schema_hash=hashlib.sha256(table.schema.serialize().to_pybytes()).hexdigest()
    rows=sorted((canonical_json(serial(r)).decode() for r in table.to_pylist()))
    return digest(dict(schema_hash=schema_hash,rows=rows))


def convert(table, obj, spec, resolver):
    output=[];quarantine=[]
    for ordinal,row in enumerate(records(table)):
        typed={f.target_column:cast_field(row[f.source_column],f) for f in spec.fields}
        event=typed['trade_date'];identifier=typed['ts_code']
        if spec.dataset=='stk_limit' and typed['asset_type']!='STK':sid,reason=None,'ASSET_OUT_OF_SCOPE'
        else:sid,reason=resolver.resolve(identifier,event,provider_exchange=typed.get('exchange'))
        if reason:
            quarantine.append(dict(provider_identifier=identifier,event_date=event.isoformat(),reason=reason,
                                   raw_object_id=obj['object_id'],raw_row_number=ordinal))
        else:
            typed.update(security_id=sid,raw_object_id=obj['object_id'],raw_row_number=ordinal,
                         retrieved_at=table.retrieved_at,available_at=table.retrieved_at)
            output.append(typed)
    return pa.Table.from_pylist(output,schema=output_schema(spec)),quarantine


def curate_slices(root: Path, batch_id: UUID, *, rebuild=False, commit=None):
    manifest=request_manifest(root)
    specs={s.dataset:s for s in load_curation_specs(root,spec_version='v2')}
    contracts={c.dataset:c for c in load_contracts(root,catalog_version='v2')}
    config_hash=digest(dict(plan=manifest['plan_hash'],specs=[s.model_dump(mode='json') for s in specs.values()]))
    code=commit or implementation_commit(root)
    with duckdb.connect(str(root/'data/warehouse/astock.duckdb')) as db:
        batch=db.execute('SELECT status,identity_snapshot_hash,knowledge_as_of,plan_hash FROM slice_batch WHERE batch_id=?',[str(batch_id)]).fetchone()
        if not batch or batch[0] not in ('CAPTURED','CURATED','REVIEWED') or batch[3]!=manifest['plan_hash']:raise SliceStop('CAPTURE_NOT_COMPLETE')
        snapshot,history,venues=identity_state(db)
        if snapshot!=batch[1]:raise SliceStop('FROZEN_INPUT_CHANGED')
        resolver=FrozenResolver(history,venues,batch[2]);requests=batch_requests(db,batch_id)
        validate_requests(requests,manifest)
        if len(requests)!=133 or any(r['status']!='COMPLETE' for r in requests):raise SliceStop('LINEAGE')
        if not verify_batch(root,db,[r['run_id'] for r in requests]):raise SliceStop('LINEAGE')
        generation=db.execute('SELECT max(generation) FROM slice_curated_binding WHERE batch_id=?',[str(batch_id)]).fetchone()[0]
        if generation is not None and not rebuild:raise SliceStop('EXISTING_CURATION_REQUIRES_REBUILD')
        generation=0 if generation is None else generation+1
        # Preflight every schema and identity before publishing any curated objects.
        for req in requests:
            table,obj=_object_table(root,db,req)
            validate_capture(table,contracts[req['dataset']],RequestParams.model_validate_json(req['request_params']),req['slice_name'])
            metadata=json.loads((root/obj['relative_path']).with_name('capture-contract.json').read_bytes())
            if metadata!=dict(contract_catalog='v2',contract_version=contracts[req['dataset']].contract_version,
                contract_hash=req['contract_hash'],request_id=req['request_id'],request_params=json.loads(req['request_params']),**obj):raise SliceStop('LINEAGE')
            if req['dataset']!='trade_cal':convert(table,obj,specs[req['dataset']],resolver)
        totals=dict(provider_rows=0,resolved_rows=0,quarantined_rows=0,curated_objects=0)
        hashes=[];reasons=defaultdict(int)
        for req in requests:
            if req['dataset']=='trade_cal':continue
            table,obj=_object_table(root,db,req)
            arrow,quarantine=convert(table,obj,specs[req['dataset']],resolver)
            logical=logical_hash(arrow)
            if generation:
                previous=db.execute('SELECT logical_hash FROM slice_curated_binding WHERE batch_id=? AND request_id=? AND generation=0',[str(batch_id),req['request_id']]).fetchone()
                if previous is None or previous[0]!=logical:raise SliceStop('REBUILD_HASH_MISMATCH')
            run=uuid4();oid=uuid4();now=datetime.now(timezone.utc)
            sink=pa.BufferOutputStream();pq.write_table(arrow,sink)
            path=publish_curated_bytes(root,dataset=req['dataset'],run_id=run,part=0,content=sink.getvalue().to_pybytes())
            schema_hash=hashlib.sha256(arrow.schema.serialize().to_pybytes()).hexdigest()
            event=RequestParams.model_validate_json(req['request_params']).trade_date
            lineage=dict(batch_id=str(batch_id),request_id=req['request_id'],generation=generation,
                         raw_object=obj,output_name=OUTPUTS[req['dataset']],logical_hash=logical,
                         config_hash=config_hash,identity_snapshot_hash=snapshot,knowledge_as_of=batch[2].isoformat(),
                         code_commit=code,curated_object_id=str(oid),quarantine=quarantine)
            atomic_new_file(path.with_name('lineage.json'),lambda p:p.write_bytes(canonical_json(lineage)))
            db.execute('BEGIN')
            try:
                db.execute('INSERT INTO curation_run VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',[
                    str(run),req['dataset'],event.isoformat(),now,now,'PARTIAL' if quarantine else 'SUCCEEDED',code,
                    config_hash,input_manifest_hash([obj]),snapshot,len(table.items),arrow.num_rows,len(quarantine)])
                db.execute('INSERT INTO curated_object_manifest VALUES (?,?,?,?,?,?,?,?)',[
                    str(oid),str(run),str(path.relative_to(root)),hashlib.sha256(path.read_bytes()).hexdigest(),schema_hash,
                    arrow.num_rows,event if arrow.num_rows else None,event if arrow.num_rows else None])
                db.execute('INSERT INTO slice_curated_binding VALUES (?,?,?,?,?,?,?)',[
                    str(batch_id),req['request_id'],generation,obj['object_id'],str(oid),logical,OUTPUTS[req['dataset']]])
                for q in quarantine:
                    db.execute('INSERT INTO identity_quarantine VALUES (?,?,?,?,?,?,?,?)',[
                        str(uuid4()),req['dataset'],q['provider_identifier'],event,q['reason'],obj['object_id'],str(run),now])
                    reasons[q['reason']]+=1
                db.execute('INSERT INTO dataset_date_audit VALUES (?,?,?,?,?,?,?,?,?,?)',[
                    req['dataset'],event,str(run),len(table.items),arrow.num_rows,len(quarantine),0,False,
                    'PARTIAL' if quarantine else 'PASS',json.dumps({'missing_count':0,'identity_conflict_count':0,
                     'null_count':sum(v is None for r in arrow.to_pylist() for v in r.values())})])
                db.execute('COMMIT')
            except Exception:
                db.execute('ROLLBACK');raise
            totals['provider_rows']+=len(table.items);totals['resolved_rows']+=arrow.num_rows
            totals['quarantined_rows']+=len(quarantine);totals['curated_objects']+=1
            hashes.append(dict(request_id=req['request_id'],logical_hash=logical))
        summary=dict(batch_id=str(batch_id),generation=generation,status='CURATED',**totals,
                     quarantine_reasons=dict(reasons),rebuild_hash_match=bool(generation),hashes=hashes)
        atomic_new_file(root/f'data/private/phase1c1/{batch_id}/curation-{generation}.json',lambda p:p.write_bytes(canonical_json(summary)))
        db.execute("UPDATE slice_batch SET status='CURATED' WHERE batch_id=?",[str(batch_id)])
        return {k:v for k,v in summary.items() if k!='hashes'}
