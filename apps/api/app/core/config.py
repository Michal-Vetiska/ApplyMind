"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "ApplyMind"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-change-me"
    secret_encryption_key: str = "dev-encryption-key-change-me!!"
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    admin_email: str = "admin@example.com"
    admin_password: str = "changeme"
    admin_name: str = "ApplyMind Owner"

    database_url: str = "postgresql+asyncpg://applymind:applymind@localhost:5432/applymind"
    database_url_sync: str = "postgresql+psycopg2://applymind:applymind@localhost:5432/applymind"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    data_dir: str = "./data"
    upload_max_mb: int = 10

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_chat_model: str = "gpt-4o-mini"
    llm_embedding_model: str = "text-embedding-3-small"
    llm_embedding_dims: int = 1536
    llm_monthly_budget_usd: float = 20.0
    llm_enabled: bool = True

    email_dry_run: bool = True
    email_sending_enabled: bool = False
    daily_send_limit: int = 10

    session_cookie_name: str = "applymind_session"
    session_max_age_hours: int = 168

    @property
    def cors_origins(self) -> list[str]:
        raw = self.cors_origins_raw.strip()
        if raw.startswith("["):
            import json

            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in raw.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key) and self.llm_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
