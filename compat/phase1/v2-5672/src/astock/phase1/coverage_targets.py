"""Source-bound coverage obligations with explicit known and unknown denominators."""
from collections import Counter
from datetime import timedelta
from astock.phase1 import domains
from astock.phase1.core import day,digest,instant,require,file_hash,stamp

PROTOCOL='PHASE1_COVERAGE_TARGET_V2'


def target(rows, *, start=None,end=None,as_of=None,taxonomies=None,goals=None):
    dated=[r['event_date'] for r in rows if r['dataset']=='trade_cal']
    start=start or min(dated,default=None);end=end or max(dated,default=None)
    as_of=as_of or max((r['retrieved_at'] for r in rows),default=stamp())
    known,conflicts=domains.known_versions(rows,as_of)
    value=dict(protocol=PROTOCOL,start=start,end=end,as_of=as_of,
        facts_hash=digest(rows),dependencies=sorted({r['source_object'] for r in rows}),
        taxonomies=taxonomies if taxonomies is not None else sorted({r['payload']['classification_version'] for r in known if r['dataset']=='industry_membership'}),
        goals=goals or [],scope='SOURCE_EVIDENCED_EPISODES_ONLY_NOT_FULL_UNIVERSE',denominator_license=False)
    value['target_hash']=digest(value)
    return value


