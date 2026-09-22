"""Idempotent server-side rewards for qualifying daily submissions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.db.models import (
    Badge,
    DailyAttempt,
    DailyAttemptStatus,
    HintUse,
    NotificationType,
    Streak,
    StreakDay,
    StreakShield,
    StreakShieldTransaction,
    Submission,
    User,
    UserBadge,
    UserTopicProgress,
    XPReason,
    XPTransaction,
)
from app.notifications.service import create_notification

DAILY_SOLVE_XP = 20
FIRST_ATTEMPT_XP = 10
NO_HINT_XP = 5
SHIELD_CAP = 2
SHIELD_REFILL_MILESTONES = {7, 30, 100}
STREAK_MILESTONES = (3, 7, 14, 30, 50, 100, 365)

BADGE_CATALOG = (
    ("first_solve", "First Commit", "Complete your first daily challenge.", "⌘", {"solves": 1}),
    (
        "topic_specialist",
        "Topic Specialist",
        "Solve five daily challenges in one topic.",
        "◎",
        {"topic_solves": 5},
    ),
    *(
        (
            f"streak_{days}",
            f"{days}-Day Streak",
            f"Keep your daily practice alive for {days} days.",
            "🔥",
            {"streak_days": days},
        )
        for days in STREAK_MILESTONES
    ),
)


def server_today():
    """The only timezone used for daily-completion and streak policy."""
    return datetime.now(ZoneInfo(get_settings().streak_timezone)).date()


def xp_level_info(xp: int) -> tuple[int, str, int, int]:
    """Return level number, title, XP into the level, and XP needed next.

    Level requirements grow gently (100, 200, 300...) and are always derived
    from the immutable ledger total.
    """
    safe_xp = max(0, xp)
    level = 1
    spent = 0
    while safe_xp >= spent + level * 100:
        spent += level * 100
        level += 1
    titles = ("Explorer", "Builder", "Solver", "Architect", "Legend")
    title = titles[min((level - 1) // 5, len(titles) - 1)]
    return level, title, safe_xp - spent, level * 100


def ensure_badge_catalog(db: Session) -> None:
    """Keep the catalog deploy-safe; inserts are idempotent across workers."""
    for code, name, description, icon, criteria in BADGE_CATALOG:
        db.execute(
            insert(Badge)
            .values(
                code=code, name=name, description=description, icon=icon, criteria_json=criteria
            )
            .on_conflict_do_nothing(index_elements=[Badge.code])
        )


def _record_xp(
    db: Session,
    submission: Submission,
    amount: int,
    reason: XPReason,
    award_key: str,
    metadata: dict,
) -> bool:
    result = db.execute(
        insert(XPTransaction)
        .values(
            user_id=submission.user_id,
            submission_id=submission.id,
            amount=amount,
            reason=reason,
            award_key=award_key,
            metadata_json=metadata,
        )
        .on_conflict_do_nothing(index_elements=[XPTransaction.user_id, XPTransaction.award_key])
    )
    return bool(result.rowcount)


def _award_badge(
    db: Session, user_id, code: str, submission_id, metadata: dict | None = None
) -> bool:
    badge_id = db.scalar(select(Badge.id).where(Badge.code == code))
    if badge_id is None:
        return False
    result = db.execute(
        insert(UserBadge)
        .values(
            user_id=user_id,
            badge_id=badge_id,
            source_submission_id=submission_id,
            metadata_json=metadata or {},
        )
        .on_conflict_do_nothing(index_elements=[UserBadge.user_id, UserBadge.badge_id])
    )
    return bool(result.rowcount)


def _notify_badge_award(db: Session, submission: Submission, code: str) -> UUID | None:
    badge = next((item for item in BADGE_CATALOG if item[0] == code), None)
    if badge is None:
        return None
    _, name, description, _, _ = badge
    return create_notification(
        db,
        user_id=submission.user_id,
        notification_type=NotificationType.ACHIEVEMENT,
        title=f"Badge earned: {name}",
        body=description,
        link="/settings",
        event_key=f"badge-award:{submission.user_id}:{code}",
    )


def ensure_daily_attempt(db: Session, user_id: UUID, assignment_id: UUID) -> DailyAttempt:
    """Return the single server-owned attempt row for a daily challenge."""
    attempt = db.scalar(
        select(DailyAttempt)
        .where(
            DailyAttempt.user_id == user_id,
            DailyAttempt.daily_assignment_id == assignment_id,
        )
        .with_for_update()
    )
    if attempt is None:
        attempt = DailyAttempt(user_id=user_id, daily_assignment_id=assignment_id)
        db.add(attempt)
        db.flush()
    return attempt


def quit_daily_attempt(db: Session, user_id: UUID, assignment_id: UUID) -> DailyAttempt:
    """Unlock learning after an explicit give-up, without adding XP.

    A quit is idempotent. It does count as the user's one daily completion for
    streak purposes, as defined by the learning policy.
    """
    attempt = ensure_daily_attempt(db, user_id, assignment_id)
    if attempt.status == DailyAttemptStatus.SOLVED:
        return attempt
    if attempt.status != DailyAttemptStatus.QUIT:
        now = datetime.now(UTC)
        attempt.status = DailyAttemptStatus.QUIT
        attempt.quit_at = now
        attempt.xp_awarded = 0
        attempt.walkthrough_unlocked_at = now
    if not attempt.streak_counted:
        _streak_for_completion(db, user_id)
        attempt.streak_counted = True
    return attempt


def _streak_for_completion(
    db: Session, user_id: UUID, submission_id: UUID | None = None
) -> Streak:
    """Advance once per server day without silently protecting a missed day."""
    today = server_today()
    streak = db.scalar(select(Streak).where(Streak.user_id == user_id).with_for_update())
    if streak is None:
        streak = Streak(user_id=user_id)
        db.add(streak)
        db.flush()
    already_completed = db.scalar(
        select(StreakDay.id).where(
            StreakDay.user_id == user_id, StreakDay.solved_date == today
        )
    )
    if already_completed is not None:
        return streak

    shield = db.scalar(
        select(StreakShield).where(StreakShield.user_id == user_id).with_for_update()
    )
    if shield is None:
        shield = StreakShield(user_id=user_id, available=1)
        db.add(shield)
        db.flush()
        db.add(
            StreakShieldTransaction(
                user_id=user_id,
                shield_id=shield.id,
                amount=1,
                reason="starter_grant",
                event_key=f"starter-shield:{user_id}",
                metadata_json={"cap": SHIELD_CAP},
            )
        )

    if streak.last_solved_date is None:
        next_streak = 1
    else:
        gap = (today - streak.last_solved_date).days
        if gap <= 0:
            return streak
        if gap == 1:
            next_streak = streak.current_streak + 1
        else:
            # A shield must be deliberately used by a learner in a future
            # shield flow. It is never consumed automatically merely because
            # a submission arrives after a missed server date.
            next_streak = 1

    db.add(StreakDay(user_id=user_id, solved_date=today, submission_id=submission_id))
    streak.current_streak = next_streak
    streak.longest_streak = max(streak.longest_streak, next_streak)
    streak.last_solved_date = today

    # A shield only refills at selected milestones, is capped at two, and can
    # never refill more than once in seven server days.
    can_refill = (
        next_streak in SHIELD_REFILL_MILESTONES
        and shield.available < SHIELD_CAP
        and (
            shield.last_refilled_at is None
            or datetime.now(UTC) - shield.last_refilled_at >= timedelta(days=7)
        )
    )
    if can_refill:
        shield.available += 1
        shield.last_refilled_at = datetime.now(UTC)
        db.add(
            StreakShieldTransaction(
                user_id=user_id,
                shield_id=shield.id,
                amount=1,
                reason="milestone_refill",
                event_key=f"shield-refill:{user_id}:{next_streak}",
                metadata_json={"streak": next_streak, "cap": SHIELD_CAP},
            )
        )
    return streak


def _update_topic_progress(db: Session, submission: Submission, topic: str, xp: int) -> int:
    db.execute(
        insert(UserTopicProgress)
        .values(
            user_id=submission.user_id,
            topic=topic,
            solved_count=1,
            xp=xp,
            last_solved_at=datetime.now(UTC),
        )
        .on_conflict_do_update(
            constraint="uq_user_topic_progress",
            set_={
                "solved_count": UserTopicProgress.solved_count + 1,
                "xp": UserTopicProgress.xp + xp,
                "last_solved_at": datetime.now(UTC),
            },
        )
    )
    return (
        db.scalar(
            select(UserTopicProgress.solved_count).where(
                UserTopicProgress.user_id == submission.user_id, UserTopicProgress.topic == topic
            )
        )
        or 0
    )


def reward_submission(db: Session, submission: Submission) -> list[UUID]:
    """Award a passed *today* daily submission, safely even if replayed.

    A direct submission or an old schedule is still evaluated, but cannot
    fabricate current progress. The daily solve award key gates all derived
    rewards and topic aggregation.
    """
    assignment = submission.daily_assignment
    if assignment is None or assignment.assignment_date != server_today():
        return []
    attempt = ensure_daily_attempt(db, submission.user_id, assignment.id)
    # A learner may still experiment after choosing to reveal the solution, but
    # that later passing submission must never retroactively award XP or a
    # second streak day.
    if attempt.status in {DailyAttemptStatus.QUIT, DailyAttemptStatus.SOLVED}:
        return []
    notification_ids: list[UUID] = []
    ensure_badge_catalog(db)
    base_key = f"daily-solve:{submission.user_id}:{assignment.id}"
    base_added = _record_xp(
        db,
        submission,
        DAILY_SOLVE_XP,
        XPReason.DAILY_SOLVE,
        base_key,
        {
            "assignment_id": str(assignment.id),
            "question_version_id": str(submission.question_version_id),
        },
    )
    if not base_added:
        return notification_ids

    now = datetime.now(UTC)
    attempt.status = DailyAttemptStatus.SOLVED
    attempt.source_submission_id = submission.id
    attempt.solved_at = now
    attempt.xp_awarded = DAILY_SOLVE_XP
    attempt.walkthrough_unlocked_at = now

    topic = submission.question_version.topic
    topic_solves = _update_topic_progress(db, submission, topic, DAILY_SOLVE_XP)
    if submission.attempt_number == 1:
        _record_xp(
            db,
            submission,
            FIRST_ATTEMPT_XP,
            XPReason.FIRST_ATTEMPT_BONUS,
            f"first-attempt:{submission.user_id}:{assignment.id}",
            {"assignment_id": str(assignment.id)},
        )
    used_hint = db.scalar(
        select(HintUse.id).where(
            HintUse.user_id == submission.user_id, HintUse.daily_assignment_id == assignment.id
        )
    )
    if used_hint is None:
        _record_xp(
            db,
            submission,
            NO_HINT_XP,
            XPReason.NO_HINT_BONUS,
            f"no-hint:{submission.user_id}:{assignment.id}",
            {"assignment_id": str(assignment.id)},
        )

    streak = _streak_for_completion(db, submission.user_id, submission.id)
    attempt.streak_counted = True
    if _award_badge(db, submission.user_id, "first_solve", submission.id):
        notification_id = _notify_badge_award(db, submission, "first_solve")
        if notification_id is not None:
            notification_ids.append(notification_id)
    if topic_solves >= 5:
        if _award_badge(
            db, submission.user_id, "topic_specialist", submission.id, {"topic": topic}
        ):
            notification_id = _notify_badge_award(db, submission, "topic_specialist")
            if notification_id is not None:
                notification_ids.append(notification_id)
    for days in STREAK_MILESTONES:
        if streak.current_streak >= days:
            if not _award_badge(
                db,
                submission.user_id,
                f"streak_{days}",
                submission.id,
                {"streak": streak.current_streak},
            ):
                continue
            notification_id = _notify_badge_award(db, submission, f"streak_{days}")
            if notification_id is not None:
                notification_ids.append(notification_id)
    return notification_ids


def progress_data(db: Session, user: User, calendar_days: int = 35) -> dict:
    """Build a server-derived gamification read model for dashboard and profile."""
    ensure_badge_catalog(db)
    xp = (
        db.scalar(
            select(func.coalesce(func.sum(XPTransaction.amount), 0)).where(
                XPTransaction.user_id == user.id
            )
        )
        or 0
    )
    level, level_name, xp_in_level, xp_for_next = xp_level_info(xp)
    streak = db.scalar(select(Streak).where(Streak.user_id == user.id))
    shield = db.scalar(select(StreakShield).where(StreakShield.user_id == user.id))
    today = server_today()
    active_streak = 0
    if streak and streak.last_solved_date:
        days_since_last_solve = (today - streak.last_solved_date).days
        # A current streak remains alive through the day after the last
        # completion. Once a full server day is missed, show zero immediately
        # instead of showing a stale persisted number until the next solve.
        if 0 <= days_since_last_solve <= 1:
            active_streak = streak.current_streak
    start = today - timedelta(days=calendar_days - 1)
    days = list(
        db.scalars(
            select(StreakDay)
            .where(StreakDay.user_id == user.id, StreakDay.solved_date >= start)
            .order_by(StreakDay.solved_date)
        )
    )
    topics = list(
        db.scalars(
            select(UserTopicProgress)
            .where(UserTopicProgress.user_id == user.id)
            .order_by(UserTopicProgress.xp.desc(), UserTopicProgress.topic)
        )
    )
    awards = list(
        db.scalars(
            select(UserBadge)
            .where(UserBadge.user_id == user.id)
            .options(joinedload(UserBadge.badge))
            .order_by(UserBadge.awarded_at.desc())
        )
    )
    return {
        "xp": int(xp),
        "xp_level": level,
        "xp_level_name": level_name,
        "xp_in_level": xp_in_level,
        "xp_for_next_level": xp_for_next,
        "current_streak": active_streak,
        "longest_streak": streak.longest_streak if streak else 0,
        "last_solved_date": streak.last_solved_date if streak else None,
        "server_timezone": get_settings().streak_timezone,
        "shield_available": shield.available if shield else 1,
        "shield_cap": SHIELD_CAP,
        "topic_progress": [
            {
                "topic": row.topic,
                "solved_count": row.solved_count,
                "xp": row.xp,
                "last_solved_at": row.last_solved_at,
            }
            for row in topics
        ],
        "streak_calendar": [
            {"date": row.solved_date, "is_shielded": row.is_shielded} for row in days
        ],
        "badges": [
            {
                "code": award.badge.code,
                "name": award.badge.name,
                "description": award.badge.description,
                "icon": award.badge.icon,
                "awarded_at": award.awarded_at,
            }
            for award in awards
        ],
    }
