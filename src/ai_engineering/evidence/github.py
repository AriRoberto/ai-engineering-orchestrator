import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from ai_engineering.evidence.models import EvidenceCollection, EvidenceFile
from ai_engineering.security.credentials import GitHubCredentialProvider


class EvidenceCollectionError(RuntimeError):
    pass


class GitHubTreeTransport(Protocol):
    def has_credentials(self, owner: str, repository: str) -> bool: ...

    def get_tree(self, owner: str, repository: str, ref: str) -> dict[str, object]: ...

    def get_content(
        self, owner: str, repository: str, path: str, ref: str, max_bytes: int
    ) -> bytes: ...


class UrllibGitHubTreeTransport:
    api_url = "https://api.github.com"

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        credential_provider: GitHubCredentialProvider | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.credential_provider = credential_provider

    def has_credentials(self, owner: str, repository: str) -> bool:
        return self._token(owner, repository) is not None

    def _token(self, owner: str, repository: str) -> str | None:
        if not self.credential_provider:
            return None
        return self.credential_provider.token_for(owner, repository)

    def _headers(self, owner: str, repository: str, accept: str) -> dict[str, str]:
        headers = {
            "Accept": accept,
            "User-Agent": "ai-engineering-orchestrator",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = self._token(owner, repository)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def get_tree(self, owner: str, repository: str, ref: str) -> dict[str, object]:
        path = "/repos/{}/{}/git/trees/{}".format(
            quote(owner, safe=""), quote(repository, safe=""), quote(ref, safe="")
        )
        url = f"{self.api_url}{path}?{urlencode({'recursive': '1'})}"
        request = Request(  # noqa: S310 -- URL base is a fixed GitHub HTTPS endpoint.
            url,
            headers=self._headers(owner, repository, "application/vnd.github+json"),
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            return json.load(response)

    def get_content(
        self, owner: str, repository: str, path: str, ref: str, max_bytes: int
    ) -> bytes:
        endpoint = "/repos/{}/{}/contents/{}".format(
            quote(owner, safe=""), quote(repository, safe=""), quote(path, safe="/")
        )
        url = f"{self.api_url}{endpoint}?{urlencode({'ref': ref})}"
        request = Request(  # noqa: S310 -- URL base is a fixed GitHub HTTPS endpoint.
            url,
            headers=self._headers(owner, repository, "application/vnd.github.raw+json"),
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            content = response.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise EvidenceCollectionError("Conteúdo excedeu o limite durante download")
        return content


@dataclass(frozen=True)
class GitHubProject:
    project_id: str
    repository_url: str
    owner: str
    repository: str
    ref: str
    visibility: str
    requires_authentication: bool


def parse_github_project(config: dict[str, object]) -> GitHubProject:
    visibility = str(config.get("visibility", ""))
    if visibility not in {"public", "private"} or config.get("mode") != "read-only":
        raise PermissionError("Coleta disponível somente para projetos GitHub somente leitura")
    if visibility == "private" and config.get("authenticated_read_only") is not True:
        raise PermissionError("Projeto privado não habilitado para leitura autenticada")
    repository_url = str(config.get("repository", ""))
    parsed = urlparse(repository_url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or parsed.hostname != "github.com" or len(parts) != 2:
        raise PermissionError("Repositório GitHub inválido")
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    valid_component = re.compile(r"^[A-Za-z0-9_.-]+$")
    if not valid_component.fullmatch(owner) or not valid_component.fullmatch(repository):
        raise PermissionError("Identificador de repositório inválido")
    ref = str(config.get("default_branch", ""))
    if not valid_component.fullmatch(ref):
        raise PermissionError("Branch padrão inválida")
    return GitHubProject(
        project_id=str(config["id"]),
        repository_url=repository_url,
        owner=owner,
        repository=repository,
        ref=ref,
        visibility=visibility,
        requires_authentication=visibility == "private",
    )


class GitHubEvidenceCollector:
    allowed_suffixes = frozenset(
        {".md", ".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".sql"}
    )
    allowed_names = frozenset(
        {"Dockerfile", "Makefile", "requirements.txt", "go.mod", "Cargo.toml", ".gitignore"}
    )
    excluded_directories = frozenset(
        {".git", ".venv", "build", "dist", "node_modules", "target", "vendor"}
    )

    def __init__(
        self,
        transport: GitHubTreeTransport,
        max_files: int = 200,
        max_file_bytes: int = 1_000_000,
        max_total_bytes: int = 5_000_000,
        max_content_files: int = 8,
        max_content_file_bytes: int = 64_000,
        max_content_total_bytes: int = 256_000,
        content_guard=None,
        secret_redactor=None,
    ) -> None:
        self.transport = transport
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.max_content_files = max_content_files
        self.max_content_file_bytes = max_content_file_bytes
        self.max_content_total_bytes = max_content_total_bytes
        self.content_guard = content_guard
        self.secret_redactor = secret_redactor

    def collect(
        self, project: GitHubProject, *, include_content: bool = False
    ) -> EvidenceCollection:
        if project.requires_authentication and not self.transport.has_credentials(
            project.owner, project.repository
        ):
            raise PermissionError("Credencial de leitura privada indisponível")
        try:
            payload = self.transport.get_tree(project.owner, project.repository, project.ref)
        except Exception as exc:
            raise EvidenceCollectionError("Falha ao consultar a árvore do GitHub") from exc
        if payload.get("truncated") is True:
            raise EvidenceCollectionError("Árvore GitHub truncada; coleta recusada")
        revision = str(payload.get("sha", ""))
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise EvidenceCollectionError("Resposta GitHub sem revisão identificável")
        files: list[EvidenceFile] = []
        total_bytes = 0
        entries = payload.get("tree", [])
        if not isinstance(entries, list):
            raise EvidenceCollectionError("Resposta GitHub com árvore inválida")
        for entry in sorted(entries, key=lambda item: str(item.get("path", ""))):
            if entry.get("type") != "blob":
                continue
            path = str(entry.get("path", ""))
            sha = str(entry.get("sha", ""))
            try:
                size = int(entry.get("size", 0))
            except (TypeError, ValueError):
                continue
            path_object = PurePosixPath(path)
            if path_object.is_absolute() or ".." in path_object.parts:
                continue
            if any(part in self.excluded_directories for part in path_object.parts[:-1]):
                continue
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                continue
            name = PurePosixPath(path).name
            if (
                path_object.suffix.casefold() not in self.allowed_suffixes
                and name not in self.allowed_names
            ):
                continue
            if size < 0 or size > self.max_file_bytes or total_bytes + size > self.max_total_bytes:
                continue
            files.append(
                EvidenceFile(
                    path=path,
                    sha=sha,
                    size=size,
                    source_url=(
                        f"{project.repository_url}/blob/{quote(revision, safe='')}/"
                        f"{quote(path, safe='/')}"
                    ),
                )
            )
            total_bytes += size
            if len(files) >= self.max_files:
                break
        if include_content:
            self._collect_content(project, files)
        return EvidenceCollection(
            project_id=project.project_id,
            repository=project.repository_url,
            ref=project.ref,
            revision=revision,
            files=files,
            total_bytes=total_bytes,
            metadata={
                "tree_entries": len(entries),
                "limits_applied": True,
                "visibility": project.visibility,
                "authenticated": project.requires_authentication,
            },
        )

    def _collect_content(
        self, project: GitHubProject, files: list[EvidenceFile]
    ) -> None:
        downloaded = 0
        total_bytes = 0
        prioritized = sorted(files, key=lambda item: (self._content_priority(item.path), item.path))
        for item in prioritized:
            if downloaded >= self.max_content_files:
                break
            if item.size > self.max_content_file_bytes:
                item.content_status = "too-large"
                continue
            if total_bytes + item.size > self.max_content_total_bytes:
                item.content_status = "total-limit"
                continue
            try:
                raw = self.transport.get_content(
                    project.owner,
                    project.repository,
                    item.path,
                    project.ref,
                    self.max_content_file_bytes,
                )
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                item.content_status = "non-utf8"
                continue
            except Exception as exc:
                raise EvidenceCollectionError("Falha ao coletar conteúdo textual") from exc
            item.content_sha256 = hashlib.sha256(raw).hexdigest()
            if self.content_guard and not self.content_guard.assess(text).allowed:
                item.content_status = "quarantined"
                downloaded += 1
                total_bytes += len(raw)
                continue
            redacted = self.secret_redactor.redact(text) if self.secret_redactor else None
            item.content = redacted.content if redacted else text
            item.content_status = "redacted" if redacted and redacted.redactions else "included"
            downloaded += 1
            total_bytes += len(raw)

    @staticmethod
    def _content_priority(path: str) -> int:
        name = PurePosixPath(path).name
        priorities = {
            "README.md": 0,
            "pyproject.toml": 1,
            "package.json": 1,
            "requirements.txt": 1,
            "Dockerfile": 2,
            "SECURITY.md": 2,
            "CHANGELOG.md": 3,
        }
        return priorities.get(name, 10)
