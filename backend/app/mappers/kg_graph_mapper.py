from typing import List, Optional

from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.kg_graph import KGGraph


class KGGraphMapper(BaseMapper[KGGraph]):
    model = KGGraph

    async def list_by_user(self, user_id: int) -> List[KGGraph]:
        result = await self.db.execute(
            select(KGGraph).where(KGGraph.user_id == user_id).order_by(KGGraph.created_at)
        )
        return result.scalars().all()

    async def get_by_name(self, user_id: int, name: str) -> Optional[KGGraph]:
        result = await self.db.execute(
            select(KGGraph).where(KGGraph.user_id == user_id, KGGraph.name == name)
        )
        return result.scalar_one_or_none()
