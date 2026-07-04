from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXPORTS_BUCKET_DEFAULT = "exports"


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    tables = table_names()

    if "export_jobs" in tables:
        job_columns = column_names("export_jobs")
        if "completed_at" not in job_columns:
            op.add_column("export_jobs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        job_indexes = index_names("export_jobs")
        if "ix_export_jobs_user_created_id" not in job_indexes:
            op.create_index(
                "ix_export_jobs_user_created_id",
                "export_jobs",
                ["user_id", "created_at", "id"],
            )

    if "export_artifacts" in tables:
        artifact_columns = column_names("export_artifacts")
        if "bucket_name" not in artifact_columns:
            op.add_column(
                "export_artifacts",
                sa.Column(
                    "bucket_name",
                    sa.String(length=128),
                    nullable=False,
                    server_default=EXPORTS_BUCKET_DEFAULT,
                ),
            )
        if "byte_size" not in artifact_columns:
            op.add_column("export_artifacts", sa.Column("byte_size", sa.BigInteger(), nullable=True))
        if "expires_at" not in artifact_columns:
            op.add_column("export_artifacts", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        if "checksum" not in artifact_columns:
            op.add_column("export_artifacts", sa.Column("checksum", sa.String(length=128), nullable=True))
        artifact_indexes = index_names("export_artifacts")
        if "ix_export_artifacts_expires_at" not in artifact_indexes:
            op.create_index("ix_export_artifacts_expires_at", "export_artifacts", ["expires_at"])
        if "ix_export_artifacts_bucket_storage_key" not in artifact_indexes:
            op.create_index(
                "ix_export_artifacts_bucket_storage_key",
                "export_artifacts",
                ["bucket_name", "storage_key"],
            )

    if "audit_csv_exports" not in tables:
        op.create_table(
            "audit_csv_exports",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column(
                "filter_params",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("bucket_name", sa.String(length=128), nullable=False, server_default=EXPORTS_BUCKET_DEFAULT),
            sa.Column("storage_key", sa.String(length=512), nullable=True),
            sa.Column("row_count", sa.Integer(), nullable=True),
            sa.Column("content_type", sa.String(length=128), nullable=False, server_default="text/csv"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_csv_exports_user_id", "audit_csv_exports", ["user_id"])
        op.create_index("ix_audit_csv_exports_status", "audit_csv_exports", ["status"])
        op.create_index(
            "ix_audit_csv_exports_user_created_id",
            "audit_csv_exports",
            ["user_id", "created_at", "id"],
        )


def downgrade() -> None:
    tables = table_names()

    if "audit_csv_exports" in tables:
        csv_indexes = index_names("audit_csv_exports")
        if "ix_audit_csv_exports_user_created_id" in csv_indexes:
            op.drop_index("ix_audit_csv_exports_user_created_id", table_name="audit_csv_exports")
        if "ix_audit_csv_exports_status" in csv_indexes:
            op.drop_index("ix_audit_csv_exports_status", table_name="audit_csv_exports")
        if "ix_audit_csv_exports_user_id" in csv_indexes:
            op.drop_index("ix_audit_csv_exports_user_id", table_name="audit_csv_exports")
        op.drop_table("audit_csv_exports")

    if "export_artifacts" in tables:
        artifact_indexes = index_names("export_artifacts")
        if "ix_export_artifacts_bucket_storage_key" in artifact_indexes:
            op.drop_index("ix_export_artifacts_bucket_storage_key", table_name="export_artifacts")
        if "ix_export_artifacts_expires_at" in artifact_indexes:
            op.drop_index("ix_export_artifacts_expires_at", table_name="export_artifacts")
        artifact_columns = column_names("export_artifacts")
        if "checksum" in artifact_columns:
            op.drop_column("export_artifacts", "checksum")
        if "expires_at" in artifact_columns:
            op.drop_column("export_artifacts", "expires_at")
        if "byte_size" in artifact_columns:
            op.drop_column("export_artifacts", "byte_size")
        if "bucket_name" in artifact_columns:
            op.drop_column("export_artifacts", "bucket_name")

    if "export_jobs" in tables:
        job_indexes = index_names("export_jobs")
        if "ix_export_jobs_user_created_id" in job_indexes:
            op.drop_index("ix_export_jobs_user_created_id", table_name="export_jobs")
        job_columns = column_names("export_jobs")
        if "completed_at" in job_columns:
            op.drop_column("export_jobs", "completed_at")
