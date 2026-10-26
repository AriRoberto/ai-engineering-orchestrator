import hashlib
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from ai_engineering.security.api_access import (
    AccessRole,
    APIAccessController,
    APIIdentity,
    APIKeyStore,
    FixedWindowQuota,
    OIDCIdentityProvider,
    RedisFixedWindowQuota,
)


def _write_keys(tmp_path, keys: list[dict[str, object]]) -> str:
    path = tmp_path / "api-keys.json"
    path.write_text(json.dumps({"keys": keys}), encoding="utf-8")
    return str(path)


def _record(secret: str, **overrides) -> dict[str, object]:
    return {
        "key_id": "operator-lab",
        "key_sha256": hashlib.sha256(secret.encode()).hexdigest(),
        "role": "operator",
        "projects": ["project-a"],
        "requests_per_minute": 2,
        **overrides,
    }


def test_key_store_authenticates_hash_without_retaining_plaintext(tmp_path) -> None:
    store = APIKeyStore.from_file(_write_keys(tmp_path, [_record("secret-value")]))

    identity = store.authenticate("secret-value")

    assert identity is not None
    assert identity.key_id == "operator-lab"
    assert store.authenticate("wrong") is None
    assert "secret-value" not in repr(store)


@pytest.mark.parametrize(
    "record",
    [
        _record("key", key_sha256="invalid"),
        _record("key", role="admin"),
        _record("key", projects=[]),
        _record("key", requests_per_minute=0),
    ],
)
def test_key_store_rejects_invalid_records(tmp_path, record) -> None:
    with pytest.raises(ValueError):
        APIKeyStore.from_file(_write_keys(tmp_path, [record]))


def test_fixed_window_quota_is_isolated_by_identity() -> None:
    quota = FixedWindowQuota()
    first = APIIdentity("first", AccessRole.OPERATOR, frozenset({"*"}), 1)
    second = APIIdentity("second", AccessRole.OPERATOR, frozenset({"*"}), 1)

    assert quota.consume(first, now=120.0) == (True, 0)
    assert quota.consume(first, now=121.0) == (False, 59)
    assert quota.consume(second, now=121.0) == (True, 0)
    assert quota.consume(first, now=180.0) == (True, 0)


def test_middleware_enforces_auth_role_project_and_quota(tmp_path) -> None:
    path = _write_keys(
        tmp_path,
        [
            _record("operator-secret"),
            _record(
                "viewer-secret",
                key_id="viewer-lab",
                role="viewer",
                requests_per_minute=10,
            ),
        ],
    )
    controller = APIAccessController.build(True, path)
    app = FastAPI()
    controller.install(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/v1/projects/{project_id}")
    def read_project(project_id: str):
        controller.authorize_project(project_id)
        return {"project_id": project_id}

    @app.post("/v1/projects/{project_id}")
    def write_project(project_id: str):
        controller.authorize_project(project_id)
        return {"project_id": project_id}

    client = TestClient(app, raise_server_exceptions=False)

    assert client.get("/health").status_code == 200
    openapi = client.get("/openapi.json").json()
    assert openapi["components"]["securitySchemes"]["ApiKeyAuth"]["name"] == "X-API-Key"
    assert openapi["paths"]["/v1/projects/{project_id}"]["get"]["security"] == [
        {"ApiKeyAuth": []}
    ]
    assert client.get("/v1/projects/project-a").status_code == 401
    viewer_write = client.post(
        "/v1/projects/project-a", headers={"X-API-Key": "viewer-secret"}
    )
    assert viewer_write.status_code == 403
    forbidden_project = client.get(
        "/v1/projects/project-b", headers={"X-API-Key": "operator-secret"}
    )
    assert forbidden_project.status_code == 403
    first = client.get(
        "/v1/projects/project-a", headers={"X-API-Key": "operator-secret"}
    )
    limited = client.get(
        "/v1/projects/project-a", headers={"X-API-Key": "operator-secret"}
    )
    assert first.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "2"
    assert limited.status_code == 429
    assert "Retry-After" in limited.headers


def test_enabled_controller_requires_keys_file() -> None:
    with pytest.raises(ValueError, match="AIEO_API_KEYS_FILE"):
        APIAccessController.build(True, None)


@pytest.mark.asyncio
async def test_oidc_provider_maps_verified_claims(monkeypatch) -> None:
    provider = OIDCIdentityProvider(
        "https://identity.example/",
        "aieo",
        "https://identity.example/jwks.json",
    )
    monkeypatch.setattr(
        provider,
        "_decode",
        lambda token: {
            "sub": "user-123",
            "aieo_role": "operator",
            "aieo_projects": ["project-a"],
            "aieo_requests_per_minute": 25,
        },
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/v1/projects/project-a",
            "headers": [(b"authorization", b"Bearer signed-token")],
        }
    )

    identity = await provider.authenticate(request)

    assert identity == APIIdentity(
        "oidc:user-123", AccessRole.OPERATOR, frozenset({"project-a"}), 25
    )


@pytest.mark.asyncio
async def test_oidc_provider_rejects_invalid_claims_and_credentials(monkeypatch) -> None:
    provider = OIDCIdentityProvider(
        "https://identity.example/",
        "aieo",
        "https://identity.example/jwks.json",
    )
    monkeypatch.setattr(provider, "_decode", lambda token: {"sub": "user-123"})
    missing_bearer = Request(
        {"type": "http", "method": "GET", "path": "/v1/projects", "headers": []}
    )
    invalid_claims = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/v1/projects",
            "headers": [(b"authorization", b"Bearer signed-token")],
        }
    )

    assert await provider.authenticate(missing_bearer) is None
    assert await provider.authenticate(invalid_claims) is None


@pytest.mark.asyncio
async def test_redis_quota_uses_atomic_global_counter() -> None:
    class FakeRedis:
        async def eval(self, script, key_count, key, limit, ttl):
            assert "INCR" in script
            assert key_count == 1
            assert key.startswith("aieo:quota:operator-lab:")
            assert (limit, ttl) == (2, 65)
            return [0, 41]

    quota = RedisFixedWindowQuota("rediss://redis.example/0")
    quota.client = FakeRedis()
    identity = APIIdentity("operator-lab", AccessRole.OPERATOR, frozenset({"*"}), 2)

    assert await quota.consume(identity) == (False, 41)


def test_oidc_mode_requires_complete_secure_configuration() -> None:
    with pytest.raises(ValueError, match="obrigatórios"):
        APIAccessController.build(True, None, auth_mode="oidc")
    with pytest.raises(ValueError, match="HTTPS"):
        APIAccessController.build(
            True,
            None,
            auth_mode="oidc",
            oidc_issuer="http://identity.example/",
            oidc_audience="aieo",
            oidc_jwks_url="https://identity.example/jwks.json",
        )
    with pytest.raises(ValueError, match="api_key ou oidc"):
        APIAccessController.build(True, None, auth_mode="unknown")
