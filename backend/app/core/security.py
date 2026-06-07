from datetime import datetime, timedelta, UTC
from jose import jwt
from uuid import uuid4

from app.core.config import settings


def create_jwt_token(data: dict, expires_delta: timedelta):
    now = datetime.now(UTC)
    to_encode = data.copy()
    to_encode.update({"exp": now + expires_delta, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: str, role: str):
    return create_jwt_token(
        data={"sub": user_id, "role": role, "type": "access"},
        expires_delta=settings.ACCESS_TOKEN_EXPIRE,
    )


def create_refresh_token(user_id: str, role: str):
    jti = str(uuid4())
    token = create_jwt_token(
        data={"sub": user_id, "role": role, "jti": jti, "type": "refresh"},
        expires_delta=settings.REFRESH_TOKEN_EXPIRE,
    )
    return token, jti
