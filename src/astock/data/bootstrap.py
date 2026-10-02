"""Bounded Phase 1C.0 identity bootstrap. No market-data ingestion runner."""

import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4, uuid5

from astock.data.warehouse_lock import warehouse_connection
import pyarrow.parquet as pq
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from astock.data.audit import RequestParams
from astock.data.contracts import load_contracts
from astock.data.curation import configuration_hash, digest, load_curation_specs, input_manifest_hash
from astock.data.identity import IdentifierHistory, IdentityHistory, is_normalized_ashare_identifier
from astock.data.probe_audit import canonical_json
from astock.data.raw_writer import RawWriter, atomic_new_file, migrate, secret_scan, verify_batch
from astock.data.tushare_client import CLIENT_VERSION, ProviderFailure, TushareClient

# Persisted identity namespace. Changing it requires an explicit identity migration.
IDENTITY_NAMESPACE = UUID('ccebbf83-788c-5e65-bc85-5fc2be681202')
BOOTSTRAP_VERSION = '1.0'
BSE_OPEN = date(2021, 11, 15)
PILOT_SWITCH = date(2025, 5, 6)
GENERAL_SWITCH = date(2025, 10, 9)
AUTHORITY_URLS = (
    'https://www.bse.cn/service/code_mapping.html',
    'https://www.bse.cn/important_news/200025487.html',
    'https://www.bse.cn/important_news/200025603.html',
    'https://www.bse.cn/important_news/200026735.html',
    'https://www.bse.cn/company/introduce.html',
)


class BSEEvidence(BaseModel):
    """Reviewed direct-page extract, kept private; never populated from search snippets."""
    model_config = ConfigDict(extra='forbid', frozen=True, hide_input_in_errors=True)
    urls: tuple[str, ...]
    retrieved_at: AwareDatetime
    pairs: list[tuple[str, str]] = Field(min_length=1)
    pilot_pairs: list[tuple[str, str]] = Field(min_length=1)
    pilot_switch: date
    general_switch: date
    venue_open: date
    mapping_extract_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    pilot_attachment_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def validate_evidence(self):
        if self.urls != AUTHORITY_URLS or (self.pilot_switch, self.general_switch, self.venue_open) != (
                PILOT_SWITCH, GENERAL_SWITCH, BSE_OPEN):
            raise ValueError('Reviewed authority scope or dates differ')
        for collection in (self.pairs, self.pilot_pairs):
            if len(collection) != len(set(collection)):
                raise ValueError('Duplicate official mapping pair')
            if any(not re.fullmatch(r'[0-9]{6}\.BJ', x) for pair in collection for x in pair):
                raise ValueError('Official pair must contain exact BSE identifiers')
            if len({p[0] for p in collection}) != len(collection) or len({p[1] for p in collection}) != len(collection):
                raise ValueError('Official mapping is ambiguous')
        if len(self.pilot_pairs) != 6 or not set(self.pilot_pairs) <= set(self.pairs):
            raise ValueError('Six official pilot pairs required')
        if self.mapping_extract_sha256 != digest(sorted(self.pairs)):
            raise ValueError('Official pair extract hash differs')
        return self


def stable_security_id(exchange: str, anchor: str, provider_list_date: date) -> str:
    suffix = {'SSE': '.SH', 'SZSE': '.SZ', 'BSE': '.BJ'}.get(exchange)
    if not suffix or not is_normalized_ashare_identifier(anchor) or not anchor.endswith(suffix):
        raise ValueError('Reviewed normalized episode anchor required')
    return str(uuid5(IDENTITY_NAMESPACE, f'{exchange}|{anchor}|{provider_list_date.isoformat()}'))


def audit_mapping(provider_rows: list[dict], evidence: BSEEvidence) -> dict:
    pairs = [(r.get('o_code'), r.get('n_code')) for r in provider_rows]
    invalid = sum(not all(is_normalized_ashare_identifier(v) and v.endswith('.BJ') for v in p) for p in pairs)
    valid = set(p for p in pairs if all(isinstance(v, str) for v in p))
    official = set(evidence.pairs)
    duplicates = len(pairs) - len(valid)
    ambiguous = (len({p[0] for p in valid}) != len(valid) or len({p[1] for p in valid}) != len(valid))
    mismatch = len(valid ^ official)
    passed = bool(pairs) and len(pairs) < 300 and not (invalid or duplicates or ambiguous or mismatch)
    return dict(status='PASS' if passed else 'PARTIAL', provider_pair_count=len(pairs),
                official_pair_count=len(official), mismatch_count=mismatch,
                duplicate_count=duplicates, invalid_count=invalid, ambiguous=ambiguous,
                pilot_pair_count=len(evidence.pilot_pairs))


