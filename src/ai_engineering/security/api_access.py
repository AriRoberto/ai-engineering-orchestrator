import hashlib
import hmac
import json
from asyncio import to_thread
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from threading import Lock
from time import time
from typing import Any, Protocol

import jwt
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from jwt import PyJWKClient
from redis.asyncio import Redis


class AccessRole(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"


@dataclass(frozen=True)
class APIIdentity:
    key_id: str
    role: AccessRole
    projects: frozenset[str]
    requests_per_minute: int


@dataclass(frozen=True)
class APIKeyRecord:
    identity: APIIdentity
    key_sha256: str


class APIKeyStore:
    def __init__(self, records: list[APIKeyRecord]) -> None:
        self._records = records

    @classmethod
    def from_file(cls, path: str) -> "APIKeyStore":
        secret_path = Path(path)
        if not secret_path.is_file():
            raise ValueError("Arquivo de chaves da API não encontrado")
        try:
            raw = secret_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError("Arquivo de chaves da API não pôde ser lido") from exc
        if len(raw) > 65_536:
            raise ValueError("Arquivo de chaves da API excede 64 KiB")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Arquivo de chaves da API contém JSON inválido") from exc
        if not isinstance(payload, dict):
            raise ValueError("Arquivo de chaves da API deve conter um objeto JSON")
        records = [cls._parse_record(item) for item in payload.get("keys", [])]
        if not records:
            raise ValueError("Arquivo de chaves da API não contém identidades")
        if len({record.identity.key_id for record in records}) != len(records):
            raise ValueError("Arquivo de chaves da API contém key_id duplicado")
        return cls(records)

    @staticmethod
    def _parse_record(item: Any) -> APIKeyRecord:
        if not isinstance(item, dict):
            raise ValueError("Identidade de API inválida")
        key_id = item.get("key_id")
        key_sha256 = item.get("key_sha256")
        projects = item.get("projects")
        quota = item.get("requests_per_minute", 60)
        if not isinstance(key_id, str) or not key_id or len(key_id) > 64:
            raise ValueError("key_id inválido")
        if (
            not isinstance(key_sha256, str)
            or len(key_sha256) != 64
            or any(character not in "0123456789abcdef" for character in key_sha256)
        ):
            raise ValueError("key_sha256 deve ser SHA-256 hexadecimal em minúsculas")
        if not isinstance(projects, list) or not projects or not all(
            isinstance(project, str) and project for project in projects
        ):
            raise ValueError("projects deve conter ao menos um projeto")
        if not isinstance(quota, int) or isinstance(quota, bool) or not 1 <= quota <= 10_000:
            raise ValueError("requests_per_minute deve estar entre 1 e 10000")
        try:
            role = AccessRole(item.get("role"))
        except ValueError as exc:
            raise ValueError("role deve ser viewer ou operator") from exc
        return APIKeyRecord(
            APIIdentity(key_id, role, frozenset(projects), quota),
            key_sha256,
        )

    def authenticate(self, presented_key: str | None) -> APIIdentity | None:
        if not presented_key or len(presented_key) > 512:
            return None
        digest = hashlib.sha256(presented_key.encode()).hexdigest()
        for record in self._records:
            if hmac.compare_digest(digest, record.key_sha256):
                return record.identity
        return None


class IdentityProvider(Protocol):
    async def authenticate(self, request: Request) -> APIIdentity | None: ...


class APIKeyIdentityProvider:
    def __init__(self, store: APIKeyStore) -> None:
        self.store = store

    async def authenticate(self, request: Request) -> APIIdentity | None:
        return self.store.authenticate(request.headers.get("X-API-Key"))


class OIDCIdentityProvider:
    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_url: str,
        role_claim: str = "aieo_role",
        projects_claim: str = "aieo_projects",
        quota_claim: str = "aieo_requests_per_minute",
    ) -> None:
        if not issuer.startswith("https://") or not jwks_url.startswith("https://"):
            raise ValueError("OIDC issuer e JWKS URL devem usar HTTPS")
        self.issuer = issuer
        self.audience = audience
        self.role_claim = role_claim
        self.projects_claim = projects_claim
        self.quota_claim = quota_claim
        self.jwks = PyJWKClient(jwks_url, cache_keys=True)

    async def authenticate(self, request: Request) -> APIIdentity | None:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token or len(token) > 16_384:
            return None
        try:
            claims = await to_thread(self._decode, token)
            return self._identity(claims)
        except (jwt.PyJWTError, ValueError, TypeError):
            return None

    def _decode(self, token: str) -> dict[str, Any]:
        signing_key = self.jwks.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )

    def _identity(self, claims: dict[str, Any]) -> APIIdentity:
        subject = claims.get("sub")
        role_value = claims.get(self.role_claim)
        projects = claims.get(self.projects_claim)
        quota = claims.get(self.quota_claim, 60)
        if not isinstance(subject, str) or not subject or len(subject) > 255:
            raise ValueError("sub inválido")
        try:
            role = AccessRole(role_value)
        except ValueError as exc:
            raise ValueError("papel OIDC inválido") from exc
        if not isinstance(projects, list) or not projects or not all(
            isinstance(project, str) and project for project in projects
        ):
            raise ValueError("projetos OIDC inválidos")
        if not isinstance(quota, int) or isinstance(quota, bool) or not 1 <= quota <= 10_000:
            raise ValueError("quota OIDC inválida")
        return APIIdentity(f"oidc:{subject}", role, frozenset(projects), quota)


