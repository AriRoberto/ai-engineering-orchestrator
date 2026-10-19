import hashlib
import hmac
import json
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from threading import Lock
from time import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse


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


_current_identity: ContextVar[APIIdentity | None] = ContextVar(
    "api_identity", default=None
)


class APIAccessController:
    def __init__(self, enabled: bool, key_store: APIKeyStore | None = None) -> None:
        if enabled and key_store is None:
            raise ValueError("Autenticação habilitada sem arquivo de chaves válido")
        self.enabled = enabled
        self.key_store = key_store
        self.quota = FixedWindowQuota()

    @classmethod
    def build(cls, enabled: bool, keys_file: str | None) -> "APIAccessController":
        if not enabled:
            return cls(False)
        if not keys_file:
            raise ValueError("AIEO_API_KEYS_FILE é obrigatório quando autenticação está habilitada")
        return cls(True, APIKeyStore.from_file(keys_file))

    def install(self, app: FastAPI) -> None:
        if self.enabled:
            self._install_openapi_security(app)

        @app.middleware("http")
        async def enforce_access(request: Request, call_next: Any) -> Any:
            if not self.enabled or self._is_public(request.url.path):
                return await call_next(request)
            identity = self.key_store.authenticate(request.headers.get("X-API-Key"))
            if identity is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Credencial de API ausente ou inválida"},
                    headers={"WWW-Authenticate": "ApiKey"},
                )
            if (
                request.method not in {"GET", "HEAD", "OPTIONS"}
                and identity.role is AccessRole.VIEWER
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Papel viewer não permite esta operação"},
                )
            allowed, retry_after = self.quota.consume(identity)
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
        return path in {"/health", "/metrics", "/openapi.json"} or path.startswith(
            ("/docs", "/redoc", "/ui")
        )

    @staticmethod
    def _install_openapi_security(app: FastAPI) -> None:
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
            components.setdefault("securitySchemes", {})["ApiKeyAuth"] = {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            }
            for path, operations in schema.get("paths", {}).items():
                if path.startswith("/v1"):
                    for operation in operations.values():
                        if isinstance(operation, dict):
                            operation["security"] = [{"ApiKeyAuth": []}]
            app.openapi_schema = schema
            return schema

        app.openapi = access_openapi
