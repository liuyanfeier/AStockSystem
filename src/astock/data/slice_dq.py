"""Offline, bounded acceptance audits. Findings never authorize further ingestion."""

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from uuid import UUID

from astock.data.warehouse_lock import warehouse_connection
import pyarrow.parquet as pq

from astock.data.audit import RequestParams
from astock.data.curation import load_curation_specs, digest
from astock.data.probe_audit import canonical_json
from astock.data.raw_writer import atomic_new_file
from astock.data.slice_capture import (SliceStop, identity_state, batch_requests, _object_table,
                                      validate_requests)
from astock.data.slice_curate import FrozenResolver, output_schema, logical_hash, convert
from astock.data.receipt_integrity import validate_slice_batch
from astock.data.slice_errors import ReceiptIntegrityError
from astock.data.slice_capture import operation_block
from astock.data.slice_plan import request_manifest, APPROVED

PRICE_TOLERANCE=0.011
PCT_TOLERANCE=0.011  # percentage points, including provider four-place percentage rounding


def causal_audit(bars, factors, previous_sessions):
    """Forward pre_close chain only. Never anchor earlier prices to a future factor."""
    grouped=defaultdict(list);series=[]
    for row in bars:grouped[row['security_id']].append(row)
    stats=dict(adjacent_pairs=0,gap_resets=0,causal_mismatch=0,factor_pairs=0,factor_mismatch=0,
               missing_factor_pairs=0,max_causal_error_pp=0.0,max_factor_error_pp=0.0)
    for sid,rows in grouped.items():
        previous=None;scale=1.0
        for row in sorted(rows,key=lambda r:r['trade_date']):
            day=row['trade_date']
            if previous is not None and previous_sessions.get(day)==previous['trade_date']:
                if row['pre_close'] is None or row['pre_close']<=0 or previous['close'] is None or previous['close']<=0:
                    raise SliceStop('CAUSAL_INPUT_INVALID')
                scale*=previous['close']/row['pre_close']
                current=row['close']*scale
                prior=previous['causal_close']
                error=abs(100*(current/prior-1)-row['pct_chg'])
                stats['adjacent_pairs']+=1
                stats['max_causal_error_pp']=max(stats['max_causal_error_pp'],error)
                stats['causal_mismatch']+=int(error>PCT_TOLERANCE)
                left=factors.get((sid,previous['trade_date']));right=factors.get((sid,day))
                if left is not None and right is not None and left>0 and right>0:
                    factor_error=abs(100*(row['close']*right/(previous['close']*left)-1)-row['pct_chg'])
                    # Independent factor return differs from quoted 0.01-rounded pre_close.
                    tolerance=PCT_TOLERANCE+100*PRICE_TOLERANCE/row['pre_close']
                    stats['factor_pairs']+=1
                    stats['max_factor_error_pp']=max(stats['max_factor_error_pp'],factor_error)
                    stats['factor_mismatch']+=int(factor_error>tolerance)
                else:stats['missing_factor_pairs']+=1
            else:
                scale=1.0
                if previous is not None:stats['gap_resets']+=1
            entry=dict(security_id=sid,trade_date=day,scale=scale,
                       **{f'causal_{field}':row[field]*scale for field in ('open','high','low','close')})
            series.append(entry);previous={**row,'causal_close':entry['causal_close']}
    return stats,series


def _duplicates(rows, dataset):
    fields=['security_id','trade_date']
    if dataset=='suspend_d':fields+=['suspend_type','suspend_timing']
    keys=[tuple(r[f] for f in fields) for r in rows]
    return len(keys)-len(set(keys))