def read_captured_universe(root: Path, db) -> tuple[list[dict], list[dict]]:
    runs = db.execute("SELECT run_id FROM ingestion_run WHERE dataset='stock_basic' AND mode='PROBE' AND status='SUCCEEDED'").fetchall()
    if len(runs) != 1:
        raise ValueError('Exactly one existing accepted stock_basic probe required; do not fetch replacements')
    run_id = runs[0][0]
    sidecar_path = root/f'data/raw/tushare/stock_basic/run_id={run_id}/manifest.json'
    sidecar = json.loads(sidecar_path.read_bytes())
    objects = sidecar['objects']
    expected = {(e, s) for e in ('SSE', 'SZSE', 'BSE') for s in ('L', 'D', 'P', 'G', 'UN')}
    actual = {(o['request_params']['exchange'], o['request_params']['list_status']) for o in objects}
    if sidecar['dataset'] != 'stock_basic' or sidecar['run_id'] != str(run_id) or len(objects) != 15 or actual != expected:
        raise ValueError('Missing or duplicate stock_basic partitions; do not fetch replacements')
    registered = db.execute('SELECT count(*) FROM raw_object_manifest WHERE run_id=?', [str(run_id)]).fetchone()[0]
    if registered != 15 or not verify_batch(root, db, [run_id]):
        raise ValueError('Existing immutable raw capture failed verification')
    registered_rows = db.execute('SELECT object_id,relative_path,sha256,row_count,schema_hash,retrieved_at,request_params FROM raw_object_manifest WHERE run_id=?',[str(run_id)]).fetchall()
    registered_by_path = {r[1]:r for r in registered_rows}
    for obj in objects:
        r = registered_by_path.get(obj['relative_path'])
        if (r is None or (obj['object_id'],obj['sha256'],obj['row_count'],obj['schema_hash']) !=
                (str(r[0]),r[2],r[3],r[4]) or obj['request_params'] != json.loads(r[6]) or
                datetime.fromisoformat(obj['retrieved_at']) != r[5] or
                obj.get('available_at') != obj['retrieved_at'] or obj.get('availability_basis') != 'OBSERVED_CAPTURE'):
            raise ValueError('Source sidecar lineage differs from registered metadata')
    rows = []
    for obj in sorted(objects, key=lambda o: o['relative_path']):
        for raw in pq.ParquetFile(root/obj['relative_path']).read().to_pylist():
            rows.append(dict(raw, raw_object_id=obj['object_id'], retrieved_at=obj['retrieved_at']))
    return rows, objects


def _provider_date(value) -> date | None:
    if value in (None, ''):
        return None
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{8}', value):
        raise ValueError('Provider date is invalid')
    return date.fromisoformat(f'{value[:4]}-{value[4:6]}-{value[6:]}')


