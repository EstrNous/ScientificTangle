from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    tables = table_names()
    if "notifications" not in tables:
        return
    notification_indexes = index_names("notifications")
    if "uq_notifications_user_type_reference_id" not in notification_indexes:
        op.create_index(
            "uq_notifications_user_type_reference_id",
            "notifications",
            ["user_id", "type", "reference_id"],
            unique=True,
            postgresql_where=sa.text("reference_id IS NOT NULL"),
        )


def downgrade() -> None:
    tables = table_names()
    if "notifications" not in tables:
        return
    notification_indexes = index_names("notifications")
    if "uq_notifications_user_type_reference_id" in notification_indexes:
        op.drop_index("uq_notifications_user_type_reference_id", table_name="notifications")
