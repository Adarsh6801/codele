import base64
import binascii
import re
import subprocess
from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth.dependencies import get_current_user, require_admin
from app.config import get_settings
from app.db.models import (
    Category,
    DailyAssignment,
    DailyAttempt,
    DailyAttemptStatus,
    HintUse,
    Level,
    Question,
    QuestionHint,
    QuestionVersion,
    QuestionVersionStatus,
    Submission,
    SubmissionStatus,
    TestCase,
    TestVisibility,
    User,
)
from app.db.session import get_db
from app.execution.tasks import evaluate_submission, execute
from app.gamification.service import (
    ensure_daily_attempt,
    progress_data,
    quit_daily_attempt,
    server_today,
)
from app.learning.schemas import (
    AdminQuestionDetailResponse,
    AdminQuestionResponse,
    AdminSubmissionResponse,
    AssignmentResponse,
    CategoryInput,
    CategoryResponse,
    ChallengeResponse,
    CreateQuestionRequest,
    DailyAttemptResponse,
    ProgressResponse,
    PublicTestCaseResponse,
    QuestionListItemResponse,
    QuestionMediaUploadRequest,
    QuestionMediaUploadResponse,
    QuestionVersionInput,
    RevealedHintResponse,
    RunSampleRequest,
    SampleRunResponse,
    SampleTestResult,
    ScheduleAssignmentRequest,
    SchedulePreviewItemResponse,
    SubmissionHistoryPageResponse,
    SubmissionHistoryResponse,
    SubmissionResponse,
    SubmissionReviewQuestionResponse,
    SubmissionReviewResponse,
    SubmitRequest,
)
from app.learning.service import challenge_response, load_assignment_for_challenge

router = APIRouter(tags=["learning"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

QUESTION_IMAGE_DATA_URL = re.compile(r"^data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)$")
MAX_QUESTION_IMAGE_BYTES = 5 * 1024 * 1024


def save_question_media(image_data_url: str) -> str:
    """Persist an admin-authored image and return its learner-safe static URL."""

    match = QUESTION_IMAGE_DATA_URL.fullmatch(image_data_url)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload a PNG, JPEG, or WebP image.",
        )
    try:
        image_bytes = base64.b64decode(match.group(2), validate=True)
    except binascii.Error as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The image data is invalid.",
        ) from error
    if not image_bytes or len(image_bytes) > MAX_QUESTION_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Question images must be 5 MB or smaller.",
        )
    extension = {"png": "png", "jpeg": "jpg", "webp": "webp"}[match.group(1)]
    media_directory = get_settings().upload_dir / "question-media"
    media_directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    (media_directory / filename).write_bytes(image_bytes)
    return f"/uploads/question-media/{filename}"


def add_version(
    db: Session, question: Question, payload: QuestionVersionInput, author_id: UUID
) -> QuestionVersion:
    category = db.scalar(select(Category).where(Category.id == payload.category_id))
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Category not found"
        )
    version_number = max((version.version_number for version in question.versions), default=0) + 1
    version = QuestionVersion(
        question=question,
        version_number=version_number,
        title=payload.title,
        statement_markdown=payload.statement_markdown,
        examples=[example.model_dump() for example in payload.examples],
        constraints_markdown=payload.constraints_markdown,
        category_id=category.id,
        level=payload.level,
        topic=category.name,
        difficulty=payload.difficulty,
        starter_code=payload.starter_code,
        solution_code=payload.solution_code,
        explanation_markdown=payload.explanation_markdown,
        explanation_en=payload.explanation_en,
        explanation_ml=payload.explanation_ml,
        solution_trace=payload.solution_trace,
        solution_notes_en=payload.solution_notes_en,
        solution_notes_ml=payload.solution_notes_ml,
        solution_video_url=payload.solution_video_url,
        solution_image_urls=payload.solution_image_urls,
        complexity_notes=payload.complexity_notes,
        alternative_approaches=[
            approach.model_dump() for approach in payload.alternative_approaches
        ],
        created_by_id=author_id,
    )
    db.add(version)
    for test in payload.public_tests:
        db.add(
            TestCase(
                question_version=version,
                position=test.position,
                visibility=TestVisibility.PUBLIC,
                input_data=test.input_data,
                expected_output=test.expected_output,
                explanation=test.explanation,
            )
        )
    for test in payload.hidden_tests:
        db.add(
            TestCase(
                question_version=version,
                position=test.position,
                visibility=TestVisibility.HIDDEN,
                input_data=test.input_data,
                expected_output=test.expected_output,
                explanation=test.explanation,
            )
        )
    for hint in payload.hints:
        db.add(
            QuestionHint(
                question_version=version,
                position=hint.position,
                content_markdown=hint.content_markdown,
                xp_penalty=hint.xp_penalty,
            )
        )
    return version


