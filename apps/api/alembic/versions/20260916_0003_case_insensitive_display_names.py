"""Enforce case-insensitive display-name uniqueness.

Revision ID: 20260916_0003
Revises: 20260916_0002
Create Date: 2026-09-16 14:20:00
"""

from alembic import op

revision = "20260916_0003"
down_revision = "20260916_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE UNIQUE INDEX uq_users_display_name_lower ON users (lower(display_name))")


def downgrade() -> None:
    op.execute("DROP INDEX uq_users_display_name_lower")
