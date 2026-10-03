"""Explicit, evidence-pinned reconstruction; never migrates or selects on open.

Callers own a managed exclusive connection. R2-A uses temporary synthetic roots
only; production use additionally needs independently approved artifacts.
"""

import hashlib
import io
import json
import re
from functools import lru_cache
import duckdb
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import AwareDatetime, Field, model_validator

from astock.data.provider_identity import (ImmutableModel, ListingEpisode, ExchangeCode,
                                          ProviderBinding, ProviderResolver, RESOLVER_PROTOCOL,
                                          canonical_resolver_member, canonical_resolver_payload)
from astock.data.raw_validation import rows_dict, safe_file, sha256, validate_raw_run
from astock.data.raw_writer import atomic_new_file
from astock.data.receipt_integrity import digest, serial, validate_slice_batch, frozen_context
from astock.data.slice_curate import cast_field, logical_hash, OUTPUTS
from astock.data.curation import load_curation_specs
from astock.data.probe_audit import canonical_json
from astock.data.warehouse_lock import require_writer


HASH = re.compile(r'[0-9a-f]{64}\Z')
SHA = re.compile(r'[0-9a-f]{40}\Z')


def checksum(value):
    return digest(serial(value))


def now():
    return datetime.now(timezone.utc)


def json_bytes(value):
    return canonical_json(serial(value))


def json_text(value):
    return json_bytes(value).decode()


def transaction(db, action):
    require_writer(db)
    db.execute('BEGIN TRANSACTION')
    try:
        result = action()
        db.execute('COMMIT')
        return result
    except BaseException:
        db.execute('ROLLBACK')
        raise


R2_TABLES = ('listing_episode','official_exchange_code','provider_native_binding','provider_binding_observation',
    'derivation_context','derivation_input','derivation_resolver_snapshot','derivation_generation','derivation_generation_event','derivation_output',
    'derivation_row_quarantine','derivation_complete_manifest','reconstruction_quality_audit',
    'reconstruction_finding_observation','reconstruction_output_quality')


def _schema_structure(db):
    placeholders=','.join('?' for _ in R2_TABLES)
    identities=db.execute(f"""SELECT database_name=current_database(),schema_name,table_name,temporary
        FROM duckdb_tables() WHERE table_name IN ({placeholders}) ORDER BY table_name""",list(R2_TABLES)).fetchall()
    if identities != [(True,'main',name,False) for name in sorted(R2_TABLES)] or db.execute('SELECT current_schema()').fetchone()!=('main',):
        raise ValueError('R2 persistent schema missing/shadowed')
    if db.execute(f'SELECT 1 FROM duckdb_views() WHERE view_name IN ({placeholders})',list(R2_TABLES)).fetchall():
        raise ValueError('R2 schema view shadow')
    columns=db.execute(f"""SELECT table_name,column_name,data_type,is_nullable,column_default FROM duckdb_columns()
        WHERE database_name=current_database() AND schema_name='main' AND table_name IN ({placeholders})
        ORDER BY table_name,column_index""",list(R2_TABLES)).fetchall()
    constraints=db.execute(f"""SELECT table_name,constraint_type,constraint_column_names,expression,
        referenced_table,referenced_column_names FROM duckdb_constraints() WHERE database_name=current_database()
        AND schema_name='main' AND table_name IN ({placeholders})""",list(R2_TABLES)).fetchall()
    return columns,sorted((t,kind,tuple(cols),expr or '',target or '',tuple(refs)) for t,kind,cols,expr,target,refs in constraints)


@lru_cache(maxsize=1)
def _expected_schema():
    from astock.paths import get_project_root
    from astock.data.raw_writer import migrate
    root=get_project_root()
    with duckdb.connect(':memory:') as db:
        migrate(db,root)
        db.execute((root/'sql/007_slice_receipt_integrity.sql').read_text())
        for name in ('008_r2_provider_identity','009_r2_derivation_publication','010_r2_append_only_quality'):
            db.execute((root/'sql'/f'{name}.sql').read_text())
        return _schema_structure(db)


def require_reconstruction_schema(db, *, published=True):
    if _schema_structure(db)!=_expected_schema():raise ValueError('R2 schema constraints/columns differ from reviewed implementation')
    if published:
        expected=[(8,'008_r2_provider_identity'),(9,'009_r2_derivation_publication'),(10,'010_r2_append_only_quality')]
        if db.execute('SELECT version,migration_id FROM schema_version WHERE version>=8 ORDER BY version').fetchall()!=expected:
            raise ValueError('R2 schema versions differ')


