from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    ingestion_columns = column_names("ingestion_tasks")
    if "task_kind" not in ingestion_columns:
        op.add_column(
            "ingestion_tasks",
            sa.Column("task_kind", sa.String(length=32), server_default="document_ingestion", nullable=False),
        )
    if "dictionary_version_id" not in ingestion_columns:
        op.add_column(
            "ingestion_tasks",
            sa.Column("dictionary_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
    query_columns = column_names("query_runs")
    if "dictionary_version_id" not in query_columns:
        op.add_column(
            "query_runs",
            sa.Column("dictionary_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("query_runs", "dictionary_version_id")
    op.drop_column("ingestion_tasks", "dictionary_version_id")
    op.drop_column("ingestion_tasks", "task_kind")
