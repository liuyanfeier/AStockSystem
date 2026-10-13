"""Whitelist public business results; never copy a private report directory to Git."""
from copy import deepcopy
from pathlib import Path
from astock.research.core import digest, encoded, require
from astock.research.publication import publish_bytes


def public_snapshot(snapshot: dict) -> dict:
    allowed = {'protocol','purpose','bundle_id','as_of','window_start','window_end','code_hash',
               'parameters','parameters_hash','market','features','candidates','excluded',
               'limitations','radar','composition'}
    result = deepcopy({k:v for k,v in snapshot.items() if k in allowed})
    # Intern repeated provenance vectors without dropping any business metric or source.
    # A full-market JSON must not repeat the same daily source hashes thousands of times.
    source_hash_sets = {}
    for feature in result.get('features', []):
        hashes = sorted(set(feature.pop('source_hashes', [])))
        key = digest(hashes)
        source_hash_sets[key] = hashes
        feature['source_hash_set_id'] = key
    result['source_hash_sets'] = source_hash_sets
    # A manual list is personal even when it contains otherwise public tickers.
    result['manual_cards'] = []
    sources = []
    for source in snapshot['sources']:
        allowed_source = {'dataset', 'sha256', 'retrieved_at', 'available_at', 'format',
                          'adapter', 'calendar_exchange', 'evidence_grade', 'volume_unit', 'amount_unit'}
        s = {k:deepcopy(v) for k,v in source.items() if k in allowed_source}
        # Free-form source descriptions and request extensions are private input.
        s['source'] = ('Tushare本地采集链' if s.get('evidence_grade') == 'LOCAL_CAPTURE_BOUND'
                       else '合成测试来源' if s.get('evidence_grade') == 'SYNTHETIC'
                       else '用户声明来源（说明不公开）')
        s['evidence_hashes'] = [e['sha256'] for e in source.get('evidence',[])]
        sources.append(s)
    result.update(sources=sources, publication=dict(private_snapshot_hash=digest(snapshot),
                  protocol='RESEARCH_PUBLIC_V2_1', source_lineage='features reference source_hash_sets; cards retain hashes',
                  personal_records_included=False, raw_included=False,
                  evidence_limit='业务数值/来源hash可审查；没有私有Raw/许可访问权时不能独立证明供应商真实性'))
    return result


def publish_public(snapshot: dict, root: Path, output: Path) -> str:
    root = root.resolve()
    target = (root/output).absolute() if not output.is_absolute() else output.absolute()
    current = target
    while current != current.parent:
        require(not current.is_symlink(), 'PUBLIC_REPORT_SYMLINK')
        current = current.parent
    require(target.resolve().is_relative_to(root/'docs/research/results'), 'PUBLIC_REPORT_PATH')
    from astock.reports.research import markdown
    result = public_snapshot(snapshot)
    run = digest(result)
    target.mkdir(parents=True, exist_ok=True)
    publish_bytes(target/f'{run}.json', encoded(result)+b'\n')
    publish_bytes(target/f'{run}.md', markdown(result).encode())
    return run
