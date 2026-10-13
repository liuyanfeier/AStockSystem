from copy import deepcopy
import pytest
from astock.research.core import ResearchError,digest
from astock.research.increment import compose,revision_key


class VerifiedStore:
    def __init__(self, snapshots):self.snapshots=snapshots;self.checked=[]
    def snapshot(self,bid,asof):
        self.checked.append((bid,asof))
        return self.snapshots[bid]


def snapshot(start,end,prices, *, name='current'):
    manifest=dict(protocol='RESEARCH_INPUT_V1',purpose='CURRENT_OBSERVATION',window_start=start,window_end=end,
                  universe=['C'],benchmarks=[],universe_scope='WATCHLIST',files=[dict(sha256=name)])
    from datetime import date,timedelta
    d=date.fromisoformat(start);last=date.fromisoformat(end);cal=[]
    while d<=last:
        cal.append(dict(exchange='SSE',date=d.isoformat(),is_open=1,source_hash=name));d+=timedelta(days=1)
    return manifest,dict(instruments=[dict(code='C',exchange='SSE',kind='STOCK',source_hash=name)],
                         calendar=cal,daily=prices)


def test_increment_verified_union_retains_sources_and_old_snapshot():
    a=snapshot('2026-09-01','2026-09-02',[dict(code='C',date='2026-09-01',close=10,source_hash='a')],name='a')
    b=snapshot('2026-09-02','2026-09-03',[dict(code='C',date='2026-09-03',close=12,source_hash='b')],name='b')
    store=VerifiedStore({'A':a,'B':b});before=deepcopy(a)
    m,rows=compose(store,['B','A'],'2026-09-04T00:00:00+08:00',{})
    assert len(store.checked)==2
    assert m['window_start']=='2026-09-01' and m['window_end']=='2026-09-03'
    assert sorted(r['close'] for r in rows['daily'])==[10,12]
    assert rows['instruments'][0]['component_sources']==['a','b']
    assert a==before


def test_increment_equal_duplicates_and_explicit_revision():
    row=dict(code='C',date='2026-09-01',close=10,source_hash='a')
    a=snapshot('2026-09-01','2026-09-01',[row],name='a')
    b=snapshot('2026-09-01','2026-09-01',[{**row,'source_hash':'b'}],name='b')
    store=VerifiedStore({'A':a,'B':b})
    _,r=compose(store,['A','B'],'2026-09-02T00:00:00Z',{})
    assert len(r['daily'])==1 and r['daily'][0]['component_sources']==['a','b']
    b[1]['daily'][0]['close']=11
    with pytest.raises(ResearchError,match='INCREMENT_REVISION_SELECTION_REQUIRED'):compose(store,['A','B'],'2026-09-02T00:00:00Z',{})
    key=revision_key('daily',row)
    _,r=compose(store,['A','B'],'2026-09-02T00:00:00Z',{key:'b'})
    assert r['daily'][0]['close']==11 and a[1]['daily'][0]['close']==10
    with pytest.raises(ResearchError,match='INCREMENT_SELECTION_UNKNOWN_SOURCE'):compose(store,['A','B'],'2026-09-02T00:00:00Z',{key:'not-a-source'})
    with pytest.raises(ResearchError,match='INCREMENT_UNUSED_SELECTION'):compose(store,['A','B'],'2026-09-02T00:00:00Z',{key:'b','extra':'b'})


def test_increment_disjoint_calendar_gap_and_benchmark_scope():
    a=snapshot('2026-09-01','2026-09-01',[])
    b=snapshot('2026-09-03','2026-09-03',[])
    store=VerifiedStore({'A':a,'B':b})
    with pytest.raises(ResearchError,match='INCREMENT_CALENDAR_GAP'):compose(store,['A','B'],'2026-09-04T00:00:00Z',{})
    b[0]['benchmarks']=['UNKNOWN']
    with pytest.raises(ResearchError,match='INCREMENT_PURPOSE_OR_BENCHMARK'):compose(store,['A','B'],'2026-09-04T00:00:00Z',{})
    with pytest.raises(ResearchError,match='INCREMENT_DUPLICATE_BUNDLE'):compose(store,['A','A'],'2026-09-04T00:00:00Z',{})


def test_status_apis_not_silently_coalesced():
    assert revision_key('status',dict(code='C',date='2026-09-01',status_event=dict(api='stock_st'))) != revision_key('status',dict(code='C',date='2026-09-01',status_event=dict(api='stk_limit')))
