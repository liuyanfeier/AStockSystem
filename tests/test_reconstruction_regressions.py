"""F1–F3 end-to-end regressions: temporary synthetic six-dataset stores only."""
import hashlib, json, shutil
from pathlib import Path
from collections import Counter
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4
import duckdb
import pytest
from astock.data.raw_writer import migrate, RawWriter
from astock.data.audit import RequestParams
from astock.data.tushare_client import ProviderTable, TushareClient
from astock.data.receipt_migration import apply_receipt_integrity_upgrade
from astock.data.provider_identity import ListingEpisode, ExchangeCode, ProviderBinding, SourceObservation
from astock.data.curation import load_curation_specs
from astock.data.reconstruction import Approval, Context, Input, checksum, apply_reconstruction_schema, import_approved_cases, load_resolver, specs_hash, register_context, start_generation, publish_output, complete_generation, select_complete, compare_generations, converted
from astock.data.reconstruction_dq import load_policy, evidence_hash, audit_complete_generation
ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)
DAY = date(2025, 5, 6)
OBS = NOW - timedelta(hours=1)

def build(tmp_path, days=1, factor_values=None, day_offsets=None, factor_scope=None, context_days=None, duplicate_factor=False):
    root = tmp_path / str(uuid4())
    root.mkdir()
    for name in ('sql', 'config', 'docs'):
        shutil.copytree(ROOT / name, root / name)
    db = duckdb.connect(':memory:')
    migrate(db, root)
    apply_receipt_integrity_upgrade(root, db, verification_sha='a' * 40)
    ep = ListingEpisode(episode_id=uuid4(), security_id='synthetic-dq-security', venue='SZSE', asset_type='STK', valid_from=date(2000, 1, 1), retrieved_at=NOW, available_at=NOW, evidence_ids=('synthetic-proof',), approval_ref='synthetic-independent-review')
    code = ExchangeCode(code_id=uuid4(), episode_id=ep.episode_id, identifier='000001.SZ', valid_from=ep.valid_from, available_at=NOW, evidence_ids=('synthetic-code',), approval_ref=ep.approval_ref)
    factor_ep = ep.model_copy(update={'episode_id':uuid4(),'security_id':'synthetic-other'})
    factor_code = code.model_copy(update={'code_id':uuid4(),'episode_id':factor_ep.episode_id,'identifier':'000002.SZ'})
    offsets = day_offsets or list(range(days))
    sessions = [dict(venue='SZSE', episode_id=str(ep.episode_id), event_date=DAY + timedelta(days=offsets[n]), previous_session=DAY + timedelta(days=offsets[n] - 1), certified=True, evidence_venue='SZSE', evidence_ref='synthetic-calendar') for n in range(days)]
    evidence = dict(sessions=sessions, reference_exceptions=[], bse_transitions=[], source_dispositions=[])
    approval = Approval(resolver_protocol="R2_RESOLVER_UTC_INSTANT_V2", time_integrity_addendum_hash=hashlib.sha256((ROOT / "docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md").read_bytes()).hexdigest(), correction_addendum_hash=hashlib.sha256((root / 'docs/remediation/phase1c1/r2-a-design-v1-addendum-3.md').read_bytes()).hexdigest(), review_ref=ep.approval_ref, reviewed_sha='a' * 40, approved_at=NOW, design_hash=hashlib.sha256((root / 'docs/remediation/phase1c1/r2-a-design-v1.md').read_bytes()).hexdigest(), policy_hash=load_policy(root)[1], approved_case_set_hash=checksum(dict(episodes=[], codes=[], bindings=[])), dq_evidence_hash=evidence_hash(evidence), publication_addendum_hash=hashlib.sha256((root / 'docs/remediation/phase1c1/r2-a-design-v1-addendum-1.md').read_bytes()).hexdigest(), disposition_addendum_hash=hashlib.sha256((root / 'docs/remediation/phase1c1/r2-a-design-v1-addendum-2.md').read_bytes()).hexdigest())
    apply_reconstruction_schema(root, db, approval)
    inputs = []
    scopes = {}
    specs = load_curation_specs(root, spec_version='v2')
    for n in range(days):
        day = DAY + timedelta(days=offsets[n])
        close = 10.0 if n == 0 else 11.0
        pre_close = 10.0 if n < 2 else 11.0
        for spec in specs:
            dataset = spec.dataset
            run = uuid4()
            db.execute("INSERT INTO ingestion_run(run_id,source,dataset,mode,started_at,status,code_commit,config_hash,provider_client_version) VALUES (?,'tushare',?,'AUDIT',?,'RUNNING',?,?,'1.0.0')", [run, dataset, OBS, 'a' * 40, 'b' * 64])
            fields = [f.source_column for f in spec.fields]
            base = {f.source_column: dict(string='synthetic', date32=day.strftime('%Y%m%d'), float64=10.0, int64=1)[f.logical_type] for f in spec.fields}
            base.update(open=close, high=12.0, low=9.0, ts_code='000001.SZ', asset_type='STK', exchange='SZSE', close=close, pre_close=pre_close, pct_chg=0.0, change=0.0, adj_factor=1.0)
            if dataset == 'adj_factor':
                value = 1.0 if factor_values is None else factor_values[n]
                base['adj_factor'] = value
                if factor_scope=='identity':base['ts_code']='000002.SZ'
                if factor_scope == 'event':
                    base['trade_date'] = (day - timedelta(days=1)).strftime('%Y%m%d')
            items = [] if dataset in ('stock_st', 'suspend_d') or (dataset == 'adj_factor' and factor_values is not None and (value == 'MISSING')) else [[base[f] for f in fields]]
            if duplicate_factor and dataset=='adj_factor':items=items*2
            raw = RawWriter(root, db).write(run, dataset, 0, ProviderTable(fields=fields, items=items, retrieved_at=OBS), RequestParams(trade_date=day))
            RawWriter(root, db).sidecar(run, dataset)
            inputs.append(Input(request_id=checksum((dataset, day)), raw_object_id=raw.object_id, dataset=dataset, raw_hash=raw.sha256, raw_schema_hash=raw.schema_hash, row_count=len(items), is_output=True))
            for ordinal in range(len(items)):
                scopes.setdefault(dataset, []).append(SourceObservation(raw_object_id=raw.object_id, raw_row_number=ordinal, event_date=day - timedelta(days=1) if dataset == 'adj_factor' and factor_scope == 'event' else day))
    bindings = [ProviderBinding(binding_id=uuid4(), binding_version=1, dataset=dataset, native_identifier='000002.SZ' if dataset=='adj_factor' and factor_scope=='identity' else '000001.SZ', episode_id=factor_ep.episode_id if dataset=='adj_factor' and factor_scope=='identity' else ep.episode_id, representation_kind='EVENT_NATIVE', observations=tuple(observations), first_observed_at=OBS, decision_at=NOW, available_at=NOW, evidence_ids=('synthetic-capture',), decision_status='APPROVED', approval_ref=ep.approval_ref) for (dataset, observations) in scopes.items()]
    cases = dict(episodes=[ep.model_dump(),factor_ep.model_dump()] if factor_scope=='identity' else [ep.model_dump()], codes=[code.model_dump(),factor_code.model_dump()] if factor_scope=='identity' else [code.model_dump()], bindings=[b.model_dump() for b in bindings])
    approval = approval.model_copy(update={'approved_case_set_hash': checksum(cases)})
    import_approved_cases(root, db, cases, approval)
    context = Context(resolver_protocol=approval.resolver_protocol, time_integrity_addendum_hash=approval.time_integrity_addendum_hash, parent_batch_id=uuid4(), parent_generation=0, parent_identity_hash='b' * 64, parent_plan_hash='c' * 64, resolver_hash=load_resolver(db).snapshot_hash, specs_hash=specs_hash(root), policy_hash=approval.policy_hash, design_hash=approval.design_hash, dq_evidence_hash=approval.dq_evidence_hash, publication_addendum_hash=approval.publication_addendum_hash, disposition_addendum_hash=approval.disposition_addendum_hash, correction_addendum_hash=approval.correction_addendum_hash, knowledge_as_of=NOW, implementation_sha='a' * 40, approval=approval, inputs=tuple(inputs[:6 * context_days] if context_days is not None else inputs), fixture_only=True)
    cid = register_context(root, db, context, allow_fixture=True)
    gid = start_generation(db, cid, allow_fixture=True)
    for item in context.inputs:
        publish_output(root, db, cid, gid, item.request_id, allow_fixture=True)
    complete_generation(root, db, cid, gid, allow_fixture=True)
    return dict(episode=ep, root=root, db=db, cid=cid, gid=gid, approval=approval, evidence=evidence, bindings=bindings, context=context, inputs=inputs)

