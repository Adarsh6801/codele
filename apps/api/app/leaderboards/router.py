from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.models import Friendship, NotificationType, User
from app.db.session import get_db
from app.leaderboards.schemas import (
    FriendRequestCreate,
    FriendRequestResponse,
    FriendResponse,
    LeaderboardPeriod,
    LeaderboardResponse,
)
from app.leaderboards.service import invalidate_leaderboard_cache, leaderboard_page
from app.notifications.service import create_notification

leaderboard_router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])
social_router = APIRouter(prefix="/social", tags=["social"])


def _pair(left: UUID, right: UUID) -> tuple[UUID, UUID]:
    return (left, right) if str(left) < str(right) else (right, left)


def _friend_payload(friendship: Friendship, viewer_id: UUID, user: User) -> dict:
    return {
        "id": friendship.id,
        "user_id": user.id,
        "display_name": user.display_name,
        "profile_image_url": user.profile_image_url,
        "leaderboard_visible": user.leaderboard_visible,
        "accepted_at": friendship.accepted_at,
        "direction": "outgoing" if friendship.requested_by_id == viewer_id else "incoming",
        "created_at": friendship.created_at,
    }


@leaderboard_router.get("/global", response_model=LeaderboardResponse)
def global_leaderboard(
    period: LeaderboardPeriod = "all",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeaderboardResponse:
    return LeaderboardResponse(
        **leaderboard_page(db, current_user, "global", period, page, page_size)
    )


@leaderboard_router.get("/friends", response_model=LeaderboardResponse)
def friends_leaderboard(
    period: LeaderboardPeriod = "all",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LeaderboardResponse:
    return LeaderboardResponse(
        **leaderboard_page(db, current_user, "friends", period, page, page_size)
    )


@social_router.get("/friends", response_model=list[FriendResponse])
def list_friends(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[FriendResponse]:
    rows = db.execute(
        select(Friendship, User)
        .join(
            User,
            or_(
                (Friendship.first_user_id == current_user.id)
                & (User.id == Friendship.second_user_id),
                (Friendship.second_user_id == current_user.id)
                & (User.id == Friendship.first_user_id),
            ),
        )
        .where(
            Friendship.status == "accepted",
            or_(
                Friendship.first_user_id == current_user.id,
                Friendship.second_user_id == current_user.id,
            ),
        )
        .order_by(func.lower(User.display_name))
    )
    return [
        FriendResponse(
            **{
                key: value
                for key, value in _friend_payload(item, current_user.id, user).items()
                if key not in {"direction", "created_at"}
            }
        )
        for item, user in rows
    ]


@social_router.get("/requests", response_model=list[FriendRequestResponse])
def list_friend_requests(
    direction: str = Query(default="incoming", pattern="^(incoming|outgoing)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FriendRequestResponse]:
    # With a canonical pair the requested-by field, not pair position, defines request direction.
    request_filter = (
        Friendship.requested_by_id != current_user.id
        if direction == "incoming"
        else Friendship.requested_by_id == current_user.id
    )
    rows = db.execute(
        select(Friendship, User)
        .join(
            User,
            or_(
                (Friendship.first_user_id == current_user.id)
                & (User.id == Friendship.second_user_id),
                (Friendship.second_user_id == current_user.id)
                & (User.id == Friendship.first_user_id),
            ),
        )
        .where(
            Friendship.status == "pending",
            or_(
                Friendship.first_user_id == current_user.id,
                Friendship.second_user_id == current_user.id,
            ),
            request_filter,
        )
        .order_by(Friendship.created_at.desc())
    )
    return [
        FriendRequestResponse(**_friend_payload(item, current_user.id, user)) for item, user in rows
    ]


@social_router.post(
    "/requests", response_model=FriendRequestResponse, status_code=status.HTTP_201_CREATED
)
def create_friend_request(
    payload: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FriendRequestResponse:
    target = db.scalar(
        select(User).where(func.lower(User.display_name) == payload.display_name.strip().lower())
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="You cannot add yourself"
        )
    first_user_id, second_user_id = _pair(current_user.id, target.id)
    relationship = db.scalar(
        select(Friendship).where(
            Friendship.first_user_id == first_user_id, Friendship.second_user_id == second_user_id
        )
    )
    if relationship is not None:
        detail = (
            "You are already friends"
            if relationship.status == "accepted"
            else "A friend request already exists"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    relationship = Friendship(
        first_user_id=first_user_id,
        second_user_id=second_user_id,
        requested_by_id=current_user.id,
        status="pending",
    )
    db.add(relationship)
    notification_id = create_notification(
        db,
        user_id=target.id,
        notification_type=NotificationType.SOCIAL,
        title="New friend request",
        body=f"{current_user.display_name} wants to compare coding progress with you.",
        link="/leaderboard",
        event_key=f"friend-request:{relationship.id}",
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A friend request already exists"
        ) from None
    db.refresh(relationship)
    if notification_id is not None:
        from app.notifications.tasks import deliver_notification

        deliver_notification.delay(str(notification_id))
    return FriendRequestResponse(**_friend_payload(relationship, current_user.id, target))


@social_router.post("/requests/{friendship_id}/accept", response_model=FriendResponse)
def accept_friend_request(
    friendship_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FriendResponse:
    relationship = db.scalar(
        select(Friendship).where(Friendship.id == friendship_id).with_for_update()
    )
    if relationship is None or relationship.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pending request not found"
        )
    if current_user.id == relationship.requested_by_id or current_user.id not in {
        relationship.first_user_id,
        relationship.second_user_id,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the recipient can accept this request",
        )
    relationship.status = "accepted"
    relationship.accepted_at = datetime.now(UTC)
    requester_id = relationship.requested_by_id
    notification_id = create_notification(
        db,
        user_id=requester_id,
        notification_type=NotificationType.SOCIAL,
        title="Friend request accepted",
        body=f"{current_user.display_name} accepted your friend request.",
        link="/leaderboard",
        event_key=f"friend-accepted:{relationship.id}",
    )
    db.commit()
    if notification_id is not None:
        from app.notifications.tasks import deliver_notification

        deliver_notification.delay(str(notification_id))
    invalidate_leaderboard_cache()
    friend_id = (
        relationship.second_user_id
        if relationship.first_user_id == current_user.id
        else relationship.first_user_id
    )
    friend = db.scalar(select(User).where(User.id == friend_id))
    return FriendResponse(
        **{
            key: value
            for key, value in _friend_payload(relationship, current_user.id, friend).items()
            if key not in {"direction", "created_at"}
        }
    )


@social_router.delete(
    "/friends/{friendship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
)
def remove_friendship(
    friendship_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    relationship = db.scalar(
        select(Friendship).where(Friendship.id == friendship_id).with_for_update()
    )
    if relationship is None or current_user.id not in {
        relationship.first_user_id,
        relationship.second_user_id,
    }:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friendship not found")
    db.delete(relationship)
    db.commit()
    invalidate_leaderboard_cache()
