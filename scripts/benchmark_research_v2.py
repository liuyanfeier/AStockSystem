"""Offline deterministic scale benchmark. No network and no actual investment signals."""
import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from astock.features.market import features,ObservationParameters
from astock.research.core import encoded,read_json,digest
from astock.research.store import ResearchStore
from astock.research.tushare import make_capture_bundle
from research_fixture import approved_mock,BytesStream,ASOF
from market_fixture import plan,response
import httpx


def main():
    args=argparse.ArgumentParser()
    args.add_argument('--output',type=Path,required=True)
    args.add_argument('--store-stocks',type=int,default=0)
    args.add_argument('--work',type=Path,default=Path('/tmp/astock-v2-profile'))
    a=args.parse_args()
    a.work = a.work.resolve()
    p=ObservationParameters.model_validate(read_json(Path('config/research/observation-v1.json')))
    cal=[dict(exchange='SSE',date=(date(2026,4,1)+timedelta(days=i)).isoformat(),is_open=1,source_hash='a'*64) for i in range(128)]
    result=dict(scope='SYNTHETIC; feature calculation excludes SQL/Raw unless store measurements listed',features=[])
    for n in [100,500,6000]:
        prices=[dict(code=f'TEST-{c}',date=r['date'],close=10+i*.01,high=10.1+i*.01,low=9.9+i*.01,amount=1e8,source_hash='b'*64) for c in range(n) for i,r in enumerate(cal)]
        factors=[dict(code=r['code'],date=r['date'],adj_factor=1,source_hash='c'*64) for r in prices]
        begin=time.perf_counter()
        groups=defaultdict(list);fg=defaultdict(list)
        for r in prices:groups[r['code']].append(r)
        for r in factors:fg[r['code']].append(r)
        for c in range(n):features(f'TEST-{c}',dict(kind='STOCK',exchange='SSE'),groups[f'TEST-{c}'],fg[f'TEST-{c}'],cal,date(2026,8,6),p,radar=True)
        result['features'].append(dict(stocks=n,price_rows=len(prices),seconds=time.perf_counter()-begin))
        del prices,factors,groups,fg
    if a.store_stocks:
        a.work.mkdir(parents=True,exist_ok=True)
        capture_plan=plan()
        before=time.perf_counter()
        captured,_,destination=approved_mock(a.work,capture_plan,lambda m,n:httpx.Response(200,stream=BytesStream(encoded(response(capture_plan,m,a.store_stocks)))))
        assert captured['complete_this_run']==299,captured
        result['mock_capture_seconds']=time.perf_counter()-before
        before=time.perf_counter()
        manifest=make_capture_bundle(destination)
        result['manifest_seconds']=time.perf_counter()-before
        store=ResearchStore(destination/'research.duckdb')
        before=time.perf_counter();bid=store.import_bundle(destination/f'{digest(manifest)}.bundle.json')
        result['import_seconds']=time.perf_counter()-before
        before=time.perf_counter();_,rows=store.snapshot(bid,ASOF)
        result['verified_snapshot_seconds']=time.perf_counter()-before
        before=time.perf_counter();store.snapshot(bid,ASOF)
        result['repeated_verified_snapshot_seconds']=time.perf_counter()-before
        from astock.research.service import analyze
        before=time.perf_counter();report=analyze(store,bid,ASOF,p,radar=True)
        result['radar_seconds_after_snapshot']=time.perf_counter()-before
        assert len(report['features'])==a.store_stocks
        result['store_stocks']=a.store_stocks
        result['normalized_rows']=sum(len(v) for v in rows.values())
        result['disk_bytes']=sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())
        print({k:v for k,v in result.items() if k!='features'},flush=True)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(encoded(result)+b'\n')
    print(result,flush=True)


if __name__=='__main__':main()
