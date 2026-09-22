"""Add LinkedIn profiles and cover images.

Revision ID: 20260916_0005
Revises: 20260916_0004
"""

import sqlalchemy as sa

from alembic import op

revision = "20260916_0005"
down_revision = "20260916_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("cover_image_url", sa.String(length=500)))
    op.add_column("users", sa.Column("linkedin_url", sa.String(length=500)))
    op.execute(
        "CREATE UNIQUE INDEX uq_users_linkedin_url_lower ON users (lower(linkedin_url)) "
        "WHERE linkedin_url IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_users_linkedin_url_lower")
    op.drop_column("users", "linkedin_url")
    op.drop_column("users", "cover_image_url")
