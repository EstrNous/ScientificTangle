from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
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

    if "source_span_lookup" in tables:
        lookup_columns = column_names("source_span_lookup")
        if "access_level" not in lookup_columns:
            op.add_column(
                "source_span_lookup",
                sa.Column(
                    "access_level",
                    sa.String(length=32),
                    nullable=False,
                    server_default="internal",
                ),
            )
        if "allowed_roles" not in lookup_columns:
            op.add_column(
                "source_span_lookup",
                sa.Column(
                    "allowed_roles",
                    postgresql.JSONB(astext_type=sa.Text()),
                    nullable=False,
                    server_default=sa.text("'[]'::jsonb"),
                ),
            )
        lookup_indexes = index_names("source_span_lookup")
        if "ix_source_span_lookup_access_level" not in lookup_indexes:
            op.create_index(
                "ix_source_span_lookup_access_level",
                "source_span_lookup",
                ["access_level"],
            )
        if "ix_source_span_lookup_document_access" not in lookup_indexes:
            op.create_index(
                "ix_source_span_lookup_document_access",
                "source_span_lookup",
                ["document_id", "access_level"],
            )

    if "indexed_documents" in tables:
        indexed_indexes = index_names("indexed_documents")
        if "ix_indexed_documents_access_deletion" not in indexed_indexes:
            op.create_index(
                "ix_indexed_documents_access_deletion",
                "indexed_documents",
                ["access_level", "deletion_status"],
            )


def downgrade() -> None:
    tables = table_names()

    if "indexed_documents" in tables:
        indexed_indexes = index_names("indexed_documents")
        if "ix_indexed_documents_access_deletion" in indexed_indexes:
            op.drop_index("ix_indexed_documents_access_deletion", table_name="indexed_documents")

    if "source_span_lookup" in tables:
        lookup_indexes = index_names("source_span_lookup")
        if "ix_source_span_lookup_document_access" in lookup_indexes:
            op.drop_index("ix_source_span_lookup_document_access", table_name="source_span_lookup")
        if "ix_source_span_lookup_access_level" in lookup_indexes:
            op.drop_index("ix_source_span_lookup_access_level", table_name="source_span_lookup")
        lookup_columns = column_names("source_span_lookup")
        if "allowed_roles" in lookup_columns:
            op.drop_column("source_span_lookup", "allowed_roles")
        if "access_level" in lookup_columns:
            op.drop_column("source_span_lookup", "access_level")
