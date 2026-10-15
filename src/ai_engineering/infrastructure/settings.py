from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Engineering Orchestrator"
    environment: str = "development"
    log_level: str = "INFO"
    demo_mode: bool = True
    max_steps: int = 12
    agent_timeout_seconds: float = 5.0
    max_retries: int = 1
    database_url: str | None = None
    llm_provider: str = "simulated"
    llm_model: str = "gpt-6-astra"
    llm_planning_enabled: bool = True
    max_llm_input_tokens: int = 4_000
    max_llm_output_tokens: int = 1_000
    embedding_dimensions: int = 16
    knowledge_chunk_size: int = 800
    knowledge_chunk_overlap: int = 100
    mcp_project_config_dir: str = "configs/projects"
    model_config = SettingsConfigDict(env_prefix="AIEO_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
