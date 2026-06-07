from typing import List

from sqlalchemy import delete, select

from app.mappers.base_mapper import BaseMapper
from app.models.agent_image_tool import AgentImageTool


class AgentImageToolMapper(BaseMapper[AgentImageTool]):
    model = AgentImageTool

    async def list_by_agent_id(self, agent_id: int) -> List[AgentImageTool]:
        stmt = select(self.model).where(self.model.agent_id == agent_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def bulk_bind(self, agent_id: int, image_tool_ids: List[int]) -> List[AgentImageTool]:
        binds = [self.model(agent_id=agent_id, image_tool_id=tid) for tid in image_tool_ids]
        self.db.add_all(binds)
        await self.db.flush()
        return binds

    async def bulk_unbind(self, agent_id: int, image_tool_ids: List[int]) -> int:
        if not image_tool_ids:
            return 0
        stmt = delete(self.model).where(
            self.model.agent_id == agent_id,
            self.model.image_tool_id.in_(image_tool_ids),
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def sync_bind(self, agent_id: int, image_tool_ids: List[int]) -> None:
        current = await self.list_by_agent_id(agent_id)
        current_ids = {x.image_tool_id for x in current}
        new_ids = set(image_tool_ids)

        to_add = new_ids - current_ids
        to_remove = current_ids - new_ids

        if to_remove:
            stmt = delete(self.model).where(
                self.model.agent_id == agent_id,
                self.model.image_tool_id.in_(to_remove),
            )
            await self.db.execute(stmt)

        if to_add:
            binds = [self.model(agent_id=agent_id, image_tool_id=tid) for tid in to_add]
            self.db.add_all(binds)

        await self.db.flush()