def plan_bootstrap(rows: list[dict], evidence: BSEEvidence, *, observed_at: datetime) -> dict:
    """Audit first, then validate a complete candidate history before any admission.

    Delist dates are retained metadata, not invented exclusive boundaries. No historical
    knowledge is claimed: admission availability is the current observation boundary.
    """
    code_counts = Counter((r.get('exchange'), r.get('ts_code')) for r in rows)
    aliases = {x: pair for pair in evidence.pairs for x in pair}
    pilots = set(evidence.pilot_pairs)
    identifiers, venues, quarantine = [], [], []
    episode_ids = set()
    pair_episodes = defaultdict(list)
    parsed = []
    for r in rows:
        code, exchange = r.get('ts_code'), r.get('exchange')
        reason = None
        try:
            listed, delisted = _provider_date(r.get('list_date')), _provider_date(r.get('delist_date'))
        except ValueError:
            listed, delisted, reason = None, None, 'IDENTITY_METADATA_REVIEW'
        if not is_normalized_ashare_identifier(code):
            reason = 'NON_NORMALIZED_IDENTIFIER'
        elif exchange not in ('SSE', 'SZSE', 'BSE') or not code.endswith({'SSE':'.SH','SZSE':'.SZ','BSE':'.BJ'}[exchange]):
            reason = 'ASSET_OUT_OF_SCOPE'
        elif code_counts[(exchange, code)] > 1:
            reason = 'AMBIGUOUS_IDENTIFIER'
        elif listed is None:
            reason = reason or 'MISSING_LIST_DATE'
        elif delisted is not None and delisted < listed:
            reason = 'IDENTITY_METADATA_REVIEW'
        elif exchange == 'BSE' and delisted is not None and delisted < BSE_OPEN:
            reason = 'PRE_BSE_LEGACY'
        elif exchange == 'BSE' and code not in aliases and not code.startswith('920') and r.get('list_status') != 'D':
            reason = 'NO_IDENTIFIER_MAPPING'
        pair = aliases.get(code) if exchange == 'BSE' else None
        if pair is not None and not reason:
            pair_episodes[pair].append((listed, delisted))
        parsed.append((r, listed, delisted, pair, reason))
    # Multiple snapshot rows for aliases are never silently merged into one episode.
    ambiguous_pairs = {p for p, episodes in pair_episodes.items() if len(episodes) > 1}
    for r, listed, delisted, pair, reason in parsed:
        code, exchange = r.get('ts_code'), r.get('exchange')
        if pair in ambiguous_pairs:
            reason = 'AMBIGUOUS_IDENTIFIER'
        if reason:
            quarantine.append(dict(provider_identifier=code if isinstance(code,str) else '<missing>',
                                   event_date=listed.isoformat() if listed else None,
                                   reason=reason, raw_object_id=r['raw_object_id']))
            continue
        anchor = pair[0] if pair else code
        sid = stable_security_id(exchange, anchor, listed)
        start = max(listed, BSE_OPEN) if exchange == 'BSE' else listed
        if pair:
            switch = PILOT_SWITCH if pair in pilots else GENERAL_SWITCH
            if listed >= switch or (code == pair[0] and r.get('list_status') != 'D'):
                quarantine.append(dict(provider_identifier=code, event_date=listed.isoformat(),
                                       reason='IDENTITY_METADATA_REVIEW', raw_object_id=r['raw_object_id']))
                continue
            intervals = [(pair[0], start, switch), (pair[1], switch, None)]
            evidence_source = '|'.join((AUTHORITY_URLS[0], AUTHORITY_URLS[2 if pair in pilots else 3]))
        else:
            intervals = [(code, start, None)]
            evidence_source = 'raw_object:'+r['raw_object_id']
        retrieved = max(datetime.fromisoformat(r['retrieved_at']), evidence.retrieved_at) if exchange == 'BSE' else datetime.fromisoformat(r['retrieved_at'])
        for identifier, valid_from, valid_to in intervals:
            identifiers.append(IdentifierHistory(security_id=sid, source='tushare', identifier_type='ts_code',
                identifier=identifier, exchange=exchange, valid_from=valid_from, valid_to=valid_to,
                published_at=None, available_at=observed_at, retrieved_at=retrieved,
                evidence_source=evidence_source))
        venues.append(dict(security_id=sid, venue=exchange, effective_from=start.isoformat(), effective_to=None,
            provider_list_date=listed.isoformat(), provider_delist_date=delisted.isoformat() if delisted else None,
            source='tushare', available_at=observed_at.isoformat(), retrieved_at=retrieved.isoformat(),
            evidence_source=(AUTHORITY_URLS[4]+'|' if exchange == 'BSE' else '')+'raw_object:'+r['raw_object_id']))
        episode_ids.add(sid)
    IdentityHistory(identifiers)
    return dict(identifiers=identifiers, venues=venues, quarantine=quarantine,
                security_id_count=len(episode_ids), provider_rows=len(rows),
                duplicate_code_count=sum(c-1 for c in code_counts.values() if c>1),
                overlapping_pair_count=len(ambiguous_pairs))


def identity_snapshot_hash(plan: dict) -> str:
    """Versioned CURRENT_RECONSTRUCTION hash; excludes variable observation timestamps.

    It is not a PIT knowledge snapshot. Effective mappings, evidence, raw lineage and
    quarantines change the hash; row order and rebuild wall-clock times do not.
    """
    excluded = {'available_at', 'retrieved_at', 'published_at'}
    identifiers = [{k:v for k,v in row.model_dump(mode='json').items() if k not in excluded}
                   for row in plan['identifiers']]
    venues = [{k:v for k,v in row.items() if k not in excluded} for row in plan['venues']]
    sort = lambda values: sorted(values, key=lambda v: canonical_json(v))
    return digest(dict(version=BOOTSTRAP_VERSION, basis='CURRENT_RECONSTRUCTION',
                       identifiers=sort(identifiers), venues=sort(venues), quarantine=sort(plan['quarantine'])))


