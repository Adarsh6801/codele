"""Create the Codele community, mentor and challenge-programme foundation.

Revision ID: 20260922_0019
Revises: 20260919_0018
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


revision = "20260922_0019"
down_revision = "20260919_0018"
branch_labels = None
depends_on = None


community_challenge_status = postgresql.ENUM(
    "draft", "published", "archived", name="community_challenge_status", create_type=False
)
community_enrollment_status = postgresql.ENUM(
    "active", "completed", "forgone", "expired", name="community_enrollment_status", create_type=False
)
community_task_kind = postgresql.ENUM(
    "problem", "video", "article", "summary", "image", "resource",
    name="community_task_kind",
    create_type=False,
)


def upgrade() -> None:
    # The role is deliberately separate from moderation: mentors can provide
    # identified learning support without receiving administrative authority.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'mentor'")

    bind = op.get_bind()
    community_challenge_status.create(bind, checkfirst=True)
    community_enrollment_status.create(bind, checkfirst=True)
    community_task_kind.create(bind, checkfirst=True)

    op.create_table(
        "community_challenges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("description_markdown", sa.Text()),
        sa.Column(
            "status",
            community_challenge_status,
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("completion_deadline_days", sa.Integer(), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500)),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("duration_days >= 1", name="ck_community_challenge_duration_positive"),
        sa.CheckConstraint(
            "completion_deadline_days >= 1", name="ck_community_challenge_deadline_positive"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "ix_community_challenges_status_created",
        "community_challenges",
        ["status", "created_at"],
    )

    op.create_table(
        "community_challenge_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("challenge_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("day_offset", sa.Integer(), nullable=False),
        sa.Column("kind", community_task_kind, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("instructions_markdown", sa.Text()),
        sa.Column("question_version_id", sa.UUID()),
        sa.Column("video_url", sa.String(length=500)),
        sa.Column("resource_url", sa.String(length=500)),
        sa.Column("asset_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("summary_markdown", sa.Text()),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("position > 0", name="ck_community_task_position_positive"),
        sa.CheckConstraint("day_offset > 0", name="ck_community_task_day_offset_positive"),
        sa.ForeignKeyConstraint(["challenge_id"], ["community_challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_version_id"], ["question_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("challenge_id", "position", name="uq_community_challenge_task_position"),
    )
    op.create_index("ix_community_tasks_challenge_day", "community_challenge_tasks", ["challenge_id", "day_offset"])

    op.create_table(
        "community_enrollments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("challenge_id", sa.UUID(), nullable=False),
        sa.Column("status", community_enrollment_status, nullable=False, server_default=sa.text("'active'")),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("forgone_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["community_challenges.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "challenge_id", name="uq_community_enrollment_user_challenge"),
    )
    op.create_index("ix_community_enrollments_challenge_status", "community_enrollments", ["challenge_id", "status"])
    op.create_index(
        "uq_community_active_enrollment_user",
        "community_enrollments",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "community_task_progress",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("enrollment_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completion_note", sa.Text()),
        sa.ForeignKeyConstraint(["enrollment_id"], ["community_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["community_challenge_tasks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", "task_id", name="uq_community_task_progress"),
    )
    op.create_index("ix_community_task_progress_enrollment", "community_task_progress", ["enrollment_id"])

    op.create_table(
        "community_discussions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_community_discussions_created", "community_discussions", ["created_at"])
    op.create_index("ix_community_discussions_author_created", "community_discussions", ["author_id", "created_at"])

    op.create_table(
        "community_discussion_replies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("discussion_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("parent_reply_id", sa.UUID()),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("is_accepted_answer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["discussion_id"], ["community_discussions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_reply_id"], ["community_discussion_replies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_community_replies_discussion_created", "community_discussion_replies", ["discussion_id", "created_at"])
    op.create_index("ix_community_replies_parent", "community_discussion_replies", ["parent_reply_id"])


def downgrade() -> None:
    op.drop_index("ix_community_replies_parent", table_name="community_discussion_replies")
    op.drop_index("ix_community_replies_discussion_created", table_name="community_discussion_replies")
    op.drop_table("community_discussion_replies")
    op.drop_index("ix_community_discussions_author_created", table_name="community_discussions")
    op.drop_index("ix_community_discussions_created", table_name="community_discussions")
    op.drop_table("community_discussions")
    op.drop_index("ix_community_task_progress_enrollment", table_name="community_task_progress")
    op.drop_table("community_task_progress")
    op.drop_index("uq_community_active_enrollment_user", table_name="community_enrollments")
    op.drop_index("ix_community_enrollments_challenge_status", table_name="community_enrollments")
    op.drop_table("community_enrollments")
    op.drop_index("ix_community_tasks_challenge_day", table_name="community_challenge_tasks")
    op.drop_table("community_challenge_tasks")
    op.drop_index("ix_community_challenges_status_created", table_name="community_challenges")
    op.drop_table("community_challenges")

    bind = op.get_bind()
    community_task_kind.drop(bind, checkfirst=True)
    community_enrollment_status.drop(bind, checkfirst=True)
    community_challenge_status.drop(bind, checkfirst=True)
    # PostgreSQL cannot safely remove an enum value. The mentor enum remains
    # available after a downgrade so existing accounts are never corrupted.