def admin_question_detail(version: QuestionVersion) -> AdminQuestionDetailResponse:
    public_tests = sorted(
        (test for test in version.test_cases if test.visibility == TestVisibility.PUBLIC),
        key=lambda test: test.position,
    )
    hidden_tests = sorted(
        (test for test in version.test_cases if test.visibility == TestVisibility.HIDDEN),
        key=lambda test: test.position,
    )
    return AdminQuestionDetailResponse(
        question_id=version.question_id,
        question_version_id=version.id,
        slug=version.question.slug,
        title=version.title,
        status=version.status,
        difficulty=version.difficulty,
        category_id=version.category_id,
        topic=version.category.name,
        level=version.level,
        version_number=version.version_number,
        statement_markdown=version.statement_markdown,
        examples=version.examples,
        constraints_markdown=version.constraints_markdown,
        starter_code=version.starter_code,
        solution_code=version.solution_code,
        explanation_markdown=version.explanation_markdown,
        explanation_en=version.explanation_en,
        explanation_ml=version.explanation_ml,
        solution_trace=version.solution_trace,
        solution_notes_en=version.solution_notes_en,
        solution_notes_ml=version.solution_notes_ml,
        solution_video_url=version.solution_video_url,
        solution_image_urls=version.solution_image_urls,
        complexity_notes=version.complexity_notes,
        alternative_approaches=version.alternative_approaches,
        public_tests=[
            {
                "position": test.position,
                "input_data": test.input_data,
                "expected_output": test.expected_output,
                "explanation": test.explanation,
            }
            for test in public_tests
        ],
        hidden_tests=[
            {
                "position": test.position,
                "input_data": test.input_data,
                "expected_output": test.expected_output,
                "explanation": test.explanation,
            }
            for test in hidden_tests
        ],
        hints=[
            {
                "position": hint.position,
                "content_markdown": hint.content_markdown,
                "xp_penalty": hint.xp_penalty,
            }
            for hint in sorted(version.hints, key=lambda hint: hint.position)
        ],
    )


def validation_errors(version: QuestionVersion) -> list[str]:
    errors: list[str] = []
    if not any(test.visibility == TestVisibility.PUBLIC for test in version.test_cases):
        errors.append("at least one public test is required")
    if not any(test.visibility == TestVisibility.HIDDEN for test in version.test_cases):
        errors.append("at least one hidden test is required")
    if len(version.hints) != 3 or {hint.position for hint in version.hints} != {1, 2, 3}:
        errors.append("three numbered hints are required")
    if not version.solution_code:
        errors.append("a solution is required")
    if not version.explanation_en:
        errors.append("an English explanation is required")
    if not version.explanation_ml:
        errors.append("a Malayalam explanation is required")
    if not version.solution_trace:
        errors.append("a solution walkthrough trace is required")
    else:
        steps = [item.get("step") for item in version.solution_trace if isinstance(item, dict)]
        if (
            len(steps) != len(version.solution_trace)
            or any(not isinstance(step, int) or step < 1 for step in steps)
            or len(set(steps)) != len(steps)
        ):
            errors.append("the solution walkthrough trace cannot be rendered")
        elif any(
            not isinstance(item.get("array"), list)
            or not isinstance(item.get("cursor"), int)
            or item["cursor"] < 0
            or not isinstance(item.get("note_en"), str)
            or not item["note_en"].strip()
            or not isinstance(item.get("note_ml"), str)
            or not item["note_ml"].strip()
            for item in version.solution_trace
        ):
            errors.append(
                "each walkthrough step needs array, cursor, English note, and Malayalam note"
            )
    if not version.complexity_notes:
        errors.append("complexity notes are required")
    if not version.alternative_approaches:
        errors.append("at least one alternative approach is required")
    return errors


