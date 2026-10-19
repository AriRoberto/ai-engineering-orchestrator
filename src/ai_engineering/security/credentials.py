from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class GitHubCredentialProvider(Protocol):
    def token_for(self, owner: str, repository: str) -> str | None: ...


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
        path = Path(self.token_file)
        if not path.is_file():
            return None
        try:
            with path.open(encoding="utf-8") as stream:
                raw_value = stream.read(4097)
        except (OSError, UnicodeError):
            return None
        if len(raw_value) > 4096:
            return None
        value = raw_value.strip()
        return value or None
