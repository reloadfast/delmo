"""create rules, rule_conditions, and move_logs tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rule_conditions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("condition_type", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "move_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("torrent_hash", sa.String(), nullable=False),
        sa.Column("torrent_name", sa.String(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("rule_name", sa.String(), nullable=True),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column("destination_path", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="success"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_move_logs_torrent_hash", "move_logs", ["torrent_hash"])
    op.create_index("ix_move_logs_created_at", "move_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_move_logs_created_at", table_name="move_logs")
    op.drop_index("ix_move_logs_torrent_hash", table_name="move_logs")
    op.drop_table("move_logs")
    op.drop_table("rule_conditions")
    op.drop_table("rules")