def audit_tables(tables, quarantine, resolver, previous_sessions):
    """Return aggregate summary and private details; no row-count equality assumption."""
    errors=Counter();reviews=Counter();coverage=[];cross=[];private_missing=[];boundaries=[]
    basic_only=0;limit_only=0;daily_venue_counts=Counter();after_hours=[]
    bars=[];factors={};type_names=defaultdict(set)
    for (dataset,day),rows in tables.items():
        errors['duplicate_keys']+=_duplicates(rows,dataset)
        if dataset=='daily':bars.extend(rows)
        if dataset=='adj_factor':
            for r in rows:
                value=r['adj_factor']
                if value is None or value<=0:errors['nonpositive_factor']+=1
                else:factors[(r['security_id'],day)]=value
        if dataset=='stock_st':
            for r in rows:type_names[(day,r['type'])].add(r['type_name'])
    errors['risk_type_name_conflict']=sum(len(v)>1 for v in type_names.values())
    for days in APPROVED.values():
        for text in days:
            day=date.fromisoformat(text)
            daily={r['security_id']:r for r in tables.get(('daily',day),[])}
            basic={r['security_id']:r for r in tables.get(('daily_basic',day),[])}
            limit={r['security_id']:r for r in tables.get(('stk_limit',day),[])}
            suspend=tables.get(('suspend_d',day),[])
            full_s={r['security_id'] for r in suspend if r['suspend_type']=='S' and r['suspend_timing'] in (None,'','全天')}
            resume={r['security_id'] for r in suspend if r['suspend_type']=='R'}
            reviews['full_day_suspension_with_bar']+=len(full_s & daily.keys())
            reviews['suspension_and_resume_same_date']+=len(full_s & resume)
            entry=dict(trade_date=text)
            for label,other,field in [('daily_basic',basic,'close'),('stk_limit',limit,'pre_close')]:
                common=daily.keys() & other.keys()
                mismatch=sum(daily[sid][field] is None or other[sid][field] is None or
                             abs(daily[sid][field]-other[sid][field])>PRICE_TOLERANCE for sid in common)
                errors[label+'_price_mismatch']+=mismatch
                missing=daily.keys()-other.keys();provider_only=other.keys()-daily.keys()
                entry[label]=dict(intersection=len(common),missing=len(missing),provider_only=len(provider_only),mismatch=mismatch)
                reviews[label+'_missing_or_provider_only']+=len(missing)+len(provider_only)
                if label=='daily_basic':basic_only+=len(provider_only)
                else:limit_only+=len(provider_only)
            cross.append(entry)
            expected={}
            for sid,vs in resolver.venues.items():
                for v in vs:
                    if v['effective_from']<=day and (v['effective_to'] is None or day<v['effective_to']):
                        if sid in expected:raise SliceStop('VENUE_IDENTITY_CONFLICT')
                        expected[sid]=v
            for sid in daily:
                if sid in expected:daily_venue_counts[expected[sid]['venue']]+=1
            after_hours.append(dict(trade_date=text,
                ah_volume_nonnull=sum(r.get('ah_volume_hands') is not None for r in daily.values()),
                ah_volume_positive=sum(r.get('ah_volume_hands') is not None and r.get('ah_volume_hands')>0 for r in daily.values()),
                ah_amount_nonnull=sum(r.get('ah_amount_cny_thousand') is not None for r in daily.values())))
            counts=Counter(observed_bar=0,full_day_suspension=0,delist_metadata_review=0,
                           listing_boundary_review=0,unexplained_missing=0)
            for sid,v in expected.items():
                delist=v.get('provider_delist_date')
                if delist and day>=delist:
                    # Preserve an open interval; provider endpoint meaning remains unclassified.
                    counts['delist_metadata_review']+=1
                    if day==delist:boundaries.append(dict(security_id=sid,trade_date=text,
                         classification='BOUNDARY_REVIEW',bar_observed=sid in daily,full_day_suspension=sid in full_s,
                         provider_delist_date=delist.isoformat(),effective_to=None))
                elif sid in daily:counts['observed_bar']+=1
                elif sid in full_s:counts['full_day_suspension']+=1
                elif day==v['provider_list_date']:
                    counts['listing_boundary_review']+=1
                else:
                    counts['unexplained_missing']+=1
                    private_missing.append(dict(security_id=sid,trade_date=text))
            errors['unexplained_missing_daily']+=counts['unexplained_missing']
            reviews['listing_boundary_review']+=counts['listing_boundary_review']
            reviews['delist_metadata_review']+=counts['delist_metadata_review']
            errors['bar_outside_venue_universe']+=len(daily.keys()-expected.keys())
            for r in daily.values():
                if (r['security_id'],day) not in factors:errors['daily_missing_factor']+=1
            coverage.append(dict(trade_date=text,expected_open_venue_intervals=len(expected),daily_rows=len(daily),
                                 full_day_suspensions=len(full_s),**counts))
            if day<date(2016,8,1) and not tables.get(('stock_st',day)):
                reviews['early_stock_st_empty_not_proof_of_no_ST']+=1
    errors['unresolved_traded_identity']=sum(1 for q in quarantine if q['dataset']=='daily' and q['reason'] not in ('PRE_BSE_LEGACY',))
    reasons=Counter(q['reason'] for q in quarantine)
    reviews['quarantined_records']=len(quarantine)
    causal,_=causal_audit(bars,factors,previous_sessions)
    errors['causal_return_mismatch']=causal['causal_mismatch']
    errors['factor_return_mismatch']=causal['factor_mismatch']
    errors['missing_factor_pairs']=causal['missing_factor_pairs']
    transitions=[]
    for boundary,left,right in [(date(2025,5,6),date(2025,4,30),date(2025,5,6)),
                               (date(2025,10,9),date(2025,9,30),date(2025,10,9))]:
        changing={r.security_id for vs in resolver.index.values() for r in vs if r.exchange=='BSE' and r.valid_from==boundary}
        l={r['security_id']:r for r in tables.get(('daily',left),[])}
        r={r['security_id']:r for r in tables.get(('daily',right),[])}
        observed=changing & l.keys() & r.keys()
        unchanged=sum(l[sid]['ts_code']==r[sid]['ts_code'] for sid in observed)
        errors['bse_switch_identifier_unchanged']+=unchanged
        reviews['bse_transition_not_observed_both_sessions']+=len(changing-observed)
        transitions.append(dict(effective_date=boundary.isoformat(),mapped_securities=len(changing),
            continuity_observed=len(observed),not_observed_both_sessions=len(changing-observed),incorrect_same_identifier=unchanged))
    summary=dict(status='BLOCKED' if sum(errors.values()) else ('PARTIAL' if sum(reviews.values()) or boundaries else 'PASS'),
        errors=dict(errors),error_count=sum(errors.values()),reviews=dict(reviews),review_count=sum(reviews.values()),
        daily_venue_rows=dict(daily_venue_counts),after_hours_fields=after_hours,
        risk_warning_rows=sum(len(v) for (dataset,_),v in tables.items() if dataset=='stock_st'),
        suspension_rows=sum(len(v) for (dataset,_),v in tables.items() if dataset=='suspend_d'),
        coverage=coverage,cross_table=cross,causal=causal,bse_transitions=transitions,
        quarantine_reasons=dict(reasons),delist_selected_boundary_cases=len(boundaries),
        provider_only=dict(daily_basic=basic_only,stk_limit=limit_only),
        tolerances=dict(price=PRICE_TOLERANCE,pct_chg_pp=PCT_TOLERANCE,
                        factor_pct_pp='0.011 + 100 * 0.011 / pre_close'))
    return summary,dict(unexplained_missing=private_missing,delist_boundary_review=boundaries)


