from datetime import datetime
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.db.models import Level, UserRole


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("email must be valid")
        return normalized

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class DisplayNameAvailabilityResponse(BaseModel):
    display_name: str
    available: bool


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("email must be valid")
        return normalized


class PasswordResetRequestResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: UserRole
    level: Level
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileResponse(UserResponse):
    profile_image_url: str | None
    cover_image_url: str | None
    linkedin_url: str | None
    display_name_changes_remaining: int
    display_name_change_available_at: datetime | None
    leaderboard_visible: bool


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(
        default=None, min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$"
    )
    linkedin_url: str | None = Field(default=None, max_length=500)
    leaderboard_visible: bool | None = None

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("linkedin_url")
    @classmethod
    def normalize_linkedin_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        raw_url = value.strip()
        parsed = urlsplit(raw_url if "://" in raw_url else f"https://{raw_url}")
        hostname = (parsed.hostname or "").lower()
        if hostname not in {"linkedin.com", "www.linkedin.com"} or not parsed.path.strip("/"):
            raise ValueError("linkedin_url must be a LinkedIn profile URL")
        return f"https://www.linkedin.com{parsed.path.rstrip('/')}"


class ProfileImageRequest(BaseModel):
    image_data_url: str = Field(min_length=32, max_length=7_000_000)
