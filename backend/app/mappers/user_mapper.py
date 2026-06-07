from typing import Optional
from sqlalchemy import select, or_

from app.mappers.base_mapper import BaseMapper
from app.models.user import User


class UserMapper(BaseMapper[User]):
    model = User

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email_or_username(self, email_or_username)->User:
        stmt = select(User).where(
            or_(
                User.email == email_or_username,
                User.username == email_or_username
            )
        )

        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        return user