def admit_bootstrap(db, plan: dict, *, commit: str, config_hash: str, input_hash: str,
                    observed_at: datetime) -> tuple[str, bool]:
    """Single-writer, all-or-nothing first admission; subsequent identical runs reuse it.

    A changed provider episode/metadata or evidence requires review, never a new UUID
    silently replacing an admitted identity. Phase 1C.0 does not implement corrections.
    """
    from astock.data.warehouse_lock import require_writer
    require_writer(db)
    snapshot = identity_snapshot_hash(plan)
    prior = db.execute("SELECT curation_run_id,config_hash,input_manifest_hash,identity_snapshot_hash FROM curation_run WHERE dataset='stock_basic' AND partition_key='PHASE1C0_BOOTSTRAP'").fetchall()
    if prior:
        if len(prior) == 1 and prior[0][1:] == (config_hash, input_hash, snapshot):
            result = db.execute('SELECT * FROM security_identifier_history')
            names = [c[0] for c in result.description]
            identifiers = [IdentifierHistory(**dict(zip(names,v,strict=True))) for v in result.fetchall()]
            result = db.execute('SELECT * FROM security_venue_history')
            names = [c[0] for c in result.description]
            venues = [dict(zip(names,v,strict=True)) for v in result.fetchall()]
            for v in venues:
                for k in ('effective_from','effective_to','provider_list_date','provider_delist_date'):
                    v[k] = v[k].isoformat() if v[k] else None
            quarantines = [dict(provider_identifier=r[0],event_date=r[1].isoformat() if r[1] else None,reason=r[2],raw_object_id=str(r[3])) for r in db.execute('SELECT provider_identifier,event_date,reason,raw_object_id FROM identity_quarantine WHERE curation_run_id=?',[str(prior[0][0])]).fetchall()]
            IdentityHistory(identifiers)
            if identity_snapshot_hash(dict(identifiers=identifiers, venues=venues, quarantine=quarantines)) != snapshot:
                raise ValueError('Stored identity snapshot changed; review required')
            return str(prior[0][0]), False
        raise ValueError('Admitted identity inputs or metadata changed; review required')
    if db.execute('SELECT count(*) FROM security_identifier_history').fetchone()[0] or db.execute('SELECT count(*) FROM security_venue_history').fetchone()[0]:
        raise ValueError('Existing identity state requires review before bootstrap')
    IdentityHistory(plan['identifiers'])
    run_id = uuid4()
    db.execute('BEGIN')
    try:
        db.execute('INSERT INTO curation_run VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',[
            str(run_id),'stock_basic','PHASE1C0_BOOTSTRAP',observed_at,observed_at,
            'PARTIAL' if plan['quarantine'] else 'SUCCEEDED',commit,config_hash,input_hash,snapshot,
            plan['provider_rows'],plan['provider_rows']-len(plan['quarantine']),len(plan['quarantine'])])
        if plan['identifiers']:
            fields = list(IdentifierHistory.model_fields)
            db.executemany('INSERT INTO security_identifier_history VALUES ('+','.join('?' for _ in fields)+')',
                           [[getattr(r,k) for k in fields] for r in plan['identifiers']])
        if plan['venues']:
            db.executemany('INSERT INTO security_venue_history VALUES (?,?,?,?,?,?,?,?,?,?)',
                           [list(v.values()) for v in plan['venues']])
        for q in plan['quarantine']:
            if db.execute('SELECT count(*) FROM raw_object_manifest WHERE object_id=? AND dataset=\'stock_basic\'', [q['raw_object_id']]).fetchone()[0] != 1:
                raise ValueError('Quarantine lineage is not registered')
            db.execute('INSERT INTO identity_quarantine VALUES (?,?,?,?,?,?,?,?)',[
                str(uuid4()),'stock_basic',q['provider_identifier'],q['event_date'],q['reason'],q['raw_object_id'],str(run_id),observed_at])
        db.execute('COMMIT')
    except Exception:
        db.execute('ROLLBACK')
        raise
    return str(run_id), True


