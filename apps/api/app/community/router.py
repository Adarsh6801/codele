from __future__ import annotations

import base64
import binascii
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user, require_admin
from app.community.schemas import (
    AuthorResponse,
    ChallengeDetailResponse,
    ChallengeSummaryResponse,
    ChallengeTaskInput,
    ChallengeTaskResponse,
    ChallengeUpsert,
    CommunityMediaUploadRequest,
    DiscussionCreate,
    DiscussionDetail,
    DiscussionListItem,
    DiscussionPage,
    EnrollmentResponse,
    ReplyCreate,
    ReplyResponse,
)
from app.config import get_settings
from app.db.models import (
    CommunityChallenge,
    CommunityChallengeStatus,
    CommunityChallengeTask,
    CommunityDiscussion,
    CommunityDiscussionReply,
    CommunityEnrollment,
    CommunityEnrollmentStatus,
    CommunityTaskProgress,
    NotificationType,
    QuestionVersion,
    User,
    UserRole,
)
from app.db.session import get_db
from app.gamification.service import server_today
from app.notifications.service import create_notification

router = APIRouter(prefix="/community", tags=["community"])
admin_router = APIRouter(prefix="/admin/community", tags=["admin community"])
MENTOR_ROLES = {UserRole.MENTOR, UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN}
MEDIA_DATA_URL = re.compile(
    r"^data:(image/(?:png|jpeg|webp)|video/(?:mp4|webm));base64,([A-Za-z0-9+/=]+)$"
)
MEDIA_EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "video/mp4": "mp4",
    "video/webm": "webm",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024


def _save_community_media(data_url: str) -> str:
    match = MEDIA_DATA_URL.fullmatch(data_url)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload a PNG, JPEG, WebP, MP4, or WebM file.",
        )
    mime_type = match.group(1)
    try:
        file_bytes = base64.b64decode(match.group(2), validate=True)
    except binascii.Error as error:
        raise HTTPException(status_code=422, detail="The uploaded file is invalid") from error
    maximum_size = MAX_VIDEO_BYTES if mime_type.startswith("video/") else MAX_IMAGE_BYTES
    if not file_bytes or len(file_bytes) > maximum_size:
        label = "Videos" if mime_type.startswith("video/") else "Images"
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{label} must be {maximum_size // (1024 * 1024)} MB or smaller.",
        )
    directory = get_settings().upload_dir / "community-media"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{MEDIA_EXTENSIONS[mime_type]}"
    (directory / filename).write_bytes(file_bytes)
    return f"/uploads/community-media/{filename}"


def _author(user: User) -> AuthorResponse:
    return AuthorResponse(
        id=user.id,
        display_name=user.display_name,
        profile_image_url=user.profile_image_url,
        role=user.role.value,
    )


def _reply(reply: CommunityDiscussionReply) -> ReplyResponse:
    return ReplyResponse(
        id=reply.id,
        discussion_id=reply.discussion_id,
        parent_reply_id=reply.parent_reply_id,
        body_markdown=reply.body_markdown,
        is_accepted_answer=reply.is_accepted_answer,
        is_mentor=reply.author.role in MENTOR_ROLES,
        author=_author(reply.author),
        created_at=reply.created_at,
        updated_at=reply.updated_at,
    )


def _discussion_item(discussion: CommunityDiscussion, reply_count: int) -> DiscussionListItem:
    return DiscussionListItem(
        id=discussion.id,
        title=discussion.title,
        tags=discussion.tags,
        is_pinned=discussion.is_pinned,
        author=_author(discussion.author),
        reply_count=reply_count,
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
    )


def _task_response(
    task: CommunityChallengeTask,
    enrollment: CommunityEnrollment | None,
    progress_by_task: dict[UUID, CommunityTaskProgress],
    *,
    force_available: bool = False,
) -> ChallengeTaskResponse:
    available = force_available
    completed_at = None
    if enrollment is not None:
        available_from = enrollment.joined_at.date() + timedelta(days=task.day_offset - 1)
        available = (
            server_today() >= available_from
            and enrollment.status == CommunityEnrollmentStatus.ACTIVE
        )
        progress = progress_by_task.get(task.id)
        completed_at = progress.completed_at if progress else None
    return ChallengeTaskResponse(
        id=task.id,
        position=task.position,
        day_offset=task.day_offset,
        kind=task.kind,
        title=task.title,
        instructions_markdown=task.instructions_markdown,
        # Do not hide plan metadata, but only expose a task's learning content
        # once the learner has reached its scheduled day.
        question_version_id=task.question_version_id if available else None,
        video_url=task.video_url if available else None,
        resource_url=task.resource_url if available else None,
        asset_urls=task.asset_urls if available else [],
        summary_markdown=task.summary_markdown if available else None,
        is_required=task.is_required,
        available=available,
        completed_at=completed_at,
    )


