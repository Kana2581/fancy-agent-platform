from typing import List

from sqlalchemy import delete, select

from app.mappers.base_mapper import BaseMapper
from app.models.agent_builtin_tool import AgentBuiltinTool


class AgentBuiltinToolMapper(BaseMapper[AgentBuiltinTool]):
    model = AgentBuiltinTool

    async def list_by_agent_id(self, agent_id: int) -> List[AgentBuiltinTool]:
        stmt = select(self.model).where(self.model.agent_id == agent_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def sync_bind(self, agent_id: int, tool_types: List[str]) -> None:
        current = await self.list_by_agent_id(agent_id)
        current_types = {row.tool_type for row in current}
        new_types = set(tool_types)

        to_remove = current_types - new_types
        to_add = new_types - current_types

        if to_remove:
            stmt = delete(self.model).where(
                self.model.agent_id == agent_id,
                self.model.tool_type.in_(to_remove),
            )
            await self.db.execute(stmt)

        if to_add:
            rows = [self.model(agent_id=agent_id, tool_type=t) for t in to_add]
            self.db.add_all(rows)

        await self.db.flush()
