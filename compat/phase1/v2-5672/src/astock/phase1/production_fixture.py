"""Explicit TEST-root production-shaped rehearsal; never legal source/approval."""
from copy import deepcopy
from pathlib import Path
import shutil
import httpx
from pydantic import SecretStr
from astock.phase1 import PROTOCOL,acquisition as a,contracts as c,fixtures as f,pipeline as p
from astock.phase1.core import PRODUCTION,digest,encoded,file_hash,publish,require,strict_json


def approval_bytes(root,name,text):
    path=root/'test-evidence'/name;path.parent.mkdir(parents=True,exist_ok=True);publish(path,text.encode())
    return dict(path=str(path.relative_to(root)),sha256=file_hash(path))


def licenses(root,destination,plan):
    review=dict(protocol=PROTOCOL,namespace='PRODUCTION',root=str(root.resolve()),destination=str(destination.resolve()),
        plan_hash=digest(plan),pins=plan['pins'],legacy_hash=plan['legacy_hash'],budget=plan['budget'],execution_license=True,
        implementation_sha='TEST_ONLY_NOT_A_GIT_RELEASE',reviewer='TEST_ONLY_SYNTHETIC_REVIEWER',review_ref='TEST_ONLY',approved_at='2025-05-30T00:00:00Z',test_only=True,
        evidence=approval_bytes(root,'capture-review.txt','TEST ONLY, synthetic capture review, no actual license.'))
    human=dict(execution_license=True,source='DIRECT_USER',instruction='TEST ONLY synthetic human license',authorized_at='2025-05-31T00:00:00Z',test_only=True,
        review_hash=digest(review),evidence=approval_bytes(root,'capture-human.txt','TEST ONLY, no actual human runtime approval.'))
    return review,human


