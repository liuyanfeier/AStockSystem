"""Explicit future signed offline fact batches; never author production approvals."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from astock.phase1 import acquisition
from astock.phase1.core import PRODUCTION, digest, file_hash, instant, require, safe_path, strict_json


def authorize(root: Path, destination: Path, packages: list[dict], approval: dict | None,
              human: dict | None, *, runtime=True) -> dict:
    require(destination.resolve() == (root / PRODUCTION).resolve(), 'CANONICAL_FACT_DESTINATION')
    require(isinstance(approval, dict) and isinstance(human, dict), 'MATCHED_FACT_POLICY_LICENSE_REQUIRED')
    expected = dict(protocol='PHASE1_FACT_ADMISSION_V1', namespace='PRODUCTION', root=str(root.resolve()),
                    destination=str(destination.resolve()), packages_hash=digest(sorted(packages, key=digest)), pins=acquisition.pins(root) if runtime else approval.get('pins'))
    from astock.phase1 import versions
    versions.validate(root,expected['pins'])
    require(all(approval.get(k) == v for k, v in expected.items()), 'FACT_APPROVAL_SCOPE_CHANGED')
    testing=bool(approval.get('test_only'))
    if testing:
        from astock.phase1.authorization import test_scope
        test_scope(root,approval)
    sha = 'TEST_ONLY' if testing else subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    require(not runtime or testing or sha == approval.get('implementation_sha') and not subprocess.check_output(['git', 'status', '--porcelain'], cwd=root), 'CLEAN_REVIEWED_SHA_REQUIRED')
    if approval.get('test_only'):
        from astock.phase1.authorization import test_scope
        test_scope(root,approval)
        require(human.get('test_only') is True,'TEST_LICENSE_NAMESPACE')
    require(approval.get('execution_license') is True and approval.get('reviewer') and approval.get('review_ref')
            and isinstance(approval.get('policy'), dict), 'INDEPENDENT_FACT_POLICY_REQUIRED')
    require(human.get('execution_license') is True and human.get('source') == 'DIRECT_USER'
            and human.get('review_hash') == digest(approval) and human.get('instruction'), 'ACTUAL_HUMAN_REQUIRED')
    require(instant(approval['approved_at']) <= instant(human['authorized_at']) <= datetime.now(timezone.utc), 'FACT_APPROVAL_TIME')
    for value in (approval, human):
        ev = value.get('evidence')
        require(isinstance(ev, dict) and set(ev) == {'path', 'sha256'}, 'ACTUAL_LICENSE_BYTES_REQUIRED')
        require(file_hash(safe_path(root, root / ev['path'], exists=True)) == ev['sha256'], 'LICENSE_EVIDENCE_CHANGED')
    for package in packages:
        require(package['namespace'] == 'PRODUCTION' and package['evidence'] == 'REVIEWED_EVIDENCE_BATCH', 'PRODUCTION_FACT_NAMESPACE')
        require(package.get('evidence_refs'), 'FACT_SOURCE_EVIDENCE_REQUIRED')
        for ref in package['evidence_refs']:
            body = safe_path(root, root / ref['path'], exists=True)
            source = safe_path(root, root / ref['source_path'], exists=True)
            require(file_hash(body) == ref['sha256'] and file_hash(source) == ref['source_hash'], 'FACT_SOURCE_CHANGED')
            receipt = strict_json(source.read_bytes())
            url = urlparse(receipt['url'])
            require(url.scheme == 'https' and url.hostname and any(url.hostname == h or url.hostname.endswith('.' + h)
                    for h in ('sse.com.cn', 'szse.cn', 'bse.cn', 'chinaclear.cn', 'tushare.pro'))
                    and url.hostname != 'api.tushare.pro' and not url.username and not url.password, 'OFFICIAL_DOCUMENT_SOURCE_REQUIRED')
            require(receipt['http_status'] == 200 and receipt['complete_body'] is True
                    and receipt['body_hash'] == ref['sha256'] and receipt['body_bytes'] == body.stat().st_size
                    and instant(receipt['retrieved_at']) <= instant(package['retrieved_at']), 'FACT_EVIDENCE_RECEIPT_REQUIRED')
        proof = package['request'].get('metadata', {}).get('knowledge')
        if proof:
            require(proof.get('namespace') == 'APPROVED_POLICY' and proof.get('policy_hash') == digest(approval['policy'])
                    and proof.get('approval_ref') == approval['review_ref']
                    and proof.get('evidence_hash') in {r['sha256'] for r in package['evidence_refs']}, 'VERSION_SPECIFIC_POLICY_REQUIRED')
    return dict(approval_ref=approval['review_ref'], approved_knowledge_policy_hash=digest(approval['policy']),
                approval_hash=digest(approval), approval=approval, human=human, batch_object_ids=sorted(digest(p) for p in packages))
