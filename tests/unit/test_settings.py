import pytest
from pydantic import ValidationError

from ai_engineering.infrastructure.settings import Settings


def test_development_keeps_local_access_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.api_auth_mode == "api_key"


def test_staging_fails_closed_without_federated_distributed_access() -> None:
    with pytest.raises(ValidationError, match="autenticação OIDC"):
        Settings(environment="staging", _env_file=None)


def test_staging_accepts_oidc_and_redis() -> None:
    settings = Settings(
        environment="staging",
        api_auth_enabled=True,
        api_auth_mode="oidc",
        oidc_issuer="https://identity.example/",
        oidc_audience="aieo",
        oidc_jwks_url="https://identity.example/jwks.json",
        api_quota_redis_url="rediss://redis.example/0",
        _env_file=None,
    )

    assert settings.api_quota_redis_url.get_secret_value().startswith("rediss://")
