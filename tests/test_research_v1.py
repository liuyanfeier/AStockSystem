"""Business regressions with synthetic real-shaped inputs; never use local private sources."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from typer.testing import CliRunner

from astock.cli.main import app
from astock.features.market import ObservationParameters
from astock.reports.research import markdown, publish
from astock.research.core import ResearchError, digest, encoded
from astock.research.journal import append_event
from astock.research.service import analyze
from astock.research.store import ResearchStore
from astock.data.warehouse_lock import warehouse_connection


PARAMS = dict(version="SYNTHETIC_OBSERVATION_TEST", return_sessions=3, trend_sessions=3,
              breakout_sessions=3, activity_sessions=3, top_n=5, min_mean_amount_cny=0,
              max_stale_calendar_days=7, strategy_validated=False, risk_budget=None)
ASOF = "2026-09-15T20:00:00+08:00"


@pytest.fixture
def sample(tmp_path):
    start=date(2026,9,7)
    dates=[start+timedelta(days=i) for i in range(5)]
    files=[]
    def add(dataset, rows, *, adapter="native-v1", **kwargs):
        path=tmp_path/f"{dataset}.parquet"
        pq.write_table(pa.Table.from_pylist(rows),path)
        spec=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),dataset=dataset,
                  format="parquet",source="SYNTHETIC_FIXTURE",retrieved_at="2026-09-12T20:00:00+08:00",
                  available_at="2026-09-12T20:00:00+08:00",adapter=adapter,**kwargs)
        files.append(spec)
        return path
    instruments=[dict(code=c,name=c,exchange="SSE",kind=k) for c,k in (("STOCK-A","STOCK"),("STOCK-B","STOCK"),("BENCH-A","INDEX"))]
    add("instruments",instruments)
    add("calendar",[dict(exchange="SSE",date=d.isoformat(),is_open=1) for d in dates])
    prices=[]
    indices=[]
    for code,trend,target in (("STOCK-A",1,prices),("STOCK-B",-1,prices),("BENCH-A",0.1,indices)):
        for i,d in enumerate(dates):
            close=10+i*trend
            target.append(dict(code=code,date=d.isoformat(),open=close,high=close+0.1,low=close-0.1,close=close,
                               pre_close=None,volume=1000.0,amount=10000000.0))
    add("daily",prices,volume_unit="shares",amount_unit="CNY")
    add("index_daily",indices,volume_unit="shares",amount_unit="CNY")
    add("adj_factor",[dict(code=c,date=d.isoformat(),adj_factor=1.0) for c in ("STOCK-A","STOCK-B") for d in dates])
    bundle=dict(protocol="RESEARCH_INPUT_V1",purpose="CURRENT_OBSERVATION",window_start=dates[0].isoformat(),window_end=dates[-1].isoformat(),
                universe=["STOCK-A","STOCK-B"],benchmarks=["BENCH-A"],universe_scope="WATCHLIST",files=files)
    manifest=tmp_path/"bundle.json"
    manifest.write_text(json.dumps(bundle))
    return manifest,bundle,add


def change_file(sample,dataset,transform):
    manifest,bundle,_=sample
    spec=next(f for f in bundle["files"] if f["dataset"]==dataset)
    path=Path(spec["path"])
    rows=pq.read_table(path).to_pylist()
    pq.write_table(pa.Table.from_pylist(transform(rows)),path)
    spec["sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(bundle))


def run(sample,tmp_path,params=None,asof=ASOF):
    store=ResearchStore(tmp_path/"research.duckdb")
    bundle_id=store.import_bundle(sample[0])
    return store,bundle_id,analyze(store,bundle_id,asof,ObservationParameters(**(params or PARAMS)),["STOCK-A","STOCK-B"])


def test_end_to_end_deterministic_report_and_reopen(sample,tmp_path):
    store,bundle_id,snapshot=run(sample,tmp_path)
    assert [c["code"] for c in snapshot["candidates"]]==["STOCK-A"]
    assert snapshot["market"]["breadth_denominator"]==2
    assert snapshot["features"][0]["relative_return"] is not None
    assert snapshot["candidates"][0]["metrics"]["breakout"] is True
    assert snapshot["candidates"][0]["trade_eligible"] is False
    assert any("状态未知" in x for x in snapshot["candidates"][0]["no_trade_conditions"])
    first=publish(snapshot,tmp_path/"reports")
    reopened=analyze(ResearchStore(store.path),bundle_id,ASOF,ObservationParameters(**PARAMS),["STOCK-A","STOCK-B"])
    assert snapshot==reopened
    assert publish(reopened,tmp_path/"reports")==first
    assert store.save_report(snapshot)==store.save_report(reopened)
    text=markdown(snapshot)
    for term in ("入场观察条件","反面证据","逻辑失效条件","不交易条件","OBSERVATION_ONLY","非全市场","UNKNOWN"):
        assert term in text
    # Original source files can disappear: retained bytes still drive verification.
    for f in sample[1]["files"]:Path(f["path"]).unlink()
    assert analyze(store,bundle_id,ASOF,ObservationParameters(**PARAMS))["features"]==snapshot["features"]


def test_no_future_information_or_false_identity(sample,tmp_path):
    store,bundle_id,snapshot=run(sample,tmp_path,asof="2026-09-12T10:00:00+08:00")
    assert not snapshot["candidates"]
    assert snapshot["market"]["breadth_denominator"]==0
    assert all(s["close"] is None for s in snapshot["features"])
    assert any("不可知" in s for s in snapshot["limitations"])


@pytest.mark.parametrize("failure",["hash","identity","duplicate","ohlc","units","time","calendar"])
def test_bad_input_does_not_partially_import(sample,tmp_path,failure):
    path,bundle,_=sample
    if failure=="hash":bundle["files"][0]["sha256"]="0"*64
    elif failure=="identity":bundle["universe"].append("UNSUPPORTED-ID")
    elif failure=="duplicate":change_file(sample,"daily",lambda rows:rows+[rows[0]])
    elif failure=="ohlc":change_file(sample,"daily",lambda rows:[{**rows[0],"close":0},*rows[1:]])
    elif failure=="units":bundle["files"][2].pop("amount_unit")
    elif failure=="time":bundle["files"][0]["available_at"]="2026-09-01T00:00:00+08:00"
    else:change_file(sample,"calendar",lambda rows:rows[:-1])
    path.write_text(json.dumps(bundle))
    store=ResearchStore(tmp_path/"isolated.duckdb")
    with pytest.raises(ValueError):store.import_bundle(path)
    assert not store.path.exists()


def test_missing_middle_session_never_bridges_returns(sample,tmp_path):
    change_file(sample,"daily",lambda rows:[r for r in rows if not (r["code"]=="STOCK-A" and r["date"]=="2026-09-09")])
    _,_,snapshot=run(sample,tmp_path)
    f=next(f for f in snapshot["features"] if f["code"]=="STOCK-A")
    assert f["consecutive_sessions"]==2 and f["window_return"] is None and f["above_ma"] is None
    assert not snapshot["candidates"]


def test_missing_last_day_not_previous_close(sample,tmp_path):
    change_file(sample,"daily",lambda rows:[r for r in rows if r["date"]!="2026-09-11"])
    _,_,snapshot=run(sample,tmp_path)
    assert all(f["close"] is None for f in snapshot["features"])
    assert not snapshot["candidates"]


def test_adjustment_factor_split_and_missing_factor(sample,tmp_path):
    change_file(sample,"daily",lambda rows:[{**r,**{f:r[f]/2 for f in ("open","high","low","close")}} if r["code"]=="STOCK-A" and r["date"]=="2026-09-11" else r for r in rows])
    change_file(sample,"adj_factor",lambda rows:[{**r,"adj_factor":2.0} if r["code"]=="STOCK-A" and r["date"]=="2026-09-11" else r for r in rows])
    _,_,snapshot=run(sample,tmp_path)
    assert snapshot["features"][0]["window_return"]==pytest.approx(14/11-1)
    change_file(sample,"adj_factor",lambda rows:[r for r in rows if r["code"]!="STOCK-B"])
    # Separate store because changed bundle is an additive, independent input snapshot.
    other=tmp_path/"other";other.mkdir()
    _,_,new=run(sample,other)
    b=next(f for f in new["features"] if f["code"]=="STOCK-B")
    assert b["window_return"] is None and b["price_basis"]=="UNKNOWN"


def test_tushare_units_zero_activity_st_and_suspend(sample,tmp_path):
    change_file(sample,"daily",lambda rows:[{**{("ts_code" if k=="code" else "trade_date" if k=="date" else "vol" if k=="volume" else k):v for k,v in r.items()},"vol":10,"amount":0} for r in rows])
    spec=next(f for f in sample[1]["files"] if f["dataset"]=="daily")
    spec.update(adapter="tushare-v1",volume_unit="lots100",amount_unit="thousand_CNY")
    sample[2]("status",[dict(code="STOCK-A",date="2026-09-11",st="YES",suspended="YES",up_limit=14.,down_limit=10.)])
    sample[0].write_text(json.dumps(sample[1]))
    _,_,snapshot=run(sample,tmp_path)
    a=next(f for f in snapshot["features"] if f["code"]=="STOCK-A")
    assert a["mean_amount_cny"]==0 and a["activity_ratio"] is None
    card=next(c for c in snapshot["candidates"]+snapshot["manual_cards"] if c["code"]=="STOCK-A")
    assert card["status"]["st"]=="YES" and not card["trade_eligible"]
    assert any("价格限制" in s for s in card["no_trade_conditions"])
    with warehouse_connection(tmp_path/"research.duckdb",read_only=True) as db:
        row=db.execute("SELECT payload FROM research_observation WHERE dataset='daily' LIMIT 1").fetchone()
        assert json.loads(row[0])["volume"]==1000


def test_stale_all_closed_and_unknown_exchange(sample,tmp_path):
    _,_,snapshot=run(sample,tmp_path,asof="2026-10-15T20:00:00+08:00")
    assert not snapshot["candidates"] and any("时效" in s for s in snapshot["limitations"])
    change_file(sample,"calendar",lambda rows:[{**r,"is_open":0} for r in rows])
    for dataset in ("daily","index_daily","adj_factor"):
        change_file(sample,dataset,lambda rows:[])
    other=tmp_path/"closed";other.mkdir()
    _,_,closed=run(sample,other)
    assert closed["market"]["breadth_denominator"]==0
    change_file(sample,"instruments",lambda rows:[{**r,"exchange":"UNKNOWN"} for r in rows])
    other=tmp_path/"unknown";other.mkdir()
    _,_,unknown=run(sample,other)
    assert not unknown["candidates"]


def test_journal_append_only_asof_exit_and_followup(sample,tmp_path):
    store,bundle_id,snapshot=run(sample,tmp_path)
    report=store.save_report(snapshot)
    event=dict(event_id="POSITION-1",kind="POSITION",code="STOCK-A",event_at="2026-09-14T10:00:00+08:00",recorded_at="2026-09-15T10:00:00+08:00",
               research_report_id=report,shares=100,thesis="manual hypothesis",invalidation="business evidence contradicts",exit_conditions="user-supplied thesis exit",review_due="2026-09-15T12:00:00+08:00")
    path=tmp_path/"event.json";path.write_text(json.dumps(event))
    assert append_event(store,path)==append_event(store,path)
    result=analyze(store,bundle_id,ASOF,ObservationParameters(**PARAMS))
    assert result["journal"]["positions"][0]["review_overdue"] is True
    earlier=analyze(store,bundle_id,"2026-09-14T20:00:00+08:00",ObservationParameters(**PARAMS))
    assert not earlier["journal"]["positions"]
    event["shares"]=200;path.write_text(json.dumps(event))
    with pytest.raises(ResearchError,match="JOURNAL_ID_CONFLICT"):append_event(store,path)
    event.update(event_id="POSITION-2",shares=0,correction_of="POSITION-1")
    path.write_text(json.dumps(event));append_event(store,path)
    assert not analyze(store,bundle_id,ASOF,ObservationParameters(**PARAMS))["journal"]["positions"]


def test_old_database_never_migrated_and_report_tamper(sample,tmp_path):
    path=tmp_path/"old.duckdb"
    with duckdb.connect(str(path)) as db:db.execute("CREATE TABLE old_fact(i INTEGER); INSERT INTO old_fact VALUES (1)")
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ResearchError,match="NOT_A_RESEARCH_STORE"):ResearchStore(path).import_bundle(sample[0])
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    store,_,snapshot=run(sample,tmp_path)
    run_id=publish(snapshot,tmp_path/"reports")
    report=tmp_path/"reports"/f"{run_id}.report.md";report.write_text("TAMPERED")
    with pytest.raises(ResearchError,match="REPORT_OUTPUT_CHANGED"):publish(snapshot,tmp_path/"reports")
    source=next((store.path.parent/"raw").iterdir());source.write_bytes(b"TAMPERED")
    with pytest.raises(ResearchError,match="RETAINED_SOURCE_CHANGED"):store.snapshot(snapshot["bundle_id"],ASOF)


def test_cli_public_store_and_output_rejected(tmp_path):
    runner=CliRunner()
    result=runner.invoke(app,["research","import","--bundle",str(tmp_path/"missing.json"),"--store",str(tmp_path/"public.duckdb")])
    assert result.exit_code==1 and not (tmp_path/"public.duckdb").exists()
    result=runner.invoke(app,["research","report","--bundle","unknown","--as-of",ASOF,"--output","docs/research-report"])
    assert result.exit_code==1 and "private details suppressed" in result.output
    assert runner.invoke(app,["research","--help"]).exit_code==0


def test_transaction_rollback_keeps_no_partial_business_facts(sample,tmp_path,monkeypatch):
    from astock.data.warehouse_lock import WarehouseConnection
    original=WarehouseConnection.executemany
    def fail_after_first(self,sql,rows):
        original(self,sql,rows[:1])
        raise RuntimeError("SYNTHETIC_WRITE_FAILURE")
    monkeypatch.setattr(WarehouseConnection,"executemany",fail_after_first)
    store=ResearchStore(tmp_path/"research.duckdb")
    with pytest.raises(RuntimeError,match="SYNTHETIC_WRITE_FAILURE"):store.import_bundle(sample[0])
    with warehouse_connection(store.path,read_only=True) as db:
        assert db.execute("SELECT count(*) FROM research_bundle").fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM research_observation").fetchone()[0]==0


def test_retained_source_rebuild_detects_database_fact_tamper(sample,tmp_path):
    store,bundle_id,_=run(sample,tmp_path)
    with warehouse_connection(store.path) as db:
        db.execute("DELETE FROM research_observation WHERE dataset='daily'")
    with pytest.raises(ResearchError,match="STORED_OBSERVATIONS_CHANGED"):store.snapshot(bundle_id,ASOF)


def test_idempotent_import_evidence_and_future_event_rejection(sample,tmp_path):
    evidence=tmp_path/"source-proof.json";evidence.write_text('{"source":"SYNTHETIC"}')
    sample[1]["files"][0]["evidence"]=[dict(path=str(evidence),sha256=hashlib.sha256(evidence.read_bytes()).hexdigest())]
    sample[0].write_text(json.dumps(sample[1]))
    store,bundle_id,_=run(sample,tmp_path)
    assert store.import_bundle(sample[0])==bundle_id
    evidence.write_text("CHANGED")
    with pytest.raises(ValueError):store.import_bundle(sample[0])
    # Rebuild relies on the retained original proof, not on an edited external file.
    assert store.snapshot(bundle_id,ASOF)[0]
    original=sample[1]["files"][0];original["evidence"]=[]
    for spec in sample[1]["files"]:
        spec["retrieved_at"]=spec["available_at"]="2026-09-08T20:00:00+08:00"
    sample[0].write_text(json.dumps(sample[1]))
    with pytest.raises(ValueError):ResearchStore(tmp_path/"future.duckdb").import_bundle(sample[0])


def test_holiday_not_weekday_inference_and_unknown_kind_rejected(sample,tmp_path):
    change_file(sample,"calendar",lambda rows:[{**r,"is_open":0} if r["date"]=="2026-09-09" else r for r in rows])
    for dataset in ("daily","index_daily","adj_factor"):
        change_file(sample,dataset,lambda rows:[r for r in rows if r["date"]!="2026-09-09"])
    _,_,snapshot=run(sample,tmp_path)
    assert snapshot["features"][0]["consecutive_sessions"]==4
    assert snapshot["features"][0]["window_return"]==pytest.approx(14/10-1)
    change_file(sample,"instruments",lambda rows:[{**r,"kind":"STOCK"} for r in rows])
    with pytest.raises(ValueError):ResearchStore(tmp_path/"fake-index.duckdb").import_bundle(sample[0])


def test_cli_actual_import_report_journal_use_only_private_roots(sample,tmp_path,monkeypatch):
    import astock.cli.research as commands
    monkeypatch.setattr(commands,"get_project_root",lambda:tmp_path)
    store=tmp_path/"data/private/research-v1/research.duckdb"
    output=tmp_path/"reports/private/research-v1"
    runner=CliRunner()
    result=runner.invoke(app,["research","import","--bundle",str(sample[0]),"--store",str(store)])
    assert result.exit_code==0,result.output
    bundle_id=result.output.split("bundle=")[1].split(";")[0]
    params=tmp_path/"params.json";params.write_text(json.dumps(PARAMS))
    args=["--bundle",bundle_id,"--as-of",ASOF,"--parameters",str(params),"--store",str(store)]
    result=runner.invoke(app,["research","report",*args,"--output",str(output),"--watch","STOCK-B"])
    assert result.exit_code==0,result.output
    assert len(list(output.glob("*.report.md")))==1
    assert runner.invoke(app,["research","market",*args]).exit_code==0
    assert runner.invoke(app,["research","screen",*args]).exit_code==0
    outside=tmp_path/"public-target";outside.mkdir()
    alias=tmp_path/"data/private/research-v1/escaped";alias.symlink_to(outside,target_is_directory=True)
    result=runner.invoke(app,["research","report",*args,"--output",str(alias)])
    assert result.exit_code==1 and not list(outside.iterdir())


def test_raw_directory_alias_cannot_write_outside_private_store(sample,tmp_path):
    external=tmp_path/"external";external.mkdir()
    (tmp_path/"raw").symlink_to(external,target_is_directory=True)
    with pytest.raises(ResearchError,match="RAW_DIRECTORY_SYMLINK"):
        ResearchStore(tmp_path/"research.duckdb").import_bundle(sample[0])
    assert not list(external.iterdir())
