"""Execution-time authorization evidence; historical review never uses future HEAD."""
from pathlib import Path
from datetime import datetime, timezone
from astock.phase1.core import digest, file_hash, instant, require, safe_path, strict_json


def test_scope(root, approval):
    from astock.paths import get_project_root
    require(root.resolve() != get_project_root().resolve(), 'TEST_LICENSE_CANONICAL_ROOT_FORBIDDEN')
    marker = strict_json(safe_path(root, root/'TEST_ONLY_PHASE1.json', exists=True).read_bytes())
    require(marker == {'namespace':'TEST_PRODUCTION_SHAPE','root':str(root.resolve())} and
            approval.get('test_only') is True, 'TEST_ROOT_MARKER_REQUIRED')


def validate(root, destination, plan, approval, human, *, at=None):
    from astock.phase1 import versions
    require(isinstance(approval,dict) and isinstance(human,dict), 'MATCHED_INDEPENDENT_HUMAN_REQUIRED')
    versions.validate(root, plan['pins'])
    expected = dict(protocol=plan['protocol'], namespace='PRODUCTION', plan_hash=digest(plan),
        root=str(root.resolve()), destination=str(destination.resolve()), pins=plan['pins'],
        legacy_hash=plan['legacy_hash'], budget=plan['budget'])
    require(all(approval.get(k)==v for k,v in expected.items()), 'APPROVAL_SCOPE_CHANGED')
    require(approval.get('execution_license') is True and approval.get('reviewer') and approval.get('review_ref')
            and approval.get('implementation_sha'), 'INDEPENDENT_APPROVAL_REQUIRED')
    require(human.get('execution_license') is True and human.get('review_hash')==digest(approval)
            and human.get('source')=='DIRECT_USER' and human.get('instruction'), 'ACTUAL_HUMAN_REQUIRED')
    require(instant(approval['approved_at']) <= instant(human['authorized_at']) <= instant(at or datetime.now(timezone.utc)), 'AUTHORIZATION_TIME')
    if approval.get('test_only') or human.get('test_only'):
        test_scope(root, approval)
        require(human.get('test_only') is True, 'TEST_LICENSE_NAMESPACE')
    for value in (approval,human):
        ref=value.get('evidence')
        require(isinstance(ref,dict) and set(ref)=={'path','sha256'}, 'ACTUAL_LICENSE_BYTES_REQUIRED')
        require(file_hash(safe_path(root,root/ref['path'],exists=True))==ref['sha256'], 'LICENSE_EVIDENCE_CHANGED')
    for m in plan['members']:
        if m.get('empty_evidence'):
            ref=m.get('metadata',{}).get('empty_policy_evidence')
            require(isinstance(ref,dict) and ref['sha256']==m['empty_evidence']['evidence_hash'] and
                    file_hash(safe_path(root,root/ref['path'],exists=True))==ref['sha256'], 'EMPTY_POLICY_CHANGED')
    return dict(protocol='PHASE1_CAPTURE_AUTHORIZATION_V2', plan_hash=digest(plan),plan=plan,
        approval=approval,human=human,approval_hash=digest(approval),human_hash=digest(human),
        implementation_sha=approval['implementation_sha'],pins=plan['pins'],root=str(root.resolve()),
        destination=str(destination.resolve()),legacy_hash=plan['legacy_hash'],prior_consumption_hash=plan['prior_consumption_hash'])


def retained(root,destination,db,plan_hash):
    row=db.execute('SELECT authorization_hash,payload FROM p1_authorization WHERE plan_hash=?',[plan_hash]).fetchone()
    require(row is not None,'PRODUCTION_AUTHORIZATION_MISSING')
    h,payload=row;record=strict_json(payload.encode());at=record.pop('persisted_at')
    bound=db.execute('SELECT payload FROM p1_plan WHERE plan_hash=?',[plan_hash]).fetchone()
    require(bound is not None and record['plan_hash']==plan_hash and record['plan']==strict_json(bound[0].encode()),'AUTHORIZATION_PLAN_CHANGED')
    checked=validate(root,destination,record['plan'],record['approval'],record['human'],at=at)
    require(record==checked and digest(dict(record,persisted_at=at))==h,'AUTHORIZATION_BINDING_CHANGED')
    return h,dict(record,persisted_at=at)
