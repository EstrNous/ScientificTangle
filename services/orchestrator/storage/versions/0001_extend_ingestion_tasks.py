from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def column_names() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("ingestion_tasks")
    }


def index_names() -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("ingestion_tasks")
    }


def upgrade() -> None:
    if "ingestion_tasks" not in table_names():
        op.create_table(
            "ingestion_tasks",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
            sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
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
    columns = column_names()
    if "user_id" not in columns:
        op.add_column(
            "ingestion_tasks",
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                server_default="00000000-0000-0000-0000-000000000000",
            ),
        )
        op.alter_column("ingestion_tasks", "user_id", server_default=None)
    if "report" not in columns:
        op.add_column(
            "ingestion_tasks",
            sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
    if "updated_at" not in columns:
        op.add_column(
            "ingestion_tasks",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    indexes = index_names()
    if "ix_ingestion_tasks_user_id" not in indexes:
        op.create_index("ix_ingestion_tasks_user_id", "ingestion_tasks", ["user_id"])
    if "ix_ingestion_tasks_status" not in indexes:
        op.create_index("ix_ingestion_tasks_status", "ingestion_tasks", ["status"])
    if "ix_ingestion_tasks_created_at" not in indexes:
        op.create_index("ix_ingestion_tasks_created_at", "ingestion_tasks", ["created_at"])


def downgrade() -> None:
    if "ingestion_tasks" in table_names():
        op.drop_table("ingestion_tasks")