def load_admin_version(db: Session, version_id: UUID) -> QuestionVersion | None:
    return db.scalar(
        select(QuestionVersion)
        .where(QuestionVersion.id == version_id)
        .options(
            joinedload(QuestionVersion.question),
            joinedload(QuestionVersion.category),
            selectinload(QuestionVersion.test_cases),
            selectinload(QuestionVersion.hints),
        )
    )


def category_response(db: Session, category: Category) -> CategoryResponse:
    question_count = db.scalar(
        select(func.count(QuestionVersion.id)).where(QuestionVersion.category_id == category.id)
    ) or 0
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        question_count=int(question_count),
    )


@admin_router.get("/categories", response_model=list[CategoryResponse])
def list_categories(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[CategoryResponse]:
    categories = list(db.scalars(select(Category).order_by(Category.name)))
    return [category_response(db, category) for category in categories]


@admin_router.post(
    "/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
def create_category(
    payload: CategoryInput,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CategoryResponse:
    category = Category(
        name=payload.name.strip(),
        slug=payload.slug.strip().lower(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Category name or slug is already in use"
        ) from None
    db.refresh(category)
    return category_response(db, category)


@admin_router.put("/categories/{category_id}", response_model=CategoryResponse)
def edit_category(
    category_id: UUID,
    payload: CategoryInput,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CategoryResponse:
    category = db.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    category.name = payload.name.strip()
    category.slug = payload.slug.strip().lower()
    category.description = payload.description.strip() if payload.description else None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Category name or slug is already in use"
        ) from None
    db.refresh(category)
    return category_response(db, category)


@admin_router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    category = db.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    question_count = db.scalar(
        select(func.count(QuestionVersion.id)).where(QuestionVersion.category_id == category.id)
    ) or 0
    if question_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This category is used by question versions. "
                "Reassign those questions before deleting it."
            ),
        )
    db.delete(category)
    db.commit()


@admin_router.post(
    "/question-media",
    response_model=QuestionMediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_question_media(
    payload: QuestionMediaUploadRequest,
    _: User = Depends(require_admin),
) -> QuestionMediaUploadResponse:
    """Store a PNG, JPEG, or WebP image for an example or solution explanation."""

    return QuestionMediaUploadResponse(image_url=save_question_media(payload.image_data_url))


@admin_router.post(
    "/questions", response_model=AdminQuestionResponse, status_code=status.HTTP_201_CREATED
)
def create_question(
    payload: CreateQuestionRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminQuestionResponse:
    if db.scalar(select(Question.id).where(Question.slug == payload.slug)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Question slug is unavailable"
        )
    question = Question(slug=payload.slug)
    db.add(question)
    version = add_version(db, question, payload, current_user.id)
    db.commit()
    db.refresh(version)
    return AdminQuestionResponse(
        question_id=question.id,
        question_version_id=version.id,
        version_number=version.version_number,
    )


@admin_router.get("/questions", response_model=list[QuestionListItemResponse])
def list_questions(
    status_filter: QuestionVersionStatus | None = Query(default=None, alias="status"),
    difficulty: int | None = Query(default=None, ge=1, le=5),
    topic: str | None = Query(default=None, min_length=1, max_length=100),
    category_id: UUID | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[QuestionListItemResponse]:
    latest_version = (
        select(func.max(QuestionVersion.version_number))
        .where(QuestionVersion.question_id == Question.id)
        .correlate(Question)
        .scalar_subquery()
    )
    statement = (
        select(QuestionVersion)
        .join(Question)
        .where(QuestionVersion.version_number == latest_version, Question.is_archived.is_(False))
        .options(joinedload(QuestionVersion.question), joinedload(QuestionVersion.category))
        .order_by(QuestionVersion.created_at.desc())
    )
    if status_filter is not None:
        statement = statement.where(QuestionVersion.status == status_filter)
    if difficulty is not None:
        statement = statement.where(QuestionVersion.difficulty == difficulty)
    if topic is not None:
        statement = statement.where(QuestionVersion.topic.ilike(f"%{topic}%"))
    if category_id is not None:
        statement = statement.where(QuestionVersion.category_id == category_id)
    return [
        QuestionListItemResponse(
            question_id=version.question_id,
            question_version_id=version.id,
            slug=version.question.slug,
            title=version.title,
            status=version.status,
            difficulty=version.difficulty,
            category_id=version.category_id,
            topic=version.category.name,
            level=version.level,
            version_number=version.version_number,
        )
        for version in db.scalars(statement)
    ]


@admin_router.get("/question-versions/{version_id}", response_model=AdminQuestionDetailResponse)
def get_question_version(
    version_id: UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> AdminQuestionDetailResponse:
    version = load_admin_version(db, version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question version not found"
        )
    return admin_question_detail(version)


@admin_router.post(
    "/question-versions/{version_id}/validate", response_model=AdminQuestionDetailResponse
)
def validate_question_version(
    version_id: UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> AdminQuestionDetailResponse:
    version = load_admin_version(db, version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question version not found"
        )
    if version.status != QuestionVersionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only draft versions can be validated"
        )
    errors = validation_errors(version)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(errors)
        )
    version.status = QuestionVersionStatus.READY
    db.commit()
    db.refresh(version)
    return admin_question_detail(load_admin_version(db, version.id) or version)


@admin_router.post(
    "/question-versions/{version_id}/publish", response_model=AdminQuestionDetailResponse
)
def publish_question_version(
    version_id: UUID, _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> AdminQuestionDetailResponse:
    version = load_admin_version(db, version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question version not found"
        )
    if version.status != QuestionVersionStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only ready versions can be published"
        )
    version.status = QuestionVersionStatus.PUBLISHED
    version.published_at = func.now()
    db.commit()
    return admin_question_detail(load_admin_version(db, version.id) or version)


@admin_router.post("/questions/{question_id}/versions", response_model=AdminQuestionResponse)
def create_question_version(
    question_id: UUID,
    payload: QuestionVersionInput,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminQuestionResponse:
    question = db.scalar(select(Question).where(Question.id == question_id))
    if question is None or question.is_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    version = add_version(db, question, payload, current_user.id)
    db.commit()
    db.refresh(version)
    return AdminQuestionResponse(
        question_id=question.id,
        question_version_id=version.id,
        version_number=version.version_number,
    )


@admin_router.put("/question-versions/{version_id}", response_model=AdminQuestionDetailResponse)
def edit_draft_question_version(
    version_id: UUID,
    payload: QuestionVersionInput,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminQuestionDetailResponse:
    version = load_admin_version(db, version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question version not found"
        )
    if version.status != QuestionVersionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft versions can be edited; create a new version instead",
        )
    version.title = payload.title
    version.statement_markdown = payload.statement_markdown
    version.examples = [example.model_dump() for example in payload.examples]
    version.constraints_markdown = payload.constraints_markdown
    version.level = payload.level
    category = db.scalar(select(Category).where(Category.id == payload.category_id))
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Category not found"
        )
    version.category_id = category.id
    version.topic = category.name
    version.difficulty = payload.difficulty
    version.starter_code = payload.starter_code
    version.solution_code = payload.solution_code
    version.explanation_markdown = payload.explanation_markdown
    version.explanation_en = payload.explanation_en
    version.explanation_ml = payload.explanation_ml
    version.solution_trace = payload.solution_trace
    version.solution_notes_en = payload.solution_notes_en
    version.solution_notes_ml = payload.solution_notes_ml
    version.solution_video_url = payload.solution_video_url
    version.solution_image_urls = payload.solution_image_urls
    version.complexity_notes = payload.complexity_notes
    version.alternative_approaches = [
        approach.model_dump() for approach in payload.alternative_approaches
    ]
    version.test_cases.clear()
    version.hints.clear()
    db.flush()
    for test in payload.public_tests:
        version.test_cases.append(
            TestCase(
                position=test.position,
                visibility=TestVisibility.PUBLIC,
                input_data=test.input_data,
                expected_output=test.expected_output,
                explanation=test.explanation,
            )
        )
    for test in payload.hidden_tests:
        version.test_cases.append(
            TestCase(
                position=test.position,
                visibility=TestVisibility.HIDDEN,
                input_data=test.input_data,
                expected_output=test.expected_output,
                explanation=test.explanation,
            )
        )
    for hint in payload.hints:
        version.hints.append(
            QuestionHint(
                position=hint.position,
                content_markdown=hint.content_markdown,
                xp_penalty=hint.xp_penalty,
            )
        )
    db.commit()
    return admin_question_detail(load_admin_version(db, version.id) or version)


@admin_router.post(
    "/daily-assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED
)
def schedule_assignment(
    payload: ScheduleAssignmentRequest,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DailyAssignment:
    if payload.assignment_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Assignment date is past"
        )
    version = db.scalar(
        select(QuestionVersion).where(QuestionVersion.id == payload.question_version_id)
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question version not found"
        )
    if version.level != payload.level:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assignment level must match question version",
        )
    if version.status not in {QuestionVersionStatus.READY, QuestionVersionStatus.PUBLISHED}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only ready or published question versions can be scheduled",
        )
    assignment = DailyAssignment(
        assignment_date=payload.assignment_date,
        level=payload.level,
        question_version_id=version.id,
    )
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Assignment already exists"
        ) from None
    db.refresh(assignment)
    return assignment


@admin_router.get("/daily-assignments/preview", response_model=list[SchedulePreviewItemResponse])
def preview_assignments(
    days: int = Query(default=30, ge=7, le=90),
    start_date: date = Query(default_factory=date.today),
    level: Level | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[SchedulePreviewItemResponse]:
    if days not in {7, 30, 90}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Preview days must be one of: 7, 30, or 90",
        )
    end_date = date.fromordinal(start_date.toordinal() + days - 1)
    statement = (
        select(DailyAssignment)
        .where(
            DailyAssignment.assignment_date.between(start_date, end_date),
            DailyAssignment.legacy_language.is_(None),
        )
        .options(joinedload(DailyAssignment.question_version).joinedload(QuestionVersion.category))
        .order_by(DailyAssignment.assignment_date, DailyAssignment.level)
    )
    if level is not None:
        statement = statement.where(DailyAssignment.level == level)
    return [
        SchedulePreviewItemResponse(
            id=assignment.id,
            assignment_date=assignment.assignment_date,
            level=assignment.level,
            question_version_id=assignment.question_version_id,
            title=assignment.question_version.title,
            topic=assignment.question_version.category.name,
        )
        for assignment in db.scalars(statement)
    ]


@admin_router.get("/submissions", response_model=list[AdminSubmissionResponse])
def list_admin_submissions(
    submission_status: SubmissionStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=250),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminSubmissionResponse]:
    """Expose recent execution outcomes to authorized admin users only."""
    statement = (
        select(Submission)
        .options(joinedload(Submission.user))
        .order_by(Submission.created_at.desc())
        .limit(limit)
    )
    if submission_status is not None:
        statement = statement.where(Submission.status == submission_status)
    return [
        AdminSubmissionResponse(
            id=submission.id,
            question_version_id=submission.question_version_id,
            daily_assignment_id=submission.daily_assignment_id,
            language=submission.language,
            status=submission.status,
            passed_test_count=submission.passed_test_count,
            total_test_count=submission.total_test_count,
            created_at=submission.created_at,
            evaluated_at=submission.evaluated_at,
            test_results=submission.test_results,
            attempt_number=submission.attempt_number,
            user_id=submission.user_id,
            user_email=submission.user.email,
            user_display_name=submission.user.display_name,
        )
        for submission in db.scalars(statement)
    ]


@router.get("/daily-assignment", response_model=ChallengeResponse)
def get_daily_assignment(
    assignment_date: date = Query(default_factory=date.today),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChallengeResponse:
    assignment = db.scalar(
        select(DailyAssignment.id).where(
            DailyAssignment.assignment_date == assignment_date,
            DailyAssignment.level == current_user.level,
            DailyAssignment.legacy_language.is_(None),
        )
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No daily assignment is scheduled"
        )
    loaded_assignment = load_assignment_for_challenge(db, assignment)
    if loaded_assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Daily assignment not found"
        )
    response = challenge_response(loaded_assignment)
    if loaded_assignment.assignment_date == server_today():
        attempt = ensure_daily_attempt(db, current_user.id, loaded_assignment.id)
        db.commit()
        response.attempt_status = attempt.status
        response.walkthrough_unlocked_at = attempt.walkthrough_unlocked_at
    return response


@router.post(
    "/daily-assignments/{assignment_id}/quit", response_model=DailyAttemptResponse
)
def quit_daily_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyAttemptResponse:
    """Give up on today's daily challenge and unlock its learning material."""
    assignment = db.scalar(
        select(DailyAssignment).where(
            DailyAssignment.id == assignment_id,
            DailyAssignment.level == current_user.level,
            DailyAssignment.assignment_date == server_today(),
        )
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Today's assignment not found"
        )
    attempt = quit_daily_attempt(db, current_user.id, assignment.id)
    if attempt.status == DailyAttemptStatus.SOLVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This challenge is already solved"
        )
    db.commit()
    return DailyAttemptResponse(
        assignment_id=assignment.id,
        status=attempt.status,
        xp_awarded=attempt.xp_awarded,
        streak_counted=attempt.streak_counted,
        walkthrough_unlocked_at=attempt.walkthrough_unlocked_at,
    )


