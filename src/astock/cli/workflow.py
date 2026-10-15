"""Chinese research intake and read-only run status; no order or acquisition path."""
from datetime import datetime, timedelta
from pathlib import Path
import re
import uuid
from zoneinfo import ZoneInfo

import typer

from astock.decision.attempts import attempt_status
from astock.decision.plan_models import PlanDraft, PlanInput
from astock.decision.plans import existing_plan_input, preview_plans, record_plan_input
from astock.decision.settings import workflow_policy
from astock.paths import get_project_root
from astock.portfolio import manual


def _lines(prompt: str) -> list[str]:
    return [s.strip() for s in re.split('[；;]', typer.prompt(prompt)) if s.strip()]


def plan_command(profile: Path = typer.Option(..., '--profile'),
                 request_id: str | None = typer.Option(None, '--request-id')) -> None:
    """中文研究计划：新增/重开、结束观察、明确复核当前证据。"""
    try:
        root = get_project_root()
        identifier = request_id or uuid.uuid4().hex
        if existing_plan_input(root, profile, identifier):
            typer.echo('该研究请求已保存；重复调用没有新增记录。')
            return
        state = preview_plans(root, profile)
        typer.echo(f"研究模式：{state['mode']}；请求号：{identifier}。")
        for row in state['plans']:
            typer.echo(f"- {row['code']}：{'已结束，可重开新版本' if row['ended'] else '观察中'}；复核时间 {row['plan']['review_due']}")
        choice = typer.prompt('选择 1 新增/重开研究计划，2 结束研究观察，3 明确复核当前证据', type=int)
        actions = {1: 'CREATE', 2: 'END_WATCH', 3: 'REVIEW_EVIDENCE'}
        if choice not in actions:
            raise ValueError('PLAN_ACTION')
        if choice == 1:
            typer.echo('有保留证据的可选代码：' + '、'.join(state['available_codes']))
        code = typer.prompt('完整证券代码（如600036.SH）').strip().upper()
        draft = None
        if choice == 1:
            if code not in state['available_codes']:
                raise ValueError('PLAN_COMPANY_EVIDENCE_REQUIRED')
            if code not in state['latest_reviewed_codes']:
                typer.echo('该对象只有保留基线材料；下一报告列为待刷新，不视为本轮已复核。')
            values = dict(thesis=typer.prompt('研究逻辑'), attention_reason=typer.prompt('为什么现在关注'),
                          observable_checks=_lines('下一步可观察检查（多项用分号分开）'),
                          invalidation_conditions=_lines('哪些事实会挑战或推翻逻辑（多项用分号分开）'),
                          no_trade_reasons=_lines('当前不应交易的理由（多项用分号分开）'))
            metrics = state['metrics'][code]
            for metric in metrics:
                typer.echo(f"- {metric['id']}：{metric['name']}")
            metric_id = typer.prompt('首个需要跟踪的已披露指标ID').strip()
            if metric_id not in {m['id'] for m in metrics}:
                raise ValueError('PLAN_METRIC_REQUIRED')
            expectation = typer.prompt('指标期望：1 不低于基线，2 不高于基线，3 为正', type=int)
            expectations = {1: 'NOT_LOWER', 2: 'NOT_HIGHER', 3: 'POSITIVE'}
            if expectation not in expectations:
                raise ValueError('PLAN_EXPECTATION')
            reason = typer.prompt('为什么检查该指标')
            values['criteria'] = [dict(id='primary', metric_id=metric_id, expectation=expectations[expectation],
                                       reason=reason, failure='CHALLENGED')]
            proposed = manual.now_utc() + timedelta(days=workflow_policy().default_research_review_days)
            values['review_due'] = datetime.fromisoformat(typer.prompt('研究复核时间（保留时区；不是交易退出时间）',
                default=proposed.astimezone(ZoneInfo('Asia/Shanghai')).isoformat()))
            values['unresolved_material_risk'] = typer.prompt('尚未解决的重大风险（可留空）', default='', show_default=False).strip() or None
            draft = PlanDraft.model_validate(values)
        elif choice == 2:
            typer.echo('结束观察保留原计划；已有持仓风险继续检查，不代表实际卖出。')
        else:
            typer.echo('这是对当前目录和来源版本的明确研究复核，可更新研究检查；不解除未解决重大风险、持仓或交易限制。')
        reason = typer.prompt('本次研究操作的理由（普通已阅请用record）')
        request = PlanInput(request_id=identifier, mode=state['mode'], action=actions[choice], code=code,
                            expected_plan_hash=state['plan_hash'], reason=reason, draft=draft)
        if not typer.confirm('确认保存这项研究操作？', default=False):
            typer.echo('已取消，研究记录未变。')
            return
        receipt = record_plan_input(root, profile, request)
        typer.echo(f"研究操作已保存：{receipt['code']}；请求号 {receipt['request_id']}；未产生订单。")
        typer.echo('请在下一次显式观察中查看计划和待办；冻结配置保持原样。')
    except (typer.Abort, EOFError):
        typer.echo('研究录入已取消；已有记录保留。')
        raise typer.Exit(1) from None
    except Exception:
        typer.echo('研究操作未保存：核对证据范围、指标、复核时间、当前计划和预览是否变化；已有记录保留。')
        raise typer.Exit(1) from None


def daily_status_command(profile: Path = typer.Option(..., '--profile'),
                         attempt: str | None = typer.Option(None, '--attempt')) -> None:
    """只读查看离线任务阶段与恢复建议；不打开数据库或采集。"""
    try:
        rows = attempt_status(get_project_root(), profile, attempt)
        if not rows:
            typer.echo('尚无日常运行回执；没有记录不代表任务已成功。')
        for row in rows[:10]:
            typer.echo(f"{row['attempt_id']}：{row['state']}；观察 {row['observed_at']}；阶段 {row['stage']}。")
            typer.echo(row['next_step'])
            if row['state'] != 'SUCCEEDED':
                typer.echo(f"核对原任务后可使用 daily --profile 原配置 --resume {row['attempt_id']}；不会重新采集。")
        typer.echo('状态查询只读；只有启动回执不能证明进程仍在运行。')
    except Exception:
        typer.echo('任务状态读取失败：核对配置输出路径、任务号和回执完整性；未更改记录。')
        raise typer.Exit(1) from None
