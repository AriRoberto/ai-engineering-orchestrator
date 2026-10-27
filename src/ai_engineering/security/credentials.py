from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class GitHubCredentialProvider(Protocol):
    def token_for(self, owner: str, repository: str) -> str | None: ...


def read_secret_file(path: str, *, max_bytes: int = 4096) -> str | None:
    """Lê um segredo pequeno sem registrá-lo ou aceitar arquivos inesperadamente grandes."""
    secret_path = Path(path)
    if not secret_path.is_file():
        return None
    try:
        with secret_path.open(encoding="utf-8") as stream:
            raw_value = stream.read(max_bytes + 1)
    except (OSError, UnicodeError):
        return None
    if len(raw_value) > max_bytes:
        return None
    value = raw_value.strip()
    return value or None


@dataclass(frozen=True)
class ScopedGitHubTokenProvider:
    token: str | None = field(repr=False)
    allowed_repository: str

    def token_for(self, owner: str, repository: str) -> str | None:
        requested = f"{owner}/{repository}"
        if requested.casefold() != self.allowed_repository.casefold():
            return None
        value = (self.token or "").strip()
        return value or None


@dataclass(frozen=True)
class FileGitHubTokenProvider:
    token_file: str
    allowed_repository: str

    def token_for(self, owner: str, repository: str) -> str | None:
        requested = f"{owner}/{repository}"
        if requested.casefold() != self.allowed_repository.casefold():
            return None
        return read_secret_file(self.token_file)
