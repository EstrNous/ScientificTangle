from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_runs", sa.Column("raw_question", sa.Text(), nullable=True))
    op.add_column("query_runs", sa.Column("evidence_bundle", postgresql.JSONB(), nullable=True))
    op.add_column("query_runs", sa.Column("answer", postgresql.JSONB(), nullable=True))
    op.add_column("query_runs", sa.Column("graph_subgraph", postgresql.JSONB(), nullable=True))
    op.add_column("query_runs", sa.Column("warnings", postgresql.JSONB(), nullable=True))
    op.add_column("query_runs", sa.Column("error_code", sa.String(length=128), nullable=True))
    op.add_column("query_runs", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("query_runs", sa.Column("request_id", sa.String(length=128), nullable=True))
    op.add_column(
        "query_runs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute("UPDATE query_runs SET raw_question = COALESCE(raw_question, '')")
    op.execute("UPDATE query_runs SET request_id = COALESCE(request_id, 'legacy')")
    op.alter_column("query_runs", "raw_question", nullable=False)
    op.alter_column("query_runs", "request_id", nullable=False)


def downgrade() -> None:
    op.drop_column("query_runs", "updated_at")
    op.drop_column("query_runs", "request_id")
    op.drop_column("query_runs", "error_message")
    op.drop_column("query_runs", "error_code")
    op.drop_column("query_runs", "warnings")
    op.drop_column("query_runs", "graph_subgraph")
    op.drop_column("query_runs", "answer")
    op.drop_column("query_runs", "evidence_bundle")
    op.drop_column("query_runs", "raw_question")
