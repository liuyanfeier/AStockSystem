"""Phase 1C.0 synthetic governance tests; no private data or credential access."""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import duckdb
import httpx
import pyarrow as pa
import pytest
from pydantic import SecretStr, ValidationError

from astock.data.bootstrap import (
    AUTHORITY_URLS, BSEEvidence, BSE_OPEN, PILOT_SWITCH, GENERAL_SWITCH, stable_security_id,
    audit_mapping, plan_bootstrap, identity_snapshot_hash, admit_bootstrap, capture_mapping,
    classify_identifier_fact, read_captured_universe,
)
from astock.data.contracts import load_contracts
from astock.data.curation import load_curation_specs, configuration_hash, digest, publish_curated_bytes
from astock.data.identity import IdentityHistory, IdentifierHistory
from astock.data.raw_writer import migrate
from astock.data.tushare_client import TushareClient, ProviderFailure
from astock.paths import get_project_root
from astock.settings import Settings

ROOT=get_project_root()
NOW=datetime(2026,1,1,tzinfo=timezone.utc)
RAW='00000000-0000-0000-0000-000000000001'


def evidence():
    # Deliberately different last digits; no suffix inference is possible.
    pairs=[(f'83000{i}.BJ',f'92010{i}.BJ') for i in range(6)]+[('831999.BJ','920888.BJ')]
    return BSEEvidence(urls=AUTHORITY_URLS,retrieved_at=NOW,pairs=pairs,pilot_pairs=pairs[:6],
        pilot_switch=PILOT_SWITCH,general_switch=GENERAL_SWITCH,venue_open=BSE_OPEN,
        mapping_extract_sha256=digest(sorted(pairs)),pilot_attachment_sha256='a'*64)


def row(code='000001.SZ',exchange='SZSE',**changes):
    result=dict(ts_code=code,exchange=exchange,name='Synthetic name',list_status='L',
                list_date='20200101',delist_date=None,raw_object_id=RAW,
                retrieved_at=NOW.isoformat())
    result.update(changes)
    return result


def plan(rows):
    return plan_bootstrap(rows,evidence(),observed_at=NOW+timedelta(days=1))


def test_catalogs_are_explicit_and_historical_bytes_unchanged():
    baseline=json.loads((ROOT/'tests/fixtures/contract_v1_sha256.json').read_text())
    assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'config/contracts/v1').glob('*.yaml')}==baseline
    assert len(load_contracts(ROOT,catalog_version='v1'))==12
    assert len(load_contracts(ROOT,catalog_version='v2'))==9
    with pytest.raises(TypeError): load_contracts(ROOT)
    with pytest.raises(ValueError): load_contracts(ROOT,catalog_version='latest')


def test_v2_field_boundaries_and_curation_types_empty():
    contracts={c.dataset:c for c in load_contracts(ROOT,catalog_version='v2')}
    assert {'fullname','curr_type'}<=set(contracts['stock_basic'].required_fields)
    assert not {'industry','area','act_name','act_ent_type','is_hs'}&set(contracts['stock_basic'].required_fields)
    assert {'ah_vol','ah_amount'}<=set(contracts['daily'].required_fields)
    assert {'pe_ttm','turnover_rate_f','float_share','free_share','circ_mv','limit_status'}<=set(contracts['daily_basic'].required_fields)
    specs={s.dataset:s for s in load_curation_specs(ROOT)}
    for s in specs.values():
        empty=s.empty_table()
        assert empty.num_rows==0 and empty.schema==s.arrow_schema()
        assert not any(pa.types.is_null(f.type) for f in empty.schema)
    assert specs['daily'].arrow_schema().field('volume_hands').type==pa.float64()
    assert specs['daily_basic'].arrow_schema().field('total_mv_10k_cny').type==pa.float64()
    assert specs['daily_basic'].research_usage=='CURRENT_RECONSTRUCTION'
    assert configuration_hash(ROOT)==configuration_hash(ROOT)


def test_deterministic_uuid_names_independent_and_code_reuse_distinct():
    a=plan([row()]);b=plan([row(name='Different company spelling')])
    assert a['identifiers'][0].security_id==b['identifiers'][0].security_id
    assert stable_security_id('SZSE','000001.SZ',date(2020,1,1))==a['identifiers'][0].security_id
    different=stable_security_id('SZSE','000001.SZ',date(2025,1,1))
    assert different!=a['identifiers'][0].security_id
    old=a['identifiers'][0].model_copy(update={'valid_to':date(2021,1,1)})
    new=old.model_copy(update={'security_id':different,'valid_from':date(2025,1,1),'valid_to':None})
    history=IdentityHistory([old,new])
    assert history.resolve(source='tushare',identifier_type='ts_code',identifier='000001.SZ',exchange='SZSE',event_date=date(2025,1,1),as_of=NOW+timedelta(days=1))==different


