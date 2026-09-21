from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RELATIVE_", env_file=".env")

    environment: str = "development"

    # Neon. Set as a Fly secret in production; never committed.
    database_url: str = "postgresql://localhost/relative"

    # Phase 3 adds the Claude API key here.


@lru_cache
def get_settings() -> Settings:
    return Settings()
