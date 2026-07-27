from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Human Design: предназначение"
    app_env: str = "development"
    public_base_url: str = "http://localhost:8000"
    mini_app_url: str = "http://localhost:5173"
    # Comma-separated or JSON list string; "*" means allow all
    cors_origins: str = "*"

    # Demo mode: live | fixture | auto
    demo_mode: Literal["live", "fixture", "auto"] = "auto"

    # Security
    session_secret: str = "change-me-demo-session-secret"
    session_ttl_seconds: int = 3600
    auth_token_ttl_seconds: int = 3600
    init_data_max_age_seconds: int = 86400

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = "demo-telegram-secret"
    telegram_webhook_auto_setup: bool = True

    # Human Design Hub
    hd_hub_api_key: str = ""
    hd_hub_base_url: str = "https://api.humandesignhub.app"
    hd_hub_timeout_seconds: float = 15.0

    # LLM (OpenAI-compatible)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0
    llm_enabled: bool = True

    knowledge_dir: Path = Path(__file__).resolve().parents[2] / "knowledge"
    fixtures_dir: Path = Path(__file__).resolve().parents[2] / "fixtures"
    prompts_dir: Path = Path(__file__).resolve().parents[2] / "prompts"
    static_dir: Path = Path(__file__).resolve().parents[1] / "static"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "*").strip()
        if not raw or raw == "*":
            return ["*"]
        if raw.startswith("["):
            import json

            parsed = json.loads(raw)
            return [str(item) for item in parsed]
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    def resolved_mini_app_url(self) -> str:
        """In production prefer PUBLIC_BASE_URL when Mini App is served by backend."""
        if self.is_production:
            if (
                not self.mini_app_url
                or "localhost" in self.mini_app_url
                or "127.0.0.1" in self.mini_app_url
            ):
                return self.public_base_url.rstrip("/")
        return self.mini_app_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
