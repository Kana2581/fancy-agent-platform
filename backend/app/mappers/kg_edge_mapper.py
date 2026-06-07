from typing import List, Optional

from sqlalchemy import select, or_

from app.mappers.base_mapper import BaseMapper
from app.models.kg_edge import KGEdge


class KGEdgeMapper(BaseMapper[KGEdge]):
    model = KGEdge

    async def list_by_graph(self, graph_id: int) -> List[KGEdge]:
        result = await self.db.execute(
            select(KGEdge).where(KGEdge.graph_id == graph_id)
        )
        return result.scalars().all()

    async def get_neighbors(self, graph_id: int, node_id: int) -> List[KGEdge]:
        result = await self.db.execute(
            select(KGEdge).where(
                KGEdge.graph_id == graph_id,
                or_(KGEdge.source_node_id == node_id, KGEdge.target_node_id == node_id),
            )
        )
        return result.scalars().all()

    async def find_duplicate(
        self, graph_id: int, source_node_id: int, target_node_id: int, relation: str
    ) -> Optional[KGEdge]:
        result = await self.db.execute(
            select(KGEdge).where(
                KGEdge.graph_id == graph_id,
                KGEdge.source_node_id == source_node_id,
                KGEdge.target_node_id == target_node_id,
                KGEdge.relation == relation,
            )
        )
        return result.scalar_one_or_none()
