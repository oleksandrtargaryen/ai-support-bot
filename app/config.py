from datetime import time
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str
    webhook_base_url: str = ""
    webhook_secret: str = "webhook"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/support_bot"

    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "faq"

    llm_model: str = "openai:gpt-4o-mini"
    embeddings_model: str = "openai:text-embedding-3-small"

    admin_api_key: str

    # Working hours: Mon-Sat, closed on Sunday (weekday 6)
    work_day_start: time = time(9, 0)
    work_day_end: time = time(18, 0)
    closed_weekdays: tuple[int, ...] = (6,)
    slot_step_minutes: int = 30

    @property
    def webhook_path(self) -> str:
        return f"/webhook/{self.webhook_secret}"

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
