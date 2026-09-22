# ruff: noqa: E501
"""Create the Phase 1 PostgreSQL database foundation.

Revision ID: 20260916_0001
Revises:
Create Date: 2026-09-16 00:00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260916_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role = postgresql.ENUM(
    "user", "moderator", "admin", "super_admin", name="user_role", create_type=False
)
level = postgresql.ENUM("rookie", "hacker", "architect", name="level", create_type=False)
question_version_status = postgresql.ENUM(
    "draft", "scheduled", "published", "retired", name="question_version_status", create_type=False
)
test_visibility = postgresql.ENUM("public", "hidden", name="test_visibility", create_type=False)
submission_status = postgresql.ENUM(
    "queued", "running", "passed", "failed", "error", name="submission_status", create_type=False
)
programming_language = postgresql.ENUM(
    "python", "javascript", name="programming_language", create_type=False
)
xp_reason = postgresql.ENUM(
    "daily_solve",
    "first_attempt_bonus",
    "hint_use_adjustment",
    "admin_adjustment",
    name="xp_reason",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        user_role,
        level,
        question_version_status,
        test_visibility,
        submission_status,
        programming_language,
        xp_reason,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("role", user_role, nullable=False, server_default="user"),
        sa.Column("level", level, nullable=False, server_default="rookie"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False, unique=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_table(
        "question_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("statement_markdown", sa.Text(), nullable=False),
        sa.Column("level", level, nullable=False),
        sa.Column("topic", sa.String(100), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column(
            "starter_code",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "solution_code",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", question_version_status, nullable=False, server_default="draft"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("question_id", "version_number", name="uq_question_version_number"),
        sa.CheckConstraint("version_number > 0", name="ck_question_version_number_positive"),
        sa.CheckConstraint(
            "difficulty BETWEEN 1 AND 5", name="ck_question_version_difficulty_range"
        ),
    )
    op.create_index("ix_question_versions_status_level", "question_versions", ["status", "level"])
    op.create_table(
        "test_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("visibility", test_visibility, nullable=False),
        sa.Column("input_data", postgresql.JSONB(), nullable=False),
        sa.Column("expected_output", postgresql.JSONB(), nullable=False),
        sa.Column("explanation", sa.Text()),
        sa.ForeignKeyConstraint(
            ["question_version_id"], ["question_versions.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("question_version_id", "position", name="uq_test_case_position"),
        sa.CheckConstraint("position > 0", name="ck_test_case_position_positive"),
    )
    op.create_table(
        "question_hints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("xp_penalty", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["question_version_id"], ["question_versions.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("question_version_id", "position", name="uq_hint_position"),
        sa.CheckConstraint("position > 0", name="ck_hint_position_positive"),
        sa.CheckConstraint("xp_penalty >= 0", name="ck_hint_xp_penalty_nonnegative"),
    )
    op.create_table(
        "daily_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assignment_date", sa.Date(), nullable=False),
        sa.Column("level", level, nullable=False),
        sa.Column("question_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["question_version_id"], ["question_versions.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("assignment_date", "level", name="uq_daily_assignment_date_level"),
    )
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_assignment_id", postgresql.UUID(as_uuid=True)),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("language", programming_language, nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("status", submission_status, nullable=False, server_default="queued"),
        sa.Column("test_results", postgresql.JSONB()),
        sa.Column("passed_test_count", sa.Integer()),
        sa.Column("total_test_count", sa.Integer()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["question_version_id"], ["question_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["daily_assignment_id"], ["daily_assignments.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_submission_user_idempotency_key"
        ),
        sa.CheckConstraint(
            "passed_test_count IS NULL OR passed_test_count >= 0",
            name="ck_submission_passed_nonnegative",
        ),
        sa.CheckConstraint(
            "total_test_count IS NULL OR total_test_count >= 0",
            name="ck_submission_total_nonnegative",
        ),
        sa.CheckConstraint(
            "passed_test_count IS NULL OR total_test_count IS NULL OR passed_test_count <= total_test_count",
            name="ck_submission_passed_not_greater_than_total",
        ),
    )
    op.create_index("ix_submissions_user_created_at", "submissions", ["user_id", "created_at"])
    op.create_index("ix_submissions_question_version_id", "submissions", ["question_version_id"])
    op.create_table(
        "xp_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True)),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", xp_reason, nullable=False),
        sa.Column("award_key", sa.String(255), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "award_key", name="uq_xp_transaction_award"),
    )
    op.create_index(
        "ix_xp_transactions_user_created_at", "xp_transactions", ["user_id", "created_at"]
    )
    op.create_table(
        "streaks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_solved_date", sa.Date()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", name="uq_streak_user"),
        sa.CheckConstraint("current_streak >= 0", name="ck_streak_current_nonnegative"),
        sa.CheckConstraint("longest_streak >= 0", name="ck_streak_longest_nonnegative"),
        sa.CheckConstraint(
            "longest_streak >= current_streak", name="ck_streak_longest_at_least_current"
        ),
    )
    op.execute("""
        CREATE FUNCTION prevent_xp_transaction_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'xp_transactions is an immutable ledger';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER xp_transactions_immutable
        BEFORE UPDATE OR DELETE ON xp_transactions
        FOR EACH ROW EXECUTE FUNCTION prevent_xp_transaction_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS xp_transactions_immutable ON xp_transactions")
    op.execute("DROP FUNCTION IF EXISTS prevent_xp_transaction_mutation()")
    op.drop_table("streaks")
    op.drop_index("ix_xp_transactions_user_created_at", table_name="xp_transactions")
    op.drop_table("xp_transactions")
    op.drop_index("ix_submissions_question_version_id", table_name="submissions")
    op.drop_index("ix_submissions_user_created_at", table_name="submissions")
    op.drop_table("submissions")
    op.drop_table("daily_assignments")
    op.drop_table("question_hints")
    op.drop_table("test_cases")
    op.drop_index("ix_question_versions_status_level", table_name="question_versions")
    op.drop_table("question_versions")
    op.drop_table("questions")
    op.drop_table("users")
    bind = op.get_bind()
    for enum_type in (
        xp_reason,
        programming_language,
        submission_status,
        test_visibility,
        question_version_status,
        level,
        user_role,
    ):
        enum_type.drop(bind, checkfirst=True)
