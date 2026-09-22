from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.service import decode_access_token_claims
from app.db.models import User, UserRole
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        user_id, token_session_version = decode_access_token_claims(token)
    except (ValueError, jwt.PyJWTError):
        raise credentials_exception() from None

    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active or user.session_version != token_session_version:
        raise credentials_exception()
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Return a FastAPI dependency that enforces one of the supplied roles."""

    def role_guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return current_user

    return role_guard


require_admin = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_moderator = require_roles(UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)
require_super_admin = require_roles(UserRole.SUPER_ADMIN)