class Approval(ImmutableModel):
    review_ref: str = Field(min_length=1)
    reviewed_sha: str
    design_hash: str
    policy_hash: str
    approved_case_set_hash: str
    dq_evidence_hash: str
    publication_addendum_hash: str
    disposition_addendum_hash: str
    correction_addendum_hash: str
    resolver_protocol: Literal['R2_RESOLVER_UTC_INSTANT_V2']
    time_integrity_addendum_hash: str
    approved_at: AwareDatetime

    @model_validator(mode='after')
    def hashes(self):
        if not SHA.fullmatch(self.reviewed_sha) or any(not HASH.fullmatch(h) for h in
                (self.design_hash, self.policy_hash, self.approved_case_set_hash, self.dq_evidence_hash, self.publication_addendum_hash, self.disposition_addendum_hash, self.correction_addendum_hash, self.time_integrity_addendum_hash)):
            raise ValueError('Approval requires exact reviewed SHA and artifact hashes')
        return self


def apply_reconstruction_schema(root, db, approval: Approval):
    """008–010 in one transaction, only after explicit 007 deployment."""
    approval = Approval.model_validate(approval)
    require_writer(db)
    from astock.data.reconstruction_dq import load_policy
    if load_policy(root)[1]!=approval.policy_hash or sha256(root/'docs/remediation/phase1c1/r2-a-design-v1.md')!=approval.design_hash or sha256(root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-1.md')!=approval.publication_addendum_hash:
        raise ValueError('Schema approval differs from reviewed policy/design')
    if sha256(root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-2.md')!=approval.disposition_addendum_hash:
        raise ValueError('Disposition design differs from approval')
    if sha256(root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-3.md')!=approval.correction_addendum_hash:
        raise ValueError('Correction design differs from approval')
    if sha256(root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md')!=approval.time_integrity_addendum_hash:
        raise ValueError('Time integrity design differs from approval')
    from astock.data.receipt_schema import require_integrity_schema
    require_integrity_schema(db)
    versions = db.execute('SELECT version FROM schema_version ORDER BY version').fetchall()
    if versions == [(v,) for v in range(1, 11)]:
        require_reconstruction_schema(db)
        return 'ALREADY_VALID'
    if versions != [(v,) for v in range(1, 8)]:
        raise ValueError('R2 requires exact schema001–007, no partial upgrade')
    def apply():
        for version, name in ((8, '008_r2_provider_identity'), (9, '009_r2_derivation_publication'),
                              (10, '010_r2_append_only_quality')):
            db.execute((root / 'sql' / f'{name}.sql').read_text())
            db.execute('INSERT INTO schema_version(version,migration_id,description) VALUES (?,?,?)',
                       [version, name, 'Explicit approved reconstruction: ' + approval.review_ref])
        require_reconstruction_schema(db)
    transaction(db, apply)
    return 'UPGRADED'


def load_resolver(db):
    def read(table):
        rows = rows_dict(db, f'SELECT * FROM {table} ORDER BY ALL', [])
        for row in rows:
            row['evidence_ids'] = json.loads(row['evidence_ids'])
        return rows
    episodes = read('listing_episode'); codes = read('official_exchange_code')
    bindings = read('provider_native_binding')
    for b in bindings:
        b['observations'] = rows_dict(db, '''SELECT raw_object_id,raw_row_number,event_date
            FROM provider_binding_observation WHERE binding_id=? ORDER BY ALL''', [b['binding_id']])
    return ProviderResolver(episodes, codes, bindings)


def resolver_payload(resolver):
    """Same canonical membership and serialization as ProviderResolver.snapshot_hash."""
    return canonical_resolver_payload(resolver)


def load_context_resolver(db, context):
    """Validate pinned members without admitting any records added after registration."""
    if context.resolver_protocol != RESOLVER_PROTOCOL:
        raise ValueError('Unsupported resolver protocol')
    row=db.execute('''SELECT s.resolver_hash,s.payload FROM derivation_context c
        LEFT JOIN derivation_resolver_snapshot s ON s.context_id=c.context_id
        WHERE c.context_hash=?''',[context.context_hash]).fetchone()
    current=load_resolver(db)
    if row is None:
        # Registration only: a new context must pin the entire current membership.
        if current.snapshot_hash!=context.resolver_hash:raise ValueError('Resolver snapshot changed')
        return current
    if row[0]!=context.resolver_hash or row[1] is None:
        raise ValueError('Missing/changed context resolver snapshot')
    payload=json.loads(row[1])
    if set(payload)!={'episodes','official_codes','provider_bindings'} or checksum(payload)!=context.resolver_hash:
        raise ValueError('Context resolver snapshot hash/membership changed')
    pinned=ProviderResolver(payload['episodes'],payload['official_codes'],payload['provider_bindings'])
    if pinned.snapshot_hash!=context.resolver_hash or resolver_payload(pinned)!=payload:
        raise ValueError('Noncanonical context resolver snapshot')
    for frozen,live,id_field in ((pinned.episodes,current.episodes,'episode_id'),
                                (pinned.codes,current.codes,'code_id'),
                                (pinned.bindings,current.bindings,'binding_id')):
        members={getattr(m,id_field):canonical_resolver_member(m) for m in live}
        for member in frozen:
            if members.get(getattr(member,id_field))!=canonical_resolver_member(member):
                raise ValueError('Pinned resolver member changed/missing')
    return pinned


def raw_capture(root, db, object_id, cache=None):
    key = str(object_id)
    if cache is not None and key in cache:
        return cache[key]
    manifests = rows_dict(db, 'SELECT * FROM raw_object_manifest WHERE object_id=?', [key])
    if len(manifests) != 1:
        raise ValueError('Missing exact raw FK')
    run = rows_dict(db, 'SELECT * FROM ingestion_run WHERE run_id=?', [manifests[0]['run_id']])[0]
    captures = validate_raw_run(root, db, run['run_id'])
    for capture in captures:
        if cache is not None:
            cache[str(capture['manifest']['object_id'])] = capture
    return next(c for c in captures if str(c['manifest']['object_id']) == key)


def import_approved_cases(root, db, case_set, approval: Approval):
    """Only exact reviewed payload; no proposal auto-admission or wildcard joins."""
    approval = Approval.model_validate(approval)
    require_writer(db)
    if sha256(root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md')!=approval.time_integrity_addendum_hash:
        raise ValueError('Time integrity design differs from approval')
    if checksum(case_set) != approval.approved_case_set_hash:
        raise ValueError('Case set differs from independent approval')
    if set(case_set) != {'episodes', 'codes', 'bindings'}:
        raise ValueError('Unknown case set fields')
    episodes = [ListingEpisode.model_validate(e) for e in case_set['episodes']]
    codes = [ExchangeCode.model_validate(c) for c in case_set['codes']]
    bindings = [ProviderBinding.model_validate(b) for b in case_set['bindings']]
    if any(e.approval_ref != approval.review_ref or e.available_at < approval.approved_at for e in episodes):
        raise ValueError('Episode is not approved at its actual knowledge time')
    if any(c.approval_ref != approval.review_ref or c.available_at < approval.approved_at for c in codes):
        raise ValueError('Official code is not approved at its actual knowledge time')
    cache = {}
    for b in bindings:
        observed_at=[]
        if b.decision_status != 'APPROVED' or b.approval_ref != approval.review_ref or b.decision_at < approval.approved_at:
            raise ValueError('Unapproved binding')
        for obs in b.observations:
            capture = raw_capture(root, db, obs.raw_object_id, cache)
            manifest = capture['manifest']; table = capture['arrow']
            if manifest['dataset'] != b.dataset or obs.raw_row_number >= table.num_rows:
                raise ValueError('Binding source dataset or ordinal differs')
            row = table.slice(obs.raw_row_number, 1).to_pylist()[0]
            event = row.get('trade_date')
            event = date.fromisoformat(event) if isinstance(event, str) and '-' in event else (
                datetime.strptime(event, '%Y%m%d').date() if isinstance(event, str) else event)
            if row.get('ts_code') != b.native_identifier or event != obs.event_date:
                raise ValueError('Binding does not match observed capture')
            observed_at.append(manifest['retrieved_at'])
        if b.first_observed_at != min(observed_at):
            raise ValueError('First observation must match earliest exact scoped capture')
    require_reconstruction_schema(db)
    old = load_resolver(db)
    ProviderResolver([*old.episodes, *episodes], [*old.codes, *codes], [*old.bindings, *bindings])
    def insert(table, model, exclude=()):
        row = model.model_dump(exclude=set(exclude))
        fields = list(row)
        values = [json_text(v) if k == 'evidence_ids' else v for k, v in row.items()]
        db.execute(f'INSERT INTO {table}({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})', values)
    def apply():
        for e in episodes: insert('listing_episode', e)
        for c in codes: insert('official_exchange_code', c)
        remaining = list(bindings)
        inserted = {b.binding_id for b in old.bindings}
        while remaining:
            ready = [b for b in remaining if b.supersedes_binding_id is None or b.supersedes_binding_id in inserted]
            if not ready: raise ValueError('Cyclic supersession')
            for b in ready:
                insert('provider_native_binding', b, ('observations',))
                for obs in b.observations:
                    db.execute('INSERT INTO provider_binding_observation VALUES (?,?,?,?)',
                               [b.binding_id, obs.raw_object_id, obs.raw_row_number, obs.event_date])
                remaining.remove(b); inserted.add(b.binding_id)
    transaction(db, apply)
    return load_resolver(db).snapshot_hash


class Input(ImmutableModel):
    request_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    raw_object_id: UUID
    dataset: str
    raw_hash: str
    raw_schema_hash: str
    row_count: int = Field(ge=0)
    is_output: bool


class Context(ImmutableModel):
    parent_batch_id: UUID
    parent_generation: int = Field(ge=0)
    parent_identity_hash: str
    parent_plan_hash: str
    resolver_hash: str
    specs_hash: str
    policy_hash: str
    design_hash: str
    dq_evidence_hash: str
    publication_addendum_hash: str
    disposition_addendum_hash: str
    correction_addendum_hash: str
    resolver_protocol: Literal['R2_RESOLVER_UTC_INSTANT_V2']
    time_integrity_addendum_hash: str
    knowledge_as_of: AwareDatetime
    implementation_sha: str
    approval: Approval
    inputs: tuple[Input, ...] = Field(min_length=1)
    fixture_only: bool = False
    identity_basis: str = 'CURRENT_RECONSTRUCTION'
    availability_basis: str = 'OBSERVED_CAPTURE'

    @model_validator(mode='after')
    def validate_pins(self):
        hashes = [self.parent_identity_hash, self.parent_plan_hash, self.resolver_hash, self.specs_hash,
                  self.policy_hash, self.design_hash, self.dq_evidence_hash, self.publication_addendum_hash, self.disposition_addendum_hash, self.correction_addendum_hash, self.time_integrity_addendum_hash, *[h for i in self.inputs for h in (i.raw_hash, i.raw_schema_hash)]]
        if any(not HASH.fullmatch(h) for h in hashes) or not SHA.fullmatch(self.implementation_sha):
            raise ValueError('Invalid context digest')
        if self.implementation_sha != self.approval.reviewed_sha or self.design_hash != self.approval.design_hash or self.policy_hash != self.approval.policy_hash:
            raise ValueError('Context differs from independent approval')
        if self.dq_evidence_hash != self.approval.dq_evidence_hash or self.publication_addendum_hash != self.approval.publication_addendum_hash or self.disposition_addendum_hash != self.approval.disposition_addendum_hash:
            raise ValueError('Context DQ evidence/addendum differs from approval')
        if self.correction_addendum_hash!=self.approval.correction_addendum_hash:
            raise ValueError('Context correction addendum differs from approval')
        if self.resolver_protocol!=self.approval.resolver_protocol or self.time_integrity_addendum_hash!=self.approval.time_integrity_addendum_hash:
            raise ValueError('Context time integrity protocol/design differs from approval')
        if self.knowledge_as_of < self.approval.approved_at:
            raise ValueError('Context knowledge precedes approval')
        if self.identity_basis != 'CURRENT_RECONSTRUCTION' or self.availability_basis != 'OBSERVED_CAPTURE':
            raise ValueError('Cannot claim historical PIT')
        if len({i.request_id for i in self.inputs}) != len(self.inputs) or len({i.raw_object_id for i in self.inputs}) != len(self.inputs):
            raise ValueError('Duplicate context input')
        if any(i.dataset not in {*OUTPUTS, 'trade_cal'} or i.is_output != (i.dataset in OUTPUTS) for i in self.inputs):
            raise ValueError('Unknown output scope')
        if not self.fixture_only and (len(self.inputs) != 133 or sum(i.is_output for i in self.inputs) != 126):
            raise ValueError('Production requires133 exact inputs/126 outputs')
        if not any(i.is_output for i in self.inputs): raise ValueError('No expected output')
        return self

    @property
    def context_hash(self):
        payload = self.model_dump()
        payload['inputs'] = sorted(payload['inputs'], key=lambda i: str(i['request_id']))
        return checksum(payload)


def specs_hash(root):
    specs = load_curation_specs(root, spec_version='v2')
    return checksum([s.model_dump() for s in sorted(specs, key=lambda s: s.dataset)])


def validate_context(root, db, context: Context):
    context = Context.model_validate(context)
    require_reconstruction_schema(db)
    from astock.data.reconstruction_dq import load_policy
    if load_policy(root)[1] != context.policy_hash or specs_hash(root) != context.specs_hash:
        raise ValueError('Policy/spec input changed')
    if sha256(root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-2.md')!=context.disposition_addendum_hash:
        raise ValueError('Disposition addendum changed')
    design = root / 'docs/remediation/phase1c1/r2-a-design-v1.md'
    if sha256(root / 'docs/remediation/phase1c1/r2-a-design-v1-addendum-1.md') != context.publication_addendum_hash:
        raise ValueError('Publication addendum changed')
    if sha256(design) != context.design_hash:
        raise ValueError('Design snapshot changed')
    if sha256(root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-3.md')!=context.correction_addendum_hash:
        raise ValueError('Correction addendum changed')
    if sha256(root/'docs/remediation/phase1c1/r2-a-design-v1-addendum-4.md')!=context.time_integrity_addendum_hash:
        raise ValueError('Time integrity addendum changed')
    load_context_resolver(db,context)
    cache = {}
    for i in context.inputs:
        obj = raw_capture(root, db, i.raw_object_id, cache)['manifest']
        if (obj['dataset'], obj['sha256'], obj['schema_hash'], obj['row_count']) != (i.dataset, i.raw_hash, i.raw_schema_hash, i.row_count):
            raise ValueError('Frozen raw input changed')
    if not context.fixture_only:
        frozen = frozen_context(root, db, context.parent_batch_id)
        proofs = validate_slice_batch(root, db, context.parent_batch_id, context=frozen)
        from astock.data.slice_capture import identity_state
        if identity_state(db)[0] != context.parent_identity_hash or context.knowledge_as_of < frozen.batch['knowledge_as_of']:
            raise ValueError('Parent identity snapshot/knowledge changed')
        if frozen.batch['identity_snapshot_hash'] != context.parent_identity_hash or frozen.batch['plan_hash'] != context.parent_plan_hash:
            raise ValueError('Parent frozen context changed')
        expected = {(str(p.request['request_id']), str(p.object['object_id'])) for p in proofs}
        if expected != {(str(i.request_id), str(i.raw_object_id)) for i in context.inputs}:
            raise ValueError('R1 request/raw manifest differs')
        parent = rows_dict(db, '''SELECT b.request_id,b.raw_object_id FROM slice_curated_binding b
            WHERE b.batch_id=? AND b.generation=?''', [context.parent_batch_id, context.parent_generation])
        if {(str(r['request_id']), str(r['raw_object_id'])) for r in parent} != {
                (str(i.request_id), str(i.raw_object_id)) for i in context.inputs if i.is_output}:
            raise ValueError('Parent generation is not the exact126 inputs')
    return context


def register_context(root, db, context, *, allow_fixture=False):
    require_writer(db)
    context = validate_context(root, db, context)
    if context.fixture_only and not allow_fixture: raise ValueError('Fixture context cannot enter production')
    existing = db.execute('SELECT context_id,payload FROM derivation_context WHERE context_hash=?', [context.context_hash]).fetchone()
    if existing:
        if Context.model_validate_json(existing[1]).context_hash != context.context_hash: raise ValueError('Corrupt context')
        return existing[0]
    context_id = uuid4()
    snapshot=resolver_payload(load_context_resolver(db,context))
    def register():
        db.execute('INSERT INTO derivation_context VALUES (?,?,?,?,?)',
                   [context_id, context.context_hash, json_text(context.model_dump()), context.fixture_only, now()])
        db.execute('INSERT INTO derivation_resolver_snapshot VALUES (?,?,?)',
                   [context_id,context.resolver_hash,json_text(snapshot)])
        for i in context.inputs:
            db.execute('INSERT INTO derivation_input VALUES (?,?,?,?,?,?,?,?)',
                       [context_id, i.request_id, i.raw_object_id, i.dataset, i.raw_hash, i.raw_schema_hash, i.row_count, i.is_output])
    transaction(db, register)
    return context_id


def get_context(db, context_id):
    row = db.execute('SELECT context_hash,payload FROM derivation_context WHERE context_id=?', [context_id]).fetchone()
    if row is None: raise ValueError('Unknown explicit context')
    context = Context.model_validate_json(row[1])
    if context.context_hash != row[0]: raise ValueError('Context hash mismatch')
    actual = rows_dict(db, 'SELECT request_id,raw_object_id,dataset,raw_hash,raw_schema_hash,row_count,is_output FROM derivation_input WHERE context_id=? ORDER BY request_id', [context_id])
    if checksum(actual) != checksum(sorted([i.model_dump() for i in context.inputs], key=lambda i: str(i['request_id']))):
        raise ValueError('Context input registration changed')
    load_context_resolver(db,context)
    return context


def generation_state(db, context_id, generation_id):
    header = db.execute('SELECT context_id FROM derivation_generation WHERE generation_id=?', [generation_id]).fetchone()
    if header is None or str(header[0]) != str(context_id): raise ValueError('Unknown explicit generation')
    states = db.execute('SELECT sequence,state FROM derivation_generation_event WHERE generation_id=? ORDER BY sequence', [generation_id]).fetchall()
    permitted = ([('PLANNED')], ['PLANNED', 'BUILDING'], ['PLANNED', 'BUILDING', 'COMPLETE'], ['PLANNED', 'BUILDING', 'BLOCKED'])
    if [s[0] for s in states] != list(range(len(states))) or [s[1] for s in states] not in permitted:
        raise ValueError('Invalid append-only generation history')
    return states[-1][1]


def start_generation(db, context_id, *, allow_fixture=False):
    require_writer(db)
    context = get_context(db, context_id)
    if context.fixture_only and not allow_fixture: raise ValueError('Fixture generation cannot enter production')
    generation = uuid4()
    def start():
        db.execute('INSERT INTO derivation_generation VALUES (?,?,?)', [generation, context_id, now()])
        for sequence, state in enumerate(('PLANNED', 'BUILDING')):
            db.execute('INSERT INTO derivation_generation_event VALUES (?,?,?,?,?)', [generation, sequence, state, now(), '{}'])
    transaction(db, start)
    return generation


def converted(root, db, context, input):
    capture = raw_capture(root, db, input.raw_object_id)
    raw = capture['arrow']; obj = capture['manifest']
    spec = next(s for s in load_curation_specs(root, spec_version='v2') if s.dataset == input.dataset)
    fields = list(spec.arrow_schema()) + [
        pa.field('security_id', pa.string(), nullable=False), pa.field('episode_id', pa.string(), nullable=False),
        pa.field('venue', pa.string(), nullable=False), pa.field('binding_id', pa.string(), nullable=False),
        pa.field('official_code_at_event', pa.string(), nullable=False),
        pa.field('representation_kind', pa.string(), nullable=False),
        pa.field('binding_available_at', pa.timestamp('us', tz='UTC'), nullable=False),
        pa.field('raw_object_id', pa.string(), nullable=False), pa.field('raw_row_number', pa.int64(), nullable=False),
        pa.field('retrieved_at', pa.timestamp('us', tz='UTC'), nullable=False),
        pa.field('available_at', pa.timestamp('us', tz='UTC'), nullable=False)]
    schema = pa.schema(fields, metadata={'output_name': OUTPUTS[input.dataset], 'spec_version': spec.spec_version,
        'identity_basis': 'CURRENT_RECONSTRUCTION', 'availability_basis': 'OBSERVED_CAPTURE',
        'research_usage': spec.research_usage, 'context_hash': context.context_hash})
    resolver = load_context_resolver(db,context); resolved = []; quarantined = []
    for ordinal, source in enumerate(raw.to_pylist()):
        typed = {f.target_column: cast_field(source[f.source_column], f) for f in spec.fields}
        hit = resolver.resolve(provider='tushare', dataset=input.dataset, native_identifier=typed['ts_code'],
            event_date=typed['trade_date'], raw_object_id=input.raw_object_id, raw_row_number=ordinal,
            knowledge_as_of=context.knowledge_as_of, provider_exchange=typed.get('exchange'), provider_asset_type=typed.get('asset_type'))
        if hit.reason:
            quarantined.append(dict(raw_object_id=str(input.raw_object_id), raw_row_number=ordinal,
                provider_identifier=typed['ts_code'], event_date=typed['trade_date'], reason=hit.reason))
        else:
            typed.update(security_id=hit.security_id, episode_id=str(hit.episode_id), venue=hit.venue,
                binding_id=str(hit.binding_id), official_code_at_event=hit.exchange_code_at_event,
                representation_kind=hit.representation_kind, binding_available_at=hit.binding_available_at,
                raw_object_id=str(input.raw_object_id), raw_row_number=ordinal,
                retrieved_at=obj['retrieved_at'], available_at=obj['retrieved_at'])
            resolved.append(typed)
    table = pa.Table.from_pylist(resolved, schema=schema)
    conserve(table, quarantined, input)
    return table, quarantined


def conserve(table, quarantine, input):
    identities = [(r['raw_object_id'], r['raw_row_number']) for r in table.to_pylist()] + [
        (str(r['raw_object_id']), r['raw_row_number']) for r in quarantine]
    if len(identities) != input.row_count or set(identities) != {(str(input.raw_object_id), n) for n in range(input.row_count)}:
        raise ValueError('Source row conservation failure')


def output_bytes(table):
    target = io.BytesIO(); pq.write_table(table, target, compression='zstd')
    return target.getvalue()


def expected_output(context_id, generation_id, input, context, table, quarantine):
    relative = f'data/curated/reconstruction/context_id={context_id}/generation_id={generation_id}/request_id={input.request_id}.parquet'
    value = output_bytes(table)
    lineage = dict(context_id=str(context_id), context_hash=context.context_hash, generation_id=str(generation_id),
        request_id=str(input.request_id), input=input.model_dump(), policy_hash=context.policy_hash,
        specs_hash=context.specs_hash, resolver_hash=context.resolver_hash, implementation_sha=context.implementation_sha,
        logical_hash=logical_hash(table), file_hash=hashlib.sha256(value).hexdigest(),
        schema_hash=hashlib.sha256(table.schema.serialize().to_pybytes()).hexdigest(),
        quarantine=quarantine, identity_basis=context.identity_basis, availability_basis=context.availability_basis)
    return relative, value, json_bytes(lineage), lineage


def new_path(root, relative):
    # Files may not exist yet; reject symlinks in every ancestor before publication.
    root = root.resolve(); path = root
    parts = relative.split('/')
    if not parts or any(p in ('', '.', '..') for p in parts) or '\\' in relative: raise ValueError('Unsafe new path')
    for p in parts:
        path /= p
        if path.is_symlink(): raise ValueError('Symlink publication path')
    if not path.resolve().is_relative_to(root / 'data/curated/reconstruction'): raise ValueError('Unsafe new path')
    return path


def verify_output(root, db, context_id, generation_id, input, context):
    table, quarantine = converted(root, db, context, input)
    relative, value, lineage_bytes, lineage = expected_output(context_id, generation_id, input, context, table, quarantine)
    path = safe_file(root, relative, under='data/curated/reconstruction')
    sidecar = safe_file(root, relative + '.lineage.json', under='data/curated/reconstruction')
    if path.read_bytes() != value or sidecar.read_bytes() != lineage_bytes:
        raise ValueError('Output/orphan differs from independent reconstruction')
    physical = pq.read_table(pa.BufferReader(value))
    if logical_hash(physical) != lineage['logical_hash'] or physical.schema != table.schema:
        raise ValueError('Physical schema/logical hash mismatch')
    registered = rows_dict(db, 'SELECT * FROM derivation_output WHERE generation_id=? AND request_id=?', [generation_id, input.request_id])
    if len(registered) != 1: raise ValueError('Output not registered')
    row = registered[0]
    expected = dict(context_id=context_id, generation_id=generation_id, request_id=input.request_id,
        relative_path=relative, file_hash=lineage['file_hash'], logical_hash=lineage['logical_hash'],
        lineage_hash=hashlib.sha256(lineage_bytes).hexdigest(), schema_hash=lineage['schema_hash'],
        resolved_count=table.num_rows, quarantine_count=len(quarantine))
    if checksum({k: row[k] for k in expected}) != checksum(expected): raise ValueError('Output registration mismatch')
    recorded = rows_dict(db, '''SELECT raw_object_id,raw_row_number,event_date,provider_identifier,reason
        FROM derivation_row_quarantine WHERE generation_id=? AND request_id=? ORDER BY raw_row_number''', [generation_id, input.request_id])
    if checksum(recorded) != checksum(quarantine): raise ValueError('Quarantine registration mismatch')
    conserve(physical, recorded, input)
    return table, quarantine, expected



def block_generation(db, context_id, generation_id, reason):
    """Terminal integrity failure, appended only; injected crash is recoverable."""
    require_writer(db)
    state=generation_state(db,context_id,generation_id)
    if state=='BLOCKED':return 'ALREADY_BLOCKED'
    if state!='BUILDING':raise ValueError('Cannot rewrite complete generation history')
    transaction(db,lambda:db.execute('INSERT INTO derivation_generation_event VALUES (?,?,?,?,?)',
        [generation_id,2,'BLOCKED',now(),json_text({'reason':reason})]))
    return 'BLOCKED'


def publish_output(root, db, context_id, generation_id, request_id, *, allow_fixture=False, fault=None):
    require_writer(db)
    context = validate_context(root, db, get_context(db, context_id))
    if context.fixture_only and not allow_fixture: raise ValueError('Fixture cannot enter production')
    state = generation_state(db, context_id, generation_id)
    if state not in ('BUILDING', 'COMPLETE'): raise ValueError('Generation is blocked')
    matches = [i for i in context.inputs if i.is_output and str(i.request_id) == str(request_id)]
    if len(matches) != 1: raise ValueError('Unexpected output request')
    input = matches[0]
    if db.execute('SELECT count(*) FROM derivation_output WHERE generation_id=? AND request_id=?', [generation_id, request_id]).fetchone()[0]:
        verify_output(root, db, context_id, generation_id, input, context)
        return 'ALREADY_VALID'
    if state == 'COMPLETE': raise ValueError('Complete generation cannot acquire new output')
    table, quarantine = converted(root, db, context, input)
    relative, value, lineage_bytes, lineage = expected_output(context_id, generation_id, input, context, table, quarantine)
    path = new_path(root, relative); sidecar = new_path(root, relative + '.lineage.json')
    for destination, content, point in ((path, value, 'FILE'), (sidecar, lineage_bytes, 'LINEAGE')):
        if destination.exists():
            if destination.read_bytes() != content:
                block_generation(db,context_id,generation_id,'CORRUPT_ORPHAN')
                raise ValueError('Corrupt orphan retained; publication blocked')
        else:
            atomic_new_file(destination, lambda tmp: tmp.write_bytes(content))
        if fault: fault(point)
    def register():
        db.execute('INSERT INTO derivation_output VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            [context_id, generation_id, request_id, relative, lineage['file_hash'], lineage['logical_hash'],
             hashlib.sha256(lineage_bytes).hexdigest(), lineage['schema_hash'], table.num_rows, len(quarantine), now()])
        for row in quarantine:
            db.execute('INSERT INTO derivation_row_quarantine VALUES (?,?,?,?,?,?,?)',
                       [generation_id, request_id, input.raw_object_id, row['raw_row_number'], row['event_date'], row['provider_identifier'], row['reason']])
        if fault: fault('DB')
        verify_output(root, db, context_id, generation_id, input, context)
    transaction(db, register)
    if fault: fault('REGISTERED')
    return 'PUBLISHED'


def complete_generation(root, db, context_id, generation_id, *, allow_fixture=False, fault=None):
    require_writer(db)
    context = validate_context(root, db, get_context(db, context_id))
    if context.fixture_only and not allow_fixture: raise ValueError('Fixture cannot enter production')
    state = generation_state(db, context_id, generation_id)
    if state == 'COMPLETE':
        select_complete(root, db, context_id, generation_id, allow_fixture=allow_fixture)
        return 'ALREADY_VALID'
    if state != 'BUILDING': raise ValueError('Cannot promote blocked generation')
    def promote():
        expected = [i for i in context.inputs if i.is_output]
        registered = db.execute('SELECT request_id FROM derivation_output WHERE generation_id=?', [generation_id]).fetchall()
        if {str(r[0]) for r in registered} != {str(i.request_id) for i in expected}: raise ValueError('Partial generation cannot be COMPLETE')
        manifest = [verify_output(root, db, context_id, generation_id, i, context)[2] for i in sorted(expected, key=lambda i: str(i.request_id))]
        db.execute('INSERT INTO derivation_complete_manifest VALUES (?,?,?,?)', [generation_id, json_text(manifest), checksum(manifest), now()])
        if fault: fault('PROMOTION')
        db.execute('INSERT INTO derivation_generation_event VALUES (?,?,?,?,?)', [generation_id, 2, 'COMPLETE', now(), '{}'])
    transaction(db, promote)
    return 'COMPLETE'


def select_complete(root, db, context_id, generation_id, *, allow_fixture=False):
    context = validate_context(root, db, get_context(db, context_id))
    if context.fixture_only and not allow_fixture: raise ValueError('Fixture cannot enter production DQ')
    if generation_state(db, context_id, generation_id) != 'COMPLETE': raise ValueError('DQ/rebuild requires explicit COMPLETE generation')
    expected = sorted([i for i in context.inputs if i.is_output], key=lambda i: str(i.request_id))
    actual = db.execute('SELECT request_id FROM derivation_output WHERE generation_id=?', [generation_id]).fetchall()
    if {str(r[0]) for r in actual} != {str(i.request_id) for i in expected}: raise ValueError('Complete output membership changed')
    result = [(i, *verify_output(root, db, context_id, generation_id, i, context)) for i in expected]
    manifest = [r[3] for r in result]
    row = db.execute('SELECT manifest,manifest_hash FROM derivation_complete_manifest WHERE generation_id=?', [generation_id]).fetchone()
    if row is None or checksum(json.loads(row[0])) != row[1] or row[1] != checksum(manifest): raise ValueError('Complete manifest changed')
    return context, result


def compare_generations(root, db, context_id, left, right, *, allow_fixture=False):
    _, a = select_complete(root, db, context_id, left, allow_fixture=allow_fixture)
    _, b = select_complete(root, db, context_id, right, allow_fixture=allow_fixture)
    def semantic(rows):
        return {str(i.request_id): dict(raw=i.model_dump(), logical_hash=r['logical_hash'], schema_hash=r['schema_hash'],
                                       quarantine=q) for i, table, q, r in rows}
    if checksum(semantic(a)) != checksum(semantic(b)): raise ValueError('Same-context rebuild mismatch')
    return dict(outputs=len(a), logical_schema_source_match=True, context_hash=get_context(db, context_id).context_hash)
