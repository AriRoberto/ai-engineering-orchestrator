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
)
from ai_engineering.knowledge.service import collection_counts, validate_collection


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

    def sync_collection(self, project_id, collection, entries):
        validate_collection(project_id, collection, entries)
        incoming = {document.id for document, _chunks in entries}
        with Session(self.engine) as session, session.begin():
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:scope))"),
                {"scope": f"knowledge:{project_id}:{collection}"},
            )
            existing = set(
                session.scalars(
                    select(DocumentRow.id).where(
                        DocumentRow.project_id == project_id, DocumentRow.collection == collection
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
