from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    tables = table_names()

    if "review_decisions" not in tables:
        op.create_table(
            "review_decisions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("candidate_id", sa.String(length=128), nullable=False),
            sa.Column("candidate_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("document_id", sa.String(length=128), nullable=True),
            sa.Column("source_span_id", sa.String(length=128), nullable=True),
            sa.Column("claim_id", sa.String(length=128), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("candidate_id", "candidate_type", name="uq_review_decisions_candidate"),
        )
        op.create_index("ix_review_decisions_status", "review_decisions", ["status"])
        op.create_index("ix_review_decisions_candidate_type", "review_decisions", ["candidate_type"])
        op.create_index("ix_review_decisions_document_id", "review_decisions", ["document_id"])
        op.create_index("ix_review_decisions_source_span_id", "review_decisions", ["source_span_id"])
        op.create_index("ix_review_decisions_decided_at", "review_decisions", ["decided_at"])
        op.create_index("ix_review_decisions_reviewer_user_id", "review_decisions", ["reviewer_user_id"])
        op.create_index(
            "ix_review_decisions_status_decided_at",
            "review_decisions",
            ["status", "decided_at"],
        )

    if "indexed_documents" in tables:
        indexed_columns = column_names("indexed_documents")
        if "deletion_status" not in indexed_columns:
            op.add_column(
                "indexed_documents",
                sa.Column(
                    "deletion_status",
                    sa.String(length=32),
                    nullable=False,
                    server_default="none",
                ),
            )
        if "deleted_at" not in indexed_columns:
            op.add_column(
                "indexed_documents",
                sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            )
        if "tombstone_reason" not in indexed_columns:
            op.add_column("indexed_documents", sa.Column("tombstone_reason", sa.Text(), nullable=True))
        if "updated_at" not in indexed_columns:
            op.add_column(
                "indexed_documents",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
            )
        indexed_indexes = index_names("indexed_documents")
        if "ix_indexed_documents_deletion_status" not in indexed_indexes:
            op.create_index(
                "ix_indexed_documents_deletion_status",
                "indexed_documents",
                ["deletion_status"],
            )
        if "ix_indexed_documents_deleted_at" not in indexed_indexes:
            op.create_index("ix_indexed_documents_deleted_at", "indexed_documents", ["deleted_at"])

    if "audit_events" in tables:
        audit_indexes = index_names("audit_events")
        if "ix_audit_events_user_created_id" not in audit_indexes:
            op.create_index(
                "ix_audit_events_user_created_id",
                "audit_events",
                ["user_id", "created_at", "id"],
            )
        if "ix_audit_events_resource_type" not in audit_indexes:
            op.create_index("ix_audit_events_resource_type", "audit_events", ["resource_type"])

    if "export_jobs" in tables:
        export_indexes = index_names("export_jobs")
        if "ix_export_jobs_user_status_created" not in export_indexes:
            op.create_index(
                "ix_export_jobs_user_status_created",
                "export_jobs",
                ["user_id", "status", "created_at"],
            )

    if "export_artifacts" not in tables:
        op.create_table(
            "export_artifacts",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("export_job_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("artifact_kind", sa.String(length=32), nullable=False),
            sa.Column("storage_key", sa.String(length=512), nullable=True),
            sa.Column("file_url", sa.String(length=1024), nullable=True),
            sa.Column("content_type", sa.String(length=128), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["export_job_id"], ["export_jobs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_export_artifacts_export_job_id", "export_artifacts", ["export_job_id"])
        op.create_index("ix_export_artifacts_artifact_kind", "export_artifacts", ["artifact_kind"])


def downgrade() -> None:
    tables = table_names()
    if "export_artifacts" in tables:
        op.drop_index("ix_export_artifacts_artifact_kind", table_name="export_artifacts")
        op.drop_index("ix_export_artifacts_export_job_id", table_name="export_artifacts")
        op.drop_table("export_artifacts")
    if "export_jobs" in tables:
        export_indexes = index_names("export_jobs")
        if "ix_export_jobs_user_status_created" in export_indexes:
            op.drop_index("ix_export_jobs_user_status_created", table_name="export_jobs")
    if "audit_events" in tables:
        audit_indexes = index_names("audit_events")
        if "ix_audit_events_resource_type" in audit_indexes:
            op.drop_index("ix_audit_events_resource_type", table_name="audit_events")
        if "ix_audit_events_user_created_id" in audit_indexes:
            op.drop_index("ix_audit_events_user_created_id", table_name="audit_events")
    if "indexed_documents" in tables:
        indexed_indexes = index_names("indexed_documents")
        if "ix_indexed_documents_deleted_at" in indexed_indexes:
            op.drop_index("ix_indexed_documents_deleted_at", table_name="indexed_documents")
        if "ix_indexed_documents_deletion_status" in indexed_indexes:
            op.drop_index("ix_indexed_documents_deletion_status", table_name="indexed_documents")
        indexed_columns = column_names("indexed_documents")
        if "updated_at" in indexed_columns:
            op.drop_column("indexed_documents", "updated_at")
        if "tombstone_reason" in indexed_columns:
            op.drop_column("indexed_documents", "tombstone_reason")
        if "deleted_at" in indexed_columns:
            op.drop_column("indexed_documents", "deleted_at")
        if "deletion_status" in indexed_columns:
            op.drop_column("indexed_documents", "deletion_status")
    if "review_decisions" in tables:
        op.drop_index("ix_review_decisions_status_decided_at", table_name="review_decisions")
        op.drop_index("ix_review_decisions_reviewer_user_id", table_name="review_decisions")
        op.drop_index("ix_review_decisions_decided_at", table_name="review_decisions")
        op.drop_index("ix_review_decisions_source_span_id", table_name="review_decisions")
        op.drop_index("ix_review_decisions_document_id", table_name="review_decisions")
        op.drop_index("ix_review_decisions_candidate_type", table_name="review_decisions")
        op.drop_index("ix_review_decisions_status", table_name="review_decisions")
        op.drop_table("review_decisions")
