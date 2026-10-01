"""Typed local settings; secrets are excluded from normal representations."""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from astock.paths import ProjectPaths, get_project_root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        env_ignore_empty=True,
        extra="ignore",
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    tushare_token: SecretStr | None = Field(
        default=None, validation_alias="TUSHARE_TOKEN", repr=False, exclude=True
    )
    data_dir: Path = Field(default=Path("data"), validation_alias="ASTOCK_DATA_DIR")
    db_path: Path | None = Field(default=None, validation_alias="ASTOCK_DB_PATH")

    @field_validator("tushare_token", mode="before")
    @classmethod
    def normalize_empty_token(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def token_configured(self) -> bool:
        return self.tushare_token is not None

    def paths(self, root: Path | None = None) -> ProjectPaths:
        return ProjectPaths.from_config(
            root if root is not None else get_project_root(), self.data_dir, self.db_path
        )


def load_settings(root: Path | None = None) -> Settings:
    """Read only the checkout's .env; process environment takes precedence."""
    project_root = root if root is not None else get_project_root()
    return Settings(_env_file=project_root / ".env", _env_file_encoding="utf-8")
