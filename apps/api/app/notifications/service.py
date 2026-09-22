"""Server-side preference evaluation and idempotent notification creation."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Notification, NotificationPreference, NotificationType


def ensure_preferences(db: Session, user_id: UUID) -> NotificationPreference:
    preference = db.scalar(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    if preference is None:
        preference = NotificationPreference(user_id=user_id)
        db.add(preference)
        db.flush()
    return preference


def _enabled(preference: NotificationPreference, notification_type: NotificationType) -> bool:
    category_field = f"{notification_type.value}_updates"
    return preference.in_app_enabled and bool(getattr(preference, category_field))


def create_notification(
    db: Session,
    *,
    user_id: UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    event_key: str,
    link: str | None = None,
) -> UUID | None:
    """Queue one in-app alert only when its category is enabled.

    ``event_key`` is unique, so retries from a Celery worker cannot create a
    second notification for the same server-side event.
    """

    if not _enabled(ensure_preferences(db, user_id), notification_type):
        return None
    notification_id = uuid4()
    result = db.execute(
        insert(Notification)
        .values(
            id=notification_id,
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            link=link,
            event_key=event_key,
        )
        .on_conflict_do_nothing(index_elements=[Notification.event_key])
    )
    return notification_id if result.rowcount else None
