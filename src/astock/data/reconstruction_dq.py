"""Frozen R2 DQ semantics: observations, evidence and admission are separate."""

import hashlib
import json
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

from astock.data.receipt_integrity import digest,serial
from astock.data.slice_dq import causal_audit


def load_policy(root: Path):
    path=root/'config/dq/r2-v1.json'
    manifest=json.loads((root/'docs/remediation/phase1c1/r2-a-design-v1-manifest.json').read_text())
    value=path.read_bytes();checksum=hashlib.sha256(value).hexdigest()
    if checksum!=manifest['digests']['config/dq/r2-v1.json']:
        raise ValueError('DQ policy differs from frozen design')
    policy=json.loads(value)
    if policy['price_tolerance']!=0.011 or policy['causal_tolerance_percentage_points']!=0.011 or policy['null_imputation']:
        raise ValueError('Fixed audit semantics changed')
    return policy,checksum


def finding(rule,*,dataset,event_date,raw_object_id=None,raw_row_number=None,
            episode_id=None,security_id=None,venue=None,severity='ERROR',blocking=True,
            decision='EVIDENCE_REQUIRED',evidence_ids=(),approval_ref=None,details=None):
    if (raw_object_id is None)!=(raw_row_number is None) or (raw_row_number is not None and (type(raw_row_number)is not int or raw_row_number<0)):
        raise ValueError('Finding source must be an exact zero-based raw row')
    if raw_object_id is None and episode_id is None:
        raise ValueError('Finding needs source row or episode key')
    key=dict(rule=rule,dataset=dataset,event_date=event_date,raw_object_id=raw_object_id,
             raw_row_number=raw_row_number,episode_id=episode_id,security_id=security_id,venue=venue)
    return dict(finding_key=digest(serial(key)),**key,severity=severity,blocking=blocking,decision=decision,
                evidence_ids=list(evidence_ids),approval_ref=approval_ref,details=details or {})


def local_status(findings):
    return 'BLOCKED' if any(f['severity']=='ERROR' for f in findings) else ('PARTIAL' if findings else 'PASS')


def batch_status(findings):
    return 'BLOCKED' if any(f['blocking'] for f in findings) else ('PARTIAL' if findings else 'PASS')


def session_basis(*,venue,episode_id,event_date,sessions):
    record=sessions.get((venue,str(episode_id),event_date))
    if record:
        previous=record['previous_session']
        if previous>=event_date:
            raise ValueError('Calendar previous session must precede event')
        if record.get('certified') and record.get('evidence_ref') and record.get('evidence_venue')==venue:
            return 'CERTIFIED',previous
    sse=sessions.get(('SSE_DIAGNOSTIC',str(episode_id),event_date))
    if sse and sse['previous_session']<event_date:
        return 'PROVISIONAL_SSE_BASIS',sse['previous_session']
    return 'NOT_CERTIFIED',None


def coverage_observation(episode,*,dataset,event_date,bar_observed,suspensions,session,
                         identity_status='RESOLVED'):
    observation='OBSERVED_BAR' if bar_observed else 'NO_BAR'
    base=dict(dataset=dataset,event_date=event_date,episode_id=str(episode.episode_id),security_id=episode.security_id,
              venue=episode.venue)
    flags=[]
    def add(rule,**kw):flags.append(finding(rule,**base,**kw))
    if identity_status!='RESOLVED':
        add('UNRESOLVED_COVERAGE_IDENTITY');disposition='EVIDENCE_REQUIRED'
    elif not episode.contains(event_date):
        if bar_observed:
            add('BAR_OUTSIDE_APPROVED_EPISODE',decision='CONFLICT');disposition='CONFLICT'
        else:disposition='VERIFIED_OUTSIDE_EPISODE'
    elif episode.asset_type=='UNKNOWN':
        add('UNKNOWN_ASSET');disposition='EVIDENCE_REQUIRED'
    elif episode.asset_type!='STK' or episode.venue=='OTHER':disposition='VERIFIED_OUT_OF_SCOPE'
    else:
        types={s['suspend_type'] for s in suspensions}
        full=any(s['suspend_type']=='S' and (s.get('suspend_timing')=='全天' or s.get('whole_day_certified') is True)
                 for s in suspensions)
        if {'S','R'}<=types:
            add('SUSPENSION_RESUME_CONFLICT',severity='REVIEW',decision='CONFLICT')
        if full and bar_observed:
            add('FULL_DAY_SUSPENSION_WITH_BAR',severity='REVIEW',decision='CONFLICT')
        if bar_observed:disposition='VERIFIED_IN_SCOPE'
        elif full and 'R' not in types:disposition='EXPLAINED_FULL_DAY_SUSPENSION'
        else:
            add('UNEXPLAINED_MISSING_BAR');disposition='UNEXPLAINED_MISSING'
        if episode.provider_delist_date and event_date>=episode.provider_delist_date:
            add('UNCLASSIFIED_DELIST_METADATA',severity='REVIEW',blocking=not bar_observed)
        if session!='CERTIFIED':
            add('SESSION_NOT_CERTIFIED',details={'basis':session})
            if not bar_observed:disposition='SESSION_NOT_CERTIFIED'
    return dict(**base,observation=observation,identity_status=identity_status,disposition=disposition,
                universe_basis='HISTORICAL_EPISODE',venue_session_basis=session,findings=flags,
                local_status=local_status(flags),batch_gate_status=batch_status(flags))


