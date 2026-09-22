"""Scheduled housekeeping for weekly leaderboard cache boundaries."""

from app.execution.celery_app import celery_app
from app.leaderboards.service import invalidate_leaderboard_cache


@celery_app.task(name="codele.reset_weekly_leaderboard")
def reset_weekly_leaderboard() -> None:
    """Weekly scores are timestamp-derived; only cached views need resetting."""
    invalidate_leaderboard_cache()
