from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def column_names(table_name: str) -> set[str]:
    return {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def unique_constraints(table_name: str) -> list[dict[str, object]]:
    return sa.inspect(op.get_bind()).get_unique_constraints(table_name)


def upgrade() -> None:
    if "deactivated_at" not in column_names("users"):
        op.add_column(
            "users", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True)
        )
    op.execute("UPDATE users SET email = lower(btrim(email)) WHERE email IS NOT NULL")
    existing_unique_columns = {
        tuple(constraint["column_names"])
        for constraint in unique_constraints("users")
    }
    if ("email",) not in existing_unique_columns:
        op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    named_constraints = {
        constraint["name"] for constraint in unique_constraints("users")
    }
    if "uq_users_email" in named_constraints:
        op.drop_constraint("uq_users_email", "users", type_="unique")
    if "deactivated_at" in column_names("users"):
        op.drop_column("users", "deactivated_at")
