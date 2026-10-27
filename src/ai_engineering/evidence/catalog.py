import json
import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import yaml
from pydantic import BaseModel, Field


class ProjectSummary(BaseModel):
    id: str
    owner: str
    repository: str
    default_branch: str
    visibility: str
    mode: str


class PublicProjectCreate(BaseModel):
    repository: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9._-]{1,100}$")
    project_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{1,62}$")


class ProjectCatalog:
    def __init__(self, config_dir: str, timeout_seconds: float = 10.0) -> None:
        self.config_dir = Path(config_dir)
        self.timeout_seconds = timeout_seconds

    def list(self) -> list[ProjectSummary]:
        projects: list[ProjectSummary] = []
        for path in sorted(self.config_dir.glob("*.yaml")):
            try:
                config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                projects.append(ProjectSummary.model_validate(config))
            except (OSError, UnicodeError, yaml.YAMLError, ValueError):
                continue
        return projects

    def register_public(self, request: PublicProjectCreate) -> ProjectSummary:
        owner, repository = request.repository.split("/", 1)
        metadata = self._fetch_public_metadata(owner, repository)
        canonical_owner = str(metadata.get("owner", {}).get("login", ""))
        canonical_name = str(metadata.get("name", ""))
        default_branch = str(metadata.get("default_branch", ""))
        if metadata.get("private") is not False:
            raise ValueError("Somente repositórios públicos podem ser cadastrados pela interface")
        component = re.compile(r"^[A-Za-z0-9_.-]+$")
        identifiers = (canonical_owner, canonical_name, default_branch)
        if not all(component.fullmatch(item) for item in identifiers):
            raise ValueError("Metadados inválidos retornados pelo GitHub")
        project_id = request.project_id or re.sub(
            r"[^a-z0-9-]", "", canonical_name.casefold().replace("_", "-")
        )
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", project_id):
            raise ValueError("Não foi possível derivar um ID de projeto válido")
        destination = self.config_dir / f"{project_id}.yaml"
        if destination.exists():
            raise FileExistsError("Já existe um projeto com este ID")
        config = {
            "id": project_id,
            "owner": canonical_owner,
            "repository": f"https://github.com/{canonical_owner}/{canonical_name}",
            "default_branch": default_branch,
            "visibility": "public",
            "mode": "read-only",
            "knowledge_namespace": f"project/{project_id}",
            "mcp": {"allowed_tools": ["project-catalog:project_summary"]},
        }
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(config, stream, sort_keys=False, allow_unicode=True)
        except OSError as exc:
            raise RuntimeError("Diretório de projetos indisponível para escrita") from exc
        return ProjectSummary.model_validate(config)

    def _fetch_public_metadata(self, owner: str, repository: str) -> dict[str, object]:
        endpoint = "https://api.github.com/repos/{}/{}".format(
            quote(owner, safe=""), quote(repository, safe="")
        )
        request = Request(  # noqa: S310 -- endpoint HTTPS fixo do GitHub.
            endpoint,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ai-engineering-orchestrator",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                payload = json.load(response)
        except Exception as exc:
            raise ValueError("Repositório público não encontrado no GitHub") from exc
        if not isinstance(payload, dict):
            raise ValueError("Resposta inválida do GitHub")
        return payload
