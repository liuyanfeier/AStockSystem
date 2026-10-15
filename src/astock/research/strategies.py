"""Source-bound, whole-pool strategy observations; no real fills or private Journal."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from astock.decision.increment import LinkedResearchStore
from astock.features.strategy import strategy_frames
from astock.research.core import digest, encoded, instant, require
from astock.research.increment import compose
from astock.research.publication import publish_bytes
from astock.research.store import ResearchStore
from astock.screening.strategies import evaluate_strategy, strategy_code_hash
from astock.screening.strategy_models import StrategyParameters


def observe_setups(primary: ResearchStore, bundle: str, as_of: str, required_market_date: str,
                    parameters: StrategyParameters, *, components: list[str] | None = None,
                    owners: dict[str, ResearchStore] | None = None,
                    revisions: dict[str, str] | None = None) -> dict:
    require(instant(as_of) >= parameters.frozen_at, 'STRATEGY_PARAMETERS_AFTER_ASOF')
    store = LinkedResearchStore(primary, owners or {})
    members = components or []
    manifest, rows = compose(store, [bundle,*members], as_of, revisions or {}) if members else store.snapshot(bundle,as_of)
    return observations_from_snapshot(manifest, rows, [bundle, *members], as_of, required_market_date, parameters)


def observations_from_snapshot(manifest: dict, rows: dict, bundle_ids: list[str], as_of: str,
                               required_market_date: str, parameters: StrategyParameters) -> dict:
    """Compute from verified application inputs; no source admission or persistence here."""
    require(instant(as_of) >= parameters.frozen_at, 'STRATEGY_PARAMETERS_AFTER_ASOF')
    grades = sorted({f.get('evidence_grade','USER_DECLARED') for f in manifest['files']})
    synthetic = grades == ['SYNTHETIC']
    require(synthetic or instant(as_of) <= datetime.now(timezone.utc), 'STRATEGY_FUTURE_REAL_OBSERVATION')
    frames = strategy_frames(manifest,rows,as_of,required_market_date,parameters)
    summary = {variant:dict(pool=len(frames),known=0,unknown=0,condition_matches=0,
                           first_matches=0,paper_ready=0,rejection_reasons=Counter(),paper_blockers=Counter())
               for variant in parameters.variants}
    observations, hash_sets = [], {}
    for frame in frames:
        if synthetic:
            frame = frame.model_copy(update={'knowledge_basis':'OFFLINE_SYNTHETIC'})
        for variant in parameters.variants:
            value = evaluate_strategy(frame,parameters,variant)
            counts = summary[variant]
            counts['unknown' if value['condition_match'] is None else 'known'] += 1
            counts['condition_matches'] += value['condition_match'] is True
            counts['first_matches'] += value['first_match'] is True
            counts['paper_ready'] += value['paper_ready']
            counts['rejection_reasons'].update(value['rejection_reasons'])
            counts['paper_blockers'].update(value['paper_blockers'])
            if value['condition_match'] is True:
                observations.append(value)
                hash_sets[value['source_hash_set_id']] = frame.source_hashes
    ranked = {}
    for variant in parameters.variants:
        candidates = [v for v in observations if v['variant']==variant]
        ranked[variant] = sorted(candidates,key=lambda v:(not bool(v['first_match']),
            -Decimal(v['metrics']['relative_return']),v['code']))[:parameters.top_n]
    return dict(protocol='STRATEGY_OBSERVATIONS_V1',mode='OFFLINE_SYNTHETIC' if synthetic else 'CURRENT_OBSERVATION',
        as_of=instant(as_of).isoformat(),market_date=manifest['window_end'],required_market_date=required_market_date,
        parameters=parameters.model_dump(mode='json'),parameters_hash=digest(parameters.model_dump(mode='json')),
        code_hash=strategy_code_hash(),bundle_ids=bundle_ids,source_manifest_hash=digest(manifest),
        source_grades=grades,source_hash_sets=hash_sets,
        summary={v:{**c,'rejection_reasons':dict(c['rejection_reasons']),'paper_blockers':dict(c['paper_blockers'])}
                 for v,c in summary.items()},observations=observations,ranked=ranked,
        full_matching_observations_retained=True,real_trade_eligible=False,risk_budget=None,order=None,
        effectiveness='NOT_VALIDATED',
        limitations=['当前截面形态研究；非当时已知的历史PIT回测，当前上市/行业池有幸存者与时点缺口',
            '形态满足、首次满足及实验执行资格分别统计；未知保留，不推断可成交',
            '当前取得的真实历史数据未获真实前瞻模拟执行准入；所有真实交易资格保持false',
            '显示排序仅按首次满足、20日相对表现及代码；不是收益预测；所有符合形态的记录保留',
            '排除及执行阻断原因可重叠；每组输入可判+未知=完整观察池数量',
            '代码和参数在观察时固定；旧日期的形态是当前资料重算，不伪造过去的判断',
            '暂不把人工/AI判断回填规则；当前未生成PAPER成交或真实订单'])


def setup_markdown(report: dict) -> str:
    names={'P0':'趋势回踩恢复','B0':'突破对照','T0':'简单趋势对照'}
    lines=['# 三组策略形态观察', '',
        f"证据模式：{report['mode']}；观察时间：{report['as_of']}；行情截至：{report['market_date']}；要求行情日：{report['required_market_date']}。",
        f"参数版本：{report['parameters']['version']}；冻结：{report['parameters']['frozen_at']}。", '',
        '形态观察不产生交易许可或订单；策略效果尚未验证。']
    if report['market_date'] != report['required_market_date']:
        lines += ['行情未覆盖要求日期；以下只描述保留截面，不能称作今天的信号。']
    for variant,name in names.items():
        counts=report['summary'][variant]
        lines += ['',f'## {variant} {name}', '',
            f"观察池{counts['pool']}；输入可判{counts['known']}；未知{counts['unknown']}；形态符合{counts['condition_matches']}；首次满足{counts['first_matches']}；实验入场前置资格{counts['paper_ready']}。", '']
        for item in report['ranked'][variant]:
            lines += [f"- {item['name'] or item['code']} {item['code']}：{'首次满足' if item['first_match'] else '前次也满足或前次未知'}；"
                f"20日相对表现 {item['metrics']['relative_return']}；回踩日 {item['metrics']['touch_date'] or '不适用'}。",
                f"  实验执行阻断：{'、'.join(item['paper_blockers']) or '仍须下一交易日开盘、状态、资金和T+1检查'}。"]
        if not report['ranked'][variant]:
            lines += ['没有可展示的符合形态对象；未知输入不当作不符合或正常交易。']
    lines += ['', '## 来源与局限', '', *[f'- {text}' for text in report['limitations']],
              '',f"代码Hash：{report['code_hash']}；参数Hash：{report['parameters_hash']}。"]
    return '\n'.join(lines)+'\n'


def publish_setups(report: dict, output: Path) -> tuple[str, Path, Path]:
    require(not any(p.is_symlink() for p in (output,*output.parents)), 'STRATEGY_OUTPUT_SYMLINK')
    output.mkdir(parents=True,exist_ok=True)
    # Renderer changes are addressed with their immutable JSON/Markdown pair.
    from hashlib import sha256
    report['renderer_hash'] = sha256(Path(__file__).read_bytes()).hexdigest()
    key=digest(report)
    json_path, markdown_path=output/f'{key}.json',output/f'{key}.md'
    publish_bytes(json_path,encoded(report)+b'\n')
    publish_bytes(markdown_path,setup_markdown(report).encode())
    return key,json_path,markdown_path
