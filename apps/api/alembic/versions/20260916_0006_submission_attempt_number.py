"""Persist per-user attempt numbers for question versions.

Revision ID: 20260916_0006
Revises: 20260916_0005
"""

import sqlalchemy as sa

from alembic import op

revision = "20260916_0006"
down_revision = "20260916_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_submissions_user_question_attempt",
        "submissions",
        ["user_id", "question_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_submissions_user_question_attempt", table_name="submissions")
    op.drop_column("submissions", "attempt_number")
