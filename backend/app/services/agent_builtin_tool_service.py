from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.agent_builtin_tool_mapper import AgentBuiltinToolMapper
from app.utils.langchain.builtin_tools import VALID_BUILTIN_TOOL_TYPES


class AgentBuiltinToolService:
    def __init__(self, db: AsyncSession):
        self.mapper = AgentBuiltinToolMapper(db=db)
        self.db = db

    async def list_tool_types_for_agent(self, agent_id: int) -> List[str]:
        rows = await self.mapper.list_by_agent_id(agent_id)
        return [row.tool_type for row in rows]

    async def sync_tools(self, agent_id: int, tool_types: List[str]) -> List[str]:
        valid = [t for t in tool_types if t in VALID_BUILTIN_TOOL_TYPES]
        await self.mapper.sync_bind(agent_id, valid)
        await self.db.commit()
        return valid