def audit(env, cid=None, gid=None):
    return audit_complete_generation(env['root'], env['db'], cid or env['cid'], gid or env['gid'], evidence=env['evidence'], allow_fixture=True)

def observations(env, result):
    return [json.loads(r[0]) for r in env['db'].execute('SELECT payload FROM reconstruction_finding_observation WHERE audit_id=?', [result['audit_id']]).fetchall()]

def daily_quality(env, result):
    return {next((i.raw_object_id for i in env['inputs'] if i.request_id == request)): status for (request, status) in env['db'].execute('SELECT request_id,local_status FROM reconstruction_output_quality WHERE audit_id=?', [result['audit_id']]).fetchall() if any((i.request_id == request and i.dataset == 'daily' for i in env['inputs']))}

@pytest.mark.parametrize('offsets,values,expected', [([0], ['MISSING'], 'MISSING_DAILY_FACTOR'), ([0], [None], 'INVALID_DAILY_FACTOR'), ([0], [0.0], 'INVALID_DAILY_FACTOR'), ([0], [-1.0], 'INVALID_DAILY_FACTOR'), ([0], [1.0], None), ([0, 1], ['MISSING', 1.0], 'MISSING_DAILY_FACTOR'), ([0, 3], [1.0, 'MISSING'], 'MISSING_DAILY_FACTOR'), ([0, 3], [1.0, 1.0], None)])
def test_each_daily_requires_factor_even_without_pair(tmp_path, offsets, values, expected):
    env = build(tmp_path, days=len(offsets), factor_values=values, day_offsets=offsets)
    try:
        result = audit(env)
        findings = observations(env, result)
        actual = [f for f in findings if f['rule'].endswith('DAILY_FACTOR')]
        daily = [i for i in env['inputs'] if i.dataset == 'daily']
        if expected:
            bad = next((n for (n, value) in enumerate(values) if value == 'MISSING' or value is None or value <= 0))
            assert len(actual) == 1 and actual[0]['rule'] == expected and actual[0]['blocking']
            assert actual[0]['event_date'] == (DAY + timedelta(days=offsets[bad])).isoformat()
            assert actual[0]['raw_object_id'] == str(daily[bad].raw_object_id) and actual[0]['raw_row_number'] == 0
            assert daily_quality(env, result)[daily[bad].raw_object_id] == 'BLOCKED'
            assert result['local_status'] == result['batch_gate_status'] == 'BLOCKED'
        else:
            assert not actual and result['local_status'] == result['batch_gate_status'] == 'PASS'
            assert set(daily_quality(env, result).values()) == {'PASS'}
        if offsets == [0, 3]:
            assert result['causal']['certified_pairs'] == 0
    finally:
        env['db'].close()

