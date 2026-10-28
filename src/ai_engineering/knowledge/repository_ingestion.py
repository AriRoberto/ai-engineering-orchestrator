import argparse
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.exc import SQLAlchemyError

from ai_engineering.knowledge.embeddings import EmbeddingProvider, validate_vectors
from ai_engineering.knowledge.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeProvenance,
    KnowledgeScope,
)
from ai_engineering.knowledge.service import DeterministicEmbeddingProvider, KnowledgeRepository
from ai_engineering.security.content import KnowledgeContentGuard
from ai_engineering.security.secrets import SecretRedactor

ALLOWED_SUFFIXES = {
    ".md",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".css",
    ".html",
    ".sql",
    ".yaml",
    ".yml",
    ".toml",
    ".sh",
    ".json",
}
EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    "coverage",
    "logs",
    "evals",
}
EXCLUDED_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock"}
SENSITIVE_NAME = re.compile(r"(^\.env|secret|credential|^id_|\.pem$|\.key$)", re.IGNORECASE)


@dataclass
class RepositorySnapshot:
    project_id: str
    collection: str
    revision: str
    entries: list[tuple[KnowledgeDocument, list[KnowledgeChunk]]]
    files: list[dict]
    working_tree_dirty: bool
    embedding_key: str = "deterministic:deterministic-demo:1:16"

    def report(self) -> dict:
        return {
            "project_id": self.project_id,
            "collection": self.collection,
            "revision": self.revision,
            "embedding_key": self.embedding_key,
            "working_tree_dirty": self.working_tree_dirty,
            "documents": len(self.entries),
            "chunks": sum(len(chunks) for _document, chunks in self.entries),
            "files": self.files,
        }

    def publish(self, repository: KnowledgeRepository, allow_empty: bool = False) -> dict[str, int]:
        if not self.entries and not allow_empty:
            raise ValueError("Coleção vazia: use --allow-empty para autorizar sua remoção")
        return repository.sync_collection(
            self.project_id, self.collection, self.entries, self.embedding_key
        )

    def with_embeddings(self, provider: EmbeddingProvider) -> "RepositorySnapshot":
        parts = [chunk for _document, chunks in self.entries for chunk in chunks]
        vectors = provider.embed_many([chunk.content for chunk in parts])
        validate_vectors(vectors, len(parts), provider.dimensions)
        entries = []
        offset = 0
        for document, chunks in self.entries:
            updated = document.model_copy(deep=True)
            updated.embedding_key = provider.key
            updated.provenance.embedding_model = provider.model
            updated.provenance.embedding_dimensions = provider.dimensions
            updated.provenance.embedding_version = provider.version
            identity = json.dumps(
                updated.provenance.model_dump(exclude={"revision"}), sort_keys=True
            )
            updated.id = uuid5(NAMESPACE_URL, updated.source + identity)
            converted = []
            for chunk in chunks:
                converted.append(
                    chunk.model_copy(
                        update={
                            "id": uuid5(updated.id, str(chunk.position)),
                            "document_id": updated.id,
                            "embedding": vectors[offset],
                        },
                        deep=True,
                    )
                )
                offset += 1
            entries.append((updated, converted))
        return RepositorySnapshot(
            self.project_id,
            self.collection,
            self.revision,
            entries,
            self.files,
            self.working_tree_dirty,
            provider.key,
        )


def line_chunks(content: str, size: int) -> list[tuple[str, int, int]]:
    if size < 1:
        raise ValueError("Tamanho de fragmento deve ser positivo")
    parts = []
    buffer = ""
    start_line = 1
    end_line = 1
    for line_number, line in enumerate(content.splitlines(keepends=True), 1):
        if buffer and len(buffer) + len(line) > size:
            parts.append((buffer, start_line, end_line))
            buffer = ""
        while len(line) > size:
            parts.append((line[:size], line_number, line_number))
            line = line[size:]
        if line:
            if not buffer:
                start_line = line_number
            buffer += line
            end_line = line_number
    if buffer:
        parts.append((buffer, start_line, end_line))
    return parts


