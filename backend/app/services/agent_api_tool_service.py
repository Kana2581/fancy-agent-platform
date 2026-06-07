from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.agent_api_tool_mapper import AgentApiToolMapper


class AgentApiToolService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = AgentApiToolMapper(db)

    async def list_tools_for_agent(self, agent_id: int) -> List[int]:
        rows = await self.mapper.list_by_agent_id(agent_id)
        return [r.api_tool_id for r in rows]

    async def bind_tools(self, agent_id: int, tool_ids: List[int]) -> None:
        await self.mapper.sync_bind(agent_id, tool_ids)
        await self.db.commit()

    async def unbind_tools(self, agent_id: int, tool_ids: List[int]) -> int:
        res = await self.mapper.bulk_unbind(agent_id, tool_ids)
        await self.db.commit()
        return res
