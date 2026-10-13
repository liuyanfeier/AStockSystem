"""Compose verified immutable bundles; corrections need explicit source selections."""
from astock.research.core import digest, require

PROVENANCE = {'source_hash', 'retrieved_at', 'available_at', 'evidence_grade', 'component_sources'}


def revision_key(dataset: str, row: dict) -> str:
    if dataset == 'calendar':
        return digest([dataset, row['exchange'], row['date']])
    if dataset == 'status':
        return digest([dataset,row['code'],row['date'],row.get('status_event',{}).get('api'),row.get('event_key')])
    if dataset == 'industry_membership':
        return digest([dataset, row['code']])
    return digest([dataset, row.get('code'), row.get('date'), row.get('industry_code')])


def compose(store, bundles: list[str], as_of: str, revisions: dict[str, str]) -> tuple[dict, dict]:
    require(len(set(bundles)) == len(bundles), 'INCREMENT_DUPLICATE_BUNDLE')
    verified = [store.snapshot(b, as_of) for b in bundles]
    primary = verified[0][0]
    require(all(m['purpose'] == primary['purpose'] and m['benchmarks'] == primary['benchmarks'] for m,_ in verified), 'INCREMENT_PURPOSE_OR_BENCHMARK')
    records = {}
    sources = {}
    allowed = set(primary['universe'] + primary['benchmarks'])
    ignored = set()
    for manifest, rows in verified:
        for source in manifest['files']:
            sources[digest(source)] = source
        for dataset, values in rows.items():
            for row in values:
                if row.get('code') and row['code'] not in allowed and dataset != 'industry_membership':
                    ignored.add(row['code'])
                    continue
                key = revision_key(dataset,row)
                records.setdefault((dataset,key), []).append(row)
    result, used = {}, set()
    for (dataset,key), versions in sorted(records.items()):
        semantic = {digest({k:v for k,v in r.items() if k not in PROVENANCE}) for r in versions}
        choice = revisions.get(key)
        if len(semantic)>1:
            require(choice is not None, 'INCREMENT_REVISION_SELECTION_REQUIRED')
        if choice is not None:
            matches = [r for r in versions if r['source_hash']==choice]
            require(bool(matches), 'INCREMENT_SELECTION_UNKNOWN_SOURCE')
            require(len({digest({k:v for k,v in r.items() if k not in PROVENANCE}) for r in matches})==1, 'INCREMENT_SOURCE_CONFLICT')
            row = matches[0]
            used.add(key)
        else:
            row = min(versions,key=lambda r:(r.get('available_at',''),r['source_hash']))
        result.setdefault(dataset,[]).append({**row, 'component_sources': sorted({r['source_hash'] for r in versions})})
    require(set(revisions)==used, 'INCREMENT_UNUSED_SELECTION')
    manifest = {**primary, 'window_start': min(m['window_start'] for m,_ in verified),
                'window_end': max(m['window_end'] for m,_ in verified), 'files':[sources[k] for k in sorted(sources)],
                'composition': dict(component_ids=bundles, revisions=revisions, ignored_outside_current_pool=sorted(ignored),
                                    basis='来源逐个完整验证；重复数值合并保留来源；冲突由明确record-key/source-hash选择')}
    identities = {r['code']:r for r in result.get('instruments',[])}
    require(set(identities)==allowed, 'INCREMENT_IDENTITIES_UNAVAILABLE')
    # Completeness of the enlarged civil-day calendar is proved here; gaps in prices remain UNKNOWN.
    from datetime import timedelta
    from astock.research.core import day
    start,end = day(manifest['window_start']),day(manifest['window_end'])
    calendars = {(r['exchange'],r['date']):r for r in result.get('calendar',[])}
    for exchange in {r.get('calendar_exchange',r['exchange']) for r in identities.values()}-{'UNKNOWN'}:
        require(all((exchange,(start+timedelta(days=i)).isoformat()) in calendars for i in range((end-start).days+1)), 'INCREMENT_CALENDAR_GAP')
    for dataset in ('daily','index_daily','adj_factor','status'):
        for row in result.get(dataset,[]):
            identity = identities[row['code']]
            require(identity['kind']==('INDEX' if dataset=='index_daily' else 'STOCK'), 'INCREMENT_KIND')
            if identity.get('list_date'):
                require(day(row['date'])>=day(identity['list_date']), 'INCREMENT_PRE_LISTING')
            exchange=identity.get('calendar_exchange',identity['exchange'])
            require(exchange=='UNKNOWN' or calendars[(exchange,row['date'])]['is_open']==1,'INCREMENT_NON_SESSION')
    return manifest,result
