#!/usr/bin/env python3
"""Offline reproducible stage profiling using ONLY explicitly synthetic responses."""
from pathlib import Path
import argparse
import hashlib
import json
import runpy
import resource
import sys
import time
import tracemalloc

from astock.features.market import ObservationParameters, features
from astock.reports.research import publish
from astock.research.core import encoded, private_path, read_json
from astock.research.publication import publish_bytes
from astock.research.service import analyze
from astock.research.store import ResearchStore
from astock.research.tushare import DATASETS


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--size',type=int,default=10)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    output=private_path(root,args.output)
    output.mkdir(parents=True,exist_ok=True)
    support=runpy.run_path(str(root/'tests/research_fixture.py'))
    plan=support['fixture_plan'](args.size)
    files=[]
    for i,m in enumerate(plan['members']):
        body=encoded(support['response'](plan,m))
        path=output/f'{i}.response.json';publish_bytes(path,body)
        spec=dict(path=str(path),sha256=hashlib.sha256(body).hexdigest(),dataset=DATASETS[m['api']],
                  format='json',adapter='tushare-response-v1',request=m,source='SYNTHETIC PROFILE',
                  retrieved_at=support['ASOF'],available_at=support['ASOF'],evidence_grade='SYNTHETIC')
        if m['api']=='index_basic':spec['calendar_exchange']='SSE'
        if m['api'] in {'daily','index_daily'}:spec.update(volume_unit='lots100',amount_unit='thousand_CNY')
        files.append(spec)
    bundle=dict(protocol='RESEARCH_INPUT_V1',purpose='CURRENT_OBSERVATION',window_start=plan['window_start'],window_end=plan['window_end'],
                universe=plan['universe'],benchmarks=plan['benchmarks'],universe_scope='WATCHLIST',files=files)
    path=output/'bundle.json';publish_bytes(path,encoded(bundle))
    p=ObservationParameters.model_validate(read_json(root/'config/research/observation-v1.json'))
    store=ResearchStore(output/'research.duckdb')
    metrics={}
    def stage(name,fn):
        tracemalloc.start();start=time.perf_counter();result=fn()
        elapsed=time.perf_counter()-start;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        metrics[name]=dict(seconds=round(elapsed,4),python_peak_bytes=peak,
                           process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024))
        return result
    bid=stage('import',lambda:store.import_bundle(path))
    manifest,rows=stage('full_source_verification_and_read',lambda:store.snapshot(bid,support['ASOF']))
    identities={r['code']:r for r in rows['instruments']}
    stage('features',lambda:[features(c,identities[c],rows.get('daily' if c in plan['universe'] else 'index_daily',[]),
                                          rows['adj_factor'],rows['calendar'],p_end(manifest),p) for c in plan['universe']+plan['benchmarks']])
    snapshot=stage('analyze_including_full_audit',lambda:analyze(store,bid,support['ASOF'],p))
    stage('report_publication',lambda:publish(snapshot,output/'reports'))
    metrics.update(size=args.size,sessions=snapshot['features'][0]['expected_sessions'],
                   logical_bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),synthetic=True,
                   note='tracemalloc reports Python allocations, not native DuckDB/Arrow RSS')
    (output/'profile.json').write_bytes(encoded(metrics)+b'\n')
    print(json.dumps(metrics,indent=2))


def p_end(manifest):
    from astock.research.core import day
    return day(manifest['window_end'])


if __name__=='__main__':main()