def reference_check(left,right,*,dataset,event_date,raw_object_id,raw_row_number,episode_id,
                    field='pre_close',approved_exceptions=()):
    base=dict(dataset=dataset,event_date=event_date,raw_object_id=raw_object_id,raw_row_number=raw_row_number,
              episode_id=str(episode_id))
    if left is None or right is None:
        matches=[e for e in approved_exceptions if e.get('decision')=='APPROVED_NOT_APPLICABLE'
                 and e.get('approval_ref') and e.get('evidence_ids') and e.get('field')==field
                 and all(str(e.get(k))==str(v) for k,v in base.items())]
        if len(matches)>1:
            return [finding('REFERENCE_EXCEPTION_CONFLICT',**base,decision='CONFLICT')]
        if matches:
            return [finding('REFERENCE_NOT_APPLICABLE',**base,severity='REVIEW',blocking=False,
                            decision='APPROVED_NOT_APPLICABLE',evidence_ids=matches[0]['evidence_ids'],
                            approval_ref=matches[0]['approval_ref'])]
        return [finding('MISSING_REFERENCE_PRICE',**base,details={'field':field})]
    if not all(type(v) in (int,float) and math.isfinite(v) for v in (left,right)):
        return [finding('INVALID_NUMERIC_REFERENCE',**base)]
    return [finding('NUMERIC_REFERENCE_MISMATCH',**base)] if abs(left-right)>0.011 else []


def bse_transition(left,right,*,old_code,new_code,switch_date,episode_id,sessions_certified):
    base=dict(dataset='daily',event_date=switch_date,episode_id=str(episode_id),venue='BSE')
    findings=[]
    if left is None or right is None:
        findings.append(finding('BSE_TRANSITION_NOT_OBSERVED',**base,severity='REVIEW',blocking=False))
        return dict(official='NOT_OBSERVED',provider='NOT_OBSERVED',continuity='NOT_OBSERVED',session='NOT_CERTIFIED',findings=findings)
    official=left.exchange_code_at_event==old_code and right.exchange_code_at_event==new_code
    continuity=left.reason is None and right.reason is None and left.security_id==right.security_id and left.episode_id==right.episode_id
    same=left.native_identifier==right.native_identifier
    provider=(not same) or (left.representation_kind==right.representation_kind=='RETROSPECTIVE' and left.binding_id is not None and right.binding_id is not None)
    for good,rule in ((official,'BSE_OFFICIAL_INTERVAL_CONFLICT'),(continuity,'BSE_EPISODE_CONTINUITY_CONFLICT'),(provider,'BSE_NATIVE_REPRESENTATION_CONFLICT')):
        if not good:findings.append(finding(rule,**base,decision='CONFLICT'))
    if not sessions_certified:findings.append(finding('BSE_SESSION_NOT_CERTIFIED',**base))
    return dict(official='VALID' if official else 'CONFLICT',provider='VALID' if provider else 'CONFLICT',
                continuity='VALID' if continuity else 'CONFLICT',session='CERTIFIED' if sessions_certified else 'NOT_CERTIFIED',findings=findings)


