"""Explicit additive upgrade: caller owns deployment approval; no on-open backfill."""

import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from astock.data.raw_validation import require, rows_dict
from astock.data.receipt_integrity import (VALIDATOR_VERSION, batch_requests, binding_schema_exists,
                                         check_binding, frozen_context, validate_slice_batch,
                                         validate_slice_receipt)


def register_completion(root: Path, db, request: dict, *, verification_sha: str,
                        context=None, purpose: str = 'FINALIZE'):
    """Run inside the owner's transaction; never trust a caller-supplied proof."""
    require(bool(re.fullmatch('[0-9a-f]{40}', verification_sha)), 'VERIFICATION_COMMIT_REQUIRED')
    require(binding_schema_exists(db), 'BINDING_SCHEMA_REQUIRED')
    proof = validate_slice_receipt(root, db, request, context=context, require_binding=False)
    existing = db.execute('SELECT count(*) FROM slice_receipt_completion_binding WHERE batch_id=? AND ordinal=?',
                          [str(request['batch_id']), request['ordinal']]).fetchone()[0]
    if existing:
        check_binding(db, proof)
        return proof
    fields = proof.binding_fields()
    now = datetime.now(timezone.utc)
    db.execute('INSERT INTO slice_receipt_completion_binding VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
               [*fields.values(), verification_sha, now])
    db.execute('INSERT INTO slice_receipt_validation_audit VALUES (?,?,?,?,?,?,?,?,?,?,?)',
               [str(uuid4()), str(request['batch_id']), request['ordinal'], purpose, 'VALID',
                'EXACT_COMPLETION', VALIDATOR_VERSION, verification_sha, now, proof.evidence_hash, 1])
    check_binding(db, proof)
    return proof


def apply_receipt_integrity_upgrade(root: Path, db, *, verification_sha: str) -> dict:
    """007 + validated bindings + audit + version in ONE transaction.

    Not called by generic migrate(), CLI audit, or existing-batch capture. G1 uses
    only synthetic/isolated databases; G3 requires approved backup/copy deployment.
    """
    require(bool(re.fullmatch('[0-9a-f]{40}', verification_sha)), 'VERIFICATION_COMMIT_REQUIRED')
    require(db.execute('SELECT max(version) FROM schema_version').fetchone()[0] in (6, 7),
            'UPGRADE_BASE_VERSION')
    db.execute('BEGIN TRANSACTION')
    try:
        version = db.execute('SELECT max(version) FROM schema_version').fetchone()[0]
        tables = db.execute("SELECT count(*) FROM information_schema.tables WHERE table_name IN ('slice_receipt_completion_binding','slice_receipt_validation_audit')").fetchone()[0]
        require((version == 7 and tables == 2) or (version == 6 and tables == 0), 'UPGRADE_SCHEMA_CONFLICT')
        batches = rows_dict(db, 'SELECT batch_id FROM slice_batch ORDER BY batch_id', [])
        contexts = {}
        # Validate historical evidence before any DDL/DML; no guessed repair.
        for batch in batches:
            batch_id = batch['batch_id']
            context = frozen_context(root, db, batch_id)
            contexts[batch_id] = context
            validate_slice_batch(root, db, batch_id, context=context, complete=False,
                                 require_binding=version == 7)
        if version == 6:
            db.execute((root / 'sql/007_slice_receipt_integrity.sql').read_text())
            for batch in batches:
                batch_id = batch['batch_id']
                for request in batch_requests(db, batch_id):
                    if request['status'] == 'COMPLETE':
                        register_completion(root, db, request, verification_sha=verification_sha,
                                            context=contexts[batch_id], purpose='UPGRADE')
            # Acceptance repeated before publishing schema_version7.
            for batch in batches:
                proofs = validate_slice_batch(root, db, batch['batch_id'], complete=False, require_binding=False,
                                              context=contexts[batch['batch_id']])
                for proof in proofs:
                    check_binding(db, proof)
            db.execute("INSERT INTO schema_version(version,migration_id,description) VALUES (7,'007_slice_receipt_integrity','Exact receipt binding and append-only validation history')")
        db.execute('COMMIT')
        return dict(schema_version=7, result='ALREADY_VALID' if version == 7 else 'UPGRADED',
                    batches_checked=len(batches))
    except Exception:
        db.execute('ROLLBACK')
        raise
