"""Chinese manual intake; the application service owns validation and persistence."""
from datetime import datetime
from pathlib import Path
import uuid
from zoneinfo import ZoneInfo

import typer

from astock.paths import get_project_root
from astock.portfolio.manual import existing_input, now_utc, preview_positions, record_manual_input
from astock.portfolio.models import ManualInput


def record_command(profile: Path = typer.Option(..., '--profile'),
                   request_id: str | None = typer.Option(None, '--request-id')) -> None:
    """中文录入：已阅/备注、持仓快照、实际成交；不会下单。"""
    try:
        root = get_project_root()
        identifier = request_id or uuid.uuid4().hex
        old = existing_input(root, profile, identifier)
        if old:
            typer.echo(f"该请求已记录：{old['request_id']}；重复调用没有新增记录。")
            return
        state = preview_positions(root, profile)
        typer.echo(f"录入模式：{'真实人工记录' if state['mode'] == 'USER_MANUAL' else '模拟记录'}；请求号：{identifier}。")
        typer.echo('仅保存你提供的事实；成交记录不会自动推算持仓，也不会向券商下单。')
        choice = typer.prompt('选择 1 已阅/研究备注，2 持仓快照，3 实际成交', type=int)
        kinds = {1: 'NOTE', 2: 'POSITION', 3: 'EXECUTION'}
        if choice not in kinds:
            raise ValueError('UNKNOWN_INPUT_KIND')
        kind = kinds[choice]
        code = typer.prompt('证券代码（如600036.SH，须完整填写）').strip().upper()
        event_at = datetime.fromisoformat(typer.prompt(
            '事实/快照时间（保留时区）', default=now_utc().astimezone(ZoneInfo('Asia/Shanghai')).isoformat()))
        values = dict(request_id=identifier, mode=state['mode'], kind=kind, code=code, event_at=event_at)
        quantity = None
        if kind == 'POSITION':
            quantity = typer.prompt('该时点实际持股数（0表示明确无该股持仓）', type=int)
            values['shares'] = quantity
        elif kind == 'EXECUTION':
            values['side'] = typer.prompt('实际成交方向（BUY买入 / SELL卖出）').strip().upper()
            values['shares'] = typer.prompt('已成交股数', type=int)
            values['price_cny'] = typer.prompt('实际成交价（元）').strip()
            remaining = typer.prompt('成交后实际持股数（留空则不更新持仓）', default='', show_default=False).strip()
            quantity = int(remaining) if remaining else None
            values['remaining_shares'] = quantity
        if kind != 'NOTE':
            values['expected_position_hash'] = state['position_hash']
            projected = {row['code']: row['shares'] for row in state['positions']}
            if quantity is not None:
                if quantity:
                    projected[code] = quantity
                else:
                    projected.pop(code, None)
                if code not in {row['code'] for row in state['positions']} and quantity:
                    values['thesis'] = typer.prompt('本次声明的持仓逻辑（可留空）', default='', show_default=False).strip() or None
                    values['invalidation'] = typer.prompt('逻辑失效观察条件（可留空）', default='', show_default=False).strip() or None
            typer.echo('本次录入后的已报持仓：' + ('；'.join(f'{code} {shares}股' for code, shares in sorted(projected.items())) or '暂无已报持仓；不据此推断空仓'))
            if quantity is not None:
                values['complete_positions_confirmed'] = typer.confirm('确认上述列表已覆盖当前全部持仓？', default=False)
            else:
                typer.echo('未补成交后持仓：账户完整性保持未确认，旧股数需要核对。')
            cash = typer.prompt('本次确认的账户现金（元，留空则未知）', default='', show_default=False).strip()
            values.update(cash_cny=cash or None, cash_confirmed=bool(cash))
        values['note'] = typer.prompt('已阅说明/备注' if kind == 'NOTE' else '补充备注（可留空）',
                                      default='' if kind != 'NOTE' else '已阅，风险与待办仍按原计划复核', show_default=False)
        request = ManualInput.model_validate(values)
        typer.echo(f'将保存：{code}；{kind}；事实时间 {request.event_at.isoformat()}；模式 {state["mode"]}。')
        if not typer.confirm('确认保存以上人工记录？', default=False):
            typer.echo('已取消，本次未保存。')
            return
        result = record_manual_input(root, profile, request)
        typer.echo(f"已保存，请求号：{result['request_id']}；未产生订单。")
        if result['position_updated']:
            typer.echo(f"已报持仓快照：{result['code']} {result['shares_after']}股。")
        typer.echo('下一次简报使用 daily --observe-now --market-date YYYY-MM-DD；日期是核查要求，不会获取新行情。')
    except (typer.Abort, EOFError):
        typer.echo('录入已取消；未产生订单。')
        raise typer.Exit(1) from None
    except Exception:
        typer.echo('录入未保存：请检查代码、数量、时间、模式，以及持仓预览是否已变化；已有记录保持原样。')
        raise typer.Exit(1) from None