def dq_slices(root: Path,batch_id: UUID):
    with warehouse_connection(root/'data/warehouse/astock.duckdb') as db:
        batch=db.execute('SELECT status,identity_snapshot_hash,knowledge_as_of FROM slice_batch WHERE batch_id=?',[str(batch_id)]).fetchone()
        if not batch or batch[0] not in ('CURATED','REVIEWED'):raise SliceStop('CURATION_NOT_COMPLETE')
        snapshot,history,venues=identity_state(db)
        if snapshot!=batch[1]:raise SliceStop('FROZEN_INPUT_CHANGED')
        resolver=FrozenResolver(history,venues,batch[2]);requests=batch_requests(db,batch_id)
        try:
            validate_slice_batch(root,db,batch_id)
        except ReceiptIntegrityError as error:
            operation_block(root,batch_id,error.code)
            raise
        generation=db.execute('SELECT max(generation) FROM slice_curated_binding WHERE batch_id=?',[str(batch_id)]).fetchone()[0]
        specs={s.dataset:s for s in load_curation_specs(root,spec_version='v2')}
        tables={};quarantine=[];previous={};objects=0
        for req in requests:
            raw,obj=_object_table(root,db,req)
            if req['dataset']=='trade_cal':
                for row in raw.items:
                    r=dict(zip(raw.fields,row,strict=True))
                    if str(r['is_open'])=='1':
                        day=date.fromisoformat(f"{r['cal_date'][:4]}-{r['cal_date'][4:6]}-{r['cal_date'][6:]}")
                        p=r['pretrade_date']
                        prior=date.fromisoformat(f'{p[:4]}-{p[4:6]}-{p[6:]}')
                        if prior>=day:raise SliceStop('CALENDAR')
                        previous[day]=prior
                continue
            binding=db.execute('''SELECT c.relative_path,c.sha256,c.schema_hash,c.row_count,b.logical_hash,b.raw_object_id
                FROM slice_curated_binding b JOIN curated_object_manifest c ON b.curated_object_id=c.object_id
                WHERE b.batch_id=? AND b.request_id=? AND b.generation=?''',[str(batch_id),req['request_id'],generation]).fetchone()
            if not binding or str(binding[5])!=obj['object_id']:raise SliceStop('LINEAGE')
            relative,checksum,schema_hash,count,logical,_=binding;path=root/relative
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()/'data/curated') or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:raise SliceStop('LINEAGE')
            arrow=pq.ParquetFile(path).read()
            if not arrow.schema.equals(output_schema(specs[req['dataset']]),check_metadata=True):raise SliceStop('SCHEMA')
            if hashlib.sha256(arrow.schema.serialize().to_pybytes()).hexdigest()!=schema_hash or arrow.num_rows!=count or logical_hash(arrow)!=logical:raise SliceStop('LINEAGE')
            regenerated,q=convert(raw,obj,specs[req['dataset']],resolver)
            if logical_hash(regenerated)!=logical:raise SliceStop('LINEAGE_RECONSTRUCTION')
            lineage=json.loads(path.with_name('lineage.json').read_bytes())
            if lineage['raw_object']!=obj or lineage['logical_hash']!=logical or lineage['quarantine']!=q:raise SliceStop('LINEAGE')
            day=RequestParams.model_validate_json(req['request_params']).trade_date
            tables[(req['dataset'],day)]=arrow.to_pylist()
            quarantine.extend(dict(dataset=req['dataset'],**r) for r in q);objects+=1
        if objects!=126:raise SliceStop('LINEAGE')
        summary,private=audit_tables(tables,quarantine,resolver,previous)
        raw_counts=db.execute('SELECT count(*),sum(attempts),count(DISTINCT object_id) FROM slice_request WHERE batch_id=?',[str(batch_id)]).fetchone()
        summary.update(batch_id=str(batch_id),generation=generation,raw_requests=raw_counts[0],http_attempts=raw_counts[1],
                       raw_objects=raw_counts[2],curated_objects=objects,lineage='PASS',schema='PASS',
                       identity_basis='CURRENT_RECONSTRUCTION',availability_basis='OBSERVED_CAPTURE')
        missing_by_day={r['trade_date']:r['unexplained_missing'] for r in summary['coverage']}
        audit_status='BLOCKED' if summary['error_count'] else ('PARTIAL' if summary['status']=='PARTIAL' else 'PASS')
        current=db.execute('''SELECT c.curation_run_id,s.dataset,s.request_params FROM slice_curated_binding b
            JOIN curated_object_manifest c ON c.object_id=b.curated_object_id
            JOIN slice_request s ON s.batch_id=b.batch_id AND s.request_id=b.request_id
            WHERE b.batch_id=? AND b.generation=?''',[str(batch_id),generation]).fetchall()
        for run,dataset,params in current:
            day=RequestParams.model_validate_json(params).trade_date.isoformat()
            details=json.loads(db.execute('SELECT details FROM dataset_date_audit WHERE curation_run_id=?',[str(run)]).fetchone()[0])
            details['missing_count']=missing_by_day[day] if dataset=='daily' else 0
            db.execute('UPDATE dataset_date_audit SET status=?,details=? WHERE curation_run_id=?',
                       [audit_status,json.dumps(details),str(run)])
        # Append audit evidence; never overwrite an earlier inspection.
        report=root/f'data/private/phase1c1/{batch_id}/dq-{generation}-{digest(summary)[:16]}.json'
        if not report.exists():atomic_new_file(report,lambda p:p.write_bytes(canonical_json(dict(summary=summary,private=private))))
        if summary['error_count']==0:db.execute("UPDATE slice_batch SET status='REVIEWED' WHERE batch_id=?",[str(batch_id)])
        return summary
