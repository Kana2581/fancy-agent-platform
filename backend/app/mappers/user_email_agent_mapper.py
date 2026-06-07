from typing import Optional

from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.user_email_agent import UserEmailAgent


class UserEmailAgentMapper(BaseMapper[UserEmailAgent]):
    model = UserEmailAgent

    async def get_by_user_id(self, user_id: int) -> Optional[UserEmailAgent]:
        stmt = select(UserEmailAgent).where(UserEmailAgent.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
