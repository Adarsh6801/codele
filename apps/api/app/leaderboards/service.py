"""Leaderboard score calculation, caching, and deterministic pagination."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

import redis
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Friendship, Streak, User, XPTransaction

LeaderboardPeriod = Literal["all", "weekly"]
CACHE_TTL_SECONDS = 60


def _redis_client():
    return redis.Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_connect_timeout=0.2,
        socket_timeout=0.2,
    )


def invalidate_leaderboard_cache() -> None:
    """Best-effort invalidation: the database remains the source of truth."""
    try:
        client = _redis_client()
        keys = list(client.scan_iter(match="codele:leaderboard:v1:*"))
        if keys:
            client.delete(*keys)
    except redis.RedisError:
        pass


def weekly_start_utc() -> datetime:
    local_now = datetime.now(ZoneInfo(get_settings().streak_timezone))
    monday = (local_now - timedelta(days=local_now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return monday.astimezone(UTC)


def friend_ids(db: Session, user_id: UUID) -> list[UUID]:
    relationships = db.execute(
        select(Friendship.first_user_id, Friendship.second_user_id).where(
            Friendship.status == "accepted",
            or_(Friendship.first_user_id == user_id, Friendship.second_user_id == user_id),
        )
    )
    return [second if first == user_id else first for first, second in relationships]


def _cache_key(scope: str, period: LeaderboardPeriod, user_id: UUID | None = None) -> str:
    suffix = str(user_id) if scope == "friends" and user_id else "public"
    return f"codele:leaderboard:v1:{scope}:{period}:{suffix}"


def _score_rows(
    db: Session, period: LeaderboardPeriod, allowed_ids: list[UUID] | None = None
) -> list[dict]:
    xp_join = XPTransaction.user_id == User.id
    if period == "weekly":
        xp_join = and_(xp_join, XPTransaction.created_at >= weekly_start_utc())
    statement = (
        select(
            User.id,
            User.display_name,
            User.profile_image_url,
            func.coalesce(func.sum(XPTransaction.amount), 0).label("score"),
            func.coalesce(Streak.current_streak, 0).label("current_streak"),
        )
        .outerjoin(XPTransaction, xp_join)
        .outerjoin(Streak, Streak.user_id == User.id)
        .where(User.is_active.is_(True), User.leaderboard_visible.is_(True))
        .group_by(User.id, User.display_name, User.profile_image_url, Streak.current_streak)
        .order_by(
            func.coalesce(func.sum(XPTransaction.amount), 0).desc(),
            func.coalesce(Streak.current_streak, 0).desc(),
            func.lower(User.display_name).asc(),
            User.id.asc(),
        )
    )
    if allowed_ids is not None:
        if not allowed_ids:
            return []
        statement = statement.where(User.id.in_(allowed_ids))
    return [
        {
            "user_id": str(row.id),
            "display_name": row.display_name,
            "profile_image_url": row.profile_image_url,
            "score": int(row.score),
            "current_streak": int(row.current_streak),
        }
        for row in db.execute(statement)
    ]


def _load_cached_rows(
    db: Session, scope: str, period: LeaderboardPeriod, user_id: UUID | None = None
) -> list[dict]:
    key = _cache_key(scope, period, user_id)
    try:
        cached = _redis_client().get(key)
        if cached is not None:
            return json.loads(cached)
    except (redis.RedisError, json.JSONDecodeError):
        pass
    rows = _score_rows(
        db, period, friend_ids(db, user_id) if scope == "friends" and user_id else None
    )
    try:
        _redis_client().setex(key, CACHE_TTL_SECONDS, json.dumps(rows))
    except redis.RedisError:
        pass
    return rows


def leaderboard_page(
    db: Session,
    current_user: User,
    scope: Literal["global", "friends"],
    period: LeaderboardPeriod,
    page: int,
    page_size: int,
) -> dict:
    rows = _load_cached_rows(db, scope, period, current_user.id if scope == "friends" else None)
    start = (page - 1) * page_size
    return {
        "scope": scope,
        "period": period,
        "page": page,
        "page_size": page_size,
        "total": len(rows),
        "entries": [
            {
                "rank": start + index + 1,
                **row,
                "is_current_user": row["user_id"] == str(current_user.id),
            }
            for index, row in enumerate(rows[start : start + page_size])
        ],
        "generated_at": datetime.now(UTC),
    }
