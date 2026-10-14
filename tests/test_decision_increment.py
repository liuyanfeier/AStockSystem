"""Read-only linked stores and accurate bounded pending proposal."""
from pathlib import Path
from astock.decision.increment import LinkedResearchStore
from astock.research.increment import compose
from astock.research.market_capture import parse_plan
from astock.research.core import read_json
from test_research_increment import VerifiedStore, snapshot


def test_linked_stores_compose_without_copying_old_window(tmp_path):
    a=snapshot('2026-09-01','2026-09-02',[dict(code='C',date='2026-09-01',close=10,source_hash='a')],name='a')
    b=snapshot('2026-09-02','2026-09-03',[dict(code='C',date='2026-09-03',close=12,source_hash='b')],name='b')
    primary=VerifiedStore({'B':b});primary.path=tmp_path/'new.duckdb'
    old=VerifiedStore({'A':a})
    linked=LinkedResearchStore(primary,{'A':old})
    m,r=compose(linked,['B','A'],'2026-09-04T00:00:00+08:00',{})
    assert old.checked==[('A','2026-09-04T00:00:00+08:00')] and primary.checked==[('B','2026-09-04T00:00:00+08:00')]
    assert len(r['daily'])==2 and not primary.path.exists()


def test_pending_update_exact_dates_attempts_capacity_no_authorization():
    p=parse_plan(read_json(Path('config/research/decision-market-20261013-14-proposal.json')))
    assert len(p.members)==p.maximum_requests==p.maximum_attempts==49
    assert str(p.window_start)=='2026-10-13' and str(p.window_end)=='2026-10-14'
    assert not p.execution_authorized and p.retries==p.redirects==0
    assert p.max_total_body_bytes==49*2*1024**2 and p.max_added_disk_bytes==384*1024**2
    for api in ('daily','adj_factor','suspend_d','stock_st'):
        assert [m['params']['trade_date'] for m in p.members if m['api']==api]==['20261013','20261014']
    assert not Path(p.destination).exists()
