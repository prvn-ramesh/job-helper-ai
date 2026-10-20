from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Runtime
    environment: str = "development"
    log_level: str = "INFO"

    # Google Sheets
    google_oauth_credentials_path: str = "secrets/client_secret.json"
    google_oauth_token_path: str = "secrets/token.json"
    google_sheets_id: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_primary_model: str = "gemini-2.0-flash-lite"
    gemini_secondary_model: str = "gemini-2.0-flash-lite"

    # Telegram
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Browser
    chrome_profile_dir: str = "data/chrome_profile"
    headless: bool = False

    # Limits
    max_applications_per_day: int = 25
    min_score_threshold: float = 6.0

    # Feature toggles
    eligibility_check_enabled: bool = True
    review_method: str = "web"  # web | telegram | both

    # Infra
    redis_url: str = "redis://localhost:6379/0"
    sqlite_db_path: str = "data/jobs.db"

    @property
    def credentials_path(self) -> Path:
        return Path(self.google_oauth_credentials_path)

    @property
    def token_path(self) -> Path:
        return Path(self.google_oauth_token_path)

    @property
    def db_path(self) -> Path:
        return Path(self.sqlite_db_path)


# Singleton — import this everywhere
settings = Settings()
