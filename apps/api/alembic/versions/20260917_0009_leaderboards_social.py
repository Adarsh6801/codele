"""Add Phase 6 leaderboard privacy and canonical friend relationships.

Revision ID: 20260917_0009
Revises: 20260917_0008
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260917_0009"
down_revision = "20260917_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("leaderboard_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_table(
        "friendships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("second_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["first_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["second_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("first_user_id", "second_user_id", name="uq_friendship_pair"),
        sa.CheckConstraint("first_user_id <> second_user_id", name="ck_friendship_distinct_users"),
        sa.CheckConstraint("status IN ('pending', 'accepted')", name="ck_friendship_status"),
    )
    op.create_index("ix_friendships_first_status", "friendships", ["first_user_id", "status"])
    op.create_index("ix_friendships_second_status", "friendships", ["second_user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_friendships_second_status", table_name="friendships")
    op.drop_index("ix_friendships_first_status", table_name="friendships")
    op.drop_table("friendships")
    op.drop_column("users", "leaderboard_visible")
