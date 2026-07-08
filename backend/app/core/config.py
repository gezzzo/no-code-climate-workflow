from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Climate Data Analysis API"
    api_prefix: str = "/api"
    storage_dir: Path = Path("storage")
    max_standardized_rows: int = 2_000_000
    preview_default_limit: int = 100
    github_import_max_bytes: int = 200 * 1024 * 1024
    github_import_timeout_seconds: int = 30
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
