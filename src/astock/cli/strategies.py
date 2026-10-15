"""One source-only profile adapter; company and account gaps do not block scanning."""
from datetime import datetime, timezone
from pathlib import Path

import typer

from astock.decision.daily import DailyProfile, json_input, project_path
from astock.paths import get_project_root
from astock.research.core import private_path, read_json, require
from astock.research.store import ResearchStore
from astock.research.strategies import observe_setups, publish_setups
from astock.screening.strategy_models import StrategyParameters


def setups_command(profile: Path = typer.Option(...,'--profile'),
                   market_date: str = typer.Option(...,'--market-date'),
                   as_of: str | None = typer.Option(None,'--as-of'),
                   observe_now: bool = typer.Option(False,'--observe-now'),
                   parameters: Path = typer.Option(Path('config/research/strategy-research-v1.json'),'--parameters')) -> None:
    """三组规则观察：只读本地来源，不需要账户或新公司材料。"""
    try:
        root=get_project_root().resolve()
        require(bool(as_of) != observe_now, 'STRATEGY_OBSERVATION_REQUIRED')
        path=json_input(root,profile)
        require(path.is_relative_to(root/'config') or path.is_relative_to(root/'data/private'), 'DAILY_PROFILE_LOCATION')
        request=DailyProfile.model_validate(read_json(path))
        source=private_path(root,project_path(root,request.store))
        require(source.is_file(),'DAILY_SOURCE_STORE_REQUIRED')
        output=project_path(root,request.output)/'strategies'
        require(output.is_relative_to(root/'reports/private/research-v1'),'DAILY_PRIVATE_REPORT_DIRECTORY')
        owners={item.bundle:ResearchStore(private_path(root,project_path(root,item.store))) for item in request.components}
        require(len(owners)==len(request.components) and request.bundle not in owners,'DAILY_DUPLICATE_COMPONENT')
        policy=StrategyParameters.model_validate(read_json(json_input(root,parameters)))
        revisions=read_json(json_input(root,request.revisions)) if request.revisions else None
        observation=datetime.now(timezone.utc).isoformat() if observe_now else as_of
        report=observe_setups(ResearchStore(source),request.bundle,observation,market_date,policy,
            components=[c.bundle for c in request.components],owners=owners,revisions=revisions)
        key,_,markdown=publish_setups(report,output)
        typer.echo('策略形态观察：'+key)
        typer.echo('中文报告：'+str(markdown.relative_to(root)))
        for variant,summary in report['summary'].items():
            typer.echo(f"{variant}：形态{summary['condition_matches']}；首次{summary['first_matches']}；未知{summary['unknown']}；实验前置资格{summary['paper_ready']}。")
        typer.echo('未取得新行情、未生成PAPER成交或真实订单；陈旧日期不代表今天的信号。')
    except Exception:
        typer.echo('策略观察失败：核对本地来源、明确观察时间、行情要求日及参数冻结时间；未重新采集或产生订单。')
        raise typer.Exit(1) from None
