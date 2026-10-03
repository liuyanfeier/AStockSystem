"""New bindings may reference preserved approved episodes; no real approval."""
import copy
from datetime import timedelta
from uuid import uuid4

import pytest

from astock.data.admission_delta import import_delta
from astock.data.reconstruction import checksum,load_resolver
from astock.data.provider_identity import canonical_resolver_payload
from astock.data.warehouse_lock import warehouse_connection
from test_resolver_time_integrity import make_store,NOW


def test_existing_plus_delta_close_reopen_and_repeat_preserves_old_metadata(tmp_path):
    env=make_store(tmp_path)
    old=canonical_resolver_payload(env['resolver'])
    binding=env['resolver'].bindings[0]
    new=binding.model_copy(update=dict(binding_id=uuid4(),binding_version=2,
        supersedes_binding_id=binding.binding_id,decision_at=NOW+timedelta(days=1),
        available_at=NOW+timedelta(days=1),approval_ref='synthetic-independent-delta'))
    delta=dict(episodes=[],codes=[],bindings=[new.model_dump(mode='json')])
    approval=env['context'].approval.model_copy(update=dict(review_ref=new.approval_ref,
        approved_at=new.decision_at,approved_case_set_hash=checksum(delta)))
    with warehouse_connection(env['path']) as db:
        result=import_delta(env['root'],db,delta,approval)
        assert result['status']=='IMPORTED'
        merged=canonical_resolver_payload(load_resolver(db))
        assert merged['episodes']==old['episodes'] and merged['official_codes']==old['official_codes']
        assert next(b for b in merged['provider_bindings'] if b['binding_id']==str(binding.binding_id))==old['provider_bindings'][0]
    with warehouse_connection(env['path']) as db:
        assert import_delta(env['root'],db,delta,approval)['status']=='ALREADY_VALID'
        assert canonical_resolver_payload(load_resolver(db))==merged
        changed=copy.deepcopy(delta);changed['bindings'][0]['native_identifier']='000002.SZ'
        changed_approval=approval.model_copy(update={'approved_case_set_hash':checksum(changed)})
        with pytest.raises(ValueError,match='conflicts'):import_delta(env['root'],db,changed,changed_approval)
        partial=copy.deepcopy(delta);partial['bindings'].append(dict(partial['bindings'][0],binding_id=str(uuid4())))
        partial_approval=approval.model_copy(update={'approved_case_set_hash':checksum(partial)})
        with pytest.raises(ValueError,match='Partial'):import_delta(env['root'],db,partial,partial_approval)
        with pytest.raises(ValueError,match='exact approval'):import_delta(env['root'],db,changed,approval)


def test_delta_bad_observation_does_not_insert_or_retime_old_resolver(tmp_path):
    env=make_store(tmp_path);binding=env['resolver'].bindings[0]
    new=binding.model_copy(update=dict(binding_id=uuid4(),binding_version=2,
        supersedes_binding_id=binding.binding_id,decision_at=NOW+timedelta(days=1),
        available_at=NOW+timedelta(days=1),approval_ref='synthetic-delta',
        observations=(binding.observations[0].model_copy(update={'raw_row_number':999}),)))
    delta=dict(episodes=[],codes=[],bindings=[new.model_dump(mode='json')])
    approval=env['context'].approval.model_copy(update=dict(review_ref=new.approval_ref,approved_at=new.decision_at,approved_case_set_hash=checksum(delta)))
    with warehouse_connection(env['path']) as db:
        before=canonical_resolver_payload(load_resolver(db))
        with pytest.raises(ValueError,match='ordinal differs'):import_delta(env['root'],db,delta,approval)
        assert canonical_resolver_payload(load_resolver(db))==before
