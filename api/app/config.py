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

    # What this public demo may spend in a day, in USD, across everyone. Raise
    # it by setting the environment variable; the code never assumes a figure
    # that was not put here on purpose.
    daily_budget_usd: float = 5.0
    # And what any one visitor may take of it. The notice on the page quotes
    # this number, so changing it changes what the reader is told.
    daily_generates_per_visitor: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
