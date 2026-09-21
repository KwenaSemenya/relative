from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RELATIVE_", env_file=".env")

    environment: str = "development"

    # Neon. Set as a Fly secret in production; never committed.
    database_url: str = "postgresql://localhost/relative"

    # Claude. Set as a Fly secret in production; never committed.
    anthropic_api_key: str = ""
    # One model for every call. Pre-flight validation and the critique pass
    # differ by prompt and by what they are shown, not by model.
    claude_model: str = "claude-sonnet-4-6"


@lru_cache
def get_settings() -> Settings:
    return Settings()
