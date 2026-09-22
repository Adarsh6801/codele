from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()
celery_app = Celery("codele", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, task_serializer="json", accept_content=["json"])
celery_app.conf.beat_schedule = {
    "reset-weekly-leaderboard-cache": {
        "task": "codele.reset_weekly_leaderboard",
        "schedule": crontab(minute=0, hour=0, day_of_week="monday"),
    }
}
# Force registration at process startup so both the worker and scheduler use
# the same explicit task catalogue.
celery_app.autodiscover_tasks(
    ["app.execution", "app.leaderboards", "app.notifications"], force=True
)
