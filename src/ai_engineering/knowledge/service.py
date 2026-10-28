import math
import re
from collections import Counter
from typing import Protocol
from uuid import UUID

from ai_engineering.knowledge.embeddings import (
    DeterministicEmbeddingProvider as DeterministicEmbeddingProvider,
)
from ai_engineering.knowledge.embeddings import (
    EmbeddingProvider,
    validate_vectors,
)
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


class KnowledgeRepository(Protocol):
    def add(self, document: KnowledgeDocument, chunks: list[KnowledgeChunk]) -> None: ...
    def get_document(self, document_id: UUID, project_id: str) -> KnowledgeDocument | None: ...
    def delete(self, document_id: UUID, project_id: str) -> bool: ...
    def chunks_for(
        self, project_id: str, include_shared: bool
    ) -> list[tuple[KnowledgeDocument, KnowledgeChunk]]: ...
    def add_feedback(self, feedback: FeedbackCreate) -> None: ...
    def search(
        self,
        project_id: str,
        query: str,
        embedding: list[float],
        embedding_key: str,
        limit: int,
        include_shared: bool,
    ) -> list[SearchHit]: ...
    def sync_collection(
        self,
        project_id: str,
        collection: str,
        entries: list[tuple[KnowledgeDocument, list[KnowledgeChunk]]],
        embedding_key: str = "deterministic:deterministic-demo:1:16",
    ) -> dict[str, int]: ...


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

    def sync_collection(
        self,
        project_id,
        collection,
        entries,
        embedding_key="deterministic:deterministic-demo:1:16",
    ):
        validate_collection(project_id, collection, entries, embedding_key)
        existing = {
            key
            for key, document in self.documents.items()
            if document.project_id == project_id
            and document.collection == collection
            and document.embedding_key == embedding_key
        }
        incoming = {document.id for document, _chunks in entries}
        documents = self.documents.copy()
        chunks = self.chunks.copy()
        for identifier in existing - incoming:
            documents.pop(identifier)
            chunks.pop(identifier, None)
        for document, parts in entries:
            if document.id not in existing:
                documents[document.id] = document.model_copy(deep=True)
                chunks[document.id] = [part.model_copy(deep=True) for part in parts]
            else:
                refreshed = document.model_copy(deep=True)
                refreshed.created_at = documents[document.id].created_at
                documents[document.id] = refreshed
        self.documents, self.chunks = documents, chunks
        return collection_counts(existing, incoming)

    def search(self, project_id, query, embedding, embedding_key, limit, include_shared):
        candidates = [
            (document, chunk)
            for document, chunk in self.chunks_for(project_id, include_shared)
            if document.embedding_key == embedding_key
        ]
        terms = Counter(re.findall(r"\w+", query.casefold()))
        scores = []
        for document, chunk in candidates:
            validate_vectors([chunk.embedding], 1, len(embedding))
            denominator = math.sqrt(sum(value * value for value in embedding)) * math.sqrt(
                sum(value * value for value in chunk.embedding)
            )
            semantic = sum(
                left * right for left, right in zip(embedding, chunk.embedding, strict=True)
            ) / (denominator or 1)
            tokens = Counter(re.findall(r"\w+", chunk.content.casefold()))
            keyword = sum(min(count, tokens[term]) for term, count in terms.items())
            scores.append((document, chunk, semantic, keyword))
        ranks = {}
        for field in (2, 3):
            ordered = sorted(
                (item for item in scores if field == 2 or item[3] > 0),
                key=lambda item: (-item[field], str(item[1].id)),
            )[: max(20, limit * 4)]
            for rank, item in enumerate(ordered, 1):
                ranks[item[1].id] = ranks.get(item[1].id, 0.0) + 1 / (60 + rank)
        hits = [
            SearchHit(
                document_id=document.id,
                chunk_id=chunk.id,
                title=document.title,
                source=document.source,
                content=chunk.content,
                score=ranks[chunk.id],
                provenance=document.provenance,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
            )
            for document, chunk in candidates
            if chunk.id in ranks
        ]
        return sorted(hits, key=lambda hit: (-hit.score, str(hit.chunk_id)))[:limit]


def validate_collection(
    project_id, collection, entries, embedding_key="deterministic:deterministic-demo:1:16"
):
    identifiers = set()
    for document, chunks in entries:
        if (
            document.project_id != project_id
            or document.collection != collection
            or document.scope != KnowledgeScope.PROJECT
            or document.sharing_authorized
            or document.provenance is None
            or document.id in identifiers
            or document.chunks != len(chunks)
            or document.embedding_key != embedding_key
        ):
            raise ValueError("Coleção de conhecimento inconsistente")
        identifiers.add(document.id)
        for chunk in chunks:
            if (
                chunk.document_id != document.id
                or chunk.project_id != project_id
                or chunk.scope != KnowledgeScope.PROJECT
            ):
                raise ValueError("Fragmento fora do escopo da coleção")


def collection_counts(existing, incoming):
    return {
        "added": len(incoming - existing),
        "removed": len(existing - incoming),
        "unchanged": len(existing & incoming),
    }


class KnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        embeddings: EmbeddingProvider,
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
            embedding_key=self.embeddings.key,
        )
        vectors = self.embeddings.embed_many(parts)
        validate_vectors(vectors, len(parts), self.embeddings.dimensions)
        chunks = [
            KnowledgeChunk(
                document_id=document.id,
                project_id=request.project_id,
                scope=request.scope,
                content=content,
                position=position,
                embedding=vectors[position],
            )
            for position, content in enumerate(parts)
        ]
        self.repository.add(document, chunks)
        return document

    def search(
        self, project_id: str, query: str, limit: int, include_shared: bool
    ) -> list[SearchHit]:
        query_embedding = self.embeddings.embed(query)
        validate_vectors([query_embedding], 1, self.embeddings.dimensions)
        if not 1 <= limit <= 20:
            raise ValueError("Limite de busca deve estar entre 1 e 20")
        if not any(query_embedding):
            return []
        return self.repository.search(
            project_id, query, query_embedding, self.embeddings.key, limit, include_shared
        )
