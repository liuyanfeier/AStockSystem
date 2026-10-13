"""Reproduce the SYNTHETIC 299-request radar example with closed mocks, zero HTTP."""
import argparse
from pathlib import Path
import sys
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from astock.features.market import ObservationParameters
from astock.research.core import digest,encoded,read_json
from astock.research.public_results import publish_public
from astock.research.service import analyze
from astock.research.store import ResearchStore
from astock.research.tushare import make_capture_bundle
from market_fixture import plan,response
from research_fixture import approved_mock,BytesStream,ASOF


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('docs/research/results/2026-10-13-research-v2/synthetic'))
    args=parser.parse_args()
    work=args.work.resolve();work.mkdir(parents=True,exist_ok=True)
    p=plan()
    result,_,destination=approved_mock(work,p,lambda m,n:httpx.Response(200,stream=BytesStream(encoded(response(p,m)))))
    assert result['complete_this_run']==299,result
    manifest=make_capture_bundle(destination)
    store=ResearchStore(destination/'research.duckdb')
    bid=store.import_bundle(destination/f'{digest(manifest)}.bundle.json')
    parameters=ObservationParameters.model_validate(read_json(Path('config/research/observation-v1.json')))
    report=analyze(store,bid,ASOF,parameters,radar=True)
    run=publish_public(report,Path.cwd(),args.output)
    print(dict(mode='SYNTHETIC',mock_requests=299,real_market_requests=0,public_projection=run))


if __name__=='__main__':main()