def venue_causal_audit(bars,factors,sessions):
    groups=defaultdict(list)
    for b in bars:groups[(b['security_id'],str(b['episode_id']),b['venue'])].append(b)
    totals=dict(certified_pairs=0,provisional_sse_pairs=0,excluded_unknown_pairs=0,
                causal_mismatch=0,factor_mismatch=0,missing_factor_pairs=0)
    all_series=[]
    for (sid,episode,venue),rows in groups.items():
        ordered=sorted(rows,key=lambda r:r['trade_date']);previous={};provisional={}
        for i,row in enumerate(ordered):
            basis,prior=session_basis(venue=venue,episode_id=episode,event_date=row['trade_date'],sessions=sessions)
            if basis=='CERTIFIED':previous[row['trade_date']]=prior
            elif basis=='PROVISIONAL_SSE_BASIS':provisional[row['trade_date']]=prior
            if i and basis=='NOT_CERTIFIED':totals['excluded_unknown_pairs']+=1
        stats,series=causal_audit(ordered,factors,previous)
        diagnostic,_=causal_audit(ordered,factors,provisional)
        totals['certified_pairs']+=stats['adjacent_pairs'];totals['provisional_sse_pairs']+=diagnostic['adjacent_pairs']
        for k in ('causal_mismatch','factor_mismatch','missing_factor_pairs'):totals[k]+=stats[k]
        for s in series:s.update(episode_id=episode,venue=venue)
        all_series.extend(series)
    return totals,all_series


def evidence_hash(evidence):
    """Canonical evidence envelope, ordered independently of caller collection order."""
    if set(evidence)!= {'sessions','reference_exceptions','bse_transitions','source_dispositions'}:
        raise ValueError('Unknown DQ evidence fields')
    return digest(serial({key:sorted(values,key=lambda v:digest(serial(v))) for key,values in evidence.items()}))


