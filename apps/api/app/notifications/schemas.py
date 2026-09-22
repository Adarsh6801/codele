from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models import NotificationDeliveryStatus, NotificationType


class NotificationPreferenceResponse(BaseModel):
    in_app_enabled: bool
    submission_updates: bool
    achievement_updates: bool
    social_updates: bool
    account_updates: bool

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: bool | None = None
    submission_updates: bool | None = None
    achievement_updates: bool | None = None
    social_updates: bool | None = None
    account_updates: bool | None = None


class NotificationResponse(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    body: str
    link: str | None
    delivery_status: NotificationDeliveryStatus
    created_at: datetime
    read_at: datetime | None

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int


class MarkAllReadResponse(BaseModel):
    marked_count: int