@pytest.mark.parametrize('scope',['event','identity'])
def test_factor_from_wrong_scope_cannot_satisfy_daily(tmp_path,scope):
    env = build(tmp_path, factor_scope=scope)
    try:
        result = audit(env)
        assert any((f['rule'] == 'MISSING_DAILY_FACTOR' for f in observations(env, result)))
        assert result['batch_gate_status'] == 'BLOCKED'
    finally:
        env['db'].close()

def publish_context(env, context):
    cid = register_context(env['root'], env['db'], context, allow_fixture=True)
    gid = start_generation(env['db'], cid, allow_fixture=True)
    for item in context.inputs:
        publish_output(env['root'], env['db'], cid, gid, item.request_id, allow_fixture=True)
    complete_generation(env['root'], env['db'], cid, gid, allow_fixture=True)
    return (cid, gid)


def test_duplicate_factors_block_daily_without_last_row_wins(tmp_path):
    env=build(tmp_path,duplicate_factor=True)
    try:
        result=audit(env)
        assert {f['rule'] for f in observations(env,result)}=={'DUPLICATE_OUTPUT_KEY','AMBIGUOUS_DAILY_FACTOR'}
        assert set(daily_quality(env,result).values())=={'BLOCKED'}
        assert result['batch_gate_status']=='BLOCKED'
    finally:env['db'].close()


@pytest.mark.parametrize('value',[None,0,-1,float('nan'),float('inf'),float('-inf')])
def test_nonfinite_and_nonpositive_factor_never_valid(value):
    from astock.data.reconstruction_dq import valid_factor
    assert not valid_factor(value)

