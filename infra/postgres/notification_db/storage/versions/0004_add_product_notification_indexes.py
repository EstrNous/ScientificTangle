from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    tables = table_names()
    if "notifications" in tables:
        notification_indexes = index_names("notifications")
        if "ix_notifications_user_type_created_id" not in notification_indexes:
            op.create_index(
                "ix_notifications_user_type_created_id",
                "notifications",
                ["user_id", "type", "created_at", "id"],
            )
        if "ix_notifications_user_unread_created" not in notification_indexes:
            op.create_index(
                "ix_notifications_user_unread_created",
                "notifications",
                ["user_id", "is_read", "created_at"],
            )


def downgrade() -> None:
    tables = table_names()
    if "notifications" in tables:
        notification_indexes = index_names("notifications")
        if "ix_notifications_user_unread_created" in notification_indexes:
            op.drop_index("ix_notifications_user_unread_created", table_name="notifications")
        if "ix_notifications_user_type_created_id" in notification_indexes:
            op.drop_index("ix_notifications_user_type_created_id", table_name="notifications")
