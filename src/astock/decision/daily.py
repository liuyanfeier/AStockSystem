"""Resolve one private daily profile without collecting data or opening databases."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, Field

from astock.company.models import Strict
from astock.decision.models import PositionScope, RunInput
from astock.research.core import instant, private_path, read_json, require


class DailyComponent(Strict):
    bundle: str = Field(min_length=1, max_length=128)
    store: Path


class DailyObservation(Strict):
    observed_at: AwareDatetime
    required_market_date: str | None = None


class DailyProfile(Strict):
    protocol: Literal["DAILY_PROFILE_V1"]
    run: Path
    previous: Path
    latest: Path
    documents: Path
    baseline_market: Path
    bundle: str = Field(min_length=1, max_length=128)
    store: Path
    journal_store: Path
    output: Path
    parameters: Path = Path("config/research/observation-v1.json")
    strategy_parameters: Path | None = None
    components: list[DailyComponent] = Field(default_factory=list, max_length=32)
    revisions: Path | None = None
    position_scope: Path | None = None

    def close_options(self) -> dict:
        """All options are explicit: the legacy CLI's Typer defaults are never used."""
        return dict(
            run=self.run, previous=self.previous, latest=self.latest,
            documents=self.documents, baseline_market=self.baseline_market,
            bundle=self.bundle, store=self.store, journal_store=self.journal_store,
            output=self.output, parameters=self.parameters,
            strategy_parameters=self.strategy_parameters,
            component=[item.bundle for item in self.components],
            component_store=[item.store for item in self.components],
            revisions=self.revisions, position_scope=self.position_scope,
            public_output=None,
        )


def project_path(root: Path, value: Path) -> Path:
    require(".." not in value.parts, "DAILY_PARENT_TRAVERSAL")
    path = value if value.is_absolute() else root / value
    require(not any(item.is_symlink() for item in (path, *path.parents)), "DAILY_SYMLINK")
    path = path.resolve()
    require(path.is_relative_to(root), "DAILY_OUTSIDE_PROJECT")
    return path


def json_input(root: Path, value: Path) -> Path:
    path = project_path(root, value)
    require(path.suffix == ".json" and path.is_file(), "DAILY_JSON_INPUT_REQUIRED")
    return path


def load_daily_profile(root: Path, path: Path,
                       observation: DailyObservation | None = None) -> tuple[DailyProfile, RunInput]:
    """Preflight is read-only; configuration validity is not market-data readiness."""
    root = root.resolve()
    path = json_input(root, path)
    require(path.is_relative_to(root / "config") or path.is_relative_to(root / "data/private"),
            "DAILY_PROFILE_LOCATION")
    profile = DailyProfile.model_validate(read_json(path))
    return resolve_daily_profile(root, profile, observation)


def resolve_daily_profile(root: Path, profile: DailyProfile,
                          observation: DailyObservation | None = None) -> tuple[DailyProfile, RunInput]:
    root = root.resolve()
    values = profile.model_dump()
    for name in ("run", "previous", "latest", "baseline_market", "parameters"):
        values[name] = json_input(root, getattr(profile, name))
    for name in ("revisions", "position_scope", "strategy_parameters"):
        value = getattr(profile, name)
        values[name] = json_input(root, value) if value is not None else None
    if values["position_scope"] is not None:
        private_path(root, values["position_scope"])

    raw_instruction = read_json(values["run"])
    if observation:
        raw_instruction = {**raw_instruction, 'observed_at': observation.observed_at.isoformat()}
        if observation.required_market_date is not None:
            raw_instruction['required_market_date'] = observation.required_market_date
    instruction = RunInput.model_validate(raw_instruction)
    require(instruction.mode == "OFFLINE_SIMULATION" or
            instant(instruction.observed_at) <= datetime.now(timezone.utc),
            "DAILY_FUTURE_REAL_OBSERVATION")
    if values["position_scope"] is not None:
        scope = PositionScope.model_validate(read_json(values["position_scope"]))
        require(scope.mode == ("USER_MANUAL" if instruction.mode == "REAL_EVIDENCE" else "SIMULATED"),
                "DAILY_ACCOUNT_MODE")
        require(instant(scope.snapshot_at) <= instant(instruction.observed_at), "DAILY_FUTURE_ACCOUNT")

    documents = project_path(root, profile.documents)
    require(documents.is_relative_to(root / "data/private/research-v3") and documents.is_dir(),
            "DAILY_DOCUMENT_DIRECTORY")
    values["documents"] = documents
    for name in ("store", "journal_store", "output"):
        values[name] = project_path(root, getattr(profile, name))
    private_path(root, values["store"])
    require(values["store"].is_file(), "DAILY_SOURCE_STORE_REQUIRED")
    require(values["output"].is_relative_to(root / "reports/private/research-v1"),
            "DAILY_PRIVATE_REPORT_DIRECTORY")
    require(not values["output"].exists() or values["output"].is_dir(), "DAILY_REPORT_NOT_DIRECTORY")
    mode = "real" if instruction.mode == "REAL_EVIDENCE" else "simulated"
    allowed = root / "data/private/research-v1/decision-loop-v0" / mode
    require(values["journal_store"].is_relative_to(allowed) and
            values["journal_store"].suffix == ".duckdb", "DAILY_JOURNAL_MODE_PATH")
    require(not values["journal_store"].exists() or values["journal_store"].is_file(),
            "DAILY_JOURNAL_NOT_FILE")

    components = []
    for item in profile.components:
        store = project_path(root, item.store)
        private_path(root, store)
        require(store.is_file(), "DAILY_COMPONENT_STORE_REQUIRED")
        components.append(DailyComponent(bundle=item.bundle, store=store))
    bundles = [profile.bundle, *[item.bundle for item in components]]
    require(len(set(bundles)) == len(bundles), "DAILY_DUPLICATE_COMPONENT")
    require(values["journal_store"] not in {values["store"], *[item.store for item in components]},
            "DAILY_SOURCE_JOURNAL_COLLISION")
    if values["journal_store"].exists():
        require(not any(values["journal_store"].samefile(source)
                        for source in [values["store"], *[item.store for item in components]]),
                "DAILY_SOURCE_JOURNAL_HARDLINK")
    values["components"] = components
    return DailyProfile.model_validate(values), instruction
