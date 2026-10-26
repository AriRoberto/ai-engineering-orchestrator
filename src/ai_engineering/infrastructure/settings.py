from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Engineering Orchestrator"
    environment: str = "development"
    log_level: str = "INFO"
    telemetry_enabled: bool = True
    metrics_enabled: bool = True
    api_auth_enabled: bool = False
    api_auth_mode: str = "api_key"
    api_keys_file: str | None = None
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_role_claim: str = "aieo_role"
    oidc_projects_claim: str = "aieo_projects"
    oidc_quota_claim: str = "aieo_requests_per_minute"
    api_quota_redis_url: SecretStr | None = None
    otel_service_name: str = "ai-engineering-orchestrator"
    otel_exporter_otlp_endpoint: str | None = None
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
    github_evidence_timeout_seconds: float = 10.0
    github_private_read_token: SecretStr | None = None
    github_private_read_token_file: str | None = None
    github_private_read_repository: str = "AriRoberto/app-ams"
    evidence_max_files: int = 200
    evidence_max_file_bytes: int = 1_000_000
    evidence_max_total_bytes: int = 5_000_000
    evidence_max_content_files: int = 8
    evidence_max_content_file_bytes: int = 64_000
    evidence_max_content_total_bytes: int = 256_000
    evidence_context_max_chars: int = 12_000
    model_config = SettingsConfigDict(env_prefix="AIEO_", env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def require_production_access_controls(self) -> "Settings":
        if self.environment not in {"staging", "production"}:
            return self
        if not self.api_auth_enabled or self.api_auth_mode != "oidc":
            raise ValueError("staging/production exige autenticação OIDC habilitada")
        if not all((self.oidc_issuer, self.oidc_audience, self.oidc_jwks_url)):
            raise ValueError("staging/production exige configuração OIDC completa")
        if self.api_quota_redis_url is None:
            raise ValueError("staging/production exige quota distribuída via Redis")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
