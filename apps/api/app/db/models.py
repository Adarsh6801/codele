"""SQLAlchemy models for Codele's server-owned learning data.

Question versions are snapshots.  Any row that records user history keeps a
direct ``question_version_id`` so later edits to a question cannot rewrite the
past.  XP and streak fields are only written by backend scoring workflows.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(enum.StrEnum):
    USER = "user"
    MENTOR = "mentor"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Level(enum.StrEnum):
    ROOKIE = "rookie"
    HACKER = "hacker"
    ARCHITECT = "architect"


class QuestionVersionStatus(enum.StrEnum):
    DRAFT = "draft"
    READY = "ready"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    RETIRED = "retired"


class TestVisibility(enum.StrEnum):
    PUBLIC = "public"
    HIDDEN = "hidden"


class SubmissionStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class DailyAttemptStatus(enum.StrEnum):
    """A learner's final outcome for one immutable daily assignment."""

    IN_PROGRESS = "in_progress"
    SOLVED = "solved"
    QUIT = "quit"


class NotificationType(enum.StrEnum):
    SUBMISSION = "submission"
    ACHIEVEMENT = "achievement"
    SOCIAL = "social"
    ACCOUNT = "account"


class NotificationDeliveryStatus(enum.StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    SKIPPED = "skipped"
    FAILED = "failed"


class ProgrammingLanguage(enum.StrEnum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"


class CommunityChallengeStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CommunityEnrollmentStatus(enum.StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FORGONE = "forgone"
    EXPIRED = "expired"


class CommunityTaskKind(enum.StrEnum):
    PROBLEM = "problem"
    VIDEO = "video"
    ARTICLE = "article"
    SUMMARY = "summary"
    IMAGE = "image"
    RESOURCE = "resource"


class XPReason(enum.StrEnum):
    DAILY_SOLVE = "daily_solve"
    FIRST_ATTEMPT_BONUS = "first_attempt_bonus"
    HINT_USE_ADJUSTMENT = "hint_use_adjustment"
    NO_HINT_BONUS = "no_hint_bonus"
    ADMIN_ADJUSTMENT = "admin_adjustment"


def database_enum(enum_type: type[enum.Enum], name: str) -> Enum:
    """Map StrEnum members to the lowercase PostgreSQL enum values, not member names."""
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class UUIDPrimaryKey:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(String(500))
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    display_name_change_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    display_name_change_window_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        database_enum(UserRole, "user_role"), nullable=False, server_default=UserRole.USER.value
    )
    level: Mapped[Level] = mapped_column(
        database_enum(Level, "level"), nullable=False, server_default=Level.ROOKIE.value
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    # JWTs carry this server-owned number.  Incrementing it revokes every
    # previously issued access token without persisting individual JWTs.
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # Hides the user from global and friends ranking reads without changing their XP ledger.
    leaderboard_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    question_versions: Mapped[list[QuestionVersion]] = relationship(back_populates="created_by")
    submissions: Mapped[list[Submission]] = relationship(back_populates="user")
    daily_attempts: Mapped[list[DailyAttempt]] = relationship(back_populates="user")
    xp_transactions: Mapped[list[XPTransaction]] = relationship(back_populates="user")
    streak: Mapped[Streak | None] = relationship(back_populates="user", uselist=False)
    topic_progress: Mapped[list[UserTopicProgress]] = relationship(back_populates="user")
    streak_days: Mapped[list[StreakDay]] = relationship(back_populates="user")
    streak_shield: Mapped[StreakShield | None] = relationship(back_populates="user", uselist=False)
    badges: Mapped[list[UserBadge]] = relationship(back_populates="user")
    notification_preferences: Mapped[NotificationPreference | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    filed_moderation_reports: Mapped[list[ModerationReport]] = relationship(
        back_populates="reporter", foreign_keys="ModerationReport.reporter_id"
    )
    received_moderation_reports: Mapped[list[ModerationReport]] = relationship(
        back_populates="target_user", foreign_keys="ModerationReport.target_user_id"
    )
    handled_moderation_reports: Mapped[list[ModerationReport]] = relationship(
        back_populates="handled_by", foreign_keys="ModerationReport.handled_by_id"
    )
    admin_audit_logs: Mapped[list[AdminAuditLog]] = relationship(back_populates="actor")
    community_challenges_created: Mapped[list[CommunityChallenge]] = relationship(
        back_populates="created_by", foreign_keys="CommunityChallenge.created_by_id"
    )
    community_enrollments: Mapped[list[CommunityEnrollment]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    community_discussions: Mapped[list[CommunityDiscussion]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    community_discussion_replies: Mapped[list[CommunityDiscussionReply]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )


class NotificationPreference(UUIDPrimaryKey, Timestamped, Base):
    """Per-user notification choices. Category toggles are evaluated server-side."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    submission_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    achievement_updates: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    social_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    account_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    user: Mapped[User] = relationship(back_populates="notification_preferences")


class Notification(UUIDPrimaryKey, Base):
    """An in-app notification with an immutable event key for worker-safe delivery."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_notifications_event_key"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index("ix_notifications_user_unread", "user_id", "read_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        database_enum(NotificationType, "notification_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500))
    event_key: Mapped[str] = mapped_column(String(255), nullable=False)
    delivery_status: Mapped[NotificationDeliveryStatus] = mapped_column(
        database_enum(NotificationDeliveryStatus, "notification_delivery_status"),
        nullable=False,
        server_default=NotificationDeliveryStatus.PENDING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="notifications")


class Question(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "questions"

    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(nullable=False, server_default="false")

    versions: Mapped[list[QuestionVersion]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionVersion.version_number",
    )


class Category(UUIDPrimaryKey, Timestamped, Base):
    """Admin-managed classification used by every immutable question version."""

    __tablename__ = "categories"
    __table_args__ = (Index("ix_categories_name", "name"),)

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))

    question_versions: Mapped[list[QuestionVersion]] = relationship(back_populates="category")


class QuestionVersion(UUIDPrimaryKey, Base):
    __tablename__ = "question_versions"
    __table_args__ = (
        UniqueConstraint("question_id", "version_number", name="uq_question_version_number"),
        Index("ix_question_versions_status_level", "status", "level"),
        CheckConstraint("version_number > 0", name="ck_question_version_number_positive"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_question_version_difficulty_range"),
    )

    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    statement_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    constraints_markdown: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    # This name is an immutable snapshot used for historical learning and XP aggregates.
    level: Mapped[Level] = mapped_column(database_enum(Level, "level"), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    starter_code: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    solution_code: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    explanation_markdown: Mapped[str | None] = mapped_column(Text)
    # ``explanation_markdown`` remains for older published snapshots. New
    # versions carry their learning content in both supported languages.
    explanation_en: Mapped[str | None] = mapped_column(Text)
    explanation_ml: Mapped[str | None] = mapped_column(Text)
    solution_trace: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    solution_notes_en: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    solution_notes_ml: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    # Stored on the immutable version so historical submissions retain the
    # exact learning media an author selected for that question version.
    solution_video_url: Mapped[str | None] = mapped_column(String(500))
    solution_image_urls: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    complexity_notes: Mapped[str | None] = mapped_column(Text)
    alternative_approaches: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    status: Mapped[QuestionVersionStatus] = mapped_column(
        database_enum(QuestionVersionStatus, "question_version_status"),
        nullable=False,
        server_default=QuestionVersionStatus.DRAFT.value,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    question: Mapped[Question] = relationship(back_populates="versions")
    category: Mapped[Category] = relationship(back_populates="question_versions")
    created_by: Mapped[User | None] = relationship(back_populates="question_versions")
    test_cases: Mapped[list[TestCase]] = relationship(
        back_populates="question_version", cascade="all, delete-orphan"
    )
    hints: Mapped[list[QuestionHint]] = relationship(
        back_populates="question_version", cascade="all, delete-orphan"
    )
    daily_assignments: Mapped[list[DailyAssignment]] = relationship(
        back_populates="question_version"
    )
    submissions: Mapped[list[Submission]] = relationship(back_populates="question_version")
    community_challenge_tasks: Mapped[list[CommunityChallengeTask]] = relationship(
        back_populates="question_version"
    )


class TestCase(UUIDPrimaryKey, Base):
    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("question_version_id", "position", name="uq_test_case_position"),
        CheckConstraint("position > 0", name="ck_test_case_position_positive"),
    )

    question_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_versions.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    visibility: Mapped[TestVisibility] = mapped_column(
        database_enum(TestVisibility, "test_visibility"), nullable=False
    )
    input_data: Mapped[Any] = mapped_column(JSONB, nullable=False)
    expected_output: Mapped[Any] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)

    question_version: Mapped[QuestionVersion] = relationship(back_populates="test_cases")


class QuestionHint(UUIDPrimaryKey, Base):
    __tablename__ = "question_hints"
    __table_args__ = (
        UniqueConstraint("question_version_id", "position", name="uq_hint_position"),
        CheckConstraint("position > 0", name="ck_hint_position_positive"),
        CheckConstraint("xp_penalty >= 0", name="ck_hint_xp_penalty_nonnegative"),
    )

    question_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_versions.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    xp_penalty: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    question_version: Mapped[QuestionVersion] = relationship(back_populates="hints")
    uses: Mapped[list[HintUse]] = relationship(back_populates="hint")


class DailyAssignment(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "daily_assignments"
    __table_args__ = (
        Index(
            "uq_daily_assignment_date_level_active",
            "assignment_date",
            "level",
            unique=True,
            postgresql_where=text("language IS NULL"),
        ),
    )

    assignment_date: Mapped[date] = mapped_column(Date, nullable=False)
    level: Mapped[Level] = mapped_column(database_enum(Level, "level"), nullable=False)
    # Legacy language-specific schedules are retained for historical rows only.
    # New schedules keep this column NULL and are available in both editors.
    legacy_language: Mapped[ProgrammingLanguage | None] = mapped_column(
        "language", database_enum(ProgrammingLanguage, "programming_language")
    )
    question_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_versions.id", ondelete="RESTRICT"), nullable=False
    )

    question_version: Mapped[QuestionVersion] = relationship(back_populates="daily_assignments")
    submissions: Mapped[list[Submission]] = relationship(back_populates="daily_assignment")
    hint_uses: Mapped[list[HintUse]] = relationship(back_populates="daily_assignment")
    attempts: Mapped[list[DailyAttempt]] = relationship(back_populates="daily_assignment")


class Submission(UUIDPrimaryKey, Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_submission_user_idempotency_key"),
        Index("ix_submissions_user_created_at", "user_id", "created_at"),
        Index("ix_submissions_question_version_id", "question_version_id"),
        Index("ix_submissions_user_question_attempt", "user_id", "question_version_id"),
        CheckConstraint(
            "passed_test_count IS NULL OR passed_test_count >= 0",
            name="ck_submission_passed_nonnegative",
        ),
        CheckConstraint(
            "total_test_count IS NULL OR total_test_count >= 0",
            name="ck_submission_total_nonnegative",
        ),
        CheckConstraint(
            "passed_test_count IS NULL OR total_test_count IS NULL "
            "OR passed_test_count <= total_test_count",
            name="ck_submission_passed_not_greater_than_total",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # Deliberately duplicated from the assignment to preserve the exact challenge snapshot.
    question_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_versions.id", ondelete="RESTRICT"), nullable=False
    )
    daily_assignment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("daily_assignments.id", ondelete="SET NULL")
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[ProgrammingLanguage] = mapped_column(
        database_enum(ProgrammingLanguage, "programming_language"), nullable=False
    )
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        database_enum(SubmissionStatus, "submission_status"),
        nullable=False,
        server_default=SubmissionStatus.QUEUED.value,
    )
    test_results: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    passed_test_count: Mapped[int | None] = mapped_column(Integer)
    total_test_count: Mapped[int | None] = mapped_column(Integer)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="submissions")
    question_version: Mapped[QuestionVersion] = relationship(back_populates="submissions")
    daily_assignment: Mapped[DailyAssignment | None] = relationship(back_populates="submissions")
    xp_transactions: Mapped[list[XPTransaction]] = relationship(back_populates="submission")
    streak_days: Mapped[list[StreakDay]] = relationship(back_populates="submission")
    badges: Mapped[list[UserBadge]] = relationship(back_populates="source_submission")
    daily_attempt: Mapped[DailyAttempt | None] = relationship(back_populates="source_submission")


class DailyAttempt(UUIDPrimaryKey, Timestamped, Base):
    """Server-owned learning outcome for a user and one daily assignment.

    This record makes the no-XP quit path and the solve path mutually
    exclusive, while leaving the historical assignment/version untouched.
    """

    __tablename__ = "daily_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "daily_assignment_id", name="uq_daily_attempt_user_assignment"),
        UniqueConstraint("source_submission_id", name="uq_daily_attempt_source_submission"),
        CheckConstraint("xp_awarded >= 0", name="ck_daily_attempt_xp_nonnegative"),
        Index("ix_daily_attempts_user_status", "user_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    daily_assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("daily_assignments.id", ondelete="RESTRICT"), nullable=False
    )
    source_submission_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="SET NULL")
    )
    status: Mapped[DailyAttemptStatus] = mapped_column(
        database_enum(DailyAttemptStatus, "daily_attempt_status"),
        nullable=False,
        server_default=DailyAttemptStatus.IN_PROGRESS.value,
    )
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    xp_awarded: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    streak_counted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    walkthrough_unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="daily_attempts")
    daily_assignment: Mapped[DailyAssignment] = relationship(back_populates="attempts")
    source_submission: Mapped[Submission | None] = relationship(back_populates="daily_attempt")


class XPTransaction(UUIDPrimaryKey, Base):
    """Append-only XP ledger. PostgreSQL rejects UPDATE and DELETE operations."""

    __tablename__ = "xp_transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "award_key", name="uq_xp_transaction_award"),
        Index("ix_xp_transactions_user_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    submission_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="RESTRICT")
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[XPReason] = mapped_column(database_enum(XPReason, "xp_reason"), nullable=False)
    award_key: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="xp_transactions")
    submission: Mapped[Submission | None] = relationship(back_populates="xp_transactions")


class Streak(UUIDPrimaryKey, Base):
    __tablename__ = "streaks"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_streak_user"),
        CheckConstraint("current_streak >= 0", name="ck_streak_current_nonnegative"),
        CheckConstraint("longest_streak >= 0", name="ck_streak_longest_nonnegative"),
        CheckConstraint(
            "longest_streak >= current_streak", name="ck_streak_longest_at_least_current"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # These values are server-calculated after a successful daily submission.
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_solved_date: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="streak")


class HintUse(UUIDPrimaryKey, Base):
    """Immutable record that a learner chose to reveal a particular daily hint."""

    __tablename__ = "hint_uses"
    __table_args__ = (
        UniqueConstraint("user_id", "daily_assignment_id", "question_hint_id", name="uq_hint_use"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    daily_assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("daily_assignments.id", ondelete="RESTRICT"), nullable=False
    )
    question_hint_id: Mapped[UUID] = mapped_column(
        ForeignKey("question_hints.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    daily_assignment: Mapped[DailyAssignment] = relationship(back_populates="hint_uses")
    hint: Mapped[QuestionHint] = relationship(back_populates="uses")


class UserTopicProgress(UUIDPrimaryKey, Base):
    """Server-derived, per-topic view of the immutable XP ledger."""

    __tablename__ = "user_topic_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_user_topic_progress"),
        CheckConstraint("solved_count >= 0", name="ck_topic_progress_solved_nonnegative"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    solved_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    xp: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="topic_progress")


class StreakDay(UUIDPrimaryKey, Base):
    """One auditable calendar cell per user. Shielded days remain visible history."""

    __tablename__ = "streak_days"
    __table_args__ = (UniqueConstraint("user_id", "solved_date", name="uq_streak_day"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    solved_date: Mapped[date] = mapped_column(Date, nullable=False)
    submission_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="RESTRICT")
    )
    is_shielded: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="streak_days")
    submission: Mapped[Submission | None] = relationship(back_populates="streak_days")


class StreakShield(UUIDPrimaryKey, Base):
    """A small, server-managed inventory. It never accepts a client supplied count."""

    __tablename__ = "streak_shields"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_streak_shield_user"),
        CheckConstraint("available BETWEEN 0 AND 2", name="ck_streak_shield_inventory_range"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    available: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    last_refilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="streak_shield")
    transactions: Mapped[list[StreakShieldTransaction]] = relationship(back_populates="shield")


class StreakShieldTransaction(UUIDPrimaryKey, Base):
    """Append-only audit events for shield grants and consumption."""

    __tablename__ = "streak_shield_transactions"
    __table_args__ = (UniqueConstraint("user_id", "event_key", name="uq_shield_transaction_event"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    shield_id: Mapped[UUID] = mapped_column(
        ForeignKey("streak_shields.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    event_key: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    shield: Mapped[StreakShield] = relationship(back_populates="transactions")


class Badge(UUIDPrimaryKey, Base):
    __tablename__ = "badges"

    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    icon: Mapped[str] = mapped_column(String(24), nullable=False)
    criteria_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    awards: Mapped[list[UserBadge]] = relationship(back_populates="badge")


class UserBadge(UUIDPrimaryKey, Base):
    """An award row is both the showcase source and the idempotent audit record."""

    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    badge_id: Mapped[UUID] = mapped_column(
        ForeignKey("badges.id", ondelete="RESTRICT"), nullable=False
    )
    source_submission_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="RESTRICT")
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="badges")
    badge: Mapped[Badge] = relationship(back_populates="awards")
    source_submission: Mapped[Submission | None] = relationship(back_populates="badges")


class CommunityChallenge(UUIDPrimaryKey, Timestamped, Base):
    """An admin-authored programme made of scheduled learning tasks.

    Tasks use a one-based offset from a learner's join date.  That single
    representation supports daily, weekends-only, alternating-day and custom
    plans without making a learner's historical schedule mutable.
    """

    __tablename__ = "community_challenges"
    __table_args__ = (
        CheckConstraint("duration_days >= 1", name="ck_community_challenge_duration_positive"),
        CheckConstraint(
            "completion_deadline_days >= 1",
            name="ck_community_challenge_deadline_positive",
        ),
        Index("ix_community_challenges_status_created", "status", "created_at"),
    )

    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    description_markdown: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CommunityChallengeStatus] = mapped_column(
        database_enum(CommunityChallengeStatus, "community_challenge_status"),
        nullable=False,
        server_default=CommunityChallengeStatus.DRAFT.value,
    )
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_deadline_days: Mapped[int] = mapped_column(Integer, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    created_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_by: Mapped[User | None] = relationship(
        back_populates="community_challenges_created", foreign_keys=[created_by_id]
    )
    tasks: Mapped[list[CommunityChallengeTask]] = relationship(
        back_populates="challenge",
        cascade="all, delete-orphan",
        order_by="CommunityChallengeTask.position",
    )
    enrollments: Mapped[list[CommunityEnrollment]] = relationship(back_populates="challenge")


class CommunityChallengeTask(UUIDPrimaryKey, Timestamped, Base):
    """A problem or learning asset made available on one programme day."""

    __tablename__ = "community_challenge_tasks"
    __table_args__ = (
        UniqueConstraint("challenge_id", "position", name="uq_community_challenge_task_position"),
        CheckConstraint("position > 0", name="ck_community_task_position_positive"),
        CheckConstraint("day_offset > 0", name="ck_community_task_day_offset_positive"),
        Index("ix_community_tasks_challenge_day", "challenge_id", "day_offset"),
    )

    challenge_id: Mapped[UUID] = mapped_column(
        ForeignKey("community_challenges.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # Day one is the join date; multiple tasks can share a day.
    day_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[CommunityTaskKind] = mapped_column(
        database_enum(CommunityTaskKind, "community_task_kind"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    instructions_markdown: Mapped[str | None] = mapped_column(Text)
    question_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("question_versions.id", ondelete="RESTRICT")
    )
    video_url: Mapped[str | None] = mapped_column(String(500))
    resource_url: Mapped[str | None] = mapped_column(String(500))
    asset_urls: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    summary_markdown: Mapped[str | None] = mapped_column(Text)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    challenge: Mapped[CommunityChallenge] = relationship(back_populates="tasks")
    question_version: Mapped[QuestionVersion | None] = relationship(
        back_populates="community_challenge_tasks"
    )
    progress_records: Mapped[list[CommunityTaskProgress]] = relationship(back_populates="task")


class CommunityEnrollment(UUIDPrimaryKey, Timestamped, Base):
    """A user-owned immutable schedule snapshot for a joined programme."""

    __tablename__ = "community_enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", name="uq_community_enrollment_user_challenge"),
        # PostgreSQL, rather than UI state, guarantees one active programme per learner.
        Index(
            "uq_community_active_enrollment_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_community_enrollments_challenge_status", "challenge_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    challenge_id: Mapped[UUID] = mapped_column(
        ForeignKey("community_challenges.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[CommunityEnrollmentStatus] = mapped_column(
        database_enum(CommunityEnrollmentStatus, "community_enrollment_status"),
        nullable=False,
        server_default=CommunityEnrollmentStatus.ACTIVE.value,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    forgone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="community_enrollments")
    challenge: Mapped[CommunityChallenge] = relationship(back_populates="enrollments")
    task_progress: Mapped[list[CommunityTaskProgress]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan"
    )


class CommunityTaskProgress(UUIDPrimaryKey, Base):
    """Server-side completion evidence for an enrolled task."""

    __tablename__ = "community_task_progress"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "task_id", name="uq_community_task_progress"),
        Index("ix_community_task_progress_enrollment", "enrollment_id"),
    )

    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("community_enrollments.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("community_challenge_tasks.id", ondelete="RESTRICT"), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completion_note: Mapped[str | None] = mapped_column(Text)

    enrollment: Mapped[CommunityEnrollment] = relationship(back_populates="task_progress")
    task: Mapped[CommunityChallengeTask] = relationship(back_populates="progress_records")


class CommunityDiscussion(UUIDPrimaryKey, Timestamped, Base):
    """A question posted by the community; replies form its conversation tree."""

    __tablename__ = "community_discussions"
    __table_args__ = (
        Index("ix_community_discussions_created", "created_at"),
        Index("ix_community_discussions_author_created", "author_id", "created_at"),
    )

    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    author: Mapped[User] = relationship(back_populates="community_discussions")
    replies: Mapped[list[CommunityDiscussionReply]] = relationship(
        back_populates="discussion",
        cascade="all, delete-orphan",
        order_by="CommunityDiscussionReply.created_at",
    )


class CommunityDiscussionReply(UUIDPrimaryKey, Timestamped, Base):
    """A threaded response. Mentor attribution is calculated from the author's role."""

    __tablename__ = "community_discussion_replies"
    __table_args__ = (
        Index("ix_community_replies_discussion_created", "discussion_id", "created_at"),
        Index("ix_community_replies_parent", "parent_reply_id"),
    )

    discussion_id: Mapped[UUID] = mapped_column(
        ForeignKey("community_discussions.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    parent_reply_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("community_discussion_replies.id", ondelete="CASCADE")
    )
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    is_accepted_answer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    discussion: Mapped[CommunityDiscussion] = relationship(back_populates="replies")
    author: Mapped[User] = relationship(back_populates="community_discussion_replies")
    parent: Mapped[CommunityDiscussionReply | None] = relationship(
        remote_side="CommunityDiscussionReply.id", back_populates="children"
    )
    children: Mapped[list[CommunityDiscussionReply]] = relationship(back_populates="parent")


class Friendship(UUIDPrimaryKey, Timestamped, Base):
    """A canonical user pair: one pending/accepted row represents one relationship."""

    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("first_user_id", "second_user_id", name="uq_friendship_pair"),
        CheckConstraint("first_user_id <> second_user_id", name="ck_friendship_distinct_users"),
        CheckConstraint("status IN ('pending', 'accepted')", name="ck_friendship_status"),
        Index("ix_friendships_first_status", "first_user_id", "status"),
        Index("ix_friendships_second_status", "second_user_id", "status"),
    )

    first_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    second_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    requested_by_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModerationReport(UUIDPrimaryKey, Base):
    """A user-filed report that moves through an admin-owned review queue."""

    __tablename__ = "moderation_reports"
    __table_args__ = (
        CheckConstraint("reporter_id <> target_user_id", name="ck_report_distinct_users"),
        CheckConstraint(
            "status IN ('open', 'reviewing', 'resolved', 'dismissed')",
            name="ck_moderation_report_status",
        ),
        Index("ix_moderation_reports_status_created", "status", "created_at"),
        Index("ix_moderation_reports_target_created", "target_user_id", "created_at"),
    )

    reporter_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    target_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="open")
    resolution_note: Mapped[str | None] = mapped_column(Text)
    handled_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    reporter: Mapped[User] = relationship(
        back_populates="filed_moderation_reports", foreign_keys=[reporter_id]
    )
    target_user: Mapped[User] = relationship(
        back_populates="received_moderation_reports", foreign_keys=[target_user_id]
    )
    handled_by: Mapped[User | None] = relationship(
        back_populates="handled_moderation_reports", foreign_keys=[handled_by_id]
    )


class AdminAuditLog(UUIDPrimaryKey, Base):
    """Append-only trace of sensitive admin operations; the DB blocks mutations."""

    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        Index("ix_admin_audit_logs_created_at", "created_at"),
        Index("ix_admin_audit_logs_actor_created", "actor_user_id", "created_at"),
        Index("ix_admin_audit_logs_action_created", "action", "created_at"),
        Index("ix_admin_audit_logs_target", "target_type", "target_id"),
    )

    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    actor: Mapped[User] = relationship(back_populates="admin_audit_logs")
