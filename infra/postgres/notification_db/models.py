from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserInterest(Base):
    __tablename__ = "user_interests"
    __table_args__ = (
        Index("ix_user_interests_user_id", "user_id", unique=True),
        Index("ix_user_interests_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_entities: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_is_read", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_created_id", "user_id", "created_at", "id"),
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_type", "type"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(256))
    reference_type: Mapped[str | None] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"
    __table_args__ = (
        Index("ix_extracted_entities_user_interest_id", "user_interest_id"),
        Index("ix_extracted_entities_user_id", "user_id"),
        Index("ix_extracted_entities_entity_type", "entity_type"),
        Index("ix_extracted_entities_document_id", "document_id"),
        Index("ix_extracted_entities_source_span_id", "source_span_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_interest_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("user_interests.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    entity_label: Mapped[str] = mapped_column(String(256), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    document_id: Mapped[str | None] = mapped_column(String(128))
    source_span_id: Mapped[str | None] = mapped_column(String(128))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NotificationMatchResult(Base):
    __tablename__ = "notification_match_results"
    __table_args__ = (
        Index("ix_notification_match_results_user_id", "user_id"),
        Index("ix_notification_match_results_created_at", "created_at"),
        Index("ix_notification_match_results_notification_id", "notification_id"),
        Index("ix_notification_match_results_user_created_id", "user_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    notification_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="SET NULL"),
    )
    reference_id: Mapped[str | None] = mapped_column(String(256))
    reference_type: Mapped[str | None] = mapped_column(String(64))
    match_score: Mapped[float | None] = mapped_column(Float)
    match_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
