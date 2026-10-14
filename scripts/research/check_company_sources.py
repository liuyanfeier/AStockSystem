# Independent acceptance helper, not a capture/report pipeline. pypdf comes from the local document runtime.
from pathlib import Path
from decimal import Decimal
import json,re,hashlib
from pypdf import PdfReader
import argparse
parser=argparse.ArgumentParser(description='Independent finite PDF source checks; requires pypdf and Poppler, zero HTTP.')
parser.add_argument('--catalog',type=Path,required=True)
parser.add_argument('--documents',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();root=args.documents
repo=Path(__file__).resolve().parents[2]
c=json.loads(args.catalog.read_text())
readers={s['id']:PdfReader(root/(s['id']+'.pdf')) for s in c['sources']};sources={s['id']:s for s in c['sources']}
checks=[];issues=[]
source_identity_checks=[]
for source in c['sources']:
 reader=readers[source['id']]
 cover_text=''.join(p.extract_text() for p in reader.pages[:10]).replace(' ','')
 actual=hashlib.sha256((root/(source['id']+'.pdf')).read_bytes()).hexdigest()
 code_ok=source['code'].split('.')[0] in cover_text
 source_identity_checks.append(dict(source_id=source['id'],sha256_matches=actual==source['sha256'],native_code_in_front_pages=code_ok,pages=len(reader.pages)))
assert all(s['sha256_matches'] and s['native_code_in_front_pages'] for s in source_identity_checks), 'SOURCE_IDENTITY_CHECK_FAILED'
for company in c['companies']:
 for f in company['financials']:
  sid=f['reference']['source_id'];page=int(re.search(r'第(\d+)页',f['reference']['locator'])[1])
  text=readers[sid].pages[page-1].extract_text(extraction_mode='layout')
  # Independent PDF parser, not pdftotext used for manual transcription.
  pattern = r'\(?-?(?:\d{1,3}(?:,\d{3})+|\d+)\)?' if f['unit']=='CNY_MILLION' else r'\(?-?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}\)?'
  tokens=re.findall(pattern,text)
  nums=set()
  for v in tokens:
   if v.startswith('(') and v.endswith(')'):v='-'+v[1:-1]
   try:nums.add(Decimal(v.replace(',','')))
   except Exception:pass
  valid=Decimal(f['value']) in nums and (f['comparison_value'] is None or Decimal(f['comparison_value']) in nums)
  unit_ok=('百万元' in text) if f['unit']=='CNY_MILLION' else '%' in text if f['unit']=='PERCENT' else ('元' in text)
  unit_method='PYPDF_TEXT'
  if sid=='600036-ndbg-mirror':
   import subprocess
   unit_text=subprocess.run(['pdftotext','-f',str(page),'-l',str(page),'-layout',str(root/(sid+'.pdf')),'-'],capture_output=True,text=True,check=True).stdout
   unit_ok='人民币百万元' in unit_text;unit_method='PDFTOTEXT_UNIT_FALLBACK_GARBLED_UNICODE'

  unit_header_page=None
  if not unit_ok and sid=='605058-zqbg-mirror' and page==49:
   unit_header_page=47
   header=readers[sid].pages[46].extract_text(extraction_mode='layout')
   unit_ok='单位：元' in header.replace(' ','');unit_method='SAME_BALANCE_TABLE_HEADER_PAGE_47'
  change=None
  if f['comparison_value'] is not None and Decimal(f['comparison_value'])>0 and f['unit']!='PERCENT':
   change=100*(Decimal(f['value'])-Decimal(f['comparison_value']))/Decimal(f['comparison_value'])
  match=(change is None or f.get('reported_change_percent') is None or abs(change-Decimal(f.get('reported_change_percent')))<=Decimal('.02'))
  item=dict(code=company['code'],metric=f['id'],source_id=sid,sha256=sources[sid]['sha256'],pdf_page=page,value=f['value'],comparison_value=f['comparison_value'],unit=f['unit'],value_presence=valid,unit_presence=unit_ok,unit_method=unit_method,unit_header_page=unit_header_page,independent_change_percent=str(change) if change is not None else None,reported_rounding_match=match)
  checks.append(item)
  if not(valid and unit_ok and match):issues.append(item)
reference_checks=[]
for company in c['companies']:
 for group in ['profile','events','support','counter','unknowns']:
  for statement in company[group]:
   for reference in statement.get('references',[]):
    sid=reference['source_id'];page=int(re.search(r'第(\d+)页',reference['locator'])[1])
    reference_checks.append(dict(code=company['code'],statement_id=statement['id'],source_id=sid,pdf_page=page,in_document_bounds=1<=page<=len(readers[sid].pages)))
assert all(r['in_document_bounds'] for r in reference_checks)
result=dict(source_identity_checks=source_identity_checks,reference_checks=reference_checks,protocol='COMPANY_SOURCE_NUMERICAL_CHECK_V1',method='手工按原表转录后，用独立pypdf布局提取逐页复核数值/单位；Decimal另算同比。同页数字存在校验不能单独证明行归属，8家主要财务表另作视觉核对。',companies=len(c['companies']),figures=len(checks),value_checks=sum(x['value_presence'] for x in checks),unit_checks=sum(x['unit_presence'] for x in checks),issues=issues,checks=checks)
args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['checks','method','issues','reference_checks','source_identity_checks']},ensure_ascii=False)); print('issues',[(i['code'],i['metric'],i['value_presence'],i['unit_presence']) for i in issues])
