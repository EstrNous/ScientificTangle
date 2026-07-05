from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    tables = table_names()

    if "source_span_lookup" not in tables:
        op.create_table(
            "source_span_lookup",
            sa.Column("source_span_id", sa.String(length=128), nullable=False),
            sa.Column("document_id", sa.String(length=128), nullable=False),
            sa.Column("page", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("highlight_start", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("highlight_end", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("table_row_id", sa.String(length=256), nullable=True),
            sa.Column("table_block_id", sa.String(length=256), nullable=True),
            sa.Column("source_type", sa.String(length=32), nullable=False, server_default="text"),
            sa.Column("text_snippet", sa.Text(), nullable=False, server_default=""),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("source_span_id"),
        )
        op.create_index("ix_source_span_lookup_document_id", "source_span_lookup", ["document_id"])
        op.create_index("ix_source_span_lookup_page", "source_span_lookup", ["page"])
        op.create_index("ix_source_span_lookup_table_row_id", "source_span_lookup", ["table_row_id"])
        op.create_index(
            "ix_source_span_lookup_document_page",
            "source_span_lookup",
            ["document_id", "page"],
        )

    if "document_cascade_refs" not in tables:
        op.create_table(
            "document_cascade_refs",
            sa.Column("document_id", sa.String(length=128), nullable=False),
            sa.Column(
                "source_span_ids",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "claim_ids",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "vector_point_ids",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "graph_node_refs",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "minio_object_refs",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("document_id"),
        )
        op.create_index(
            "ix_document_cascade_refs_updated_at",
            "document_cascade_refs",
            ["updated_at"],
        )


def downgrade() -> None:
    tables = table_names()
    if "document_cascade_refs" in tables:
        cascade_indexes = index_names("document_cascade_refs")
        if "ix_document_cascade_refs_updated_at" in cascade_indexes:
            op.drop_index("ix_document_cascade_refs_updated_at", table_name="document_cascade_refs")
        op.drop_table("document_cascade_refs")
    if "source_span_lookup" in tables:
        lookup_indexes = index_names("source_span_lookup")
        for index_name in (
            "ix_source_span_lookup_document_page",
            "ix_source_span_lookup_table_row_id",
            "ix_source_span_lookup_page",
            "ix_source_span_lookup_document_id",
        ):
            if index_name in lookup_indexes:
                op.drop_index(index_name, table_name="source_span_lookup")
        op.drop_table("source_span_lookup")
