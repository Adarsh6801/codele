"""Derive topic mastery and relevant future daily challenges from history."""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    DailyAssignment,
    QuestionVersion,
    QuestionVersionStatus,
    Submission,
    SubmissionStatus,
    User,
)
from app.gamification.service import server_today


def topic_mastery(db: Session, user: User) -> list[dict]:
    rows = db.execute(
        select(
            QuestionVersion.topic,
            func.count(Submission.id).label("attempts"),
            func.coalesce(
                func.sum(case((Submission.status == SubmissionStatus.PASSED, 1), else_=0)), 0
            ).label("solved"),
        )
        .join(QuestionVersion, QuestionVersion.id == Submission.question_version_id)
        .where(Submission.user_id == user.id)
        .group_by(QuestionVersion.topic)
    )
    results = []
    for row in rows:
        attempts, solved = int(row.attempts), int(row.solved)
        pass_rate = solved / attempts if attempts else 0
        repetition = min(solved / 5, 1)
        # 70% verified success and 30% repeated practice, bounded to 0..100.
        results.append(
            {
                "topic": row.topic,
                "attempts": attempts,
                "solved": solved,
                "mastery_score": round((pass_rate * 0.7 + repetition * 0.3) * 100),
            }
        )
    return sorted(results, key=lambda item: (item["mastery_score"], item["topic"].lower()))


def recommendations(db: Session, user: User) -> dict:
    mastery = topic_mastery(db, user)
    by_topic = {item["topic"]: item for item in mastery}
    weak = [item for item in mastery if item["mastery_score"] < 70][:3]
    passed_versions = select(Submission.question_version_id).where(
        Submission.user_id == user.id, Submission.status == SubmissionStatus.PASSED
    )
    candidates = list(
        db.execute(
            select(DailyAssignment, QuestionVersion)
            .join(QuestionVersion, QuestionVersion.id == DailyAssignment.question_version_id)
            .where(
                DailyAssignment.assignment_date >= server_today(),
                DailyAssignment.level == user.level,
                DailyAssignment.legacy_language.is_(None),
                QuestionVersion.status.in_(
                    {QuestionVersionStatus.READY, QuestionVersionStatus.PUBLISHED}
                ),
                QuestionVersion.id.not_in(passed_versions),
            )
            .order_by(DailyAssignment.assignment_date, QuestionVersion.difficulty)
            .limit(50)
        )
    )
    candidates.sort(
        key=lambda row: (
            by_topic.get(row[1].topic, {"mastery_score": 0})["mastery_score"],
            row[0].assignment_date,
            row[1].difficulty,
            row[1].title.lower(),
        )
    )
    items = []
    for assignment, version in candidates[:3]:
        score = by_topic.get(version.topic, {"mastery_score": 0})["mastery_score"]
        reason = (
            f"Build confidence in {version.topic} ({score}% mastery)."
            if version.topic in by_topic
            else f"Explore {version.topic}, a topic you have not practised yet."
        )
        items.append(
            {
                "assignment_id": assignment.id,
                "assignment_date": assignment.assignment_date,
                "question_version_id": version.id,
                "title": version.title,
                "topic": version.topic,
                "difficulty": version.difficulty,
                "reason": reason,
            }
        )
    return {"weak_topics": weak, "topic_mastery": mastery, "recommendations": items}
