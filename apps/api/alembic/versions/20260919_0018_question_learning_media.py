"""Add optional image and video media to immutable question learning paths.

Revision ID: 20260919_0018
Revises: 20260918_0017
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260919_0018"
down_revision = "20260918_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("question_versions", sa.Column("solution_video_url", sa.String(length=500)))
    op.add_column(
        "question_versions",
        sa.Column(
            "solution_image_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("question_versions", "solution_image_urls")
    op.drop_column("question_versions", "solution_video_url")
