"""Small immutable run receipts and explicit offline resume; no market retries."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
from typing import Literal
import uuid

from pydantic import AwareDatetime, Field

from astock.company.models import Strict
from astock.decision.daily import DailyObservation, DailyProfile, json_input, load_daily_profile, project_path
from astock.decision.models import RunInput
from astock.research.core import digest, encoded, instant, read_json, require
from astock.research.publication import publish_bytes
from astock.data.warehouse_lock import warehouse_connection
from astock.research.journal import active_events
from astock.research.store import ResearchStore


Stage = Literal['START', 'MARKET', 'EVIDENCE', 'BASELINE', 'PLANS', 'DECISIONS', 'PORTFOLIO', 'PERSIST', 'PUBLISH', 'RECEIPT', 'DONE']
SAFE_MESSAGES = {
    'START': '任务回执尚未建立；检查本地目录权限和空间。',
    'MARKET': '行情来源核验或计算失败；核对本地来源、用途和覆盖，不自动重新采集。',
    'EVIDENCE': '公司目录或保留文档核验失败；核对原文件，保留现有来源。',
    'BASELINE': '原研究基线未能复现；检查原锚点和版本，不覆盖旧基线。',
    'PLANS': '研究计划版本或范围冲突；核对计划记录及基线。',
    'DECISIONS': '研究条件或时间绑定未通过；核对计划与观察日期。',
    'PORTFOLIO': '私有持仓范围或模式不一致；核对已报快照，未知保持未知。',
    'PERSIST': '研究观察写入未完成；已有追加记录保留，同版本恢复会幂等接续。',
    'PUBLISH': '报告文件对尚未完整发布；保留已有文件，同版本恢复补齐。',
    'RECEIPT': '报告可能已生成，终态回执写入未完成；先核对输出，再显式恢复。',
    'DONE': '离线任务已完成；不代表取得新行情或产生订单。',
}


class AttemptStart(Strict):
    protocol: Literal['DAILY_ATTEMPT_V1'] = 'DAILY_ATTEMPT_V1'
    attempt_id: str = Field(pattern=r'^[0-9a-f]{32}$')
    started_at: AwareDatetime
    observed_at: AwareDatetime
    required_market_date: str
    mode: Literal['REAL_EVIDENCE', 'OFFLINE_SIMULATION']
    inputs_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    engine_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    journal_inputs_hash: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    resumes_attempt_id: str | None = Field(default=None, pattern=r'^[0-9a-f]{32}$')


class AttemptResult(Strict):
    protocol: Literal['DAILY_ATTEMPT_RESULT_V1'] = 'DAILY_ATTEMPT_RESULT_V1'
    attempt_id: str = Field(pattern=r'^[0-9a-f]{32}$')
    start_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    finished_at: AwareDatetime
    state: Literal['SUCCEEDED', 'FAILED']
    stage: Stage
    report_id: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    error_category: Literal['LOCAL_IO', 'VALIDATION_OR_EXECUTION'] | None = None


class DailyRunFailure(ValueError):
    def __init__(self, attempt_id: str | None, stage: Stage, receipt_saved: bool):
        super().__init__('DAILY_RUN_FAILED')
        self.attempt_id = attempt_id
        self.stage = stage
        self.receipt_saved = receipt_saved


def engine_fingerprint() -> str:
    package = Path(__file__).resolve().parents[1]
    checkout = package.parents[1]
    files = [*package.rglob('*.py'), *checkout.joinpath('sql').glob('*.sql'),
             checkout / 'uv.lock', checkout / 'config/daily/workflow-v1.json']
    return digest({str(p.relative_to(checkout)): sha256(p.read_bytes()).hexdigest() for p in sorted(files)})


def inputs_fingerprint(profile: DailyProfile, instruction: RunInput) -> str:
    paths = [getattr(profile, name) for name in ('run', 'previous', 'latest', 'baseline_market',
                                                'parameters', 'revisions', 'position_scope')]
    run = instruction.model_dump(mode='json')
    run['observed_at'] = instant(instruction.observed_at).isoformat()
    return digest(dict(profile=profile.model_dump(mode='json'), instruction=run,
                       files={str(p): sha256(p.read_bytes()).hexdigest() for p in paths if p is not None}))


def journal_inputs_fingerprint(profile: DailyProfile, as_of: str) -> str:
    """Bind available human facts, excluding this application's derived observations."""
    if not profile.journal_store.exists():
        return digest([])
    with warehouse_connection(profile.journal_store, read_only=True) as db:
        ResearchStore(profile.journal_store)._check(db)
        events, _ = active_events(db, as_of)
    primary = {'POSITION', 'EXECUTION', 'ACCOUNT', 'INPUT', 'RESEARCH_INPUT'}
    facts = [e for e in events if e['kind'] in primary or
             e['kind'] in ('REVIEW', 'EXIT') and e.get('research_report_id') is None]
    return digest(facts)


def _directory(output: Path, identifier: str) -> Path:
    require(re.fullmatch(r'[0-9a-f]{32}', identifier) is not None, 'DAILY_ATTEMPT_ID')
    path = output / 'attempts' / identifier
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'DAILY_ATTEMPT_SYMLINK')
    return path


