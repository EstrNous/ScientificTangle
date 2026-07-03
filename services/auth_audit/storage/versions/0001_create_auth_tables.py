from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DISABLED_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$YmN4uCCwXrI8DxpumsIw2w$"
    "bFATdmJ7m4m+E5HMdw2IKWNRF6kCLIAPV+iiUdbMRiE"
)


def table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def column_names(table_name: str) -> set[str]:
    return {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def unique_column_sets(table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(constraint["column_names"])
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(table_name)
    }


def check_constraint_names(table_name: str) -> set[str | None]:
    return {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_check_constraints(table_name)
    }


def index_names(table_name: str) -> set[str]:
    return {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def upgrade() -> None:
    if "users" not in table_names():
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("username", sa.String(length=128), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=True),
            sa.Column("password_hash", sa.String(length=512), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "role IN ('admin', 'researcher', 'analyst', 'manager', 'external_partner')",
                name="ck_users_role",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username", name="uq_users_username"),
        )
    else:
        existing_columns = column_names("users")
        if "password_hash" not in existing_columns:
            op.add_column(
                "users",
                sa.Column(
                    "password_hash",
                    sa.String(length=512),
                    nullable=False,
                    server_default=DISABLED_PASSWORD_HASH,
                ),
            )
            op.alter_column("users", "password_hash", server_default=None)
        if "is_active" not in existing_columns:
            op.add_column(
                "users",
                sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            )
        op.alter_column("users", "email", existing_type=sa.Text(), nullable=True)
        if ("username",) not in unique_column_sets("users"):
            op.create_unique_constraint("uq_users_username", "users", ["username"])
        if "ck_users_role" not in check_constraint_names("users"):
            op.create_check_constraint(
                "ck_users_role",
                "users",
                "role IN ('admin', 'researcher', 'analyst', 'manager', 'external_partner')",
            )

    if "refresh_sessions" not in table_names():
        op.create_table(
            "refresh_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.Column("user_agent", sa.String(length=512), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["replaced_by_id"], ["refresh_sessions.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash", name="uq_refresh_sessions_token_hash"),
        )
    existing_indexes = index_names("refresh_sessions")
    if "ix_refresh_sessions_family_id" not in existing_indexes:
        op.create_index(
            "ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"], unique=False
        )
    if "ix_refresh_sessions_user_id" not in existing_indexes:
        op.create_index(
            "ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"], unique=False
        )


def downgrade() -> None:
    op.drop_index("ix_refresh_sessions_user_id", table_name="refresh_sessions")
    op.drop_index("ix_refresh_sessions_family_id", table_name="refresh_sessions")
    op.drop_table("refresh_sessions")
    op.drop_table("users")
