from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String, Uuid, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class EvidenceAccessStatus(StrEnum):
    COMPLETED = "COMPLETED"
    DENIED = "DENIED"
    FAILED = "FAILED"


class EvidenceAccessAudit(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: str
    status: EvidenceAccessStatus
    visibility: str = "unknown"
    authenticated: bool = False
    include_content: bool = False
    revision: str | None = None
    execution_id: UUID | None = None
    reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceAuditRepository:
    def __init__(self) -> None:
        self._items: list[EvidenceAccessAudit] = []
        self._lock = RLock()

    def add(self, audit: EvidenceAccessAudit) -> None:
        with self._lock:
            self._items.append(audit.model_copy(deep=True))

    def list(self, project_id: str) -> list[EvidenceAccessAudit]:
        with self._lock:
            return [
                item.model_copy(deep=True)
                for item in reversed(self._items)
                if item.project_id == project_id
            ]


class EvidenceAuditBase(DeclarativeBase):
    pass


class EvidenceAccessAuditRow(EvidenceAuditBase):
    __tablename__ = "evidence_access_audits"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[str] = mapped_column(String(63), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PostgresEvidenceAuditRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        EvidenceAuditBase.metadata.create_all(self.engine)

    def add(self, audit: EvidenceAccessAudit) -> None:
        with Session(self.engine) as session, session.begin():
            session.add(
                EvidenceAccessAuditRow(
                    id=audit.id,
                    project_id=audit.project_id,
                    status=audit.status.value,
                    payload=audit.model_dump(mode="json"),
                    created_at=audit.created_at,
                )
            )

    def list(self, project_id: str) -> list[EvidenceAccessAudit]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(EvidenceAccessAuditRow)
                .where(EvidenceAccessAuditRow.project_id == project_id)
                .order_by(EvidenceAccessAuditRow.created_at.desc())
            ).all()
            return [EvidenceAccessAudit.model_validate(row.payload) for row in rows]
