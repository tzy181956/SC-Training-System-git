from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SECRET_KEY = "dev-secret-key-change-me"
DEFAULT_DATABASE_URL = f"sqlite:///{(BASE_DIR / 'training.db').as_posix()}"
DEFAULT_DEVELOPMENT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
UNSAFE_CORS_ORIGIN_REGEX = r"https?://.*"


class Settings(BaseSettings):
    app_name: str = "Training Management Platform"
    app_env: Literal["development", "production"] = "development"
    api_prefix: str = "/api"
    secret_key: str = Field(default=DEFAULT_SECRET_KEY)
    access_token_expire_minutes: int = 60 * 24
    database_url: str = DEFAULT_DATABASE_URL
    cors_origins: list[str] = Field(default_factory=lambda: DEFAULT_DEVELOPMENT_CORS_ORIGINS.copy())
    cors_origin_regex: str | None = None
    training_day_rollover_hour: int = Field(default=4, ge=0, le=23)
    auto_close_overdue_sessions: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_app_env(cls, value: str | None) -> str:
        if value is None:
            return "development"
        normalized = value.strip().lower()
        return normalized or "development"

    @field_validator("cors_origin_regex", mode="before")
    @classmethod
    def normalize_cors_origin_regex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def validate_runtime_safety(self) -> "Settings":
        if not self.is_production:
            return self

        if "secret_key" not in self.model_fields_set or not self.secret_key or self.secret_key == DEFAULT_SECRET_KEY:
            raise ValueError(
                "APP_ENV=production 时必须显式配置 SECRET_KEY，且不能继续使用 dev-secret-key-change-me。"
            )

        if "database_url" not in self.model_fields_set or not self.database_url:
            raise ValueError(
                "APP_ENV=production 时必须显式配置 DATABASE_URL，不能依赖 backend/training.db 的开发默认值。"
            )

        if "cors_origins" not in self.model_fields_set or not self.cors_origins:
            raise ValueError(
                "APP_ENV=production 时必须显式配置 CORS_ORIGINS（JSON 数组），不能继续使用开发环境默认来源。"
            )

        if self.cors_origin_regex == UNSAFE_CORS_ORIGIN_REGEX:
            raise ValueError(
                "APP_ENV=production 时不要使用宽泛的 CORS_ORIGIN_REGEX=https?://.*；建议留空，除非你明确知道风险。"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