def start_attempt(profile: DailyProfile, instruction: RunInput,
                  resumes_attempt_id: str | None = None) -> AttemptStart:
    value = AttemptStart(attempt_id=uuid.uuid4().hex, started_at=datetime.now(timezone.utc),
                         observed_at=instant(instruction.observed_at), required_market_date=instruction.required_market_date,
                         mode=instruction.mode, inputs_hash=inputs_fingerprint(profile, instruction),
                         engine_hash=engine_fingerprint(), resumes_attempt_id=resumes_attempt_id,
                         journal_inputs_hash=journal_inputs_fingerprint(profile, instruction.observed_at))
    directory = _directory(profile.output, value.attempt_id)
    directory.mkdir(parents=True, exist_ok=False)
    publish_bytes(directory / 'started.json', encoded(value.model_dump(mode='json')) + b'\n')
    return value


def finish_attempt(profile: DailyProfile, start: AttemptStart, stage: Stage, *,
                   report_id: str | None = None, error: Exception | None = None) -> None:
    value = AttemptResult(attempt_id=start.attempt_id, start_hash=digest(start.model_dump(mode='json')),
        finished_at=datetime.now(timezone.utc), state='FAILED' if error is not None else 'SUCCEEDED',
        stage=stage, report_id=report_id,
        error_category=('LOCAL_IO' if isinstance(error, OSError) else 'VALIDATION_OR_EXECUTION') if error is not None else None)
    directory = _directory(profile.output, start.attempt_id)
    publish_bytes(directory / 'result.json', encoded(value.model_dump(mode='json')) + b'\n')


def receipt_output(root: Path, profile_path: Path) -> Path:
    """Status remains readable when a market input is missing; no DB open or writes."""
    root = root.resolve()
    path = json_input(root, profile_path)
    require(path.is_relative_to(root / 'config') or path.is_relative_to(root / 'data/private'), 'DAILY_PROFILE_LOCATION')
    profile = DailyProfile.model_validate(read_json(path))
    output = project_path(root, profile.output)
    require(output.is_relative_to(root / 'reports/private/research-v1'), 'DAILY_PRIVATE_REPORT_DIRECTORY')
    return output


def read_attempt(output: Path, identifier: str) -> tuple[AttemptStart, AttemptResult | None]:
    directory = _directory(output, identifier)
    for name in ('started.json', 'result.json'):
        path = directory / name
        require(not path.is_symlink(), 'DAILY_ATTEMPT_SYMLINK')
    start = AttemptStart.model_validate(read_json(directory / 'started.json'))
    require(start.attempt_id == identifier, 'DAILY_ATTEMPT_BINDING')
    result_path = directory / 'result.json'
    result = AttemptResult.model_validate(read_json(result_path)) if result_path.exists() else None
    if result:
        require(result.attempt_id == identifier and result.start_hash == digest(start.model_dump(mode='json')),
                'DAILY_ATTEMPT_BINDING')
        require((result.state == 'SUCCEEDED') == (result.report_id is not None and result.stage == 'DONE'),
                'DAILY_ATTEMPT_RESULT')
    return start, result


def attempt_status(root: Path, profile_path: Path, identifier: str | None = None) -> list[dict]:
    output = receipt_output(root, profile_path)
    base = output / 'attempts'
    require(not base.is_symlink(), 'DAILY_ATTEMPT_SYMLINK')
    identifiers = [identifier] if identifier else [p.name for p in base.iterdir() if re.fullmatch(r'[0-9a-f]{32}', p.name)] if base.exists() else []
    items = []
    for key in identifiers:
        start, result = read_attempt(output, key)
        items.append(dict(attempt_id=key, started_at=start.started_at.isoformat(), observed_at=start.observed_at.isoformat(),
            required_market_date=start.required_market_date, resumes_attempt_id=start.resumes_attempt_id,
            state=result.state if result else 'RUNNING_OR_INTERRUPTED', stage=result.stage if result else 'START',
            report_id=result.report_id if result else None,
            next_step=SAFE_MESSAGES[result.stage] if result else '只有启动回执；可能仍在运行或已中断。先确认原进程，再显式恢复，不自动重试。'))
    return sorted(items, key=lambda item: (item['started_at'], item['attempt_id']), reverse=True)


def resume_observation(root: Path, profile_path: Path, identifier: str) -> DailyObservation:
    output = receipt_output(root, profile_path)
    start, _ = read_attempt(output, identifier)
    observation = DailyObservation(observed_at=start.observed_at, required_market_date=start.required_market_date)
    profile, instruction = load_daily_profile(root, profile_path, observation)
    require(inputs_fingerprint(profile, instruction) == start.inputs_hash, 'DAILY_RESUME_INPUT_CHANGED')
    require(engine_fingerprint() == start.engine_hash, 'DAILY_RESUME_ENGINE_CHANGED')
    require(start.journal_inputs_hash is not None, 'DAILY_RESUME_JOURNAL_UNBOUND')
    require(journal_inputs_fingerprint(profile, instruction.observed_at) == start.journal_inputs_hash,
            'DAILY_RESUME_JOURNAL_CHANGED')
    return observation