@router.post(
    "/daily-assignments/{assignment_id}/hints/{position}", response_model=RevealedHintResponse
)
def reveal_hint(
    assignment_id: UUID,
    position: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RevealedHintResponse:
    """Record a hint reveal before returning its content.

    The unique database key makes repeated clicks harmless, and a hint cannot
    be retroactively revealed after a successful daily attempt to evade the
    no-hint bonus rule.
    """
    assignment = db.scalar(
        select(DailyAssignment)
        .where(
            DailyAssignment.id == assignment_id,
            DailyAssignment.level == current_user.level,
        )
        .options(selectinload(DailyAssignment.question_version).selectinload(QuestionVersion.hints))
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Daily assignment not found"
        )
    hint = next(
        (item for item in assignment.question_version.hints if item.position == position), None
    )
    if hint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hint not found")
    attempt = db.scalar(
        select(DailyAttempt).where(
            DailyAttempt.user_id == current_user.id,
            DailyAttempt.daily_assignment_id == assignment.id,
        )
    )
    if attempt is not None and attempt.status != DailyAttemptStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hints lock after this challenge is completed or revealed",
        )
    completed = db.scalar(
        select(Submission.id).where(
            Submission.user_id == current_user.id,
            Submission.daily_assignment_id == assignment.id,
            Submission.status == SubmissionStatus.PASSED,
        )
    )
    if completed is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Hints lock after a successful solve"
        )
    recorded = db.scalar(
        select(HintUse.id).where(
            HintUse.user_id == current_user.id,
            HintUse.daily_assignment_id == assignment.id,
            HintUse.question_hint_id == hint.id,
        )
    )
    if recorded is None:
        db.add(
            HintUse(
                user_id=current_user.id,
                daily_assignment_id=assignment.id,
                question_hint_id=hint.id,
            )
        )
        db.commit()
    return RevealedHintResponse(
        position=hint.position, content_markdown=hint.content_markdown, xp_penalty=hint.xp_penalty
    )


