from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
    indexes = index_names()
    if "ix_ingestion_tasks_created_at" in indexes:
        op.drop_index("ix_ingestion_tasks_created_at", table_name="ingestion_tasks")
    if "ix_ingestion_tasks_status" in indexes:
        op.drop_index("ix_ingestion_tasks_status", table_name="ingestion_tasks")
    if "ix_ingestion_tasks_user_id" in indexes:
        op.drop_index("ix_ingestion_tasks_user_id", table_name="ingestion_tasks")
    columns = column_names()
    if "updated_at" in columns:
        op.drop_column("ingestion_tasks", "updated_at")
    if "report" in columns:
        op.drop_column("ingestion_tasks", "report")
    if "user_id" in columns:
        op.drop_column("ingestion_tasks", "user_id")
