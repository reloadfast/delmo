"""add dry_run and require_complete columns to rules

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rules",
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "rules",
        sa.Column("require_complete", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("rules", "require_complete")
    op.drop_column("rules", "dry_run")
