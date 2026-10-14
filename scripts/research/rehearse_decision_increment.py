"""Read real 128-session Store, compose six marked synthetic prices; zero HTTP/writes to originals."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from astock.research.core import digest, encoded, read_json
from astock.research.increment import compose
from astock.research.store import ResearchStore
from astock.research.publication import publish_bytes
from astock.decision.increment import LinkedResearchStore
from astock.features.market import ObservationParameters, features


def main():
    root=Path(__file__).resolve().parents[2]
    original=root/'data/private/research-v1/market-v2-20261013-002/research.duckdb'
    market=read_json(root/'docs/research/results/2026-10-14-real-market-v2/0d235e75a112e3e3a03da497c51fd550ea3551e9c80d3f247dd92a5e363db9ef.json')
    cutoff='2026-10-16T16:00:00+08:00';store=ResearchStore(original)
    before=sha256(original.read_bytes()).hexdigest()
    manifest,rows=store.snapshot(market['bundle_id'],cutoff)
    selected=['600036.SH','000002.SZ','601872.SH']
    source_hash=digest(['OFFLINE_SYNTHETIC_INCREMENT',selected,'2026-10-13','2026-10-14'])
    prices=[];factors=[]
    for code in selected:
        price=next(r for r in rows['daily'] if r['code']==code and r['date']=='2026-10-12')
        factor=next(r for r in rows['adj_factor'] if r['code']==code and r['date']=='2026-10-12')
        for date,scale in [('2026-10-13',1.01),('2026-10-14',.99)]:
            bar={**price,'date':date,'source_hash':source_hash,'evidence_grade':'SYNTHETIC'}
            bar.update({k:price[k]*scale for k in ('open','high','low','close') if k in price})
            prices.append(bar)
            factors.append({**factor,'date':date,'source_hash':source_hash,'evidence_grade':'SYNTHETIC'})
    calendars=[dict(exchange=e,date=d,is_open=1,source_hash=source_hash,evidence_grade='SYNTHETIC') for e in ('SSE','SZSE') for d in ('2026-10-13','2026-10-14')]
    delta_manifest={**manifest,'window_start':'2026-10-13','window_end':'2026-10-14','files':[]}
    delta_rows=dict(instruments=rows['instruments'],industry_membership=rows.get('industry_membership',[]),calendar=calendars,daily=prices,adj_factor=factors)
    class SyntheticDelta:
        def snapshot(self,bid,asof):
            assert bid=='MARKED_SYNTHETIC_DELTA' and asof==cutoff
            return delta_manifest,delta_rows
    linked=LinkedResearchStore(store,{'MARKED_SYNTHETIC_DELTA':SyntheticDelta()})
    combined,merged=compose(linked,['MARKED_SYNTHETIC_DELTA',market['bundle_id']],cutoff,{})
    # Every old row survives semantically, with provenance preserved; there is no old-window copy/database.
    old_daily={digest(r) for r in rows['daily']}
    semantic=lambda r:{k:v for k,v in r.items() if k!='component_sources'}
    assert old_daily <= {digest(semantic(r)) for r in merged['daily']}
    params=ObservationParameters.model_validate(market['parameters']);checks=[]
    for code in selected:
        identity=next(r for r in merged['instruments'] if r['code']==code)
        calendar=[r for r in merged['calendar'] if r['exchange']==identity.get('calendar_exchange',identity['exchange'])]
        result=features(code,identity,[r for r in merged['daily'] if r['code']==code],
                        [r for r in merged['adj_factor'] if r['code']==code],calendar,
                        __import__('datetime').date(2026,10,14),params,radar=True)
        checks.append({k:result[k] for k in ('code','last_date','close','consecutive_sessions','return_20','ma20','ma60')})
    assert sha256(original.read_bytes()).hexdigest()==before
    output=root/'docs/research/results/2026-10-14-decision-loop-v0/INCREMENT_REHEARSAL.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    summary=dict(mode='REAL_BASE_PLUS_MARKED_SYNTHETIC_DELTA',base_window=[manifest['window_start'],manifest['window_end']],
                 composed_window=[combined['window_start'],combined['window_end']],base_sessions=128,
                 synthetic_sessions=2,synthetic_price_rows=6,expected_company_sessions=130,
                 company_checks=checks,old_daily_rows=len(old_daily),old_daily_rows_retained=True,original_store_unchanged=True,
                 original_store_sha256=before,old_window_database_copies=0,market_requests=0,
                 limitation='只读真实基底+显式合成delta适配器验证compose/features；不是已采集/导入真实13或14日行情；其他股票新日缺失，不生成伪全市场覆盖')
    publish_bytes(output,encoded(summary)+b'\n');print('offline actual-base composition passed',len(old_daily),checks)


if __name__=='__main__':main()
