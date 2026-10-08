"""Offline approval-descriptor domains. Never transport or author approvals."""
from pathlib import Path

from astock.data.full_backfill_v1 import BackfillError, FILES, DESTINATION, logical_id, validate_plan
from astock.data.reconstruction import checksum
from astock.data.raw_validation import sha256
from astock.data.admission_metadata_live import strict_json


def descriptor_hash(descriptors: list[dict]) -> str:
    ids = [d['request']['member_id'] for d in descriptors]
    if len(ids) != len(set(ids)):
        raise BackfillError('DUPLICATE_APPROVAL_DESCRIPTOR')
    return checksum(sorted(descriptors, key=lambda d:d['request']['member_id']))


def validate_application(root: Path, application: dict, plan: dict) -> dict:
    validate_plan(root, plan)
    inventory = application['inventory']
    candidates = application['candidates']; hold = application['hold']
    if (application['execution_license'] is not False or application['approved_at'] is not None
            or application['review_ref'] is not None or application['budget'] != 29
            or len(inventory)!=36 or len(candidates)!=29 or len(hold)!=7):
        raise BackfillError('ACQUISITION_PARTITION_INVALID')
    for name, descriptors in [('inventory',inventory),('candidates',candidates),('hold',hold)]:
        if application[name+'_descriptor_hash'] != descriptor_hash(descriptors):
            raise BackfillError('APPROVAL_DESCRIPTOR_HASH_CHANGED')
    ids = lambda ds:{d['request']['member_id'] for d in ds}
    if ids(candidates)&ids(hold) or ids(candidates)|ids(hold)!=ids(inventory):
        raise BackfillError('ACQUISITION_PARTITION_INVALID')
    if sorted(candidates+hold,key=lambda d:d['request']['member_id'])!=sorted(inventory,key=lambda d:d['request']['member_id']):
        raise BackfillError('INVENTORY_DESCRIPTOR_DRIFT')
    if (plan['budget']!=29 or plan['requests']!=[d['request'] for d in candidates]
            or application['runtime_membership_hash']!=checksum(plan['requests'])
            or application['runtime_plan_hash']!=checksum(plan)):
        raise BackfillError('RUNTIME_APPROVAL_SCOPE_DRIFT')
    descriptor = plan['approval_descriptors']
    if (descriptor is None or descriptor['descriptor_hash'] != application['candidates_descriptor_hash']
            or strict_json((root / descriptor['path']).read_bytes()) != candidates):
        raise BackfillError('PLAN_APPROVAL_DESCRIPTOR_DRIFT')
    count={}
    for d in inventory:
        m=d['request']; p=m['params']; venue=p['exchange']; start=p['start_date']; end=p['end_date']
        count[venue]=count.get(venue,0)+1
        expected_hold = venue=='BSE' or venue=='SZSE' and start=='20130101'
        if (d['group']=='HOLD')!=expected_hold or d['execution_license'] is not False:
            raise BackfillError('HOLD_SCOPE_INVALID')
        if not expected_hold and m['completeness_evidence'] is None:
            raise BackfillError('CANDIDATE_COMPLETENESS_RULE_REQUIRED')
        if m['member_id']!=logical_id(m) or d['max_attempts']!=1 or d['call_start_spacing_seconds']!=1.25:
            raise BackfillError('DESCRIPTOR_WIRE_DRIFT')
        if d['wire']!=dict(endpoint='https://api.tushare.pro',method='POST',api_name=m['dataset'],params=p,fields=','.join(m['fields'])):
            raise BackfillError('DESCRIPTOR_WIRE_DRIFT')
        if d['storage_paths']!={n:f"{DESTINATION}/{m['member_id']}/{n}" for n in FILES}:
            raise BackfillError('DESCRIPTOR_STORAGE_DRIFT')
        if start=='20121201':
            if venue not in ('SSE','SZSE') or end!='20121231':raise BackfillError('LOOKBACK_SCOPE_DRIFT')
        elif end != ('20260930' if start=='20260101' else start[:4]+'1231'):
            raise BackfillError('ANNUAL_SCOPE_DRIFT')
    if count!={'SSE':15,'SZSE':15,'BSE':6}:
        raise BackfillError('VENUE_INVENTORY_DRIFT')
    return dict(status='VALID_PROPOSED_NOT_LICENSED',candidates=29,hold=7,actual_calendar_certified=0)


def validate_references(root: Path, value) -> int:
    """File bytes are checked separately from both semantic domains."""
    count=0
    if isinstance(value,dict):
        if {'path','sha256'}<=value.keys():
            p=root/value['path']
            if not p.is_file() or sha256(p)!=value['sha256'] or 'bytes' in value and p.stat().st_size!=value['bytes']:
                raise BackfillError('ACTIVE_FILE_REFERENCE_CHANGED')
            count+=1
        for v in value.values():count+=validate_references(root,v)
    elif isinstance(value,list):
        for v in value:count+=validate_references(root,v)
    return count