def evaluate(rows,t):
    value=dict(t);h=value.pop('target_hash',None)
    require(value.get('protocol')==PROTOCOL and digest(value)==h,'COVERAGE_TARGET_CHANGED')
    require(value['facts_hash']==digest(rows) and value['dependencies']==sorted({r['source_object'] for r in rows}), 'COVERAGE_TARGET_STALE')
    for ref in value.get('evidence_refs',[]):require(file_hash(__import__('pathlib').Path(ref['path']))==ref['sha256'],'COVERAGE_TARGET_EVIDENCE_CHANGED')
    at=value['as_of'];known,conflicts=domains.known_versions(rows,at)
    obligations=[];unknown=[dict(domain='security',reason='FULL_HISTORICAL_UNIVERSE_DENOMINATOR_UNKNOWN')]
    if value['start'] and value['end']:
        first,last=day(value['start']),day(value['end']);require(first<=last,'COVERAGE_TARGET_RANGE')
        episodes=[r for r in known if r['dataset']=='listing_episodes']
        for i in range((last-first).days+1):
            date=(first+timedelta(days=i)).isoformat()
            for venue in sorted({r['payload']['exchange'] for r in episodes}):
                calendars=[r for r in known if r['dataset']=='trade_cal' and r['event_date']==date and r['payload']['exchange']==venue]
                if len(calendars)!=1 or any(r['dataset']=='trade_cal' and r['event_date']==date and r['payload']['exchange']==venue for r in conflicts):
                    unknown.append(dict(domain='calendar',venue=venue,event_date=date,reason='CIVIL_SESSION_DENOMINATOR_UNCERTIFIED'));continue
                if calendars[0]['payload']['is_open']!=1:continue
                for ep in [r for r in episodes if r['payload']['exchange']==venue and domains.active(r,date)]:
                    sid,eid=ep['payload']['security_id'],ep['payload']['episode_id']
                    mappings=[r for r in known if r['dataset']=='security_identifiers' and r['payload']['security_id']==sid and r['payload']['episode_id']==eid and r['payload']['source']=='TUSHARE' and domains.active(r,date)]
                    resolutions=[domains.resolve(rows,r['payload']['identifier'],date,at,source='TUSHARE',dataset='daily') for r in mappings]
                    if len(mappings)!=1 or len(resolutions)!=1 or resolutions[0]['status']!='RESOLVED':
                        unknown.append(dict(domain='security',security_id=sid,episode_id=eid,venue=venue,event_date=date,reason='LISTING_NATIVE_SCOPE_UNCERTIFIED'));continue
                    native=mappings[0]['payload']['identifier']
                    for ds in ('daily','daily_basic','adj_factor','stk_limit'):
                        obligations.append(dict(dataset=ds,entity=native,event_date=date,security_id=sid,episode_id=eid,venue=venue))
                    for kind in ('RISK_WARNING','SUSPENSION'):
                        obligations.append(dict(dataset='security_status',entity=sid,event_date=date,security_id=sid,episode_id=eid,venue=venue,state_type=kind))
                    for taxonomy in value['taxonomies']:
                        obligations.append(dict(dataset='industry_membership',entity=sid,event_date=date,security_id=sid,episode_id=eid,venue=venue,classification_version=taxonomy))
                    obligations.append(dict(dataset='rule_history',entity=None,event_date=date,security_id=sid,episode_id=eid,venue=venue,board=ep['payload']['board']))
    else:unknown.append(dict(domain='market',reason='CALENDAR_RANGE_UNKNOWN'))
    for domain,reason in [('financial','REPORT_PERIOD_AND_VINTAGE_SCHEDULE_UNKNOWN'),('industry','FULL_TAXONOMY_INTERVAL_DENOMINATOR_UNKNOWN'),('status','SPARSE_EVENT_ABSENCE_IS_NOT_NORMAL'),('rule','FULL_HISTORICAL_RULE_DENOMINATOR_UNKNOWN')]:
        unknown.append(dict(domain=domain,reason=reason))
    obligations+=value['goals']
    require(len({digest(o) for o in obligations})==len(obligations),'COVERAGE_TARGET_DUPLICATE')
    results=[]
    for goal in obligations:
        ds=goal['dataset'];date=goal['event_date'];entity=goal.get('entity')
        # A named archived vintage is an inventory goal, not the latest report.
        # Keep the target's knowledge ceiling even when a deadline is later.
        cutoff=min((at,goal.get('known_by',at)),key=instant)
        pool=[r for r in rows if r['dataset']==ds and (entity is None or r['entity']==entity)]
        # Episode is a target dimension; only explicit-episode facts carry it.
        fields=['state_type','classification_version','report_type','comp_type','ann_date','f_ann_date','vintage_status']
        if ds in ('security_status','security_identifiers','listing_episodes'):fields.append('episode_id')
        for field in fields:
            if field in goal:pool=[r for r in pool if r['payload'].get(field)==goal[field]]
        if goal.get('source_object'):pool=[r for r in pool if r['source_object']==goal['source_object']]
        if ds=='rule_history':pool=[r for r in pool if r['payload']['exchange']==goal['venue'] and r['payload']['board'] in ('*',goal['board'])]
        candidates,scoped_conflicts=domains.known_versions(pool,cutoff)
        if ds in ('industry_membership','security_status','rule_history'):candidates=[r for r in candidates if domains.active(r,date)]
        else:candidates=[r for r in candidates if r['event_date']==date]
        scoped_known=known if cutoff==at else domains.known_versions(rows,cutoff)[0]
        statuses=[]
        if ds=='rule_history':
            statuses=[r for r in scoped_known if r['dataset']=='security_status' and r['entity']==goal['security_id'] and r['payload']['state_type']=='RISK_WARNING' and domains.active(r,date)]
            if len(statuses)==1:
                states=('*',statuses[0]['payload']['state_value'])
                candidates=[r for r in candidates if r['payload']['state'] in states]
                scoped_conflicts=[r for r in scoped_conflicts if r['payload']['state'] in states]
        reason=None;state='observed' if candidates else 'missing'
        conflict_rows=[r for r in scoped_conflicts if r['event_date']==date or domains.active(r,date)]
        if len(candidates)>1 or conflict_rows:state='duplicate_conflict'
        if not candidates and not conflict_rows and ds=='daily':
            sparse=[r for r in scoped_known if r['dataset']=='suspend_d' and r['entity']==entity and r['event_date']==date]
            suspended=[r for r in sparse if r['payload']['suspend_type']=='S' and r['payload']['suspend_timing'] is None]
            if len(suspended)==1 and not any(r['payload']['suspend_type']=='R' for r in sparse):state='source_backed_not_applicable';reason='FULL_DAY_SUSPENSION_SOURCE'
        if ds=='rule_history':
            if len(statuses)!=1:state='uncertified';reason='RULE_STATUS_UNKNOWN_OR_CONFLICT'
            elif not candidates and not conflict_rows:reason='RULE_STATE_SCOPE_MISSING'
        if ds=='security_status' and not candidates:state='uncertified';reason='MISSING_STATE_NOT_NORMAL'
        results.append(dict(goal,state=state,reason=reason,observed_versions=len(candidates)))
    counts=Counter(r['state'] for r in results)
    dimensions=Counter((r['dataset'],r['event_date'][:4],r.get('venue','UNKNOWN'),r.get('security_id','UNKNOWN'),r.get('episode_id','UNKNOWN'),r['state']) for r in results)
    return dict(target=t,target_hash=h,expected=len(results),**{k:counts.get(k,0) for k in ('observed','missing','duplicate_conflict','uncertified','source_backed_not_applicable')},unknown_denominators=unknown,obligations=results,
        dimensions=[dict(dataset=d,year=y,venue=v,security_id=s,episode_id=e,state=k,count=n) for (d,y,v,s,e,k),n in sorted(dimensions.items())],target_scope_certified=False,research_admitted=False)
