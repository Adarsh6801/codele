from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import Level, SubmissionStatus, UserRole


class AdminUserSummary(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: UserRole
    level: Level
    is_active: bool
    created_at: datetime
    session_version: int
    submission_count: int
    xp_total: int
    current_streak: int
    badge_count: int


class AdminUserListResponse(BaseModel):
    items: list[AdminUserSummary]
    page: int
    page_size: int
    total: int


class AdminUserActivity(BaseModel):
    user: AdminUserSummary
    recent_submissions: list[dict]
    recent_xp_transactions: list[dict]
    streak_calendar: list[dict]
    badges: list[dict]


class RoleChangeRequest(BaseModel):
    role: Literal[UserRole.USER, UserRole.MODERATOR, UserRole.ADMIN]


class AdminActionResponse(BaseModel):
    id: UUID
    is_active: bool
    role: UserRole
    session_version: int
    message: str


class CreateModerationReportRequest(BaseModel):
    target_user_id: UUID
    reason: str = Field(min_length=3, max_length=120)
    details: str | None = Field(default=None, max_length=4_000)


class UpdateModerationReportRequest(BaseModel):
    status: Literal["open", "reviewing", "resolved", "dismissed"]
    resolution_note: str | None = Field(default=None, max_length=4_000)


class ModerationReportResponse(BaseModel):
    id: UUID
    status: str
    reason: str
    details: str | None
    resolution_note: str | None
    created_at: datetime
    handled_at: datetime | None
    reporter_id: UUID
    reporter_display_name: str
    target_user_id: UUID
    target_display_name: str
    handled_by_id: UUID | None
    handled_by_display_name: str | None


class ModerationReportListResponse(BaseModel):
    items: list[ModerationReportResponse]
    page: int
    page_size: int
    total: int


class AnalyticsDay(BaseModel):
    date: str
    active_users: int
    submissions: int
    passed_submissions: int
    execution_failures: int


class AnalyticsOverviewResponse(BaseModel):
    dau: int
    wau: int
    mau: int
    completion_rate: float
    execution_failure_rate: float
    evaluated_submissions: int
    average_attempt_number: float
    queue_depth: int
    daily: list[AnalyticsDay]


class AdminAuditLogResponse(BaseModel):
    id: UUID
    action: str
    target_type: str
    target_id: str
    metadata_json: dict
    created_at: datetime
    actor_user_id: UUID
    actor_display_name: str
    actor_email: str


class AdminAuditLogListResponse(BaseModel):
    items: list[AdminAuditLogResponse]
    page: int
    page_size: int
    total: int


class SubmissionMetric(BaseModel):
    status: SubmissionStatus
