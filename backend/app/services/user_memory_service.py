from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.user_memory_mapper import UserMemoryMapper
from app.models.user_memory import UserMemory
from app.schemas.user_memory_schema import UserMemoryCreate, UserMemoryUpdate


class UserMemoryService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = UserMemoryMapper(db)

    async def save(self, user_id: int, data: UserMemoryCreate) -> UserMemory:
        result = await self.mapper.upsert(
            user_id=user_id,
            key=data.key,
            content=data.content,
            memory_type=data.memory_type,
            category=data.category,
        )
        await self.db.commit()
        return result

    async def get(self, user_id: int, key: str) -> Optional[UserMemory]:
        return await self.mapper.get_by_key(user_id, key)

    async def list_by_user(
        self,
        user_id: int,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[UserMemory]:
        return await self.mapper.list_by_user(user_id, memory_type=memory_type, category=category)

    async def delete(self, user_id: int, key: str) -> bool:
        memory = await self.mapper.get_by_key(user_id, key)
        if not memory:
            return False
        result = await self.mapper.delete_by_id(memory.id)
        await self.db.commit()
        return result
