from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def column_names() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("query_runs")
    }


def index_names() -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("query_runs")
    }


def upgrade() -> None:
    if "query_runs" not in table_names():
        return
    columns = column_names()
    if "raw_query" not in columns:
        return
    if "status" not in columns:
        op.add_column(
            "query_runs",
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="pending",
            ),
        )
    if "retrieval_trace" not in columns:
        op.add_column(
            "query_runs",
            sa.Column(
                "retrieval_trace",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )
    op.alter_column(
        "query_runs",
        "raw_query",
        existing_type=sa.Text(),
        nullable=True,
    )
    indexes = index_names()
    if "ix_query_runs_user_id" not in indexes:
        op.create_index("ix_query_runs_user_id", "query_runs", ["user_id"])
    if "ix_query_runs_status" not in indexes:
        op.create_index("ix_query_runs_status", "query_runs", ["status"])
    if "ix_query_runs_created_at" not in indexes:
        op.create_index("ix_query_runs_created_at", "query_runs", ["created_at"])


def downgrade() -> None:
    if "query_runs" not in table_names():
        return
    columns = column_names()
    if "raw_query" not in columns:
        return
    indexes = index_names()
    if "ix_query_runs_created_at" in indexes:
        op.drop_index("ix_query_runs_created_at", table_name="query_runs")
    if "ix_query_runs_status" in indexes:
        op.drop_index("ix_query_runs_status", table_name="query_runs")
    if "ix_query_runs_user_id" in indexes:
        op.drop_index("ix_query_runs_user_id", table_name="query_runs")
    if "retrieval_trace" in columns:
        op.drop_column("query_runs", "retrieval_trace")
    if "status" in columns:
        op.drop_column("query_runs", "status")
    op.alter_column(
        "query_runs",
        "raw_query",
        existing_type=sa.Text(),
        nullable=False,
    )
