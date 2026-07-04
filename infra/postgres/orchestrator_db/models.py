from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from shared.contracts import IngestionTaskStatus, QueryRunStatus, TaskKind


class ExportJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportFormat(StrEnum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    JSON = "json"
    JSON_LD = "json-ld"


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
    task_kind: Mapped[str] = mapped_column(
        String(32), nullable=False, default=TaskKind.DOCUMENT_INGESTION.value
    )
    dictionary_version_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
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


class QueryRun(Base):
    __tablename__ = "query_runs"
    __table_args__ = (
        Index("ix_query_runs_user_id", "user_id"),
        Index("ix_query_runs_status", "status"),
        Index("ix_query_runs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=QueryRunStatus.PENDING.value)
    raw_question: Mapped[str] = mapped_column(Text, nullable=False)
    query_ir: Mapped[dict | None] = mapped_column(JSONB)
    evidence_bundle: Mapped[dict | None] = mapped_column(JSONB)
    answer: Mapped[dict | None] = mapped_column(JSONB)
    graph_subgraph: Mapped[dict | None] = mapped_column(JSONB)
    retrieval_trace: Mapped[dict | None] = mapped_column(JSONB)
    warnings: Mapped[list | None] = mapped_column(JSONB)
    answer_payload: Mapped[dict | None] = mapped_column(JSONB)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, default="legacy")
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    dictionary_version_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Role(Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)


class Permission(Base):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_name: Mapped[str] = mapped_column(
        String(64), ForeignKey("roles.name", ondelete="CASCADE"), primary_key=True
    )
    permission_name: Mapped[str] = mapped_column(
        String(128), ForeignKey("permissions.name", ondelete="CASCADE"), primary_key=True
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_user_id", "user_id"),
        Index("ix_audit_events_action", "action"),
        Index("ix_audit_events_created_at", "created_at"),
        Index("ix_audit_events_user_created_id", "user_id", "created_at", "id"),
        Index("ix_audit_events_resource_type", "resource_type"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(128))
    resource_id: Mapped[str | None] = mapped_column(String(256))
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    request_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DocumentDeletionStatus(StrEnum):
    NONE = "none"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewDecisionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class IndexedDocument(Base):
    __tablename__ = "indexed_documents"
    __table_args__ = (
        Index("ix_indexed_documents_task_id", "task_id"),
        Index("ix_indexed_documents_access_level", "access_level"),
        Index("ix_indexed_documents_deletion_status", "deletion_status"),
        Index("ix_indexed_documents_deleted_at", "deleted_at"),
    )

    document_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    task_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_spans_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indexed_points_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    access_level: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    deletion_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DocumentDeletionStatus.NONE.value
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tombstone_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    __table_args__ = (
        Index("ix_review_decisions_status", "status"),
        Index("ix_review_decisions_candidate_type", "candidate_type"),
        Index("ix_review_decisions_document_id", "document_id"),
        Index("ix_review_decisions_source_span_id", "source_span_id"),
        Index("ix_review_decisions_decided_at", "decided_at"),
        Index("ix_review_decisions_reviewer_user_id", "reviewer_user_id"),
        Index("ix_review_decisions_status_decided_at", "status", "decided_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    candidate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ReviewDecisionStatus.PENDING.value
    )
    reviewer_user_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    document_id: Mapped[str | None] = mapped_column(String(128))
    source_span_id: Mapped[str | None] = mapped_column(String(128))
    claim_id: Mapped[str | None] = mapped_column(String(128))
    comment: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ExportJob(Base):
    __tablename__ = "export_jobs"
    __table_args__ = (
        Index("ix_export_jobs_user_id", "user_id"),
        Index("ix_export_jobs_query_run_id", "query_run_id"),
        Index("ix_export_jobs_status", "status"),
        Index("ix_export_jobs_created_at", "created_at"),
        Index("ix_export_jobs_user_status_created", "user_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    query_run_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ExportJobStatus.PENDING.value)
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(1024))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ExportArtifact(Base):
    __tablename__ = "export_artifacts"
    __table_args__ = (
        Index("ix_export_artifacts_export_job_id", "export_job_id"),
        Index("ix_export_artifacts_artifact_kind", "artifact_kind"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    export_job_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("export_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(512))
    file_url: Mapped[str | None] = mapped_column(String(1024))
    content_type: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
