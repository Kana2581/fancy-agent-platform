from typing import List, Optional

from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.kg_node import KGNode


class KGNodeMapper(BaseMapper[KGNode]):
    model = KGNode

    async def get_by_name(self, graph_id: int, name: str) -> Optional[KGNode]:
        result = await self.db.execute(
            select(KGNode).where(KGNode.graph_id == graph_id, KGNode.name == name)
        )
        return result.scalar_one_or_none()

    async def search(self, graph_id: int, query: str, type_filter: Optional[str] = None) -> List[KGNode]:
        stmt = select(KGNode).where(KGNode.graph_id == graph_id)
        if query:
            stmt = stmt.where(
                KGNode.name.ilike(f"%{query}%") | KGNode.description.ilike(f"%{query}%")
            )
        if type_filter:
            stmt = stmt.where(KGNode.type == type_filter)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_ids(self, ids: List[int]) -> List[KGNode]:
        if not ids:
            return []
        result = await self.db.execute(select(KGNode).where(KGNode.id.in_(ids)))
        return list(result.scalars().all())

    async def upsert(
        self,
        graph_id: int,
        user_id: int,
        name: str,
        type_: str,
        description: Optional[str],
        properties: Optional[dict],
    ) -> KGNode:
        existing = await self.get_by_name(graph_id, name)
        if existing:
            update_data = {"type": type_}
            if description is not None:
                update_data["description"] = description
            if properties is not None:
                update_data["properties"] = properties
            return await self.update_by_id(existing.id, update_data)
        return await self.create_from_dict({
            "graph_id": graph_id,
            "user_id": user_id,
            "name": name,
            "type": type_,
            "description": description,
            "properties": properties,
        })
