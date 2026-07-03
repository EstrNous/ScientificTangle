from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = table_names()
    if "query_runs" not in tables:
        op.create_table(
            "query_runs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("query_ir", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("retrieval_trace", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_query_runs_user_id", "query_runs", ["user_id"])
        op.create_index("ix_query_runs_status", "query_runs", ["status"])
        op.create_index("ix_query_runs_created_at", "query_runs", ["created_at"])

    if "export_jobs" not in tables:
        op.create_table(
            "export_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("format", sa.String(length=32), nullable=False),
            sa.Column("file_url", sa.String(length=1024), nullable=True),
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
        )
        op.create_index("ix_export_jobs_user_id", "export_jobs", ["user_id"])
        op.create_index("ix_export_jobs_status", "export_jobs", ["status"])
        op.create_index("ix_export_jobs_created_at", "export_jobs", ["created_at"])


def downgrade() -> None:
    tables = table_names()
    if "export_jobs" in tables:
        op.drop_index("ix_export_jobs_created_at", table_name="export_jobs")
        op.drop_index("ix_export_jobs_status", table_name="export_jobs")
        op.drop_index("ix_export_jobs_user_id", table_name="export_jobs")
        op.drop_table("export_jobs")
    if "query_runs" in tables:
        op.drop_index("ix_query_runs_created_at", table_name="query_runs")
        op.drop_index("ix_query_runs_status", table_name="query_runs")
        op.drop_index("ix_query_runs_user_id", table_name="query_runs")
        op.drop_table("query_runs")
