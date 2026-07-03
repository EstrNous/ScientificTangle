import uuid
from datetime import datetime
from sqlalchemy import String, Index, Uuid, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from services.auth_audit.src.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    object_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    object_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        Index("ix_audit_events_user_id", "user_id"),
        Index("ix_audit_events_request_id", "request_id"),
        Index("ix_audit_events_status", "status"),
        Index("ix_audit_events_timestamp", "timestamp"),
        Index("ix_audit_events_action", "action"),
    )