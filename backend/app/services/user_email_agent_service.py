from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.user_email_agent_mapper import UserEmailAgentMapper
from app.models.user_email_agent import UserEmailAgent


class UserEmailAgentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = UserEmailAgentMapper(db)

    async def get_by_user_id(self, user_id: int) -> Optional[UserEmailAgent]:
        return await self.mapper.get_by_user_id(user_id)

    async def create(self, user_id: int, agent_id: int) -> UserEmailAgent:
        obj = await self.mapper.create_from_dict({
            "user_id": user_id,
            "agent_id": agent_id,
            "is_enabled": True,
        })
        await self.db.commit()
        return obj

    async def update(self, user_id: int, data: dict) -> Optional[UserEmailAgent]:
        existing = await self.mapper.get_by_user_id(user_id)
        if not existing:
            return None
        obj = await self.mapper.update_by_id(existing.id, data)
        await self.db.commit()
        return obj

    async def delete(self, user_id: int) -> bool:
        existing = await self.mapper.get_by_user_id(user_id)
        if not existing:
            return False
        result = await self.mapper.delete_by_id(existing.id)
        await self.db.commit()
        return result
