from typing import List

from sqlalchemy import delete, select

from app.mappers.base_mapper import BaseMapper
from app.models.agent_mcp import AgentMCP

class AgentMCPMapper(BaseMapper[AgentMCP]):
    model = AgentMCP

    # ================= 查询 =================
    async def list_by_agent_id(self, agent_id: int) -> List[AgentMCP]:
        stmt = select(self.model).where(self.model.agent_id == agent_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ================= 绑定 =================
    async def bulk_bind(self, agent_id: int, mcp_ids: List[int]) -> List[AgentMCP]:
        binds = [self.model(agent_id=agent_id, mcp_id=mcp_id) for mcp_id in mcp_ids]

        self.db.add_all(binds)
        await self.db.flush()
        return binds

    # ================= 解绑 =================
    async def bulk_unbind(self, agent_id: int, mcp_ids: List[int]) -> int:
        if not mcp_ids:
            return 0
        stmt = delete(self.model).where(
            self.model.agent_id == agent_id,
            self.model.mcp_id.in_(mcp_ids)
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def sync_bind(self, agent_id: int, mcp_ids: List[int]) -> None:
        # 当前绑定
        current = await self.list_by_agent_id(agent_id)
        current_ids = {x.mcp_id for x in current}

        new_ids = set(mcp_ids)

        # 差集计算
        to_add = new_ids - current_ids
        to_remove = current_ids - new_ids

        # 删除
        if to_remove:
            stmt = delete(self.model).where(
                self.model.agent_id == agent_id,
                self.model.mcp_id.in_(to_remove)
            )
            await self.db.execute(stmt)

        # 新增
        if to_add:
            binds = [
                self.model(agent_id=agent_id, mcp_id=mcp_id)
                for mcp_id in to_add
            ]
            self.db.add_all(binds)

        await self.db.flush()