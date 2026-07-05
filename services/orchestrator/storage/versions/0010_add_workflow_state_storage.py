from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
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

    if "document_cascade_refs" in tables:
        cascade_columns = column_names("document_cascade_refs")
        if "cascade_status" not in cascade_columns:
            op.add_column(
                "document_cascade_refs",
                sa.Column(
                    "cascade_status",
                    sa.String(length=32),
                    nullable=False,
                    server_default="none",
                ),
            )
        if "cascade_steps" not in cascade_columns:
            op.add_column(
                "document_cascade_refs",
                sa.Column(
                    "cascade_steps",
                    postgresql.JSONB(astext_type=sa.Text()),
                    nullable=False,
                    server_default=sa.text("'{}'::jsonb"),
                ),
            )
        if "last_error" not in cascade_columns:
            op.add_column("document_cascade_refs", sa.Column("last_error", sa.Text(), nullable=True))
        cascade_indexes = index_names("document_cascade_refs")
        if "ix_document_cascade_refs_cascade_status" not in cascade_indexes:
            op.create_index(
                "ix_document_cascade_refs_cascade_status",
                "document_cascade_refs",
                ["cascade_status"],
            )

    if "audit_events" in tables:
        audit_indexes = index_names("audit_events")
        if "ix_audit_events_created_id" not in audit_indexes:
            op.create_index(
                "ix_audit_events_created_id",
                "audit_events",
                ["created_at", "id"],
            )
        if "ix_audit_events_action_created_id" not in audit_indexes:
            op.create_index(
                "ix_audit_events_action_created_id",
                "audit_events",
                ["action", "created_at", "id"],
            )

    if "review_decisions" in tables:
        review_indexes = index_names("review_decisions")
        if "ix_review_decisions_status_created_id" not in review_indexes:
            op.create_index(
                "ix_review_decisions_status_created_id",
                "review_decisions",
                ["status", "created_at", "id"],
            )


def downgrade() -> None:
    tables = table_names()

    if "review_decisions" in tables:
        review_indexes = index_names("review_decisions")
        if "ix_review_decisions_status_created_id" in review_indexes:
            op.drop_index("ix_review_decisions_status_created_id", table_name="review_decisions")

    if "audit_events" in tables:
        audit_indexes = index_names("audit_events")
        if "ix_audit_events_action_created_id" in audit_indexes:
            op.drop_index("ix_audit_events_action_created_id", table_name="audit_events")
        if "ix_audit_events_created_id" in audit_indexes:
            op.drop_index("ix_audit_events_created_id", table_name="audit_events")

    if "document_cascade_refs" in tables:
        cascade_indexes = index_names("document_cascade_refs")
        if "ix_document_cascade_refs_cascade_status" in cascade_indexes:
            op.drop_index("ix_document_cascade_refs_cascade_status", table_name="document_cascade_refs")
        cascade_columns = column_names("document_cascade_refs")
        if "last_error" in cascade_columns:
            op.drop_column("document_cascade_refs", "last_error")
        if "cascade_steps" in cascade_columns:
            op.drop_column("document_cascade_refs", "cascade_steps")
        if "cascade_status" in cascade_columns:
            op.drop_column("document_cascade_refs", "cascade_status")
