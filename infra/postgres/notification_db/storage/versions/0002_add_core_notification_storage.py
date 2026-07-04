from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = table_names()

    if "notifications" in tables:
        notification_columns = column_names("notifications")
        if "reference_type" not in notification_columns:
            op.add_column(
                "notifications",
                sa.Column("reference_type", sa.String(length=64), nullable=True),
            )
        notification_indexes = index_names("notifications")
        if "ix_notifications_user_created" not in notification_indexes:
            op.create_index(
                "ix_notifications_user_created",
                "notifications",
                ["user_id", "created_at"],
            )
        if "ix_notifications_user_unread" not in notification_indexes:
            op.create_index(
                "ix_notifications_user_unread",
                "notifications",
                ["user_id", "is_read"],
            )
        if "ix_notifications_type" not in notification_indexes:
            op.create_index("ix_notifications_type", "notifications", ["type"])

    if "extracted_entities" not in tables:
        op.create_table(
            "extracted_entities",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_interest_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("entity_label", sa.String(length=256), nullable=False),
            sa.Column("entity_type", sa.String(length=64), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("document_id", sa.String(length=128), nullable=True),
            sa.Column("source_span_id", sa.String(length=128), nullable=True),
            sa.Column(
                "metadata",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["user_interest_id"],
                ["user_interests.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_extracted_entities_user_interest_id", "extracted_entities", ["user_interest_id"])
        op.create_index("ix_extracted_entities_user_id", "extracted_entities", ["user_id"])
        op.create_index("ix_extracted_entities_entity_type", "extracted_entities", ["entity_type"])
        op.create_index("ix_extracted_entities_document_id", "extracted_entities", ["document_id"])
        op.create_index("ix_extracted_entities_source_span_id", "extracted_entities", ["source_span_id"])

    if "notification_match_results" not in tables:
        op.create_table(
            "notification_match_results",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("reference_id", sa.String(length=256), nullable=True),
            sa.Column("reference_type", sa.String(length=64), nullable=True),
            sa.Column("match_score", sa.Float(), nullable=True),
            sa.Column(
                "match_payload",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["notification_id"],
                ["notifications.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_notification_match_results_user_id",
            "notification_match_results",
            ["user_id"],
        )
        op.create_index(
            "ix_notification_match_results_created_at",
            "notification_match_results",
            ["created_at"],
        )
        op.create_index(
            "ix_notification_match_results_notification_id",
            "notification_match_results",
            ["notification_id"],
        )


def downgrade() -> None:
    tables = table_names()
    if "notification_match_results" in tables:
        op.drop_index(
            "ix_notification_match_results_notification_id",
            table_name="notification_match_results",
        )
        op.drop_index(
            "ix_notification_match_results_created_at",
            table_name="notification_match_results",
        )
        op.drop_index(
            "ix_notification_match_results_user_id",
            table_name="notification_match_results",
        )
        op.drop_table("notification_match_results")
    if "extracted_entities" in tables:
        op.drop_index("ix_extracted_entities_source_span_id", table_name="extracted_entities")
        op.drop_index("ix_extracted_entities_document_id", table_name="extracted_entities")
        op.drop_index("ix_extracted_entities_entity_type", table_name="extracted_entities")
        op.drop_index("ix_extracted_entities_user_id", table_name="extracted_entities")
        op.drop_index("ix_extracted_entities_user_interest_id", table_name="extracted_entities")
        op.drop_table("extracted_entities")
    if "notifications" in tables:
        notification_indexes = index_names("notifications")
        if "ix_notifications_type" in notification_indexes:
            op.drop_index("ix_notifications_type", table_name="notifications")
        if "ix_notifications_user_unread" in notification_indexes:
            op.drop_index("ix_notifications_user_unread", table_name="notifications")
        if "ix_notifications_user_created" in notification_indexes:
            op.drop_index("ix_notifications_user_created", table_name="notifications")
        notification_columns = column_names("notifications")
        if "reference_type" in notification_columns:
            op.drop_column("notifications", "reference_type")
