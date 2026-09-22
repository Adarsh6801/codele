from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models import CommunityChallengeStatus, CommunityEnrollmentStatus, CommunityTaskKind


class AuthorResponse(BaseModel):
    id: UUID
    display_name: str
    profile_image_url: str | None
    role: str


class DiscussionCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    body_markdown: str = Field(min_length=10, max_length=20_000)
    tags: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, tags: list[str]) -> list[str]:
        return list(dict.fromkeys(tag.strip().lower() for tag in tags if tag.strip()))


class ReplyCreate(BaseModel):
    body_markdown: str = Field(min_length=1, max_length=12_000)
    parent_reply_id: UUID | None = None


class ReplyResponse(BaseModel):
    id: UUID
    discussion_id: UUID
    parent_reply_id: UUID | None
    body_markdown: str
    is_accepted_answer: bool
    is_mentor: bool
    author: AuthorResponse
    created_at: datetime
    updated_at: datetime


class DiscussionListItem(BaseModel):
    id: UUID
    title: str
    tags: list[str]
    is_pinned: bool
    author: AuthorResponse
    reply_count: int
    created_at: datetime
    updated_at: datetime


class DiscussionDetail(DiscussionListItem):
    body_markdown: str
    is_locked: bool
    replies: list[ReplyResponse]


class DiscussionPage(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[DiscussionListItem]


class ChallengeTaskInput(BaseModel):
    position: int = Field(ge=1)
    day_offset: int = Field(ge=1)
    kind: CommunityTaskKind
    title: str = Field(min_length=2, max_length=200)
    instructions_markdown: str | None = Field(default=None, max_length=20_000)
    question_version_id: UUID | None = None
    video_url: str | None = Field(default=None, max_length=500)
    resource_url: str | None = Field(default=None, max_length=500)
    asset_urls: list[str] = Field(default_factory=list, max_length=12)
    summary_markdown: str | None = Field(default=None, max_length=20_000)
    is_required: bool = True

    @model_validator(mode="after")
    def require_relevant_content(self) -> ChallengeTaskInput:
        if self.kind == CommunityTaskKind.PROBLEM and self.question_version_id is None:
            raise ValueError("A problem task must reference a question version")
        if self.kind == CommunityTaskKind.VIDEO and not self.video_url:
            raise ValueError("A video task needs a video URL")
        if self.kind in {CommunityTaskKind.IMAGE, CommunityTaskKind.RESOURCE} and not (
            self.asset_urls or self.resource_url
        ):
            raise ValueError("This task needs an uploaded asset or resource URL")
        return self


class ChallengeUpsert(BaseModel):
    slug: str | None = Field(default=None, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=4, max_length=200)
    summary: str = Field(min_length=10, max_length=500)
    description_markdown: str | None = Field(default=None, max_length=40_000)
    duration_days: int = Field(ge=1, le=365)
    completion_deadline_days: int = Field(ge=1, le=365)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    tasks: list[ChallengeTaskInput] = Field(default_factory=list, max_length=300)

    @model_validator(mode="after")
    def validate_plan(self) -> ChallengeUpsert:
        positions = [task.position for task in self.tasks]
        if len(positions) != len(set(positions)):
            raise ValueError("Each challenge task needs a unique position")
        if any(task.day_offset > self.duration_days for task in self.tasks):
            raise ValueError("A task cannot be scheduled after the challenge duration")
        return self


class ChallengeTaskResponse(BaseModel):
    id: UUID
    position: int
    day_offset: int
    kind: CommunityTaskKind
    title: str
    instructions_markdown: str | None
    question_version_id: UUID | None
    video_url: str | None
    resource_url: str | None
    asset_urls: list[str]
    summary_markdown: str | None
    is_required: bool
    available: bool
    completed_at: datetime | None


class ChallengeSummaryResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    summary: str
    duration_days: int
    completion_deadline_days: int
    thumbnail_url: str | None
    task_count: int
    status: CommunityChallengeStatus
    enrollment_status: CommunityEnrollmentStatus | None = None


class ChallengeDetailResponse(ChallengeSummaryResponse):
    description_markdown: str | None
    tasks: list[ChallengeTaskResponse]
    enrollment_id: UUID | None = None
    deadline_at: datetime | None = None


class EnrollmentResponse(BaseModel):
    id: UUID
    challenge_id: UUID
    status: CommunityEnrollmentStatus
    joined_at: datetime
    deadline_at: datetime
    completed_at: datetime | None
    forgone_at: datetime | None


class CommunityMediaUploadRequest(BaseModel):
    """A browser-selected PNG/JPEG/WebP image or MP4/WebM clip as a data URL."""

    data_url: str = Field(min_length=32, max_length=140_000_000)
