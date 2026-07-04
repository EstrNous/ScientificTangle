from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
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
        if "ix_notifications_user_created_id" not in notification_indexes:
            op.create_index(
                "ix_notifications_user_created_id",
                "notifications",
                ["user_id", "created_at", "id"],
            )
    if "notification_match_results" in tables:
        match_indexes = index_names("notification_match_results")
        if "ix_notification_match_results_user_created_id" not in match_indexes:
            op.create_index(
                "ix_notification_match_results_user_created_id",
                "notification_match_results",
                ["user_id", "created_at", "id"],
            )


def downgrade() -> None:
    tables = table_names()
    if "notification_match_results" in tables:
        match_indexes = index_names("notification_match_results")
        if "ix_notification_match_results_user_created_id" in match_indexes:
            op.drop_index(
                "ix_notification_match_results_user_created_id",
                table_name="notification_match_results",
            )
    if "notifications" in tables:
        notification_indexes = index_names("notifications")
        if "ix_notifications_user_created_id" in notification_indexes:
            op.drop_index("ix_notifications_user_created_id", table_name="notifications")