def rehearsal(repository: Path,root: Path,*,fault=lambda stage:None):
    require(not root.exists(),'FRESH_TEST_ROOT_REQUIRED')
    root.mkdir(parents=True)
    from astock.paths import get_project_root
    require(root.resolve()!=get_project_root().resolve(),'TEST_LICENSE_CANONICAL_ROOT_FORBIDDEN')
    for name in a.pins(repository):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repository/name,path)
    registry=strict_json((repository/'config/phase1/frozen-v1.json').read_bytes())
    for name in registry['pins']:
        path=root/registry['archive']/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repository/registry['archive']/name,path)
    shutil.copyfile(repository/'sql/offline/phase1_integrated_v1.sql',root/'sql/offline/phase1_integrated_v1.sql')
    publish(root/'TEST_ONLY_PHASE1.json',encoded(dict(namespace='TEST_PRODUCTION_SHAPE',root=str(root.resolve()))))
    dest=root/PRODUCTION
    members,payloads,packages=f.sample_inputs(root)
    # Production captures have observed-time knowledge unless separately admitted.
    for m in members:m['metadata'].pop('knowledge',None)
    baseline=dict(records=[],original_paths={},original_hashes={})
    plan=a.make_plan(root,dest,members,baseline)
    review,human=licenses(root,dest,plan)
    calls=[]
    def handler(q):
        w=strict_json(q.content);calls.append(w['api_name'])
        return httpx.Response(200,content=encoded(payloads[(w['api_name'],encoded(w['params']))]))
    result=a.run_batch(root,dest,plan,baseline,token=SecretStr('closed-TEST-PRODUCTION'),approval=review,human=human,
        transport=httpx.MockTransport(handler),clock=f.FixtureClock(),fault=fault)
    require(result['status']=='RAW_BATCH_VALID','PRODUCTION_SHAPED_CAPTURE_FAILED')
    # All purported official documents below are explicit synthetic TEST material.
    body_ref=approval_bytes(root,'synthetic-official-document.txt','TEST ONLY VERSION EVIDENCE, not an official historical statement.')
    source=root/'test-evidence/document-source.json'
    publish(source,encoded(dict(url='https://www.sse.com.cn/TEST_ONLY_NOT_REAL',http_status=200,complete_body=True,body_hash=body_ref['sha256'],
        body_bytes=(root/body_ref['path']).stat().st_size,retrieved_at='2025-05-30T00:00:00Z',test_only=True)))
    evidence_ref=dict(**body_ref,source_path=str(source.relative_to(root)),source_hash=file_hash(source))
    policy=dict(namespace='TEST_ONLY',version_specific_vintage='SYNTHETIC_APPROVED_VERSION')
    with a.store(root,dest,read_only=True) as db:
        for descriptor in p.inputs(root,dest,db):
            if descriptor['request']['dataset'] in c.FINANCIAL:
                member=deepcopy(descriptor['request']);response=strict_json(Path(descriptor['body_path']).read_bytes())
                rows=c.decode(root,member,encoded(response))['rows'];at=(rows[0].get('f_ann_date') or rows[0]['ann_date'])
                member['metadata']['knowledge']=f.proof(__import__('astock.phase1.core',fromlist=['day']).day(at).isoformat()+'T01:00:00Z')
                packages.append(dict(request=member,response=response,retrieved_at='2025-06-02T00:00:00Z',raw_reference=dict(kind='CAPTURE',body_path=descriptor['body_path'],body_hash=descriptor['body_hash'],source_path=descriptor['source_path'],source_hash=descriptor['source_hash'])))
    for package in packages:
        package.update(namespace='PRODUCTION',evidence='REVIEWED_EVIDENCE_BATCH',evidence_refs=[evidence_ref],retrieved_at='2025-06-02T00:00:00Z')
        proof=package['request'].get('metadata',{}).get('knowledge')
        if proof:proof.update(namespace='APPROVED_POLICY',policy_hash=digest(policy),approval_ref='TEST_ONLY_FACT',evidence_hash=body_ref['sha256'])
    fact_review=dict(protocol='PHASE1_FACT_ADMISSION_V1',namespace='PRODUCTION',root=str(root.resolve()),destination=str(dest.resolve()),
        packages_hash=digest(sorted(packages,key=digest)),pins=a.pins(root),implementation_sha='TEST_ONLY_NOT_A_GIT_RELEASE',execution_license=True,
        reviewer='TEST_ONLY',review_ref='TEST_ONLY_FACT',approved_at='2025-05-30T00:00:00Z',policy=policy,test_only=True,
        evidence=approval_bytes(root,'fact-review.txt','TEST ONLY synthetic fact review, no production adoption.'))
    fact_human=dict(execution_license=True,source='DIRECT_USER',instruction='TEST ONLY synthetic fact authorization',authorized_at='2025-05-31T00:00:00Z',review_hash=digest(fact_review),test_only=True,
        evidence=approval_bytes(root,'fact-human.txt','TEST ONLY synthetic human fact approval.'))
    p.import_evidence(root,dest,packages,fixture=False,approval=fact_review,human=fact_human)
    built=p.build(root,dest)
    before=file_hash(dest/'catalog.duckdb')
    first=p.build(root,root/'derived-a',source_destination=dest);second=p.build(root,root/'derived-b',source_destination=dest)
    require(first['logical_content_hash']==second['logical_content_hash']==built['logical_content_hash'],'PRODUCTION_SHAPED_REBUILD_MISMATCH')
    queried=p.query(root,root/'derived-a','S1','2025-05-15','2025-05-15T10:00:00Z')
    require(len(queried['domains']['financial'])==4,'PRODUCTION_SHAPED_FINANCIAL_QUERY_FAILED')
    coverage=p.coverage(root,root/'derived-a')
    require(p.build(root,root/'derived-a')['status']=='ALREADY_VALID' and file_hash(dest/'catalog.duckdb')==before,'PRODUCTION_SOURCE_CHANGED')
    # A genuine append-only correction, then source-driven increment on both targets.
    member=c.request(root,'security_status',{},metadata=dict(knowledge=dict(f.proof('2025-06-03T00:00:00Z'),namespace='APPROVED_POLICY',
        policy_hash=digest(policy),approval_ref='TEST_ONLY_FACT',evidence_hash=body_ref['sha256'])))
    correction=dict(namespace='PRODUCTION',request=member,response=f.response(member,[f.row(root,'security_status',security_id='S1',episode_id='E1',
        state_type='RISK_WARNING',state_value='ST',exchange='SZSE',valid_from='20250106',valid_to=None,evidence_source='TEST_ONLY_CORRECTION')]),
        retrieved_at='2025-06-04T00:00:00Z',evidence='REVIEWED_EVIDENCE_BATCH',evidence_refs=[evidence_ref])
    correction_review=dict(fact_review,packages_hash=digest([correction]))
    correction_human=dict(fact_human,review_hash=digest(correction_review))
    with a.store(root,dest,read_only=True) as db:old_generations=db.execute('SELECT * FROM p1_generation ORDER BY generation_hash').fetchall()
    p.import_evidence(root,dest,[correction],fixture=False,approval=correction_review,human=correction_human)
    appended=p.build(root,dest)
    changed=p.build(root,root/'derived-a',source_destination=dest)
    changed_b=p.build(root,root/'derived-b',source_destination=dest)
    require(changed['logical_content_hash']==changed_b['logical_content_hash']==appended['logical_content_hash'],'CORRECTION_REBUILD_MISMATCH')
    require(p.build(root,root/'derived-a')['status']=='ALREADY_VALID','CORRECTION_IDEMPOTENCE_FAILED')
    early=p.query(root,root/'derived-a','S1','2025-05-15','2025-06-02T00:00:00Z')
    late=p.query(root,root/'derived-a','S1','2025-05-15','2025-06-04T00:00:00Z')
    require(next(r for r in early['domains']['status'] if r['dataset']=='security_status')['payload']['state_value']=='NORMAL' and
            next(r for r in late['domains']['status'] if r['dataset']=='security_status')['payload']['state_value']=='ST','CORRECTION_CUTOFF_FAILED')
    with a.store(root,dest,read_only=True) as db:
        require(all(row in db.execute('SELECT * FROM p1_generation').fetchall() for row in old_generations),'OLD_GENERATION_CHANGED')
        p.verify_generation_inputs(root,dest,db)
    return dict(status='CLOSED_TEST_PRODUCTION_SHAPE_VALID',synthetic_test_root=str(root),actual_market_API=0,original_SQL_writes=0,
        real_approval_created=False,closed_mock_calls=len(calls),build=built,rebuild_a=first,rebuild_b=second,
        financial_query=queried,coverage=coverage,correction_increment=changed,correction_cutoffs_preserved=True,old_generations_preserved=True,source_bytes_unchanged=True,execution_license=False)
