from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
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
    if "query_runs" in tables:
        query_columns = column_names("query_runs")
        if "raw_question" not in query_columns:
            op.add_column("query_runs", sa.Column("raw_question", sa.Text(), nullable=True))
        if "answer" not in query_columns:
            op.add_column(
                "query_runs",
                sa.Column("answer", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )
        if "evidence_bundle" not in query_columns:
            op.add_column(
                "query_runs",
                sa.Column("evidence_bundle", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )
        if "graph_subgraph" not in query_columns:
            op.add_column(
                "query_runs",
                sa.Column("graph_subgraph", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )
        if "warnings" not in query_columns:
            op.add_column(
                "query_runs",
                sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )
        if "error_code" not in query_columns:
            op.add_column("query_runs", sa.Column("error_code", sa.String(length=128), nullable=True))
        if "error_message" not in query_columns:
            op.add_column("query_runs", sa.Column("error_message", sa.Text(), nullable=True))
        if "request_id" not in query_columns:
            op.add_column("query_runs", sa.Column("request_id", sa.String(length=128), nullable=True))
        if "updated_at" not in query_columns:
            op.add_column(
                "query_runs",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
            )
        refreshed_columns = column_names("query_runs")
        if "raw_query" in refreshed_columns:
            op.execute(
                "UPDATE query_runs SET raw_question = COALESCE(raw_question, raw_query, '')"
            )
        else:
            op.execute("UPDATE query_runs SET raw_question = COALESCE(raw_question, '')")
        if "answer_payload" in refreshed_columns:
            op.execute("UPDATE query_runs SET answer = COALESCE(answer, answer_payload)")
        op.execute("UPDATE query_runs SET request_id = COALESCE(request_id, 'legacy')")
        op.alter_column("query_runs", "raw_question", nullable=False)
        op.alter_column("query_runs", "request_id", nullable=False)

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
            sa.Column(
                "details",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("request_id", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    audit_indexes = index_names("audit_events") if "audit_events" in table_names() else set()
    if "ix_audit_events_user_id" not in audit_indexes:
        op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    if "ix_audit_events_action" not in audit_indexes:
        op.create_index("ix_audit_events_action", "audit_events", ["action"])
    if "ix_audit_events_created_at" not in audit_indexes:
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
            sa.Column(
                "metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("document_id"),
        )
    indexed_document_indexes = index_names("indexed_documents") if "indexed_documents" in table_names() else set()
    if "ix_indexed_documents_task_id" not in indexed_document_indexes:
        op.create_index("ix_indexed_documents_task_id", "indexed_documents", ["task_id"])
    if "ix_indexed_documents_access_level" not in indexed_document_indexes:
        op.create_index("ix_indexed_documents_access_level", "indexed_documents", ["access_level"])

    if "export_jobs" in tables:
        export_columns = column_names("export_jobs")
        if "query_run_id" not in export_columns:
            op.add_column("export_jobs", sa.Column("query_run_id", postgresql.UUID(as_uuid=True), nullable=True))
        if "payload" not in export_columns:
            op.add_column(
                "export_jobs",
                sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )
        if "error_message" not in export_columns:
            op.add_column("export_jobs", sa.Column("error_message", sa.Text(), nullable=True))
        export_indexes = index_names("export_jobs")
        if "ix_export_jobs_query_run_id" not in export_indexes:
            op.create_index("ix_export_jobs_query_run_id", "export_jobs", ["query_run_id"])


def downgrade() -> None:
    pass
