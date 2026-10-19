from datetime import UTC, datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
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
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ai_engineering.knowledge.models import (
    FeedbackCreate,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeScope,
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
    embedding: Mapped[list[float]] = mapped_column(Vector(16))


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


class PostgresKnowledgeRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)

    def add(self, document: KnowledgeDocument, chunks: list[KnowledgeChunk]) -> None:
        with Session(self.engine) as session, session.begin():
            document_row = DocumentRow(
                id=document.id,
                project_id=document.project_id,
                title=document.title,
                source=document.source,
                scope=document.scope.value,
                sharing_authorized=document.sharing_authorized,
                chunk_count=document.chunks,
                created_at=document.created_at,
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
                )
                for chunk in chunks
            )

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
        )