class Quota(Protocol):
    async def consume(self, identity: APIIdentity) -> tuple[bool, int]: ...


class FixedWindowQuota:
    def __init__(self) -> None:
        self._lock = Lock()
        self._usage: dict[tuple[str, int], int] = {}

    def consume(self, identity: APIIdentity, now: float | None = None) -> tuple[bool, int]:
        timestamp = time() if now is None else now
        window = int(timestamp // 60)
        key = (identity.key_id, window)
        with self._lock:
            count = self._usage.get(key, 0)
            if count >= identity.requests_per_minute:
                return False, max(1, 60 - int(timestamp % 60))
            self._usage[key] = count + 1
            if len(self._usage) > 10_000:
                self._usage = {
                    stored_key: value
                    for stored_key, value in self._usage.items()
                    if stored_key[1] >= window - 1
                }
        return True, 0


class AsyncFixedWindowQuota:
    def __init__(self, quota: FixedWindowQuota | None = None) -> None:
        self.quota = quota or FixedWindowQuota()

    async def consume(self, identity: APIIdentity) -> tuple[bool, int]:
        return self.quota.consume(identity)


class RedisFixedWindowQuota:
    _SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
local ttl = redis.call('TTL', KEYS[1])
if count > tonumber(ARGV[1]) then return {0, ttl} end
return {1, 0}
"""

    def __init__(self, url: str) -> None:
        if not url.startswith(("redis://", "rediss://")):
            raise ValueError("AIEO_API_QUOTA_REDIS_URL deve usar redis:// ou rediss://")
        self.client = Redis.from_url(url, decode_responses=True)

    async def consume(self, identity: APIIdentity) -> tuple[bool, int]:
        timestamp = time()
        window = int(timestamp // 60)
        key = f"aieo:quota:{identity.key_id}:{window}"
        result = await self.client.eval(
            self._SCRIPT, 1, key, identity.requests_per_minute, 65
        )
        allowed, retry_after = int(result[0]), int(result[1])
        return bool(allowed), max(1, retry_after) if not allowed else 0


_current_identity: ContextVar[APIIdentity | None] = ContextVar(
    "api_identity", default=None
)


class APIAccessController:
    def __init__(
        self,
        enabled: bool,
        identity_provider: IdentityProvider | None = None,
        quota: Quota | None = None,
        auth_mode: str = "api_key",
    ) -> None:
        if enabled and identity_provider is None:
            raise ValueError("Autenticação habilitada sem provedor de identidade válido")
        self.enabled = enabled
        self.identity_provider = identity_provider
        self.quota = quota or AsyncFixedWindowQuota()
        self.auth_mode = auth_mode

    @classmethod
    def build(
        cls,
        enabled: bool,
        keys_file: str | None,
        *,
        auth_mode: str = "api_key",
        oidc_issuer: str | None = None,
        oidc_audience: str | None = None,
        oidc_jwks_url: str | None = None,
        oidc_role_claim: str = "aieo_role",
        oidc_projects_claim: str = "aieo_projects",
        oidc_quota_claim: str = "aieo_requests_per_minute",
        redis_url: str | None = None,
    ) -> "APIAccessController":
        if not enabled:
            return cls(False)
        if auth_mode == "api_key":
            if not keys_file:
                raise ValueError(
                    "AIEO_API_KEYS_FILE é obrigatório quando autenticação API key está habilitada"
                )
            provider: IdentityProvider = APIKeyIdentityProvider(APIKeyStore.from_file(keys_file))
        elif auth_mode == "oidc":
            if not all((oidc_issuer, oidc_audience, oidc_jwks_url)):
                raise ValueError("issuer, audience e JWKS URL são obrigatórios no modo OIDC")
            provider = OIDCIdentityProvider(
                oidc_issuer,
                oidc_audience,
                oidc_jwks_url,
                oidc_role_claim,
                oidc_projects_claim,
                oidc_quota_claim,
            )
        else:
            raise ValueError("AIEO_API_AUTH_MODE deve ser api_key ou oidc")
        quota: Quota = RedisFixedWindowQuota(redis_url) if redis_url else AsyncFixedWindowQuota()
        return cls(True, provider, quota, auth_mode)

    def install(self, app: FastAPI) -> None:
        if self.enabled:
            self._install_openapi_security(app)

        @app.middleware("http")
        async def enforce_access(request: Request, call_next: Any) -> Any:
            if not self.enabled or self._is_public(request.url.path):
                return await call_next(request)
            identity = await self.identity_provider.authenticate(request)
            if identity is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Credencial de API ausente ou inválida"},
                    headers={
                        "WWW-Authenticate": "Bearer" if self.auth_mode == "oidc" else "ApiKey"
                    },
                )
            if (
                request.method not in {"GET", "HEAD", "OPTIONS"}
                and identity.role is AccessRole.VIEWER
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Papel viewer não permite esta operação"},
                )
            allowed, retry_after = await self.quota.consume(identity)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Quota de requisições excedida"},
                    headers={"Retry-After": str(retry_after)},
                )
            token = _current_identity.set(identity)
            try:
                try:
                    response = await call_next(request)
                except PermissionError as exc:
                    return JSONResponse(status_code=403, content={"detail": str(exc)})
                response.headers["X-RateLimit-Limit"] = str(identity.requests_per_minute)
                return response
            finally:
                _current_identity.reset(token)

    def authorize_project(self, project_id: str) -> None:
        if not self.enabled:
            return
        identity = _current_identity.get()
        if identity is None or (
            "*" not in identity.projects and project_id not in identity.projects
        ):
            raise PermissionError("Credencial não autorizada para este projeto")

    @staticmethod
    def _is_public(path: str) -> bool:
        return path in {"/health", "/ready", "/metrics", "/openapi.json"} or path.startswith(
            ("/docs", "/redoc", "/ui")
        )

    def _install_openapi_security(self, app: FastAPI) -> None:
        def access_openapi() -> dict[str, Any]:
            if app.openapi_schema:
                return app.openapi_schema
            schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
            )
            components = schema.setdefault("components", {})
            security_name = "OIDC" if self.auth_mode == "oidc" else "ApiKeyAuth"
            security = (
                {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
                if self.auth_mode == "oidc"
                else {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            )
            components.setdefault("securitySchemes", {})[security_name] = security
            for path, operations in schema.get("paths", {}).items():
                if path.startswith("/v1"):
                    for operation in operations.values():
                        if isinstance(operation, dict):
                            operation["security"] = [{security_name: []}]
            app.openapi_schema = schema
            return schema

        app.openapi = access_openapi
