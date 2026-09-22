from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str | None) -> bool:
    return hashed_password is not None and password_hash.verify(password, hashed_password)


def create_access_token(user_id: UUID, session_version: int = 0) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_access_token_expire_minutes * 60
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    encoded = jwt.encode(
        {
            "sub": str(user_id),
            "exp": expires_at,
            "type": "access",
            # Backward-compatible default lets tokens made before Phase 8 be
            # interpreted as session version zero until they naturally expire.
            "sv": session_version,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded, expires_in


def decode_access_token(token: str) -> UUID:
    return decode_access_token_claims(token)[0]


def decode_access_token_claims(token: str) -> tuple[UUID, int]:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access" or not isinstance(payload.get("sub"), str):
        raise jwt.InvalidTokenError("invalid access token")
    session_version = payload.get("sv", 0)
    if not isinstance(session_version, int) or session_version < 0:
        raise jwt.InvalidTokenError("invalid access token")
    return UUID(payload["sub"]), session_version
