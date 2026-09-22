"""Add editable profile data and display-name change tracking.

Revision ID: 20260916_0004
Revises: 20260916_0003
Create Date: 2026-09-16 15:15:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260916_0004"
down_revision = "20260916_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_image_url", sa.String(length=500)))
    op.add_column(
        "users",
        sa.Column("display_name_change_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users", sa.Column("display_name_change_window_started_at", sa.DateTime(timezone=True))
    )
    op.create_check_constraint(
        "ck_users_display_name_change_count_range",
        "users",
        "display_name_change_count BETWEEN 0 AND 3",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_display_name_change_count_range", "users", type_="check")
    op.drop_column("users", "display_name_change_window_started_at")
    op.drop_column("users", "display_name_change_count")
    op.drop_column("users", "profile_image_url")
