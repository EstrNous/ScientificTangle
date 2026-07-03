from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.contracts import IngestionTaskStatus


class Base(DeclarativeBase):
    pass


class IngestionTask(Base):
    __tablename__ = "ingestion_tasks"
    __table_args__ = (
        Index("ix_ingestion_tasks_user_id", "user_id"),
        Index("ix_ingestion_tasks_status", "status"),
        Index("ix_ingestion_tasks_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=IngestionTaskStatus.PENDING.value
    )
    report: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
