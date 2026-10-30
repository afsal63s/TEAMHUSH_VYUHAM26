from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

HAIKU = "claude-haiku-5-5"


class Settings(BaseSettings):
    """Settings read from the environment and .env. Later phases add their own fields."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ANTHROPIC_API_KEY: SecretStr = SecretStr("")
    MODEL_STRONG: str = HAIKU
    MODEL_CHEAP: str = HAIKU
    MODEL_LOCAL: str = HAIKU
    MAX_SPEND_USD: float = 2.00  # per process; LLM calls stop once the estimate passes it
    GENERATION_CONCURRENCY: int = 2
    TAVILY_API_KEY: SecretStr = SecretStr("")
    YOUTUBE_API_KEY: SecretStr = SecretStr("")
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "onlynerd"
    MASTER_PASSWORD: SecretStr = SecretStr("")  # empty = no check (dev mode)


@lru_cache
def get_settings() -> Settings:
    return Settings()
