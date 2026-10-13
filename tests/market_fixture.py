"""Deterministic vendor-shaped V2 responses, labelled SYNTHETIC everywhere."""
from pathlib import Path
from astock.research.core import read_json
from research_fixture import civil_days, is_session


def plan():
    return read_json(Path('config/research/market-v2-proposal.json'))


def pool(n=10):
    exchanges = ['SSE','SSE','SZSE','SZSE','BSE','SSE','SZSE','SZSE','BSE','SSE']
    markets = ['主板','科创板','主板','创业板','北交所','主板','创业板','主板','北交所','主板']
    return [dict(ts_code=f'SYNTHETIC-{i}', name=f'合成股票{i}',exchange=exchanges[i%10],market=markets[i%10],
                 list_date='20260828' if i==8 else '20000101',list_status='L',curr_type='CNY') for i in range(n)]


def response(p,m,n=10):
    api,params=m['api'],m['params']
    dates=[d for d in civil_days(p) if is_session(d)]
    securities=pool(n)
    rows=[]
    if api=='stock_basic':rows=[r for r in securities if r['exchange']==params['exchange']]
    elif api=='index_basic':rows=[dict(ts_code=params['ts_code'],name='合成基准',market='CSI',publisher='合成')]
    elif api=='trade_cal':
        rows=[dict(exchange=params['exchange'],cal_date=d.strftime('%Y%m%d'),is_open=is_session(d),pretrade_date=None) for d in civil_days(p)]
    elif api=='index_classify':
        rows=[dict(index_code=c,industry_name='合成银行' if c=='801780.SI' else '合成行业'+c,parent_code='0',level='L1',industry_code=c,is_pub='1',src='SW2021') for c in p['industry_codes']]
    elif api=='index_member_all':
        for i,r in enumerate(securities):
            industry='801780.SI' if i%10 in (0,3,4,5) else p['industry_codes'][i%2]
            if params['l1_code'] == industry:
                rows.append(dict(l1_code=industry,l1_name='合成行业',l2_code='TEST-L2',l2_name='合成二级',l3_code='TEST-L3',l3_name='合成三级',
                                 ts_code=r['ts_code'],name=r['name'],in_date=None if i==8 else '20000101',out_date=None,is_new='Y'))
    elif api=='index_daily':
        for i,d in enumerate(dates):
            close=1000+i
            rows.append(dict(ts_code=params['ts_code'],trade_date=d.strftime('%Y%m%d'),open=close,high=close+1,low=close-1,close=close,pre_close=close-1,vol=100,amount=100000))
    elif api in ('daily','adj_factor'):
        d=__import__('datetime').datetime.strptime(params['trade_date'],'%Y%m%d').date()
        i=dates.index(d)
        for k,r in enumerate(securities):
            if d < __import__('datetime').datetime.strptime(r['list_date'],'%Y%m%d').date():continue
            if k==6 and i==len(dates)-5 and api=='daily':continue
            if k==7 and i==len(dates)-1 and api=='adj_factor':continue
            factor=2 if k==3 and i>=90 else 1
            trend= -.05 if k%10 in (1,9) else 0 if k%10==2 else .1
            close=(20+i*trend)/factor
            rows.append(dict(ts_code=r['ts_code'],trade_date=d.strftime('%Y%m%d'),open=close,high=close+.01/factor,low=close-.01/factor,
                             close=close,pre_close=close-.1/factor,vol=10000,amount=0 if k==9 else 20000+i*100,adj_factor=factor))
    return dict(request_id='SYNTHETIC_V2',code=0,msg='',data=dict(fields=m['fields'],items=[[r[f] for f in m['fields']] for r in rows]))
