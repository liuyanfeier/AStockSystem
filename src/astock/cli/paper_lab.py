"""A zero-market-data demonstration, isolated from research stores and account facts."""
from hashlib import sha256
from pathlib import Path

import typer

from astock.backtest.report import publish_lab
from astock.backtest.scenarios import synthetic_scenario
from astock.backtest.strategy_lab import ThreeRuleExperiment, compare_strategies
from astock.decision.daily import json_input, project_path
from astock.paths import get_project_root
from astock.research.core import read_json, require
from astock.screening.strategy_models import StrategyParameters


def paper_demo_command(
    output: Path = typer.Option(Path('reports/private/research-v1/strategy-lab-v1'), '--output'),
    parameters: Path = typer.Option(Path('config/research/strategy-research-v1.json'), '--parameters'),
    experiment: Path = typer.Option(Path('config/decision-loop/strategy-lab-v1.json'), '--experiment'),
) -> None:
    """运行全合成的三规则中文演示；不读取行情、公司或个人账户。"""
    try:
        root = get_project_root().resolve()
        target = project_path(root, output)
        require(target.is_relative_to(root/'reports/private/research-v1'), 'STRATEGY_LAB_PRIVATE_OUTPUT')
        policy = StrategyParameters.model_validate(read_json(json_input(root, parameters)))
        lab = ThreeRuleExperiment.model_validate(read_json(json_input(root, experiment)))
        report = compare_strategies(synthetic_scenario(policy, lab), policy, lab)
        generator = Path(__file__).resolve().parents[1]/'backtest/scenarios.py'
        report['scenario'] = dict(name='SYNTHETIC_GAP_AND_BLOCKED_EXIT_V1',
            generator_hash=sha256(generator.read_bytes()).hexdigest(), calendar='FICTITIOUS_EVERY_CIVIL_DAY_OPEN')
        key, _, markdown = publish_lab(report, target)
        typer.echo('全合成策略演示：'+key)
        typer.echo('中文报告：'+str(markdown.relative_to(root)))
        typer.echo('三个对照及两倍成本结果全部保留；未取得真实行情，未写账户或生成真实订单。')
    except Exception:
        typer.echo('合成演示失败：核对实验参数及项目内私有输出目录；既有结果保留。')
        raise typer.Exit(1) from None