def capture_mapping(root: Path, db, settings, *, live: bool, commit: str) -> tuple[list[dict], list[dict]]:
    """Consume a durable one-attempt budget before POST, including failed attempts."""
    from astock.data.warehouse_lock import require_writer
    require_writer(db)
    runs = db.execute("SELECT run_id,status FROM ingestion_run WHERE dataset='bse_mapping'").fetchall()
    if runs:
        if len(runs) != 1 or runs[0][1] != 'SUCCEEDED' or not verify_batch(root, db, [runs[0][0]]):
            raise ValueError('Mapping capture requires review; never automatically retry')
        sidecar = json.loads((root/f'data/raw/tushare/bse_mapping/run_id={runs[0][0]}/manifest.json').read_bytes())
        if len(sidecar['objects']) != 1:
            raise ValueError('Exactly one mapping raw object required')
        return pq.ParquetFile(root/sidecar['objects'][0]['relative_path']).read().to_pylist(), sidecar['objects']
    if not live or not settings.token_configured:
        raise ValueError('One mapping capture requires explicit --live and local configuration')
    contract = next(c for c in load_contracts(root, catalog_version='v2') if c.dataset=='bse_mapping')
    marker = root/'data/private/phase1c0/bse-mapping-attempt.json'
    run_id, started = uuid4(), datetime.now(timezone.utc)
    atomic_new_file(marker, lambda p: p.write_bytes(canonical_json(dict(run_id=str(run_id),started_at=started.isoformat(),maximum_attempts=1))))
    db.execute('''INSERT INTO ingestion_run (run_id,source,dataset,mode,started_at,status,code_commit,
        config_hash,provider_client_version) VALUES (?,'tushare','bse_mapping','AUDIT',?,'RUNNING',?,?,?)''',
        [str(run_id),started,commit,configuration_hash(root),CLIENT_VERSION])
    client = TushareClient(settings.tushare_token)
    try:
        table = client.fetch_bse_mapping(contract)
        writer = RawWriter(root,db)
        manifest = writer.write(run_id,'bse_mapping',0,table,RequestParams())
        sidecar_path = writer.sidecar(run_id,'bse_mapping')
        if not secret_scan(settings.tushare_token,[root/manifest.relative_path,sidecar_path]):
            raise ValueError('Mapping capture failed safe storage audit')
        db.execute("UPDATE ingestion_run SET status='SUCCEEDED',finished_at=?,request_count=? WHERE run_id=?",
                   [datetime.now(timezone.utc),client.request_count,str(run_id)])
    except Exception as exc:
        error = exc.error if isinstance(exc,ProviderFailure) else None
        db.execute("UPDATE ingestion_run SET status='FAILED',finished_at=?,request_count=?,error_category=?,error_http_status=?,error_provider_code=? WHERE run_id=?",
                   [datetime.now(timezone.utc),client.request_count,error.category.value if error else None,
                    error.http_status if error else None,error.provider_code if error else None,str(run_id)])
        raise ValueError('One mapping attempt failed; stop for review') from None
    sidecar = json.loads(sidecar_path.read_bytes())
    return [dict(zip(table.fields,row,strict=True)) for row in table.items],sidecar['objects']


