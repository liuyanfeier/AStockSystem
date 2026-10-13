"""Whitelist public business results; never copy a private report directory to Git."""
from copy import deepcopy
from pathlib import Path
from astock.research.core import digest, encoded, require
from astock.research.publication import publish_bytes


def public_snapshot(snapshot: dict) -> dict:
    allowed = {'protocol','purpose','bundle_id','as_of','window_start','window_end','code_hash',
               'parameters','parameters_hash','market','features','candidates','manual_cards','excluded',
               'limitations','radar','composition'}
    result = deepcopy({k:v for k,v in snapshot.items() if k in allowed})
    sources = []
    for source in snapshot['sources']:
        s = {k:v for k,v in source.items() if k not in {'path','evidence'}}
        s['evidence_hashes'] = [e['sha256'] for e in source.get('evidence',[])]
        sources.append(s)
    result.update(sources=sources, publication=dict(private_snapshot_hash=digest(snapshot),
                  personal_records_included=False, raw_included=False,
                  evidence_limit='业务数值/来源hash可审查；没有私有Raw/许可访问权时不能独立证明供应商真实性'))
    # Never publish actual positions or manual notes/event ids, even if the account seems empty.
    result['journal'] = dict(positions=[], pending_confirmation=[], events_hash=None,
                             limitation='个人持仓/成交/复盘记录不公开；未取得账户信息不能宣称空仓')
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