def audit_complete_generation(root,db,context_id,generation_id,*,evidence,allow_fixture=False,supersedes=None):
    """Select exactly one complete generation; calculate and append one immutable audit."""
    from uuid import uuid4,UUID
    from datetime import datetime,timezone
    from astock.data.reconstruction import (select_complete,load_resolver,transaction,json_text,raw_capture)
    from astock.data.provider_identity import Resolution
    from astock.data.warehouse_lock import require_writer
    require_writer(db)
    context,outputs=select_complete(root,db,context_id,generation_id,allow_fixture=allow_fixture)
    if evidence_hash(evidence)!=context.dq_evidence_hash:
        raise ValueError('DQ evidence differs from independently approved context')
    # Accept the same canonical JSON envelope after a review artifact round-trip.
    evidence=json.loads(json.dumps(serial(evidence)))
    for section in ('sessions','reference_exceptions','bse_transitions','source_dispositions'):
        for item in evidence[section]:
            for field in ('event_date','previous_session','switch_date','before_date','after_date'):
                if field in item:item[field]=date.fromisoformat(item[field])
    sessions={}
    for record in evidence['sessions']:
        key=(record['venue'],str(record['episode_id']),record['event_date'])
        if key in sessions:raise ValueError('Ambiguous session evidence')
        sessions[key]=record
    dispositions={};used_dispositions=set()
    for d in evidence['source_dispositions']:
        key=(d['dataset'],d['event_date'],str(d['raw_object_id']),d['raw_row_number'])
        if key in dispositions or type(d['raw_row_number'])is not int or d['raw_row_number']<0 or d.get('decision')!='APPROVED_OUT_OF_SCOPE' or d.get('approval_ref')!=context.approval.review_ref or not d.get('case_ref') or not d.get('evidence_ids'):
            raise ValueError('Invalid/ambiguous exact approved source disposition')
        dispositions[key]=d
    findings=[];tables={};output_days={};coverage=[]
    for input,table,quarantine,registration in outputs:
        rows=table.to_pylist()
        manifest=raw_capture(root,db,input.raw_object_id)['manifest']
        params=json.loads(manifest['request_params'])
        event=date.fromisoformat(params['trade_date'])
        output_days[str(input.request_id)]=(input.dataset,event)
        if (input.dataset,event) in tables:raise ValueError('Duplicate dataset/event output')
        tables[(input.dataset,event)]=rows
        for q in quarantine:
            key=(input.dataset,q['event_date'],str(q['raw_object_id']),q['raw_row_number'])
            disposition=dispositions.get(key)
            if disposition:used_dispositions.add(key)
            outside=disposition is not None or q['reason'] in ('PRE_BSE_LEGACY','ASSET_OUT_OF_SCOPE')
            findings.append(finding('IDENTITY_'+q['reason'],dataset=input.dataset,event_date=q['event_date'],
                raw_object_id=q['raw_object_id'],raw_row_number=q['raw_row_number'],
                severity='REVIEW' if outside else 'ERROR',blocking=not outside,
                decision='OUT_OF_SCOPE' if outside else 'EVIDENCE_REQUIRED',
                evidence_ids=disposition['evidence_ids'] if disposition else (),
                approval_ref=disposition['approval_ref'] if disposition else None,
                details={'native':q['provider_identifier'],'approved_disposition':disposition}))
        seen=set()
        for row in rows:
            key=(row['security_id'],row['episode_id'],row['trade_date'])
            if input.dataset=='suspend_d':key+= (row['suspend_type'],row.get('suspend_timing'))
            if key in seen:
                findings.append(finding('DUPLICATE_OUTPUT_KEY',dataset=input.dataset,event_date=row['trade_date'],
                    raw_object_id=row['raw_object_id'],raw_row_number=row['raw_row_number'],episode_id=row['episode_id']))
            seen.add(key)
            if input.dataset=='adj_factor' and (row['adj_factor'] is None or row['adj_factor']<=0):
                findings.append(finding('NONPOSITIVE_FACTOR',dataset=input.dataset,event_date=row['trade_date'],
                    raw_object_id=row['raw_object_id'],raw_row_number=row['raw_row_number'],episode_id=row['episode_id']))
    if set(dispositions)!=used_dispositions:raise ValueError('Approved disposition does not match exact quarantined source')
    resolver=load_resolver(db)
    visible=[e for e in resolver.episodes if e.available_at<=context.knowledge_as_of]
    daily_days=sorted(day for dataset,day in tables if dataset=='daily')
    factors={};bars=[]
    for (dataset,day),rows in tables.items():
        if dataset=='daily':bars.extend(rows)
        if dataset=='adj_factor':
            for r in rows:factors[(r['security_id'],day)]=r['adj_factor']
    for day in daily_days:
        daily={(r['security_id'],r['episode_id']):r for r in tables[('daily',day)]}
        suspend=tables.get(('suspend_d',day),[])
        for episode in visible:
            key=(episode.security_id,str(episode.episode_id))
            basis,_=session_basis(venue=episode.venue,episode_id=episode.episode_id,event_date=day,sessions=sessions)
            observation=coverage_observation(episode,dataset='daily',event_date=day,bar_observed=key in daily,
                suspensions=[s for s in suspend if (s['security_id'],s['episode_id'])==key],session=basis)
            coverage.append(observation);findings.extend(observation['findings'])
        for dataset,field in (('daily_basic','close'),('stk_limit','pre_close')):
            if (dataset,day) not in tables:
                # Synthetic small contexts need not include every market endpoint.
                if not context.fixture_only:raise ValueError('Missing complete dataset/day')
                continue
            other={(r['security_id'],r['episode_id']):r for r in tables[(dataset,day)]}
            for key in daily.keys()|other.keys():
                row=other.get(key) or daily[key]
                base=dict(dataset=dataset,event_date=day,raw_object_id=row['raw_object_id'],
                          raw_row_number=row['raw_row_number'],episode_id=row['episode_id'])
                if key not in daily or key not in other:
                    findings.append(finding('CROSS_DATASET_MISSING_OR_PROVIDER_ONLY',**base,severity='REVIEW',blocking=True))
                else:
                    row=other[key]
                    findings.extend(reference_check(row[field],daily[key][field],**dict(base,
                        raw_object_id=row['raw_object_id'],raw_row_number=row['raw_row_number']),field=field,
                        approved_exceptions=evidence['reference_exceptions']))
    valid_bars=[]
    for r in bars:
        required=('open','high','low','close','pre_close','pct_chg')
        if any(type(r.get(f)) not in (int,float) or not math.isfinite(r[f]) for f in required) or r['close']<=0 or r['pre_close']<=0:
            findings.append(finding('CAUSAL_INPUT_INVALID',dataset='daily',event_date=r['trade_date'],
                raw_object_id=r['raw_object_id'],raw_row_number=r['raw_row_number'],episode_id=r['episode_id']))
        else:valid_bars.append(r)
    stats,series=venue_causal_audit(valid_bars,factors,sessions)
    # Pin aggregate mathematical failures to an explicit episode/date, never an arbitrary missing raw row.
    for (sid,episode,venue),group in _group_bars(valid_bars).items():
        group_stats,_=venue_causal_audit(group,factors,sessions)
        for metric,rule in (('causal_mismatch','CAUSAL_RETURN_MISMATCH'),('factor_mismatch','FACTOR_RETURN_MISMATCH'),
                            ('missing_factor_pairs','MISSING_FACTOR_PAIR')):
            if group_stats[metric]:
                findings.append(finding(rule,dataset='daily',event_date=max(r['trade_date'] for r in group),
                    episode_id=episode,security_id=sid,venue=venue,details={'count':group_stats[metric]}))
    for case in evidence['bse_transitions']:
        episode=str(case['episode_id']);before=case['before_date'];after=case['after_date']
        hits=[[r for r in tables.get(('daily',day),[]) if r['episode_id']==episode] for day in (before,after)]
        if any(len(h)>1 for h in hits):raise ValueError('Ambiguous BSE transition observation')
        def resolution(rows):
            if not rows:return None
            r=rows[0]
            return Resolution(native_identifier=r['ts_code'],reason=None,security_id=r['security_id'],
                episode_id=UUID(r['episode_id']),venue=r['venue'],exchange_code_at_event=r['official_code_at_event'],
                binding_id=UUID(r['binding_id']),binding_available_at=r['binding_available_at'],
                representation_kind=r['representation_kind'])
        certified=all(session_basis(venue='BSE',episode_id=episode,event_date=d,sessions=sessions)[0]=='CERTIFIED'
                      for d in (before,after))
        result=bse_transition(resolution(hits[0]),resolution(hits[1]),old_code=case['old_code'],new_code=case['new_code'],
            switch_date=case['switch_date'],episode_id=episode,sessions_certified=certified)
        findings.extend(result['findings'])
    # Duplicate stable keys with divergent semantics are a conflict, not silently overwritten.
    unique={}
    for f in findings:
        if f['finding_key'] in unique and digest(serial(unique[f['finding_key']]))!=digest(serial(f)):
            raise ValueError('Conflicting stable finding observations')
        unique[f['finding_key']]=f
    findings=sorted(unique.values(),key=lambda f:f['finding_key'])
    audit_id=uuid4();set_hash=digest(serial(findings));local=local_status(findings);gate=batch_status(findings)
    detail=dict(coverage=coverage,causal=stats,series=series,outputs=len(outputs),identity_basis=context.identity_basis,
                availability_basis=context.availability_basis,evidence_hash=context.dq_evidence_hash)
    if supersedes is not None:
        previous=db.execute('SELECT context_id,generation_id,policy_hash FROM reconstruction_quality_audit WHERE audit_id=?',[supersedes]).fetchone()
        if previous is None or tuple(map(str,previous))!=(str(context_id),str(generation_id),context.policy_hash):
            raise ValueError('Supersedes audit must belong to exact context/generation/policy')
    def append():
        db.execute('INSERT INTO reconstruction_quality_audit VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            [audit_id,context_id,generation_id,context.policy_hash,context.implementation_sha,datetime.now(timezone.utc),
             set_hash,local,gate,supersedes,json_text(detail)])
        for f in findings:
            db.execute('INSERT INTO reconstruction_finding_observation VALUES (?,?,?,?,?,?,?)',
                [uuid4(),audit_id,f['finding_key'],f['raw_object_id'],f['raw_row_number'],f['episode_id'],json_text(f)])
        for request,(dataset,day) in output_days.items():
            scoped=[f for f in findings if f['dataset']==dataset and f['event_date']==day]
            db.execute('INSERT INTO reconstruction_output_quality VALUES (?,?,?,?,?)',
                [audit_id,generation_id,request,local_status(scoped),digest(serial(scoped))])
    transaction(db,append)
    return dict(audit_id=str(audit_id),finding_set_hash=set_hash,findings=len(findings),local_status=local,
                batch_gate_status=gate,causal=stats,context_hash=context.context_hash)


def _group_bars(bars):
    groups=defaultdict(list)
    for b in bars:groups[(b['security_id'],b['episode_id'],b['venue'])].append(b)
    return groups


def disposition_ledger(old_findings,new_findings,approved_dispositions=()):
    """Every old stable key survives, even when a new context stops emitting it."""
    new={f['finding_key']:f for f in new_findings}
    approved={}
    for d in approved_dispositions:
        if d['finding_key'] in approved or not d.get('approval_ref') or not d.get('evidence_ids'):
            raise ValueError('Ambiguous/unapproved historical finding disposition')
        approved[d['finding_key']]=d
    ledger=[]
    for f in old_findings:
        key=f['finding_key']
        ledger.append(dict(finding_key=key,old=f,new=new.get(key),
            disposition='REMAINS' if key in new else (approved[key]['decision'] if key in approved else 'EVIDENCE_REQUIRED'),
            approval=approved.get(key)))
    prior={f['finding_key'] for f in old_findings}
    ledger.extend(dict(finding_key=k,old=None,new=f,disposition='NEW_FINDING',approval=None)
                  for k,f in new.items() if k not in prior)
    return ledger
