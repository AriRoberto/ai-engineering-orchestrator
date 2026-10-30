from datetime import UTC, datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    delete,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ai_engineering.knowledge.models import (
    FeedbackCreate,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeProvenance,
    KnowledgeScope,
    KnowledgeStatus,
    RAGEvaluationResult,
    RAGFeedback,
    RAGRelevance,
    SearchHit,
)
from ai_engineering.knowledge.service import (
    build_knowledge_status,
    collection_counts,
    validate_collection,
)


class Base(DeclarativeBase):
    pass


class DocumentRow(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(63), index=True)
    title: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(2_000))
    scope: Mapped[str] = mapped_column(String(32), index=True)
    sharing_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    collection: Mapped[str | None] = mapped_column(String(63), nullable=True)
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    embedding_key: Mapped[str] = mapped_column(
        String(200), default="deterministic:deterministic-demo:1:16"
    )


class ChunkRow(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[str] = mapped_column(String(63), index=True)
    scope: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(Vector())
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)


class FeedbackRow(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(63), index=True)
    execution_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class RAGEvaluationRow(Base):
    __tablename__ = "rag_evaluation_runs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(63), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RAGFeedbackRow(Base):
    __tablename__ = "rag_retrieval_feedback"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(63), index=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("rag_evaluation_runs.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    relevance: Mapped[str] = mapped_column(String(20))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PostgresKnowledgeRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)

    def add(self, document: KnowledgeDocument, chunks: list[KnowledgeChunk]) -> None:
        with Session(self.engine) as session, session.begin():
            self._add(session, document, chunks)

    @staticmethod
    def _add(session, document, chunks):
        document_row = DocumentRow(
            id=document.id,
            project_id=document.project_id,
            title=document.title,
            source=document.source,
            scope=document.scope.value,
            sharing_authorized=document.sharing_authorized,
            chunk_count=document.chunks,
            created_at=document.created_at,
            collection=document.collection,
            provenance=document.provenance.model_dump() if document.provenance else None,
            embedding_key=document.embedding_key,
        )
        session.add(document_row)
        session.flush()
        session.add_all(
            ChunkRow(
                id=chunk.id,
                document_id=chunk.document_id,
                project_id=chunk.project_id,
                scope=chunk.scope.value,
                content=chunk.content,
                position=chunk.position,
                embedding=chunk.embedding,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
            )
            for chunk in chunks
        )

    def sync_collection(
        self,
        project_id,
        collection,
        entries,
        embedding_key="deterministic:deterministic-demo:1:16",
    ):
        validate_collection(project_id, collection, entries, embedding_key)
        incoming = {document.id for document, _chunks in entries}
        with Session(self.engine) as session, session.begin():
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:scope))"),
                {"scope": f"knowledge:{project_id}:{collection}"},
            )
            existing = set(
                session.scalars(
                    select(DocumentRow.id).where(
                        DocumentRow.project_id == project_id,
                        DocumentRow.collection == collection,
                        DocumentRow.embedding_key == embedding_key,
                    )
                )
            )
            removed = existing - incoming
            if removed:
                session.execute(delete(DocumentRow).where(DocumentRow.id.in_(removed)))
            for document, chunks in entries:
                if document.id not in existing:
                    self._add(session, document, chunks)
                else:
                    session.execute(
                        update(DocumentRow)
                        .where(DocumentRow.id == document.id)
                        .values(provenance=document.provenance.model_dump())
                    )
        return collection_counts(existing, incoming)

    def get_document(self, document_id: UUID, project_id: str):
        with Session(self.engine) as session:
            row = session.scalar(
                select(DocumentRow).where(
                    DocumentRow.id == document_id, DocumentRow.project_id == project_id
                )
            )
            return self._document(row) if row else None

    def delete(self, document_id: UUID, project_id: str) -> bool:
        with Session(self.engine) as session, session.begin():
            result = session.execute(
                delete(DocumentRow).where(
                    DocumentRow.id == document_id, DocumentRow.project_id == project_id
                )
            )
            return bool(result.rowcount)

    def chunks_for(self, project_id: str, include_shared: bool):
        with Session(self.engine) as session:
            condition = ChunkRow.project_id == project_id
            if include_shared:
                condition = or_(
                    condition,
                    (DocumentRow.scope == KnowledgeScope.SHARED.value)
                    & DocumentRow.sharing_authorized,
                )
            rows = session.execute(
                select(DocumentRow, ChunkRow)
                .join(ChunkRow, ChunkRow.document_id == DocumentRow.id)
                .where(condition)
            ).all()
            return [(self._document(document), self._chunk(chunk)) for document, chunk in rows]

    def add_feedback(self, feedback: FeedbackCreate) -> None:
        with Session(self.engine) as session, session.begin():
            session.add(FeedbackRow(**feedback.model_dump()))

    def status(self, project_id: str) -> KnowledgeStatus:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(DocumentRow).where(DocumentRow.project_id == project_id)
            ).all()
        return build_knowledge_status(
            project_id, [self._document(row) for row in rows]
        )

    def save_evaluation(self, result: RAGEvaluationResult) -> None:
        with Session(self.engine) as session, session.begin():
            session.add(
                RAGEvaluationRow(
                    id=result.id,
                    project_id=result.project_id,
                    payload=result.model_dump(mode="json"),
                    created_at=result.created_at,
                )
            )

    def get_evaluation(self, evaluation_id: UUID, project_id: str):
        with Session(self.engine) as session:
            row = session.scalar(
                select(RAGEvaluationRow).where(
                    RAGEvaluationRow.id == evaluation_id,
                    RAGEvaluationRow.project_id == project_id,
                )
            )
        return RAGEvaluationResult.model_validate(row.payload) if row else None

    def list_evaluations(self, project_id: str):
        with Session(self.engine) as session:
            rows = session.scalars(
                select(RAGEvaluationRow)
                .where(RAGEvaluationRow.project_id == project_id)
                .order_by(RAGEvaluationRow.created_at.desc())
            ).all()
        return [RAGEvaluationResult.model_validate(row.payload) for row in rows]

    def save_retrieval_feedback(self, feedback: RAGFeedback) -> None:
        with Session(self.engine) as session, session.begin():
            session.execute(
                delete(RAGFeedbackRow).where(
                    RAGFeedbackRow.evaluation_id == feedback.evaluation_id,
                    RAGFeedbackRow.chunk_id == feedback.chunk_id,
                )
            )
            session.add(
                RAGFeedbackRow(
                    id=feedback.id,
                    project_id=feedback.project_id,
                    evaluation_id=feedback.evaluation_id,
                    chunk_id=feedback.chunk_id,
                    relevance=feedback.relevance.value,
                    comment=feedback.comment,
                    created_at=feedback.created_at,
                )
            )

    def list_retrieval_feedback(self, project_id: str):
        with Session(self.engine) as session:
            rows = session.scalars(
                select(RAGFeedbackRow).where(RAGFeedbackRow.project_id == project_id)
            ).all()
        return [
            RAGFeedback(
                id=row.id,
                project_id=row.project_id,
                evaluation_id=row.evaluation_id,
                chunk_id=row.chunk_id,
                relevance=RAGRelevance(row.relevance),
                comment=row.comment,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def search(self, project_id, query, embedding, embedding_key, limit, include_shared):
        statement = text("""
            WITH eligible AS MATERIALIZED (
                SELECT chunks.* FROM knowledge_chunks chunks
                JOIN knowledge_documents documents ON documents.id = chunks.document_id
                WHERE documents.embedding_key = :embedding_key
                  AND vector_dims(chunks.embedding) = :dimensions
                  AND (documents.project_id = :project_id OR
                       (:include_shared AND documents.scope = 'shared'
                        AND documents.sharing_authorized))
            ), vector_candidates AS (
                SELECT id, embedding <=> CAST(:embedding AS vector) AS distance
                FROM eligible
                WHERE vector_norm(embedding) > 0
                ORDER BY distance, id LIMIT :candidates
            ), lexical_candidates AS (
                SELECT chunks.id, GREATEST(
                    ts_rank_cd(to_tsvector('portuguese', chunks.content),
                               plainto_tsquery('portuguese', :query)),
                    ts_rank_cd(to_tsvector('simple', chunks.content),
                               plainto_tsquery('simple', :query))
                ) AS relevance
                FROM knowledge_chunks chunks
                JOIN eligible ON eligible.id = chunks.id
                WHERE to_tsvector('portuguese', chunks.content) @@
                        plainto_tsquery('portuguese', :query)
                   OR to_tsvector('simple', chunks.content) @@
                        plainto_tsquery('simple', :query)
                ORDER BY relevance DESC, chunks.id LIMIT :candidates
            ), ranked AS (
                SELECT id, 1.0 / (60 + row_number() OVER (ORDER BY distance, id)) AS score
                FROM vector_candidates
                UNION ALL
                SELECT id, 1.0 / (60 + row_number() OVER (ORDER BY relevance DESC, id)) AS score
                FROM lexical_candidates
            ), fused AS (
                SELECT id, SUM(score) AS score FROM ranked GROUP BY id
                ORDER BY score DESC, id LIMIT :limit
            )
            SELECT documents.id AS document_id, chunks.id AS chunk_id,
                   documents.title, documents.source, chunks.content, fused.score,
                   documents.provenance, chunks.start_line, chunks.end_line
            FROM fused JOIN knowledge_chunks chunks ON chunks.id = fused.id
            JOIN knowledge_documents documents ON documents.id = chunks.document_id
            ORDER BY fused.score DESC, chunks.id
        """)
        with Session(self.engine) as session:
            rows = (
                session.execute(
                    statement,
                    {
                        "project_id": project_id,
                        "query": query,
                        "embedding": "[" + ",".join(str(value) for value in embedding) + "]",
                        "embedding_key": embedding_key,
                        "dimensions": len(embedding),
                        "include_shared": include_shared,
                        "limit": limit,
                        "candidates": max(20, limit * 4),
                    },
                )
                .mappings()
                .all()
            )
        return [SearchHit(**row) for row in rows]

    @staticmethod
    def _document(row: DocumentRow) -> KnowledgeDocument:
        return KnowledgeDocument(
            id=row.id,
            project_id=row.project_id,
            title=row.title,
            source=row.source,
            scope=KnowledgeScope(row.scope),
            sharing_authorized=row.sharing_authorized,
            chunks=row.chunk_count,
            created_at=row.created_at,
            collection=row.collection,
            provenance=KnowledgeProvenance(**row.provenance) if row.provenance else None,
            embedding_key=row.embedding_key,
        )

    @staticmethod
    def _chunk(row: ChunkRow) -> KnowledgeChunk:
        return KnowledgeChunk(
            id=row.id,
            document_id=row.document_id,
            project_id=row.project_id,
            scope=KnowledgeScope(row.scope),
            content=row.content,
            position=row.position,
            embedding=list(row.embedding),
            start_line=row.start_line,
            end_line=row.end_line,
        )
