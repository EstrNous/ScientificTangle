from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    tables = table_names()
    if "query_runs" in tables:
        columns = column_names("query_runs")
        if "raw_query" not in columns:
            op.add_column("query_runs", sa.Column("raw_query", sa.Text(), nullable=True))
        if "answer_payload" not in columns:
            op.add_column("query_runs", sa.Column("answer_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        if "error_message" not in columns:
            op.add_column("query_runs", sa.Column("error_message", sa.Text(), nullable=True))
        if "updated_at" not in columns:
            op.add_column(
                "query_runs",
                sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            )

    if "roles" not in tables:
        op.create_table(
            "roles",
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("name"),
        )
    if "permissions" not in tables:
        op.create_table(
            "permissions",
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("name"),
        )
    if "role_permissions" not in tables:
        op.create_table(
            "role_permissions",
            sa.Column("role_name", sa.String(length=64), nullable=False),
            sa.Column("permission_name", sa.String(length=128), nullable=False),
            sa.ForeignKeyConstraint(["role_name"], ["roles.name"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["permission_name"], ["permissions.name"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("role_name", "permission_name"),
        )
    if "audit_events" not in tables:
        op.create_table(
            "audit_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("resource_type", sa.String(length=128), nullable=True),
            sa.Column("resource_id", sa.String(length=256), nullable=True),
            sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("request_id", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
        op.create_index("ix_audit_events_action", "audit_events", ["action"])
        op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    if "indexed_documents" not in tables:
        op.create_table(
            "indexed_documents",
            sa.Column("document_id", sa.String(length=128), nullable=False),
            sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("title", sa.String(length=512), nullable=False),
            sa.Column("source_type", sa.String(length=64), nullable=False),
            sa.Column("source_spans_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("indexed_points_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("access_level", sa.String(length=32), nullable=False),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("document_id"),
        )
        op.create_index("ix_indexed_documents_task_id", "indexed_documents", ["task_id"])
        op.create_index("ix_indexed_documents_access_level", "indexed_documents", ["access_level"])


def downgrade() -> None:
    tables = table_names()
    if "indexed_documents" in tables:
        op.drop_index("ix_indexed_documents_access_level", table_name="indexed_documents")
        op.drop_index("ix_indexed_documents_task_id", table_name="indexed_documents")
        op.drop_table("indexed_documents")
    if "audit_events" in tables:
        op.drop_index("ix_audit_events_created_at", table_name="audit_events")
        op.drop_index("ix_audit_events_action", table_name="audit_events")
        op.drop_index("ix_audit_events_user_id", table_name="audit_events")
        op.drop_table("audit_events")
    if "role_permissions" in tables:
        op.drop_table("role_permissions")
    if "permissions" in tables:
        op.drop_table("permissions")
    if "roles" in tables:
        op.drop_table("roles")
    if "query_runs" in tables:
        columns = column_names("query_runs")
        if "updated_at" in columns:
            op.drop_column("query_runs", "updated_at")
        if "error_message" in columns:
            op.drop_column("query_runs", "error_message")
        if "answer_payload" in columns:
            op.drop_column("query_runs", "answer_payload")
        if "raw_query" in columns:
            op.drop_column("query_runs", "raw_query")
