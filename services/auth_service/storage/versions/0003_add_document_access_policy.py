from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_access_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_level", sa.String(length=32), nullable=False),
        sa.Column("allowed_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("owner_team", sa.String(length=128), nullable=True),
        sa.Column("export_allowed", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "access_level IN ('public', 'internal', 'confidential', 'restricted')",
            name="ck_document_access_policies_access_level",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_access_policies_access_level", "document_access_policies", ["access_level"])


def downgrade() -> None:
    op.drop_index("ix_document_access_policies_access_level", table_name="document_access_policies")
    op.drop_table("document_access_policies")