@router.post(
    "/submissions/run-samples", response_model=SampleRunResponse, status_code=status.HTTP_200_OK
)
def run_sample_tests(
    payload: RunSampleRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SampleRunResponse:
    """Run only public tests in the same constrained container used by the worker."""
    tests = list(
        db.scalars(
            select(TestCase)
            .where(
                TestCase.question_version_id == payload.question_version_id,
                TestCase.visibility == TestVisibility.PUBLIC,
            )
            .order_by(TestCase.position)
        )
    )
    if not tests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No public tests are available"
        )
    test_payload = [
        {
            "input": test.input_data if isinstance(test.input_data, list) else [test.input_data],
            "expected": test.expected_output,
        }
        for test in tests
    ]
    try:
        results = execute(payload.language.value, payload.source_code, test_payload)
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT, detail="Sample execution timed out"
        ) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sample execution could not be started",
        ) from None
    public_results = [
        SampleTestResult(
            position=test.position,
            passed=bool(result.get("passed", False)),
            error=result.get("error"),
        )
        for test, result in zip(tests, results)
    ]
    return SampleRunResponse(
        passed_test_count=sum(result.passed for result in public_results),
        total_test_count=len(public_results),
        results=public_results,
    )


@router.post(
    "/submissions", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED
)
def queue_submission(
    payload: SubmitRequest,
    idempotency_key: str = Header(min_length=1, max_length=255, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Submission:
    existing = db.scalar(
        select(Submission).where(
            Submission.user_id == current_user.id, Submission.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return existing
    if (
        db.scalar(
            select(QuestionVersion.id).where(QuestionVersion.id == payload.question_version_id)
        )
        is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question version not found"
        )
    if payload.daily_assignment_id is not None:
        assignment = db.scalar(
            select(DailyAssignment).where(DailyAssignment.id == payload.daily_assignment_id)
        )
        if assignment is None or assignment.question_version_id != payload.question_version_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid daily assignment"
            )
        if assignment.assignment_date == server_today() and assignment.level == current_user.level:
            attempt = ensure_daily_attempt(db, current_user.id, assignment.id)
            if attempt.status == DailyAttemptStatus.QUIT:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You chose to view this solution. Start tomorrow's challenge for XP.",
                )
    attempt_number = (
        db.scalar(
            select(func.count(Submission.id)).where(
                Submission.user_id == current_user.id,
                Submission.question_version_id == payload.question_version_id,
            )
        )
        or 0
    ) + 1
    submission = Submission(
        user_id=current_user.id,
        question_version_id=payload.question_version_id,
        daily_assignment_id=payload.daily_assignment_id,
        idempotency_key=idempotency_key,
        language=payload.language,
        source_code=payload.source_code,
        status=SubmissionStatus.QUEUED,
        attempt_number=attempt_number,
    )
    db.add(submission)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Submission).where(
                Submission.user_id == current_user.id, Submission.idempotency_key == idempotency_key
            )
        )
        if existing is None:
            raise
        return existing
    db.refresh(submission)
    evaluate_submission.delay(str(submission.id))
    return submission


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Submission:
    submission = db.scalar(
        select(Submission).where(
            Submission.id == submission_id, Submission.user_id == current_user.id
        )
    )
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return submission