def test_duplicate_and_overlapping_alias_episodes_quarantined():
    duplicate=plan([row(),row()])
    assert duplicate['security_id_count']==0
    assert {q['reason'] for q in duplicate['quarantine']}=={'AMBIGUOUS_IDENTIFIER'}
    overlap=plan([row('830000.BJ','BSE'),row('920100.BJ','BSE')])
    assert overlap['overlapping_pair_count']==1 and not overlap['identifiers']


def test_non_normalized_retained_without_successor_merge():
    p=plan([row('T600018.SH','SSE',list_date='20000719',delist_date='20061020',list_status='D'),
            row('600018.SH','SSE',list_date='20061026')])
    assert p['security_id_count']==1
    assert p['quarantine'][0]['provider_identifier']=='T600018.SH'
    assert p['quarantine'][0]['reason']=='NON_NORMALIZED_IDENTIFIER'
    assert p['identifiers'][0].identifier=='600018.SH'


@pytest.mark.parametrize('code,old,switch',[('920100.BJ','830000.BJ',PILOT_SWITCH),('920888.BJ','831999.BJ',GENERAL_SWITCH)])
def test_bse_exact_switch_old_new_same_identity_and_observed_asof(code,old,switch):
    p=plan([row(code,'BSE',list_date='20200727')])
    assert len(p['identifiers'])==2
    a,b=p['identifiers'];assert a.security_id==b.security_id
    assert a.identifier==old and a.valid_to==switch and b.valid_from==switch
    assert a.valid_from==BSE_OPEN
    venue=p['venues'][0]
    assert venue['effective_from']=='2021-11-15' and venue['provider_list_date']=='2020-07-27'
    h=IdentityHistory(p['identifiers'])
    common=dict(exchange='BSE',as_of=NOW+timedelta(days=1))
    assert classify_identifier_fact(h,identifier=old,event_date=switch-timedelta(days=1),**common)==(a.security_id,None)
    assert classify_identifier_fact(h,identifier=code,event_date=switch,**common)==(a.security_id,None)
    assert classify_identifier_fact(h,identifier=old,event_date=switch,**common)==(None,'OUTSIDE_IDENTIFIER_INTERVAL')
    assert classify_identifier_fact(h,identifier=code,event_date=switch,exchange='BSE',as_of=NOW)==(None,'NO_IDENTIFIER_MAPPING')
    assert classify_identifier_fact(h,identifier=old,event_date=date(2021,11,14),**common)==(None,'PRE_BSE_LEGACY')


def test_venue_after_open_and_delist_boundary_not_guessed():
    p=plan([row('920777.BJ','BSE',list_date='20240101',delist_date='20250101',list_status='D')])
    assert p['venues'][0]['effective_from']=='2024-01-01'
    assert p['venues'][0]['provider_delist_date']=='2025-01-01'
    assert p['venues'][0]['effective_to'] is None and p['identifiers'][0].valid_to is None


@pytest.mark.parametrize('changes,reason',[
    ({'list_date':None},'MISSING_LIST_DATE'),
    ({'list_date':'20201399'},'IDENTITY_METADATA_REVIEW'),
    ({'ts_code':'920999.BJ','exchange':'BSE','list_date':'20150101','delist_date':'20200101','list_status':'D'},'PRE_BSE_LEGACY'),
    ({'ts_code':'830999.BJ','exchange':'BSE'},'NO_IDENTIFIER_MAPPING'),
    ({'ts_code':'000001.SH'},'ASSET_OUT_OF_SCOPE'),
])
def test_quarantine_reasons(changes,reason):
    r=row();r.update(changes);p=plan([r])
    assert p['quarantine'][0]['reason']==reason and not p['identifiers']


def test_every_provider_mapping_pair_compared_and_mismatch_not_fixed():
    e=evidence();rows=[dict(o_code=a,n_code=b) for a,b in e.pairs]
    assert audit_mapping(rows,e)['status']=='PASS'
    rows[-1]['n_code']='920999.BJ'
    assert audit_mapping(rows,e)['mismatch_count']==2
    assert audit_mapping(rows,e)['status']=='PARTIAL'
    assert rows[-1]['n_code']=='920999.BJ'
    assert audit_mapping(rows[:-1],e)['status']=='PARTIAL'
    assert audit_mapping(rows+rows[:1],e)['status']=='PARTIAL'
    with pytest.raises(ValidationError):BSEEvidence(**(e.model_dump()|{'pilot_pairs':e.pilot_pairs[:5]}))


