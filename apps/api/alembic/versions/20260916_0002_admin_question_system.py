"""Add Phase 2 authoring details and language-aware schedules.

Revision ID: 20260916_0002
Revises: 20260916_0001
Create Date: 2026-09-16 00:01:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260916_0002"
down_revision = "20260916_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE question_version_status ADD VALUE IF NOT EXISTS 'ready' BEFORE 'scheduled'"
    )
    op.add_column(
        "question_versions",
        sa.Column(
            "examples", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )
    op.add_column("question_versions", sa.Column("constraints_markdown", sa.Text()))
    op.add_column("question_versions", sa.Column("explanation_markdown", sa.Text()))
    op.add_column("question_versions", sa.Column("complexity_notes", sa.Text()))
    op.add_column(
        "daily_assignments",
        sa.Column("language", sa.Enum(name="programming_language"), nullable=True),
    )
    op.execute("UPDATE daily_assignments SET language = 'python' WHERE language IS NULL")
    op.alter_column("daily_assignments", "language", nullable=False)
    op.drop_constraint("uq_daily_assignment_date_level", "daily_assignments", type_="unique")
    op.create_unique_constraint(
        "uq_daily_assignment_date_level_language",
        "daily_assignments",
        ["assignment_date", "level", "language"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_daily_assignment_date_level_language", "daily_assignments", type_="unique"
    )
    op.create_unique_constraint(
        "uq_daily_assignment_date_level", "daily_assignments", ["assignment_date", "level"]
    )
    op.drop_column("daily_assignments", "language")
    op.drop_column("question_versions", "complexity_notes")
    op.drop_column("question_versions", "explanation_markdown")
    op.drop_column("question_versions", "constraints_markdown")
    op.drop_column("question_versions", "examples")
    # PostgreSQL enum values cannot be removed safely; the ready value remains on downgrade.
