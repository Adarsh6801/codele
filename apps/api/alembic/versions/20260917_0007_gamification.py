"""Add Phase 5 gamification ledgers, streak history, shields, and badges.

Revision ID: 20260917_0007
Revises: 20260916_0006
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260917_0007"
down_revision = "20260916_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL enum values cannot be added inside the migration transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE xp_reason ADD VALUE IF NOT EXISTS 'no_hint_bonus'")

    op.create_table(
        "hint_uses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_hint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["daily_assignment_id"], ["daily_assignments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["question_hint_id"], ["question_hints.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "daily_assignment_id", "question_hint_id", name="uq_hint_use"),
    )
    op.create_table(
        "user_topic_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("solved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_solved_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "topic", name="uq_user_topic_progress"),
        sa.CheckConstraint("solved_count >= 0", name="ck_topic_progress_solved_nonnegative"),
    )
    op.create_table(
        "streak_days",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("solved_date", sa.Date(), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True)),
        sa.Column("is_shielded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "solved_date", name="uq_streak_day"),
    )
    op.create_table(
        "streak_shields",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("available", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_refilled_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", name="uq_streak_shield_user"),
        sa.CheckConstraint("available BETWEEN 0 AND 2", name="ck_streak_shield_inventory_range"),
    )
    op.create_table(
        "streak_shield_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shield_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("event_key", sa.String(length=255), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shield_id"], ["streak_shields.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "event_key", name="uq_shield_transaction_event"),
    )
    op.create_table(
        "badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("icon", sa.String(length=24), nullable=False),
        sa.Column("criteria_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_table(
        "user_badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("badge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_submission_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_submission_id"], ["submissions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )


def downgrade() -> None:
    op.drop_table("user_badges")
    op.drop_table("badges")
    op.drop_table("streak_shield_transactions")
    op.drop_table("streak_shields")
    op.drop_table("streak_days")
    op.drop_table("user_topic_progress")
    op.drop_table("hint_uses")
