from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException

from app.auth.dependencies import require_admin
from app.auth.service import (
    create_access_token,
    decode_access_token,
    decode_access_token_claims,
    hash_password,
    verify_password,
)
from app.db.models import User, UserRole


def test_passwords_are_hashed_and_verified() -> None:
    password = "a-strong-local-test-password"
    encoded_password = hash_password(password)

    assert encoded_password != password
    assert verify_password(password, encoded_password)
    assert not verify_password("not-the-password", encoded_password)


def test_access_token_round_trips_the_user_id() -> None:
    user_id = uuid4()
    token, expires_in = create_access_token(user_id)

    assert expires_in > 0
    assert decode_access_token(token) == user_id


def test_access_token_carries_the_server_session_version() -> None:
    user_id = uuid4()
    token, _ = create_access_token(user_id, session_version=4)

    assert decode_access_token_claims(token) == (user_id, 4)


def test_invalid_access_token_is_rejected() -> None:
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("not-a-jwt")


def test_admin_role_guard_rejects_a_regular_user() -> None:
    regular_user = User(
        id=uuid4(),
        email="learner@example.test",
        display_name="learner",
        password_hash="unused",
        role=UserRole.USER,
    )

    with pytest.raises(HTTPException) as error:
        require_admin(regular_user)

    assert error.value.status_code == 403


def test_admin_role_guard_allows_admin() -> None:
    admin = User(
        id=uuid4(),
        email="admin@example.test",
        display_name="admin",
        password_hash="unused",
        role=UserRole.ADMIN,
    )

    assert require_admin(admin) is admin