def test_snapshot_hash_order_and_observation_independent_but_mapping_sensitive():
    rows=[row(),row('600001.SH','SSE')]
    a=plan(rows);b=plan_bootstrap(list(reversed(rows)),evidence(),observed_at=NOW+timedelta(days=2))
    assert identity_snapshot_hash(a)==identity_snapshot_hash(b)
    b['venues'][0]['provider_delist_date']='2025-01-01'
    assert identity_snapshot_hash(a)!=identity_snapshot_hash(b)
    assert digest(sorted([{'relative_path':'b'},{'relative_path':'a'}],key=lambda o:o['relative_path']))==digest([{'relative_path':'a'},{'relative_path':'b'}])


def test_bootstrap_admission_idempotent_and_metadata_revision_requires_review():
    with duckdb.connect(':memory:') as db:
        migrate(db,ROOT);p=plan([row()])
        args=dict(commit='a'*40,config_hash='b'*64,input_hash='c'*64,observed_at=NOW+timedelta(days=1))
        run,created=admit_bootstrap(db,p,**args);assert created
        assert admit_bootstrap(db,p,**args)==(run,False)
        assert db.execute('SELECT count(*) FROM security_identifier_history').fetchone()==(1,)
        with pytest.raises(ValueError,match='review required'):admit_bootstrap(db,plan([row(list_date='20210101')]),**args)
        db.execute("UPDATE security_venue_history SET provider_delist_date=DATE '2025-01-01'")
        with pytest.raises(ValueError,match='snapshot changed'):admit_bootstrap(db,p,**args)


def test_migration_005_preserves_existing_parent_child_rows_and_identity():
    with duckdb.connect(':memory:') as db:
        for n in ('001_foundation_schema','002_provider_lineage','003_probe_mode','004_security_identifier_history'):
            db.execute((ROOT/f'sql/{n}.sql').read_text())
        run=uuid4()
        db.execute("INSERT INTO ingestion_run (run_id,source,dataset,mode,started_at,status,code_commit,config_hash,provider_client_version) VALUES (?,'tushare','stock_basic','PROBE',?,'RUNNING',?,?,'0.1.0')",[str(run),NOW,'a'*40,'b'*64])
        db.execute('INSERT INTO raw_object_manifest VALUES (?,?,?,?,?,?,?,?,?,?,?)',[RAW,str(run),'stock_basic',f'data/raw/tushare/stock_basic/run_id={run}/part-000.parquet','a'*64,NOW,1,'b'*64,None,None,'{}'])
        p=plan([row()]);IdentityHistory.append(db,p['identifiers'][0])
        tables=('ingestion_run','raw_object_manifest','security_identifier_history')
        before={t:db.execute(f'SELECT * FROM {t}').fetchall() for t in tables}
        for _ in range(2):
            db.execute((ROOT/'sql/005_identity_bootstrap_governance.sql').read_text())
            assert {t:db.execute(f'SELECT * FROM {t}').fetchall() for t in tables}==before
        assert db.execute('SELECT count(*) FROM curated_object_manifest').fetchone()==(0,)
        with pytest.raises(ValueError):read_captured_universe(Path('/synthetic-missing'),db)


def test_curated_publication_no_clobber_and_path_escape(tmp_path):
    run=uuid4();p=publish_curated_bytes(tmp_path,dataset='daily',run_id=run,part=0,content=b'synthetic')
    with pytest.raises(FileExistsError):publish_curated_bytes(tmp_path,dataset='daily',run_id=run,part=0,content=b'replacement')
    assert p.read_bytes()==b'synthetic'
    with pytest.raises(ValueError):publish_curated_bytes(tmp_path,dataset='../escape',run_id=run,part=0,content=b'bad')
    (tmp_path/'data/curated/daily'/f'curation_run_id={uuid4()}').parent.mkdir(exist_ok=True,parents=True)
    escape=uuid4();(tmp_path/'data/curated/daily'/f'curation_run_id={escape}').symlink_to(tmp_path)
    with pytest.raises(ValueError):publish_curated_bytes(tmp_path,dataset='daily',run_id=escape,part=0,content=b'bad')


def test_bse_capture_transport_single_attempt_without_retry_or_full_probe():
    contract=next(c for c in load_contracts(ROOT,catalog_version='v2') if c.dataset=='bse_mapping')
    calls=[]
    def fail(request):calls.append(request);return httpx.Response(503)
    client=TushareClient(SecretStr('synthetic-token'),transport=httpx.MockTransport(fail))
    with pytest.raises(ProviderFailure):client.fetch_bse_mapping(contract)
    assert len(calls)==1 and client.request_count==1
    with pytest.raises(ValueError):client.fetch_bse_mapping(contract)
    assert len(calls)==1
    with duckdb.connect(':memory:') as db:
        migrate(db,ROOT)
        with pytest.raises(ValueError):capture_mapping(Path('/synthetic'),db,Settings(_env_file=None),live=False,commit='a'*40)


