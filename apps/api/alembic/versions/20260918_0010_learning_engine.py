# ruff: noqa: E501
"""Add alternative learning approaches to immutable question snapshots.

Revision ID: 20260918_0010
Revises: 20260917_0009
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260918_0010"
down_revision = "20260917_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "question_versions",
        sa.Column(
            "alternative_approaches",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    # Existing authoring data gets a clearly labelled baseline so historic
    # scheduled versions remain a complete post-solve learning path.
    op.execute(
        """
        UPDATE question_versions
        SET alternative_approaches =
          '[{"title":"Baseline approach","summary_markdown":"Start with a direct implementation, then compare it with the reference solution to identify the trade-offs.","time_complexity":"Depends on input size","space_complexity":"Depends on input size"}]'::jsonb
        WHERE alternative_approaches = '[]'::jsonb
        """
    )


def downgrade() -> None:
    op.drop_column("question_versions", "alternative_approaches")
