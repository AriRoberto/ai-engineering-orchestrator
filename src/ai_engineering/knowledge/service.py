import hashlib
import math
import re
from collections import Counter
from typing import Protocol
from uuid import UUID

from ai_engineering.knowledge.models import (
    FeedbackCreate,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    KnowledgeScope,
    SearchHit,
)
from ai_engineering.security.content import KnowledgeContentGuard


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Configuração de fragmentação inválida")
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks, start = [], 0
    while start < len(normalized):
        chunks.append(normalized[start : start + size])
        if start + size >= len(normalized):
            break
        start += size - overlap
    return chunks


class DeterministicEmbeddingProvider:
    """Embedding local explícito para demo; não representa um modelo semântico de produção."""

    def __init__(self, dimensions: int = 16) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"\w+", text.casefold()):
            digest = hashlib.sha256(token.encode()).digest()
            vector[int.from_bytes(digest[:2], "big") % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class KnowledgeRepository(Protocol):
    def add(self, document: KnowledgeDocument, chunks: list[KnowledgeChunk]) -> None: ...
    def get_document(self, document_id: UUID, project_id: str) -> KnowledgeDocument | None: ...
    def delete(self, document_id: UUID, project_id: str) -> bool: ...
    def chunks_for(
        self, project_id: str, include_shared: bool
    ) -> list[tuple[KnowledgeDocument, KnowledgeChunk]]: ...
    def add_feedback(self, feedback: FeedbackCreate) -> None: ...


class InMemoryKnowledgeRepository:
    def __init__(self) -> None:
        self.documents: dict[UUID, KnowledgeDocument] = {}
        self.chunks: dict[UUID, list[KnowledgeChunk]] = {}
        self.feedback: list[FeedbackCreate] = []

    def add(self, document: KnowledgeDocument, chunks: list[KnowledgeChunk]) -> None:
        self.documents[document.id] = document.model_copy(deep=True)
        self.chunks[document.id] = [chunk.model_copy(deep=True) for chunk in chunks]

    def get_document(self, document_id: UUID, project_id: str) -> KnowledgeDocument | None:
        document = self.documents.get(document_id)
        if not document or document.project_id != project_id:
            return None
        return document.model_copy(deep=True)

    def delete(self, document_id: UUID, project_id: str) -> bool:
        if not self.get_document(document_id, project_id):
            return False
        del self.documents[document_id]
        self.chunks.pop(document_id, None)
        return True

    def chunks_for(self, project_id: str, include_shared: bool):
        result = []
        for document in self.documents.values():
            owned = document.project_id == project_id
            shared = (
                include_shared
                and document.scope == KnowledgeScope.SHARED
                and document.sharing_authorized
            )
            if owned or shared:
                result.extend((document, chunk) for chunk in self.chunks[document.id])
        return result

    def add_feedback(self, feedback: FeedbackCreate) -> None:
        self.feedback.append(feedback.model_copy(deep=True))


class KnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        embeddings: DeterministicEmbeddingProvider,
        guard: KnowledgeContentGuard,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> None:
        self.repository = repository
        self.embeddings = embeddings
        self.guard = guard
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def ingest(self, request: KnowledgeDocumentCreate) -> KnowledgeDocument:
        if request.scope == KnowledgeScope.SHARED and not request.sharing_authorized:
            raise PermissionError("Compartilhamento exige autorização explícita")
        if not self.guard.assess(request.content).allowed:
            raise ValueError("Conteúdo rejeitado pela proteção contra prompt injection")
        parts = chunk_text(request.content, self.chunk_size, self.chunk_overlap)
        document = KnowledgeDocument(
            project_id=request.project_id,
            title=request.title,
            source=request.source,
            scope=request.scope,
            sharing_authorized=request.sharing_authorized,
            chunks=len(parts),
        )
        chunks = [
            KnowledgeChunk(
                document_id=document.id,
                project_id=request.project_id,
                scope=request.scope,
                content=content,
                position=position,
                embedding=self.embeddings.embed(content),
            )
            for position, content in enumerate(parts)
        ]
        self.repository.add(document, chunks)
        return document

    def search(
        self, project_id: str, query: str, limit: int, include_shared: bool
    ) -> list[SearchHit]:
        query_embedding = self.embeddings.embed(query)
        query_terms = Counter(re.findall(r"\w+", query.casefold()))
        hits = []
        for document, chunk in self.repository.chunks_for(project_id, include_shared):
            semantic = sum(a * b for a, b in zip(query_embedding, chunk.embedding, strict=True))
            tokens = Counter(re.findall(r"\w+", chunk.content.casefold()))
            keyword = sum(min(count, tokens[term]) for term, count in query_terms.items())
            keyword_score = keyword / max(sum(query_terms.values()), 1)
            hits.append(
                SearchHit(
                    document_id=document.id,
                    chunk_id=chunk.id,
                    title=document.title,
                    source=document.source,
                    content=chunk.content,
                    score=round((0.7 * semantic) + (0.3 * keyword_score), 6),
                )
            )
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]
