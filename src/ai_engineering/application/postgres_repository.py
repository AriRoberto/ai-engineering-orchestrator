from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, Uuid, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ai_engineering.domain.models import Execution


class ExecutionBase(DeclarativeBase):
    pass


class ExecutionRow(ExecutionBase):
    __tablename__ = "executions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[str] = mapped_column(String(63), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PostgresExecutionRepository:
    """Durable execution storage; the JSON payload preserves the complete audit timeline."""

    def __init__(self, database_url: str, *, create_schema: bool = True) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        if create_schema:
            # Keeps existing Compose volumes upgradeable while SQL migrations remain authoritative.
            ExecutionBase.metadata.create_all(self.engine)

    def save(self, execution: Execution) -> None:
        payload = execution.model_dump(mode="json")
        with Session(self.engine) as session, session.begin():
            session.merge(
                ExecutionRow(
                    id=execution.id,
                    project_id=execution.request.project_id,
                    status=execution.status.value,
                    payload=payload,
                    created_at=execution.created_at,
                    updated_at=execution.updated_at,
                )
            )

    def get(self, execution_id: UUID, project_id: str) -> Execution | None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(ExecutionRow).where(
                    ExecutionRow.id == execution_id,
                    ExecutionRow.project_id == project_id,
                )
            )
            return Execution.model_validate(row.payload) if row else None

    def list(self, project_id: str) -> list[Execution]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ExecutionRow)
                .where(ExecutionRow.project_id == project_id)
                .order_by(ExecutionRow.created_at.desc())
            ).all()
            return [Execution.model_validate(row.payload) for row in rows]
