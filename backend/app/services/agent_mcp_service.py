# app/services/agent_mcp_service.py
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.agent_mcp_mapper import AgentMCPMapper

from app.models.agent import Agent


class AgentMCPService:
    def __init__(self, db:AsyncSession):
        self.db = db
        self.mapper = AgentMCPMapper(db)

    async def list_mcps_for_agent(self, agent_id:int) -> List[int]:
        rows = await self.mapper.list_by_agent_id(agent_id)
        return [r.mcp_id for r in rows]

    async def bind_mcps(self, agent_id: int, mcp_ids: List[int]) -> List[int]:
        await self.mapper.sync_bind(agent_id, mcp_ids)
        await self.db.commit()

        return None

    async def unbind_mcps(self, agent_id:int , mcp_ids: List[int]) -> int:
        res = await self.mapper.bulk_unbind(agent_id, mcp_ids)
        await self.db.commit()
        return res