class RepositoryScanner:
    def __init__(
        self,
        root: Path,
        project_id: str,
        collection: str = "repository",
        max_file_bytes: int = 1_000_000,
        max_total_bytes: int = 20_000_000,
        chunk_size: int = 1600,
    ) -> None:
        for identifier in (project_id, collection):
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", identifier):
                raise ValueError("Projeto e coleção devem ter de 2 a 63 caracteres: a-z, 0-9, -")
        if min(max_file_bytes, max_total_bytes, chunk_size) < 1:
            raise ValueError("Limites devem ser positivos")
        self.root = root.resolve()
        self.project_id = project_id
        self.collection = collection
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes
        self.chunk_size = chunk_size
        self.git = shutil.which("git")
        if not self.git:
            raise RuntimeError("Git não encontrado")

    def _git(self, *arguments: str) -> bytes:
        result = subprocess.run(
            [self.git, "-C", str(self.root), *arguments],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError("Falha ao ler revisão Git; nenhuma coleção foi publicada")
        return result.stdout

    def scan(self, revision: str = "HEAD") -> RepositorySnapshot:
        resolved = (
            self._git("rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}")
            .decode()
            .strip()
        )
        records = self._git("ls-tree", "--full-tree", "-r", "-l", "-z", resolved).split(b"\0")
        entries = []
        files = []
        total_bytes = 0
        guard = KnowledgeContentGuard()
        redactor = SecretRedactor()
        embeddings = DeterministicEmbeddingProvider(16)
        for record in records:
            if not record:
                continue
            header, raw_path = record.split(b"\t", 1)
            mode, kind, object_id, raw_size = header.split()
            path = raw_path.decode("utf-8", errors="strict")
            relative = PurePosixPath(path)
            reason = None
            if mode not in {b"100644", b"100755"} or kind != b"blob":
                reason = "non_regular_file"
            elif (
                any(
                    part in EXCLUDED_PARTS or SENSITIVE_NAME.search(part) for part in relative.parts
                )
                or relative.name in EXCLUDED_NAMES
            ):
                reason = "excluded_path"
            elif relative.suffix.lower() not in ALLOWED_SUFFIXES and relative.name not in {
                "Dockerfile",
                "Makefile",
            }:
                reason = "unsupported_type"
            elif int(raw_size) > self.max_file_bytes:
                reason = "file_too_large"
            if reason:
                files.append({"path": path, "status": "skipped", "reason": reason})
                continue
            total_bytes += int(raw_size)
            if total_bytes > self.max_total_bytes:
                raise ValueError("Limite total excedido; nenhuma coleção foi publicada")
            raw = self._git("cat-file", "blob", object_id.decode("ascii"))
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                files.append({"path": path, "status": "skipped", "reason": "not_utf8"})
                continue
            if "\0" in content or not content.strip():
                files.append({"path": path, "status": "skipped", "reason": "binary_or_empty"})
                continue
            if "-----BEGIN " in content and "PRIVATE KEY-----" in content:
                files.append({"path": path, "status": "quarantined", "reason": "private_key"})
                continue
            if not guard.assess(content).allowed:
                files.append({"path": path, "status": "quarantined", "reason": "content_guard"})
                continue
            sanitized_lines = []
            redactions = 0
            for line in content.splitlines(keepends=True):
                body = line.rstrip("\r\n")
                result = redactor.redact(body)
                sanitized_lines.append(result.content + line[len(body) :])
                redactions += result.redactions
            sanitized_content = "".join(sanitized_lines)
            provenance = KnowledgeProvenance(
                path=path,
                revision=resolved,
                content_sha256=hashlib.sha256(sanitized_content.encode()).hexdigest(),
                document_type=relative.suffix.lstrip(".") or relative.name,
                chunk_size=self.chunk_size,
                redactions=redactions,
            )
            source = f"repo://{self.project_id}/{self.collection}/{path}"
            identity = json.dumps(provenance.model_dump(exclude={"revision"}), sort_keys=True)
            document_id = uuid5(NAMESPACE_URL, source + identity)
            chunks = [
                KnowledgeChunk(
                    id=uuid5(document_id, str(position)),
                    document_id=document_id,
                    project_id=self.project_id,
                    scope=KnowledgeScope.PROJECT,
                    content=part,
                    position=position,
                    embedding=embeddings.embed(part),
                    start_line=start_line,
                    end_line=end_line,
                )
                for position, (part, start_line, end_line) in enumerate(
                    line_chunks(sanitized_content, self.chunk_size)
                )
            ]
            document = KnowledgeDocument(
                id=document_id,
                project_id=self.project_id,
                title=path[:300],
                source=source,
                scope=KnowledgeScope.PROJECT,
                sharing_authorized=False,
                chunks=len(chunks),
                collection=self.collection,
                provenance=provenance,
            )
            entries.append((document, chunks))
            files.append(
                {
                    "path": path,
                    "status": "accepted",
                    "chunks": len(chunks),
                    "redactions": redactions,
                }
            )
        dirty = bool(self._git("status", "--porcelain", "--untracked-files=no").strip())
        return RepositorySnapshot(self.project_id, self.collection, resolved, entries, files, dirty)


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexar uma revisão Git em conhecimento isolado")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--collection", default="repository")
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--chunk-size", type=int, default=1600)
    parser.add_argument("--max-file-bytes", type=int, default=1_000_000)
    parser.add_argument("--max-total-bytes", type=int, default=20_000_000)
    parser.add_argument("--apply", action="store_true", help="Publicar; o padrão é somente prévia")
    parser.add_argument("--allow-empty", action="store_true")
    arguments = parser.parse_args()
    repository = None
    try:
        snapshot = RepositoryScanner(
            arguments.root,
            arguments.project_id,
            arguments.collection,
            arguments.max_file_bytes,
            arguments.max_total_bytes,
            arguments.chunk_size,
        ).scan(arguments.revision)
        report = snapshot.report()
        report["mode"] = "apply" if arguments.apply else "preview"
        if arguments.apply:
            from ai_engineering.infrastructure.settings import Settings
            from ai_engineering.knowledge.database import PostgresKnowledgeRepository
            from ai_engineering.knowledge.embeddings import build_embedding_provider

            settings = Settings()
            if not settings.database_url:
                raise ValueError("AIEO_DATABASE_URL é obrigatória para --apply")
            provider = build_embedding_provider(settings)
            if provider.key != snapshot.embedding_key:
                snapshot = snapshot.with_embeddings(provider)
            report["embedding_key"] = snapshot.embedding_key
            repository = PostgresKnowledgeRepository(settings.database_url)
            report["sync"] = snapshot.publish(repository, arguments.allow_empty)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")
    except (OSError, subprocess.TimeoutExpired, SQLAlchemyError):
        parser.exit(1, "Falha de leitura ou publicação; confira o acesso e as migrações do banco\n")
    finally:
        if repository:
            repository.engine.dispose()


if __name__ == "__main__":
    main()
