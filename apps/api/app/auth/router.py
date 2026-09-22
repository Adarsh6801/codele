import base64
import binascii
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.auth.schemas import (
    AccessTokenResponse,
    DisplayNameAvailabilityResponse,
    LoginRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    ProfileImageRequest,
    ProfileResponse,
    RegisterRequest,
    UpdateProfileRequest,
    UserResponse,
)
from app.auth.service import create_access_token, hash_password, verify_password
from app.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.leaderboards.service import invalidate_leaderboard_cache

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

DISPLAY_NAME_CHANGE_LIMIT = 3
DISPLAY_NAME_CHANGE_WINDOW = timedelta(days=1)
MAX_PROFILE_IMAGE_BYTES = 5 * 1024 * 1024
PROFILE_IMAGE_DATA_URL = re.compile(r"^data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)$")


def profile_response(user: User, now: datetime | None = None) -> ProfileResponse:
    """Expose profile limits without exposing storage or auth internals."""
    now = now or datetime.now(UTC)
    window_started_at = user.display_name_change_window_started_at
    if window_started_at is None or window_started_at + DISPLAY_NAME_CHANGE_WINDOW <= now:
        remaining = DISPLAY_NAME_CHANGE_LIMIT
        available_at = None
    else:
        remaining = max(DISPLAY_NAME_CHANGE_LIMIT - user.display_name_change_count, 0)
        available_at = window_started_at + DISPLAY_NAME_CHANGE_WINDOW if remaining == 0 else None
    return ProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        level=user.level,
        is_active=user.is_active,
        created_at=user.created_at,
        profile_image_url=user.profile_image_url,
        cover_image_url=user.cover_image_url,
        linkedin_url=user.linkedin_url,
        display_name_changes_remaining=remaining,
        display_name_change_available_at=available_at,
        leaderboard_visible=user.leaderboard_visible,
    )


def decode_profile_image(image_data_url: str) -> tuple[str, bytes]:
    match = PROFILE_IMAGE_DATA_URL.fullmatch(image_data_url)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Upload a PNG, JPEG, or WebP image.",
        )
    try:
        image_bytes = base64.b64decode(match.group(2), validate=True)
    except binascii.Error as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The profile image data is invalid.",
        ) from error
    if not image_bytes or len(image_bytes) > MAX_PROFILE_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Profile images must be 5 MB or smaller.",
        )
    return {"png": "png", "jpeg": "jpg", "webp": "webp"}[match.group(1)], image_bytes


def delete_stored_asset(asset_url: str | None) -> None:
    if asset_url is None:
        return
    asset_path = get_settings().upload_dir / "users" / Path(asset_url).name
    asset_path.unlink(missing_ok=True)


def save_profile_asset(image_data_url: str) -> str:
    extension, image_bytes = decode_profile_image(image_data_url)
    image_directory = get_settings().upload_dir / "users"
    image_directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}.{extension}"
    (image_directory / filename).write_bytes(image_bytes)
    return f"/uploads/users/{filename}"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_account(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    existing_user = db.scalar(
        select(User).where(
            (User.email == payload.email)
            | (func.lower(User.display_name) == payload.display_name.lower())
        )
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email or display name is unavailable"
        )

    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email or display name is unavailable"
        ) from None
    db.refresh(user)
    return user


@router.get("/display-name-availability", response_model=DisplayNameAvailabilityResponse)
def display_name_availability(
    display_name: str = Query(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$"),
    db: Session = Depends(get_db),
) -> DisplayNameAvailabilityResponse:
    """Check the case-insensitive uniqueness used during registration."""
    normalized = display_name.strip()
    existing_user = db.scalar(
        select(User.id).where(func.lower(User.display_name) == normalized.lower())
    )
    return DisplayNameAvailabilityResponse(display_name=normalized, available=existing_user is None)


@router.post("/login", response_model=AccessTokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AccessTokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(user.id, user.session_version)
    return AccessTokenResponse(access_token=token, expires_in=expires_in)


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_reset(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
) -> PasswordResetRequestResponse:
    """Accept recovery requests without exposing whether an email is registered.

    A mail-delivery provider is intentionally not coupled to the API foundation.
    Production should enqueue an email containing the reset link at this boundary.
    """
    _ = db.scalar(select(User.id).where(User.email == payload.email))
    return PasswordResetRequestResponse(
        message="If an account exists for this email, its password reset request was accepted."
    )


@router.get("/me", response_model=ProfileResponse)
def get_me(current_user: User = Depends(get_current_user)) -> ProfileResponse:
    return profile_response(current_user)


@router.patch("/me", response_model=ProfileResponse)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    new_display_name = payload.display_name
    if (
        new_display_name is None
        and "linkedin_url" not in payload.model_fields_set
        and "leaderboard_visible" not in payload.model_fields_set
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No profile changes supplied"
        )

    now = datetime.now(UTC)
    if (
        new_display_name is not None
        and new_display_name.lower() != current_user.display_name.lower()
    ):
        window_started_at = current_user.display_name_change_window_started_at
        if window_started_at is None or window_started_at + DISPLAY_NAME_CHANGE_WINDOW <= now:
            current_user.display_name_change_count = 0
            current_user.display_name_change_window_started_at = now
        elif current_user.display_name_change_count >= DISPLAY_NAME_CHANGE_LIMIT:
            retry_at = window_started_at + DISPLAY_NAME_CHANGE_WINDOW
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You can change your display name again after the 24-hour limit resets.",
                headers={"Retry-After": str(max(int((retry_at - now).total_seconds()), 1))},
            )
        name_in_use = db.scalar(
            select(User.id).where(
                func.lower(User.display_name) == new_display_name.lower(),
                User.id != current_user.id,
            )
        )
        if name_in_use is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Display name is unavailable"
            )
        current_user.display_name = new_display_name
        current_user.display_name_change_count += 1

    if "linkedin_url" in payload.model_fields_set:
        if payload.linkedin_url is not None:
            linkedin_in_use = db.scalar(
                select(User.id).where(
                    func.lower(User.linkedin_url) == payload.linkedin_url.lower(),
                    User.id != current_user.id,
                )
            )
            if linkedin_in_use is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This LinkedIn URL is already connected to another profile",
                )
        current_user.linkedin_url = payload.linkedin_url
    if "leaderboard_visible" in payload.model_fields_set:
        current_user.leaderboard_visible = bool(payload.leaderboard_visible)
    db.commit()
    db.refresh(current_user)
    invalidate_leaderboard_cache()
    return profile_response(current_user, now)


@router.put("/me/profile-image", response_model=ProfileResponse)
def update_profile_image(
    payload: ProfileImageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    old_image_url = current_user.profile_image_url
    current_user.profile_image_url = save_profile_asset(payload.image_data_url)
    try:
        db.commit()
    except Exception:
        delete_stored_asset(current_user.profile_image_url)
        db.rollback()
        raise
    delete_stored_asset(old_image_url)
    db.refresh(current_user)
    return profile_response(current_user)


@router.put("/me/cover-image", response_model=ProfileResponse)
def update_cover_image(
    payload: ProfileImageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    old_cover_url = current_user.cover_image_url
    current_user.cover_image_url = save_profile_asset(payload.image_data_url)
    try:
        db.commit()
    except Exception:
        delete_stored_asset(current_user.cover_image_url)
        db.rollback()
        raise
    delete_stored_asset(old_cover_url)
    db.refresh(current_user)
    return profile_response(current_user)


@admin_router.get("/users", response_model=list[UserResponse])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[User]:
    """Minimal protected endpoint proving the admin RBAC boundary."""
    return list(db.scalars(select(User).order_by(User.created_at.desc())))
