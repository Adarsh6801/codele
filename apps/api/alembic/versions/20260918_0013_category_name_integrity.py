"""Enforce case-insensitive category names.

Revision ID: 20260918_0013
Revises: 20260918_0012
"""

import sqlalchemy as sa

from alembic import op

revision = "20260918_0013"
down_revision = "20260918_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_categories_name_ci",
        "categories",
        [sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_categories_name_ci", table_name="categories")
