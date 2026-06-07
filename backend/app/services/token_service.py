from datetime import datetime, UTC

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def save_refresh_token(db: AsyncSession, jti: str, user_id: str, expires_at: datetime):
    db.add(RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at))
    await db.flush()


async def revoke_refresh_token(db: AsyncSession, jti: str):
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    token = result.scalar_one_or_none()
    if token:
        token.revoked = True
        await db.flush()


async def is_refresh_token_valid(db: AsyncSession, jti: str, user_id: str) -> bool:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.jti == jti,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > _utcnow(),
        )
    )
    return result.scalar_one_or_none() is not None


async def purge_expired_tokens(db: AsyncSession):
    await db.execute(
        delete(RefreshToken).where(RefreshToken.expires_at <= _utcnow())
    )
    await db.flush()
