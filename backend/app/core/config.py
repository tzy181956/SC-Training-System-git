from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Training Management Platform"
    api_prefix: str = "/api"
    secret_key: str = Field(default="dev-secret-key-change-me")
    access_token_expire_minutes: int = 60 * 24
    database_url: str = f"sqlite:///{(BASE_DIR / 'training.db').as_posix()}"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    cors_origin_regex: str = r"https?://.*"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
