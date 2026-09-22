"""Add bilingual learning paths and auditable daily outcomes.

Revision ID: 20260918_0017
Revises: 20260918_0016
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260918_0017"
down_revision = "20260918_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("question_versions", sa.Column("explanation_en", sa.Text(), nullable=True))
    op.add_column("question_versions", sa.Column("explanation_ml", sa.Text(), nullable=True))
    op.add_column(
        "question_versions",
        sa.Column(
            "solution_trace",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "question_versions",
        sa.Column(
            "solution_notes_en",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "question_versions",
        sa.Column(
            "solution_notes_ml",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    # Existing immutable versions continue to render their former explanation
    # in English until an admin authors the Malayalam counterpart in a new version.
    op.execute(
        "UPDATE question_versions SET explanation_en = explanation_markdown "
        "WHERE explanation_en IS NULL AND explanation_markdown IS NOT NULL"
    )

    attempt_status = postgresql.ENUM(
        "in_progress", "solved", "quit", name="daily_attempt_status", create_type=False
    )
    postgresql.ENUM("in_progress", "solved", "quit", name="daily_attempt_status").create(
        op.get_bind(), checkfirst=True
    )
    op.create_table(
        "daily_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_submission_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            attempt_status,
            nullable=False,
            server_default=sa.text("'in_progress'"),
        ),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_counted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("walkthrough_unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.CheckConstraint("xp_awarded >= 0", name="ck_daily_attempt_xp_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["daily_assignment_id"], ["daily_assignments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_submission_id"], ["submissions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "daily_assignment_id", name="uq_daily_attempt_user_assignment"),
        sa.UniqueConstraint("source_submission_id", name="uq_daily_attempt_source_submission"),
    )
    op.create_index("ix_daily_attempts_user_status", "daily_attempts", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_daily_attempts_user_status", table_name="daily_attempts")
    op.drop_table("daily_attempts")
    sa.Enum(name="daily_attempt_status").drop(op.get_bind(), checkfirst=True)
    op.drop_column("question_versions", "solution_notes_ml")
    op.drop_column("question_versions", "solution_notes_en")
    op.drop_column("question_versions", "solution_trace")
    op.drop_column("question_versions", "explanation_ml")
    op.drop_column("question_versions", "explanation_en")
