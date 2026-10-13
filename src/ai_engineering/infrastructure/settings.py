from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Engineering Orchestrator"
    environment: str = "development"
    log_level: str = "INFO"
    demo_mode: bool = True
    max_steps: int = 8
    agent_timeout_seconds: float = 5.0
    max_retries: int = 1
    model_config = SettingsConfigDict(env_prefix="AIEO_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