@router.get("/submissions/{submission_id}/review", response_model=SubmissionReviewResponse)
def get_submission_review(
    submission_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmissionReviewResponse:
    """Return a user's own code and the exact public problem version they attempted."""

    submission = db.scalar(
        select(Submission)
        .where(Submission.id == submission_id, Submission.user_id == current_user.id)
        .options(
            selectinload(Submission.question_version).selectinload(QuestionVersion.test_cases)
        )
    )
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    version = submission.question_version
    public_tests = sorted(
        (
            PublicTestCaseResponse(
                position=test.position,
                input_data=test.input_data,
                expected_output=test.expected_output,
                explanation=test.explanation,
            )
            for test in version.test_cases
            if test.visibility == TestVisibility.PUBLIC
        ),
        key=lambda test: test.position,
    )
    return SubmissionReviewResponse(
        id=submission.id,
        question_version_id=submission.question_version_id,
        daily_assignment_id=submission.daily_assignment_id,
        language=submission.language,
        status=submission.status,
        passed_test_count=submission.passed_test_count,
        total_test_count=submission.total_test_count,
        created_at=submission.created_at,
        evaluated_at=submission.evaluated_at,
        test_results=submission.test_results,
        attempt_number=submission.attempt_number,
        question_title=version.title,
        source_code=submission.source_code,
        question=SubmissionReviewQuestionResponse(
            question_version_id=version.id,
            title=version.title,
            statement_markdown=version.statement_markdown,
            examples=version.examples,
            constraints_markdown=version.constraints_markdown,
            level=version.level,
            category_id=version.category_id,
            topic=version.topic,
            difficulty=version.difficulty,
            starter_code=version.starter_code,
            public_tests=public_tests,
        ),
    )


@router.get("/submissions", response_model=SubmissionHistoryPageResponse)
def submission_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=5, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmissionHistoryPageResponse:
    """Return a deterministic page of the current learner's submission history."""

    total = int(
        db.scalar(
            select(func.count(Submission.id)).where(Submission.user_id == current_user.id)
        )
        or 0
    )
    submissions = list(
        db.scalars(
            select(Submission)
            .where(Submission.user_id == current_user.id)
            .options(joinedload(Submission.question_version))
            .order_by(Submission.created_at.desc(), Submission.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return SubmissionHistoryPageResponse(
        items=[
            SubmissionHistoryResponse(
                id=submission.id,
                question_version_id=submission.question_version_id,
                daily_assignment_id=submission.daily_assignment_id,
                language=submission.language,
                status=submission.status,
                passed_test_count=submission.passed_test_count,
                total_test_count=submission.total_test_count,
                created_at=submission.created_at,
                evaluated_at=submission.evaluated_at,
                test_results=submission.test_results,
                attempt_number=submission.attempt_number,
                question_title=submission.question_version.title,
            )
            for submission in submissions
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/progress", response_model=ProgressResponse)
def get_progress(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProgressResponse:
    data = progress_data(db, current_user)
    db.commit()  # Persist any newly ensured catalog rows before returning the read model.
    return ProgressResponse(**data)
