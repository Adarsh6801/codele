from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

LeaderboardPeriod = Literal["all", "weekly"]


class LeaderboardEntryResponse(BaseModel):
    rank: int
    user_id: UUID
    display_name: str
    profile_image_url: str | None
    score: int
    current_streak: int
    is_current_user: bool


class LeaderboardResponse(BaseModel):
    scope: Literal["global", "friends"]
    period: LeaderboardPeriod
    page: int
    page_size: int
    total: int
    entries: list[LeaderboardEntryResponse]
    generated_at: datetime


class FriendRequestCreate(BaseModel):
    display_name: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")


class FriendResponse(BaseModel):
    id: UUID
    user_id: UUID
    display_name: str
    profile_image_url: str | None
    leaderboard_visible: bool
    accepted_at: datetime | None


class FriendRequestResponse(FriendResponse):
    direction: Literal["incoming", "outgoing"]
    created_at: datetime