def test_actual_bad_pair_scope_and_prefix_stability(tmp_path):
    env = build(tmp_path, days=4, context_days=3)
    try:
        result = audit(env)
        first = observations(env, result)
        assert result['causal']['causal_mismatch'] == result['causal']['factor_mismatch'] == 1
        assert {f['rule'] for f in first} == {'CAUSAL_RETURN_MISMATCH', 'FACTOR_RETURN_MISMATCH'}
        daily = [i for i in env['inputs'] if i.dataset == 'daily']
        assert daily_quality(env, result) == {daily[0].raw_object_id: 'PASS', daily[1].raw_object_id: 'BLOCKED', daily[2].raw_object_id: 'PASS'}
        for f in first:
            assert f['event_date'] == '2025-05-07' and f['raw_object_id'] == str(daily[1].raw_object_id) and (f['raw_row_number'] == 0)
            assert f['previous_source'] == dict(event_date='2025-05-06', raw_object_id=str(daily[0].raw_object_id), raw_row_number=0, episode_id=str(env['episode'].episode_id))
        extended = env['context'].model_copy(update={'inputs': tuple(env['inputs'])})
        (cid, gid) = publish_context(env, extended)
        later = audit(env, cid, gid)
        assert observations(env, later) == first
        assert daily_quality(env, later)[daily[3].raw_object_id] == 'PASS'
    finally:
        env['db'].close()

def test_old_and_new_context_coexist_after_approved_successor(tmp_path):
    env = build(tmp_path)
    try:
        old = next((b for b in env['bindings'] if b.dataset == 'daily'))
        later = NOW + timedelta(days=1)
        new = old.model_copy(update=dict(binding_id=uuid4(), binding_version=2, supersedes_binding_id=old.binding_id, decision_at=later, available_at=later))
        episode=env['episode'].model_copy(update={'episode_id':uuid4(),'security_id':'later-new-member','valid_from':DAY+timedelta(days=1),'available_at':later,'retrieved_at':later})
        code=ExchangeCode(code_id=uuid4(),episode_id=episode.episode_id,identifier='000003.SZ',valid_from=episode.valid_from,available_at=later,evidence_ids=('synthetic-later-code',),approval_ref=env['approval'].review_ref)
        cases = dict(episodes=[episode.model_dump()], codes=[code.model_dump()], bindings=[new.model_dump()])
        approval = env['approval'].model_copy(update={'approved_case_set_hash': checksum(cases), 'approved_at': later})
        import_approved_cases(env['root'], env['db'], cases, approval)
        context = env['context'].model_copy(update={'resolver_hash': load_resolver(env['db']).snapshot_hash, 'knowledge_as_of': later, 'approval': approval})
        (cid, gid) = publish_context(env, context)
        for (ctx, generation) in ((env['cid'], env['gid']), (cid, gid)):
            assert len(select_complete(env['root'], env['db'], ctx, generation, allow_fixture=True)[1]) == 6
            assert audit(env, ctx, generation)['batch_gate_status'] == 'PASS'
        item = next((i for i in env['inputs'] if i.dataset == 'daily'))
        assert converted(env['root'], env['db'], env['context'], item)[0].to_pylist()[0]['binding_id'] == str(old.binding_id)
        assert converted(env['root'], env['db'], context, item)[0].to_pylist()[0]['binding_id'] == str(new.binding_id)
        (_, rebuild) = publish_context(env, env['context'])
        assert compare_generations(env['root'], env['db'], env['cid'], env['gid'], rebuild, allow_fixture=True)['logical_schema_source_match']
    finally:
        env['db'].close()

@pytest.mark.parametrize('tamper', ['episode', 'code', 'binding', 'observation', 'membership', 'payload', 'missing_snapshot'])
def test_pinned_records_and_membership_tamper_rejected(tmp_path, tamper):
    env = build(tmp_path)
    try:
        db = env['db']
        if tamper == 'episode':
            db.execute("UPDATE listing_episode SET security_id='tampered' WHERE episode_id=?", [env['episode'].episode_id])
        elif tamper == 'code':
            db.execute('UPDATE official_exchange_code SET evidence_ids=\'["tampered"]\'')
        elif tamper == 'binding':
            db.execute('UPDATE provider_native_binding SET evidence_ids=\'["tampered"]\'')
        elif tamper == 'observation':
            db.execute('DELETE FROM provider_binding_observation WHERE binding_id=?', [env['bindings'][0].binding_id])
        elif tamper == 'missing_snapshot':
            db.execute('DELETE FROM derivation_resolver_snapshot')
        else:
            payload = json.loads(db.execute('SELECT payload FROM derivation_resolver_snapshot').fetchone()[0])
            if tamper == 'membership':
                payload['provider_bindings'].pop()
            else:
                payload['episodes'][0]['security_id'] = 'tampered'
            db.execute('UPDATE derivation_resolver_snapshot SET payload=?', [json.dumps(payload)])
        with pytest.raises(ValueError):
            select_complete(env['root'], db, env['cid'], env['gid'], allow_fixture=True)
        with pytest.raises(ValueError):
            audit(env)
    finally:
        env['db'].close()
