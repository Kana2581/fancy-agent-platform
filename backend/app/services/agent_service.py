# app/services/agent_service.py
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.mappers.agent_mapper import AgentMapper
from app.models.agent import Agent

class AgentService:
    def __init__(self, db:AsyncSession):
        self.db = db
        self.mapper = AgentMapper(db=db)

    # ================= 查询 =================
    async def get_agent(self, agent_id: int) -> Optional[Agent]:
        return await self.mapper.get_by_id(agent_id)
    async def get_full_agent(self, agent_id: int,user_id:int) -> Optional[Dict[str, Any]]:
        return await self.mapper.get_full_agent(agent_id,user_id)

    async def list_agents(
        self, filters: Dict[str, Any] = {}, offset: int = 0, limit: int = 100
    ) -> List[Agent]:
        return await self.mapper.list_by_filters(filters, offset, limit)

    async def agent_exists(self, **kwargs) -> bool:
        return await self.mapper.exists(**kwargs)

    # ================= 新增 =================
    async def create_agent(self, data: Dict[str, Any]) -> Agent:

        res = await self.mapper.create_from_dict(data)
        await self.db.commit()
        return res

    # ================= 更新 =================
    async def update_agent(self, agent_id: int, data: Dict[str, Any]) -> Optional[Agent]:
        res = await self.mapper.update_by_id(agent_id, data)
        await self.db.commit()
        return res

    # ================= 删除 =================
    async def delete_agent(self, agent_id: int) -> bool:

        res = await self.mapper.delete_by_id(agent_id)
        await self.db.commit()
        return res
