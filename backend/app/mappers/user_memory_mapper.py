from typing import List, Optional

from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.user_memory import UserMemory


class UserMemoryMapper(BaseMapper[UserMemory]):
    model = UserMemory

    async def search_by_keyword(self, user_id: int, keyword: str) -> List[UserMemory]:
        result = await self.db.execute(
            select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.key.ilike(f"%{keyword}%"),
            )
        )
        return list(result.scalars().all())

    async def get_by_key(self, user_id: int, key: str) -> Optional[UserMemory]:
        result = await self.db.execute(
            select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.key == key,
            )
        )
        return result.scalars().first()

    async def list_by_user(
        self,
        user_id: int,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[UserMemory]:
        filters = {"user_id": user_id}
        if memory_type:
            filters["memory_type"] = memory_type
        if category:
            filters["category"] = category
        return await self.list_by_filters(filters=filters)

    async def upsert(
        self,
        user_id: int,
        key: str,
        content: str,
        memory_type: str = "normal",
        category: Optional[str] = None,
    ) -> UserMemory:
        existing = await self.get_by_key(user_id, key)
        if existing:
            update_data = {"content": content, "memory_type": memory_type}
            if category is not None:
                update_data["category"] = category
            return await self.update_by_id(existing.id, update_data)
        return await self.create_from_dict(
            {
                "user_id": user_id,
                "key": key,
                "content": content,
                "memory_type": memory_type,
                "category": category,
            }
        )
