from typing import List

from sqlalchemy import delete, select

from app.mappers.base_mapper import BaseMapper
from app.models.agent_api_tool import AgentApiTool


class AgentApiToolMapper(BaseMapper[AgentApiTool]):
    model = AgentApiTool

    async def list_by_agent_id(self, agent_id: int) -> List[AgentApiTool]:
        stmt = select(self.model).where(self.model.agent_id == agent_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def bulk_bind(self, agent_id: int, tool_ids: List[int]) -> List[AgentApiTool]:
        binds = [self.model(agent_id=agent_id, api_tool_id=tid) for tid in tool_ids]
        self.db.add_all(binds)
        await self.db.flush()
        return binds

    async def bulk_unbind(self, agent_id: int, tool_ids: List[int]) -> int:
        if not tool_ids:
            return 0
        stmt = delete(self.model).where(
            self.model.agent_id == agent_id,
            self.model.api_tool_id.in_(tool_ids),
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def sync_bind(self, agent_id: int, tool_ids: List[int]) -> None:
        current = await self.list_by_agent_id(agent_id)
        current_ids = {x.api_tool_id for x in current}
        new_ids = set(tool_ids)

        to_add = new_ids - current_ids
        to_remove = current_ids - new_ids

        if to_remove:
            stmt = delete(self.model).where(
                self.model.agent_id == agent_id,
                self.model.api_tool_id.in_(to_remove),
            )
            await self.db.execute(stmt)

        if to_add:
            binds = [self.model(agent_id=agent_id, api_tool_id=tid) for tid in to_add]
            self.db.add_all(binds)

        await self.db.flush()