def test_ci_is_offline_and_has_no_live_capture_step():
    workflow=(ROOT/'.github/workflows/ci.yml').read_text()
    assert 'TUSHARE_TOKEN: ""' in workflow
    assert '--live' not in workflow and 'identity bootstrap' not in workflow
    assert 'contracts --catalog v2' in workflow and 'identity specs' in workflow


def test_input_manifest_hash_order_independent_and_duplicate_paths_rejected():
    from astock.data.curation import input_manifest_hash
    assert input_manifest_hash([{'relative_path':'b'},{'relative_path':'a'}])==input_manifest_hash([{'relative_path':'a'},{'relative_path':'b'}])
    with pytest.raises(ValueError):input_manifest_hash([{'relative_path':'a'},{'relative_path':'a'}])


def test_durable_capture_budget_consumed_even_after_failed_http(tmp_path,monkeypatch):
    from astock.data import bootstrap
    settings=Settings(_env_file=None,tushare_token=SecretStr('synthetic-test-token'))
    monkeypatch.setattr(bootstrap,'load_contracts',lambda *a,**k:load_contracts(ROOT,catalog_version='v2'))
    monkeypatch.setattr(bootstrap,'configuration_hash',lambda *a:'b'*64)
    calls=[]
    class FailedClient:
        request_count=1
        def __init__(self,*args):pass
        def fetch_bse_mapping(self,contract):
            calls.append(contract.dataset)
            raise ValueError('synthetic failure')
    monkeypatch.setattr(bootstrap,'TushareClient',FailedClient)
    with duckdb.connect(':memory:') as db:
        migrate(db,ROOT)
        with pytest.raises(ValueError):capture_mapping(tmp_path,db,settings,live=True,commit='a'*40)
        assert calls==['bse_mapping']
        assert (tmp_path/'data/private/phase1c0/bse-mapping-attempt.json').is_file()
        with pytest.raises(ValueError):capture_mapping(tmp_path,db,settings,live=True,commit='a'*40)
        assert calls==['bse_mapping']
    with duckdb.connect(':memory:') as fresh:
        migrate(fresh,ROOT)
        with pytest.raises(FileExistsError):capture_mapping(tmp_path,fresh,settings,live=True,commit='a'*40)
        assert calls==['bse_mapping']


def test_governance_safe_details_and_counts_are_enforced():
    with duckdb.connect(':memory:') as db:
        migrate(db,ROOT)
        run,_=admit_bootstrap(db,plan([row()]),commit='a'*40,config_hash='b'*64,input_hash='c'*64,observed_at=NOW+timedelta(days=1))
        values=['daily',date(2025,1,1),run,1,1,0,0,False,'PASS','{"missing_count":0}']
        db.execute('INSERT INTO dataset_date_audit VALUES (?,?,?,?,?,?,?,?,?,?)',values)
        for details in ('{"token":"synthetic"}','{"missing_count":-1}','{"null_count":"1"}'):
            v=values.copy();v[1]=date(2025,1,2);v[-1]=details
            with pytest.raises(duckdb.Error):db.execute('INSERT INTO dataset_date_audit VALUES (?,?,?,?,?,?,?,?,?,?)',v)
        v=values.copy();v[1]=date(2025,1,2);v[3]=2
        with pytest.raises(duckdb.Error):db.execute('INSERT INTO dataset_date_audit VALUES (?,?,?,?,?,?,?,?,?,?)',v)


def test_official_extract_and_pilot_attachment_hash_are_verified(tmp_path):
    from zipfile import ZipFile
    from astock.data.bootstrap import validate_local_authority_files
    e=evidence()
    (tmp_path/'pairs.txt').write_text(' '.join(a[:6]+'='+b[:6] for a,b in e.pairs))
    rows=[['序号','证券简称','上市日期','旧代码','新代码']]+[[str(i),'Synthetic','2020-01-01',a[:6],b[:6]] for i,(a,b) in enumerate(e.pilot_pairs,1)]
    xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:tbl>'
    xml+=''.join('<w:tr>'+''.join('<w:tc><w:p><w:r><w:t>'+c+'</w:t></w:r></w:p></w:tc>' for c in r)+'</w:tr>' for r in rows)
    xml+='</w:tbl></w:body></w:document>'
    p=tmp_path/'pilot-list.docx'
    with ZipFile(p,'w') as z:z.writestr('word/document.xml',xml.encode())
    e=e.model_copy(update={'pilot_attachment_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    validate_local_authority_files(tmp_path/'reviewed-evidence.json',e)
    p.write_bytes(b'synthetic alteration')
    with pytest.raises(ValueError,match='bytes differ'):validate_local_authority_files(tmp_path/'reviewed-evidence.json',e)
