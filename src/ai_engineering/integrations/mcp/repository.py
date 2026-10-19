from datetime import datetime
from threading import RLock
from uuid import UUID

from sqlalchemy import JSON, DateTime, String, Uuid, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ai_engineering.integrations.mcp.models import MCPInvocation


class MCPAuditRepository:
    def __init__(self) -> None:
        self._items: list[MCPInvocation] = []
        self._lock = RLock()

    def add(self, invocation: MCPInvocation) -> None:
        with self._lock:
            self._items.append(invocation.model_copy(deep=True))

    def list(self, project_id: str) -> list[MCPInvocation]:
        with self._lock:
            return [
                item.model_copy(deep=True)
                for item in self._items
                if item.project_id == project_id
            ]


class MCPAuditBase(DeclarativeBase):
    pass


class MCPInvocationRow(MCPAuditBase):
    __tablename__ = "mcp_invocations"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[str] = mapped_column(String(63), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class PostgresMCPAuditRepository:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        MCPAuditBase.metadata.create_all(self.engine)

    def add(self, invocation: MCPInvocation) -> None:
        with Session(self.engine) as session, session.begin():
            session.add(
                MCPInvocationRow(
                    id=invocation.id,
                    project_id=invocation.project_id,
                    status=invocation.status.value,
                    payload=invocation.model_dump(mode="json"),
                    created_at=invocation.created_at,
                )
            )

    def list(self, project_id: str) -> list[MCPInvocation]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(MCPInvocationRow)
                .where(MCPInvocationRow.project_id == project_id)
                .order_by(MCPInvocationRow.created_at.desc())
            ).all()
            return [MCPInvocation.model_validate(row.payload) for row in rows]
