from datetime import datetime, UTC

from fastapi import APIRouter, Response, Cookie, HTTPException, Depends
from fastapi.responses import JSONResponse
from jose import jwt, JWTError

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.deps.db import get_db
from app.deps.service import get_user_service
from app.schemas.auth import LoginRequest, UserCreate, UserResponse
from app.services.token_service import save_refresh_token, is_refresh_token_valid, revoke_refresh_token
from app.services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.register_user(user_data.model_dump())
    return user


@router.post("/login")
async def login(
    login_data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    user = await user_service.authenticate_user(
        identifier=login_data.username,
        password=login_data.password,
    )
    user_id = str(user.id)
    role = getattr(user, "role", "user")

    access_token = create_access_token(user_id, role)
    refresh_token, jti = create_refresh_token(user_id, role)

    expires_at = datetime.now(UTC) + settings.REFRESH_TOKEN_EXPIRE
    await save_refresh_token(db, jti, user_id, expires_at.replace(tzinfo=None))
    await db.commit()

    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/auth/refresh",
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh")
async def refresh_token(
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(None, alias=settings.REFRESH_COOKIE_NAME),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload["sub"]
    jti = payload["jti"]
    role = payload.get("role", "user")

    if not await is_refresh_token_valid(db, jti, user_id):
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    await revoke_refresh_token(db, jti)

    new_access = create_access_token(user_id, role)
    new_refresh, new_jti = create_refresh_token(user_id, role)

    expires_at = datetime.now(UTC) + settings.REFRESH_TOKEN_EXPIRE
    await save_refresh_token(db, new_jti, user_id, expires_at.replace(tzinfo=None))
    await db.commit()

    response = JSONResponse({"access_token": new_access, "token_type": "bearer"})
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/auth/refresh",
    )
    return response


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(None, alias=settings.REFRESH_COOKIE_NAME),
):
    if refresh_token:
        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            jti = payload.get("jti")
            if jti:
                await revoke_refresh_token(db, jti)
                await db.commit()
        except JWTError:
            pass

    response.delete_cookie(key=settings.REFRESH_COOKIE_NAME, path="/auth/refresh")
    return {"detail": "Logged out"}