def _challenge_summary(
    challenge: CommunityChallenge,
    enrollment: CommunityEnrollment | None = None,
) -> ChallengeSummaryResponse:
    return ChallengeSummaryResponse(
        id=challenge.id,
        slug=challenge.slug,
        title=challenge.title,
        summary=challenge.summary,
        duration_days=challenge.duration_days,
        completion_deadline_days=challenge.completion_deadline_days,
        thumbnail_url=challenge.thumbnail_url,
        task_count=len(challenge.tasks),
        status=challenge.status,
        enrollment_status=enrollment.status if enrollment else None,
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise HTTPException(
            status_code=422, detail="Challenge title must contain letters or numbers"
        )
    return slug[:160]


def _load_challenge(
    db: Session, challenge_id: UUID, *, all_statuses: bool = False
) -> CommunityChallenge:
    statement = (
        select(CommunityChallenge)
        .options(selectinload(CommunityChallenge.tasks))
        .where(CommunityChallenge.id == challenge_id)
    )
    if not all_statuses:
        statement = statement.where(CommunityChallenge.status == CommunityChallengeStatus.PUBLISHED)
    challenge = db.scalar(statement)
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge


def _active_enrollment(db: Session, user_id: UUID) -> CommunityEnrollment | None:
    enrollment = db.scalar(
        select(CommunityEnrollment)
        .where(
            CommunityEnrollment.user_id == user_id,
            CommunityEnrollment.status == CommunityEnrollmentStatus.ACTIVE,
        )
        .with_for_update()
    )
    if enrollment is not None and datetime.now(UTC) > enrollment.deadline_at:
        enrollment.status = CommunityEnrollmentStatus.EXPIRED
        db.flush()
        return None
    return enrollment


@router.get("/discussions", response_model=DiscussionPage)
def list_discussions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    query: str | None = Query(default=None, max_length=100),
    tag: str | None = Query(default=None, max_length=50),
    db: Session = Depends(get_db),
) -> DiscussionPage:
    count_reply = func.count(CommunityDiscussionReply.id).label("reply_count")
    statement = (
        select(CommunityDiscussion, count_reply)
        .outerjoin(CommunityDiscussionReply)
        .where(~CommunityDiscussion.is_archived)
        .options(selectinload(CommunityDiscussion.author))
        .group_by(CommunityDiscussion.id)
    )
    if query:
        needle = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                CommunityDiscussion.title.ilike(needle),
                CommunityDiscussion.body_markdown.ilike(needle),
            )
        )
    if tag:
        statement = statement.where(CommunityDiscussion.tags.contains([tag.strip().lower()]))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.execute(
        statement.order_by(
            CommunityDiscussion.is_pinned.desc(), CommunityDiscussion.created_at.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return DiscussionPage(
        page=page,
        page_size=page_size,
        total=total,
        items=[_discussion_item(discussion, reply_count) for discussion, reply_count in rows],
    )


@router.post("/discussions", response_model=DiscussionDetail, status_code=status.HTTP_201_CREATED)
def create_discussion(
    payload: DiscussionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiscussionDetail:
    discussion = CommunityDiscussion(
        author_id=current_user.id,
        title=payload.title.strip(),
        body_markdown=payload.body_markdown.strip(),
        tags=payload.tags,
    )
    db.add(discussion)
    db.commit()
    db.refresh(discussion)
    return DiscussionDetail(
        **_discussion_item(discussion, 0).model_dump(),
        body_markdown=discussion.body_markdown,
        is_locked=discussion.is_locked,
        replies=[],
    )


@router.get("/discussions/{discussion_id}", response_model=DiscussionDetail)
def get_discussion(discussion_id: UUID, db: Session = Depends(get_db)) -> DiscussionDetail:
    discussion = db.scalar(
        select(CommunityDiscussion)
        .where(CommunityDiscussion.id == discussion_id, ~CommunityDiscussion.is_archived)
        .options(
            selectinload(CommunityDiscussion.author),
            selectinload(CommunityDiscussion.replies).selectinload(CommunityDiscussionReply.author),
        )
    )
    if discussion is None:
        raise HTTPException(status_code=404, detail="Discussion not found")
    return DiscussionDetail(
        **_discussion_item(discussion, len(discussion.replies)).model_dump(),
        body_markdown=discussion.body_markdown,
        is_locked=discussion.is_locked,
        replies=[_reply(reply) for reply in discussion.replies],
    )


@router.post(
    "/discussions/{discussion_id}/replies",
    response_model=ReplyResponse,
    status_code=status.HTTP_201_CREATED,
)
def reply_to_discussion(
    discussion_id: UUID,
    payload: ReplyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReplyResponse:
    discussion = db.scalar(
        select(CommunityDiscussion).where(CommunityDiscussion.id == discussion_id)
    )
    if discussion is None or discussion.is_archived:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if discussion.is_locked:
        raise HTTPException(status_code=409, detail="This discussion is locked")
    if payload.parent_reply_id is not None:
        parent = db.scalar(
            select(CommunityDiscussionReply).where(
                CommunityDiscussionReply.id == payload.parent_reply_id,
                CommunityDiscussionReply.discussion_id == discussion_id,
            )
        )
        if parent is None:
            raise HTTPException(
                status_code=422, detail="Reply parent does not belong to this discussion"
            )
    reply = CommunityDiscussionReply(
        discussion_id=discussion_id,
        author_id=current_user.id,
        parent_reply_id=payload.parent_reply_id,
        body_markdown=payload.body_markdown.strip(),
    )
    db.add(reply)
    if discussion.author_id != current_user.id:
        create_notification(
            db,
            user_id=discussion.author_id,
            notification_type=NotificationType.SOCIAL,
            title="New reply to your community question",
            body=f"{current_user.display_name} replied to {discussion.title}.",
            link=f"/community/discussions/{discussion.id}",
            event_key=f"community-reply:{reply.id}",
        )
    db.commit()
    db.refresh(reply)
    db.refresh(current_user)
    return _reply(reply)


@router.get("/challenges", response_model=list[ChallengeSummaryResponse])
def list_challenges(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ChallengeSummaryResponse]:
    challenges = db.scalars(
        select(CommunityChallenge)
        .where(CommunityChallenge.status == CommunityChallengeStatus.PUBLISHED)
        .options(selectinload(CommunityChallenge.tasks))
        .order_by(CommunityChallenge.published_at.desc(), CommunityChallenge.created_at.desc())
    ).all()
    enrollments = {
        enrollment.challenge_id: enrollment
        for enrollment in db.scalars(
            select(CommunityEnrollment).where(CommunityEnrollment.user_id == current_user.id)
        )
    }
    return [
        _challenge_summary(challenge, enrollments.get(challenge.id)) for challenge in challenges
    ]


@router.get("/challenges/{slug}", response_model=ChallengeDetailResponse)
def get_challenge(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChallengeDetailResponse:
    challenge = db.scalar(
        select(CommunityChallenge)
        .where(
            CommunityChallenge.slug == slug,
            CommunityChallenge.status == CommunityChallengeStatus.PUBLISHED,
        )
        .options(selectinload(CommunityChallenge.tasks))
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    enrollment = db.scalar(
        select(CommunityEnrollment)
        .where(
            CommunityEnrollment.user_id == current_user.id,
            CommunityEnrollment.challenge_id == challenge.id,
        )
        .options(selectinload(CommunityEnrollment.task_progress))
    )
    progress = {item.task_id: item for item in enrollment.task_progress} if enrollment else {}
    summary = _challenge_summary(challenge, enrollment)
    return ChallengeDetailResponse(
        **summary.model_dump(),
        description_markdown=challenge.description_markdown,
        enrollment_id=enrollment.id if enrollment else None,
        deadline_at=enrollment.deadline_at if enrollment else None,
        tasks=[_task_response(task, enrollment, progress) for task in challenge.tasks],
    )


@router.post("/challenges/{challenge_id}/join", response_model=EnrollmentResponse, status_code=201)
def join_challenge(
    challenge_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnrollmentResponse:
    challenge = _load_challenge(db, challenge_id)
    existing = db.scalar(
        select(CommunityEnrollment).where(
            CommunityEnrollment.user_id == current_user.id,
            CommunityEnrollment.challenge_id == challenge.id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="You have already joined this challenge")
    active = _active_enrollment(db, current_user.id)
    if active is not None:
        raise HTTPException(
            status_code=409,
            detail="Finish or forgo your active challenge before joining another one",
        )
    enrollment = CommunityEnrollment(
        user_id=current_user.id,
        challenge_id=challenge.id,
        deadline_at=datetime.now(UTC) + timedelta(days=challenge.completion_deadline_days),
    )
    db.add(enrollment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="You already have an active challenge"
        ) from None
    db.refresh(enrollment)
    return EnrollmentResponse.model_validate(enrollment, from_attributes=True)


@router.post("/enrollments/{enrollment_id}/forgo", response_model=EnrollmentResponse)
def forgo_challenge(
    enrollment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnrollmentResponse:
    enrollment = db.scalar(
        select(CommunityEnrollment)
        .where(
            CommunityEnrollment.id == enrollment_id, CommunityEnrollment.user_id == current_user.id
        )
        .with_for_update()
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Challenge enrollment not found")
    if enrollment.status != CommunityEnrollmentStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="This challenge is no longer active")
    enrollment.status = CommunityEnrollmentStatus.FORGONE
    enrollment.forgone_at = datetime.now(UTC)
    db.commit()
    db.refresh(enrollment)
    return EnrollmentResponse.model_validate(enrollment, from_attributes=True)


@router.post(
    "/enrollments/{enrollment_id}/tasks/{task_id}/complete", response_model=EnrollmentResponse
)
def complete_challenge_task(
    enrollment_id: UUID,
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnrollmentResponse:
    enrollment = db.scalar(
        select(CommunityEnrollment)
        .where(
            CommunityEnrollment.id == enrollment_id, CommunityEnrollment.user_id == current_user.id
        )
        .options(selectinload(CommunityEnrollment.challenge).selectinload(CommunityChallenge.tasks))
        .with_for_update()
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Challenge enrollment not found")
    if enrollment.status != CommunityEnrollmentStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="This challenge is no longer active")
    now = datetime.now(UTC)
    if now > enrollment.deadline_at:
        enrollment.status = CommunityEnrollmentStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=409, detail="This challenge reached its completion deadline"
        )
    task = next((item for item in enrollment.challenge.tasks if item.id == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task does not belong to this challenge")
    if server_today() < enrollment.joined_at.date() + timedelta(days=task.day_offset - 1):
        raise HTTPException(status_code=409, detail="This task is not available yet")
    existing = db.scalar(
        select(CommunityTaskProgress).where(
            CommunityTaskProgress.enrollment_id == enrollment.id,
            CommunityTaskProgress.task_id == task.id,
        )
    )
    if existing is None:
        db.add(CommunityTaskProgress(enrollment_id=enrollment.id, task_id=task.id))
        db.flush()
    required_ids = {task.id for task in enrollment.challenge.tasks if task.is_required}
    done_ids = set(
        db.scalars(
            select(CommunityTaskProgress.task_id).where(
                CommunityTaskProgress.enrollment_id == enrollment.id
            )
        )
    )
    if required_ids.issubset(done_ids):
        enrollment.status = CommunityEnrollmentStatus.COMPLETED
        enrollment.completed_at = now
    db.commit()
    db.refresh(enrollment)
    return EnrollmentResponse.model_validate(enrollment, from_attributes=True)


def _set_tasks(db: Session, challenge: CommunityChallenge, tasks: list[ChallengeTaskInput]) -> None:
    existing = list(challenge.tasks)
    for task in existing:
        db.delete(task)
    db.flush()
    question_ids = {
        task.question_version_id for task in tasks if task.question_version_id is not None
    }
    known_question_ids = (
        set(db.scalars(select(QuestionVersion.id).where(QuestionVersion.id.in_(question_ids))))
        if question_ids
        else set()
    )
    if known_question_ids != question_ids:
        raise HTTPException(status_code=422, detail="One or more question versions do not exist")
    for task in tasks:
        db.add(CommunityChallengeTask(challenge_id=challenge.id, **task.model_dump()))


@admin_router.post("/media", status_code=status.HTTP_201_CREATED)
def admin_upload_community_media(
    payload: CommunityMediaUploadRequest,
    current_user: User = Depends(require_admin),
) -> dict[str, str]:
    """Store an author-selected visual or clip and return its static URL."""

    return {"url": _save_community_media(payload.data_url)}


@admin_router.get("/challenges", response_model=list[ChallengeSummaryResponse])
def admin_list_challenges(
    current_user: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[ChallengeSummaryResponse]:
    challenges = db.scalars(
        select(CommunityChallenge)
        .options(selectinload(CommunityChallenge.tasks))
        .order_by(CommunityChallenge.updated_at.desc())
    ).all()
    return [_challenge_summary(challenge) for challenge in challenges]


@admin_router.post("/challenges", response_model=ChallengeDetailResponse, status_code=201)
def admin_create_challenge(
    payload: ChallengeUpsert,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ChallengeDetailResponse:
    slug = payload.slug or _slug(payload.title)
    if db.scalar(select(CommunityChallenge.id).where(CommunityChallenge.slug == slug)):
        raise HTTPException(status_code=409, detail="Challenge slug already exists")
    challenge = CommunityChallenge(
        slug=slug,
        title=payload.title.strip(),
        summary=payload.summary.strip(),
        description_markdown=payload.description_markdown,
        duration_days=payload.duration_days,
        completion_deadline_days=payload.completion_deadline_days,
        thumbnail_url=payload.thumbnail_url,
        created_by_id=current_user.id,
    )
    db.add(challenge)
    db.flush()
    _set_tasks(db, challenge, payload.tasks)
    db.commit()
    return _admin_detail(db, challenge.id)


@admin_router.put("/challenges/{challenge_id}", response_model=ChallengeDetailResponse)
def admin_update_challenge(
    challenge_id: UUID,
    payload: ChallengeUpsert,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ChallengeDetailResponse:
    challenge = _load_challenge(db, challenge_id, all_statuses=True)
    if challenge.status == CommunityChallengeStatus.PUBLISHED:
        raise HTTPException(
            status_code=409, detail="Published challenges are historical and cannot be edited"
        )
    slug = payload.slug or _slug(payload.title)
    duplicate = db.scalar(
        select(CommunityChallenge.id).where(
            CommunityChallenge.slug == slug, CommunityChallenge.id != challenge.id
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Challenge slug already exists")
    for field in (
        "title",
        "summary",
        "description_markdown",
        "duration_days",
        "completion_deadline_days",
        "thumbnail_url",
    ):
        setattr(challenge, field, getattr(payload, field))
    challenge.slug = slug
    _set_tasks(db, challenge, payload.tasks)
    db.commit()
    return _admin_detail(db, challenge.id)


@admin_router.post("/challenges/{challenge_id}/publish", response_model=ChallengeDetailResponse)
def admin_publish_challenge(
    challenge_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ChallengeDetailResponse:
    challenge = _load_challenge(db, challenge_id, all_statuses=True)
    if challenge.status == CommunityChallengeStatus.ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived challenges cannot be published")
    if not challenge.tasks:
        raise HTTPException(status_code=422, detail="Add at least one task before publishing")
    challenge.status = CommunityChallengeStatus.PUBLISHED
    challenge.published_at = datetime.now(UTC)
    db.commit()
    return _admin_detail(db, challenge.id)


def _admin_detail(db: Session, challenge_id: UUID) -> ChallengeDetailResponse:
    challenge = _load_challenge(db, challenge_id, all_statuses=True)
    summary = _challenge_summary(challenge)
    return ChallengeDetailResponse(
        **summary.model_dump(),
        description_markdown=challenge.description_markdown,
        enrollment_id=None,
        deadline_at=None,
        tasks=[_task_response(task, None, {}, force_available=True) for task in challenge.tasks],
    )
