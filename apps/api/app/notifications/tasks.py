from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.db.models import Notification, NotificationDeliveryStatus
from app.db.session import SessionLocal
from app.execution.celery_app import celery_app
from app.notifications.service import ensure_preferences


@celery_app.task(name="codele.deliver_notification")
def deliver_notification(notification_id: str) -> None:
    """Finalize in-app delivery outside the request/execution transaction."""

    with SessionLocal() as db:
        notification = db.scalar(
            select(Notification)
            .where(Notification.id == UUID(notification_id))
            .with_for_update()
        )
        if (
            notification is None
            or notification.delivery_status != NotificationDeliveryStatus.PENDING
        ):
            return
        preference = ensure_preferences(db, notification.user_id)
        category_enabled = bool(getattr(preference, f"{notification.type.value}_updates"))
        notification.delivery_status = (
            NotificationDeliveryStatus.DELIVERED
            if preference.in_app_enabled and category_enabled
            else NotificationDeliveryStatus.SKIPPED
        )
        notification.delivered_at = datetime.now(UTC)
        db.commit()