def run_bootstrap(root: Path, settings, *, authority_path: Path, live: bool=False) -> dict:
    with warehouse_connection(settings.paths(root).db_path) as db:
        load_curation_specs(root)
        evidence = BSEEvidence.model_validate_json(authority_path.read_bytes())
        validate_local_authority_files(authority_path, evidence)
        commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        if subprocess.check_output(['git','status','--porcelain','--','src/astock','config','sql'],cwd=root,text=True).strip():
            raise ValueError('Commit reviewed implementation before recording runtime code_commit')
        migrate(db,root)
        rows, objects = read_captured_universe(root,db)
        # Private anomaly audit precedes any mapping HTTP request or identity admission.
        preliminary = plan_bootstrap(rows,evidence,observed_at=datetime.now(timezone.utc))
        private = root/'data/private/phase1c0'
        prepath = private/'pre-admission-audit.json'
        if not prepath.exists():
            atomic_new_file(prepath,lambda p:p.write_bytes(canonical_json(dict(
                provider_rows=len(rows),quarantine=preliminary['quarantine'],
                normalized_sse_szse_rows=sum(r.get('exchange') in ('SSE','SZSE') and is_normalized_ashare_identifier(r.get('ts_code')) for r in rows),
                bse_rows=sum(r.get('exchange')=='BSE' for r in rows),
                duplicate_code_count=preliminary['duplicate_code_count'],
                overlapping_pair_count=preliminary['overlapping_pair_count']))))
        mapping_rows, mapping_objects = capture_mapping(root,db,settings,live=live,commit=commit)
        mapping = audit_mapping(mapping_rows,evidence)
        auditpath=private/'mapping-audit.json'
        if not auditpath.exists():
            atomic_new_file(auditpath,lambda p:p.write_bytes(canonical_json(mapping)))
        if mapping['status'] != 'PASS':
            return dict(status='PARTIAL',mapping=mapping,admitted=False)
        observed = datetime.now(timezone.utc)
        plan = plan_bootstrap(rows,evidence,observed_at=observed)
        input_hash = input_manifest_hash([*objects,*mapping_objects])
        snapshot = identity_snapshot_hash(plan)
        run_id,admitted = admit_bootstrap(db,plan,commit=commit,config_hash=configuration_hash(root),
                                        input_hash=input_hash,observed_at=observed)
        summary = dict(status='PARTIAL' if plan['duplicate_code_count'] or plan['overlapping_pair_count'] else 'PASS',mapping=mapping,admitted=admitted,curation_run_id=run_id,
            security_id_count=plan['security_id_count'],identifier_count=len(plan['identifiers']),
            venue_count=len(plan['venues']),provider_rows=plan['provider_rows'],
            quarantine_by_reason=dict(Counter(q['reason'] for q in plan['quarantine'])),
            duplicate_code_count=plan['duplicate_code_count'],overlapping_pair_count=plan['overlapping_pair_count'],
            identity_snapshot_hash=snapshot,input_manifest_hash=input_hash,config_hash=configuration_hash(root),
            availability_basis='OBSERVED_CAPTURE',snapshot_basis='CURRENT_RECONSTRUCTION',
            delist_boundary_status='REVIEW_REQUIRED_BEFORE_PHASE1C1',code_commit=commit)
        summary_path=private/'bootstrap-summary.json'
        if not summary_path.exists():
            atomic_new_file(summary_path,lambda p:p.write_bytes(canonical_json(summary)))
        return summary


def classify_identifier_fact(history: IdentityHistory, *, identifier: str, exchange: str,
                             event_date: date, as_of: datetime) -> tuple[str | None, str | None]:
    if not is_normalized_ashare_identifier(identifier):
        return None, 'NON_NORMALIZED_IDENTIFIER'
    if exchange == 'BSE' and event_date < BSE_OPEN:
        return None, 'PRE_BSE_LEGACY'
    suffix={'SSE':'.SH','SZSE':'.SZ','BSE':'.BJ'}.get(exchange)
    if not suffix or not identifier.endswith(suffix):
        return None, 'ASSET_OUT_OF_SCOPE'
    sid=history.resolve(source='tushare',identifier_type='ts_code',identifier=identifier,
                        exchange=exchange,event_date=event_date,as_of=as_of)
    if sid:
        return sid, None
    known=any(r.identifier==identifier and r.exchange==exchange and r.source=='tushare'
              and r.identifier_type=='ts_code' and r.available_at<=as_of for r in history.rows)
    return None, 'OUTSIDE_IDENTIFIER_INTERVAL' if known else 'NO_IDENTIFIER_MAPPING'


def validate_local_authority_files(authority_path: Path, evidence: BSEEvidence) -> None:
    """Check the reviewed extract/attachment bytes before trusting their selection."""
    from zipfile import ZipFile
    from xml.etree import ElementTree
    directory=authority_path.parent
    text=(directory/'pairs.txt').read_text().split()
    pairs=[tuple(v+'.BJ' for v in pair.split('=')) for pair in text]
    if sorted(pairs) != sorted(evidence.pairs):
        raise ValueError('Reviewed mapping extract bytes differ')
    attachment=directory/'pilot-list.docx'
    if hashlib.sha256(attachment.read_bytes()).hexdigest() != evidence.pilot_attachment_sha256:
        raise ValueError('Reviewed pilot attachment bytes differ')
    with ZipFile(attachment) as archive:
        document=ElementTree.fromstring(archive.read('word/document.xml'))
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    rows=[[''.join(c.itertext()) for c in r.findall('w:tc',ns)]
          for r in document.findall('.//w:tr',ns)]
    if not rows or rows[0] != ['序号','证券简称','上市日期','旧代码','新代码']:
        raise ValueError('Unexpected pilot attachment table')
    if any(len(r)!=5 for r in rows[1:]):
        raise ValueError('Unexpected pilot attachment row')
    pilot_pairs=[(r[3]+'.BJ',r[4]+'.BJ') for r in rows[1:]]
    if sorted(pilot_pairs) != sorted(evidence.pilot_pairs):
        raise ValueError('Reviewed pilot selection differs from exact attachment')
