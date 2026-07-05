from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_names() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("query_runs")}


def upgrade() -> None:
    columns = column_names()
    additions = {
        "raw_question": sa.Column("raw_question", sa.Text(), nullable=True),
        "evidence_bundle": sa.Column("evidence_bundle", postgresql.JSONB(), nullable=True),
        "answer": sa.Column("answer", postgresql.JSONB(), nullable=True),
        "graph_subgraph": sa.Column("graph_subgraph", postgresql.JSONB(), nullable=True),
        "warnings": sa.Column("warnings", postgresql.JSONB(), nullable=True),
        "error_code": sa.Column("error_code", sa.String(length=128), nullable=True),
        "request_id": sa.Column("request_id", sa.String(length=128), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("query_runs", column)
    refreshed_columns = column_names()
    if "raw_query" in refreshed_columns:
        op.execute("UPDATE query_runs SET raw_question = COALESCE(raw_question, raw_query, '')")
    else:
        op.execute("UPDATE query_runs SET raw_question = COALESCE(raw_question, '')")
    op.execute("UPDATE query_runs SET request_id = COALESCE(request_id, 'legacy')")
    refreshed = column_names()
    if "raw_question" in refreshed:
        op.alter_column("query_runs", "raw_question", nullable=False)
    if "request_id" in refreshed:
        op.alter_column("query_runs", "request_id", nullable=False)


def downgrade() -> None:
    columns = column_names()
    for name in (
        "request_id",
        "error_code",
        "warnings",
        "graph_subgraph",
        "answer",
        "evidence_bundle",
        "raw_question",
    ):
        if name in columns:
            op.drop_column("query_runs", name)
