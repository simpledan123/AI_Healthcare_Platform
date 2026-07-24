from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/demo.db"
    ai_review_mode: str = "demo"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    n8n_webhook_url: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    store_derived_sequence: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def data_dir(self) -> Path:
        path = Path("data")
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()

