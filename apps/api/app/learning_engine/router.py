from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.db.models import (
    DailyAssignment,
    DailyAttempt,
    DailyAttemptStatus,
    HintUse,
    ProgrammingLanguage,
    Submission,
    SubmissionStatus,
    User,
)
from app.db.session import get_db
from app.learning.schemas import PostSolveLearningResponse, RecommendationsResponse
from app.learning_engine.service import recommendations

router = APIRouter(tags=["learning engine"])


def learning_response(
    *,
    submission: Submission | None,
    assignment: DailyAssignment,
    attempt: DailyAttempt | None,
    language: ProgrammingLanguage,
    hints_revealed: int,
) -> PostSolveLearningResponse:
    """Build an unlocked bilingual learning path from an immutable version."""
    version = assignment.question_version
    unlocked_at = (
        attempt.walkthrough_unlocked_at
        if attempt and attempt.walkthrough_unlocked_at is not None
        else (
            submission.evaluated_at
            if submission and submission.evaluated_at
            else datetime.now(UTC)
        )
    )
    return PostSolveLearningResponse(
        submission_id=submission.id if submission else None,
        assignment_id=assignment.id,
        attempt_status=attempt.status if attempt else DailyAttemptStatus.SOLVED,
        walkthrough_unlocked_at=unlocked_at,
        title=version.title,
        topic=version.topic,
        explanation_en=version.explanation_en
        or version.explanation_markdown
        or "Learning explanation is being prepared.",
        explanation_ml=version.explanation_ml
        or "മലയാളം വിശദീകരണം തയ്യാറാക്കിക്കൊണ്ടിരിക്കുന്നു.",
        complexity_notes=version.complexity_notes or "Complexity notes are being prepared.",
        reference_solution=version.solution_code.get(language.value),
        solution_trace=version.solution_trace or [],
        solution_notes_en=version.solution_notes_en or [],
        solution_notes_ml=version.solution_notes_ml or [],
        solution_video_url=version.solution_video_url,
        solution_image_urls=version.solution_image_urls or [],
        alternative_approaches=version.alternative_approaches,
        hints_revealed=hints_revealed,
    )


@router.get("/submissions/{submission_id}/learning", response_model=PostSolveLearningResponse)
def post_solve_learning(
    submission_id: UUID,
    language: ProgrammingLanguage = ProgrammingLanguage.PYTHON,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostSolveLearningResponse:
    submission = db.scalar(
        select(Submission)
        .where(Submission.id == submission_id, Submission.user_id == current_user.id)
        .options(
            joinedload(Submission.question_version),
            joinedload(Submission.daily_assignment).joinedload(DailyAssignment.question_version),
        )
    )
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != SubmissionStatus.PASSED:
        raise HTTPException(status_code=409, detail="Learning unlocks after a passed submission")

    assignment = submission.daily_assignment
    attempt: DailyAttempt | None = None
    hints_revealed = 0
    if assignment is not None:
        attempt = db.scalar(
            select(DailyAttempt).where(
                DailyAttempt.user_id == current_user.id,
                DailyAttempt.daily_assignment_id == assignment.id,
            )
        )
        if attempt is not None and attempt.status != DailyAttemptStatus.SOLVED:
            raise HTTPException(
                status_code=409, detail="Learning has not been unlocked for this attempt"
            )
        hints_revealed = int(
            db.scalar(
                select(func.count(HintUse.id)).where(
                    HintUse.user_id == current_user.id,
                    HintUse.daily_assignment_id == assignment.id,
                )
            )
            or 0
        )
    else:
        # Preserve post-solve review for a non-daily historical submission.
        assignment = DailyAssignment(
            question_version=submission.question_version,
            level=submission.question_version.level,
            assignment_date=submission.created_at.date(),
        )

    return learning_response(
        submission=submission,
        assignment=assignment,
        attempt=attempt,
        language=language,
        hints_revealed=hints_revealed,
    )


@router.get(
    "/daily-assignments/{assignment_id}/learning", response_model=PostSolveLearningResponse
)
def unlocked_daily_learning(
    assignment_id: UUID,
    language: ProgrammingLanguage = ProgrammingLanguage.PYTHON,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostSolveLearningResponse:
    assignment = db.scalar(
        select(DailyAssignment)
        .where(DailyAssignment.id == assignment_id)
        .options(joinedload(DailyAssignment.question_version))
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Daily assignment not found")
    attempt = db.scalar(
        select(DailyAttempt).where(
            DailyAttempt.user_id == current_user.id,
            DailyAttempt.daily_assignment_id == assignment.id,
        )
    )
    if attempt is None or attempt.status not in {
        DailyAttemptStatus.SOLVED,
        DailyAttemptStatus.QUIT,
    }:
        raise HTTPException(status_code=409, detail="Solve or give up to unlock the walkthrough")
    hints_revealed = int(
        db.scalar(
            select(func.count(HintUse.id)).where(
                HintUse.user_id == current_user.id,
                HintUse.daily_assignment_id == assignment.id,
            )
        )
        or 0
    )
    return learning_response(
        submission=attempt.source_submission,
        assignment=assignment,
        attempt=attempt,
        language=language,
        hints_revealed=hints_revealed,
    )


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationsResponse:
    return RecommendationsResponse(**recommendations(db, current_user))
