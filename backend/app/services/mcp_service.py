import json
from typing import List, Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db
from app.mappers.mcp_mapper import MCPMapper
from app.models.mcp import MCP
from app.schemas.mcp_schema import MCPCreate, MCPUpdate

class MCPService:
    def __init__(self, db:AsyncSession):
        self.db = db
        self.mapper = MCPMapper(db=db)

    async def create_mcp(self, data: dict) -> MCP:
        res=await self.mapper.create_from_dict(data)
        await self.db.commit()
        return res

    async def update_mcp(self, mcp_id: int, data: MCPUpdate) -> Optional[MCP]:
        res=await self.mapper.update_by_id(
            mcp_id,
            data.model_dump(exclude_unset=True)
        )
        await self.db.commit()
        return res

    async def delete_mcp(self, mcp_id: int) -> bool:
        res = await self.mapper.delete_by_id(mcp_id)
        await self.db.commit()
        return res

    async def get_mcp(self, mcp_id: int) -> Optional[MCP]:
        return await self.mapper.get_by_id(mcp_id)

    async def list_mcps_by_user(self, user_id: int, offset: int = 0, limit: int = 100) -> List[MCP]:
        return await self.mapper.list_by_filters(
            filters={"user_id": user_id},
            offset=offset,
            limit=limit
        )

    async def extract_mcp(self, mcp_id: int) -> list[BaseTool] | None:
        # 1. 从数据库获取 MCP
        mcp: MCP = await self.mapper.get_by_id(mcp_id)
        if not mcp:
            return None

        # 2. 尝试从 config_json 中读取配置
        config = mcp.config_json or {}
        # 如果 config_json 是字符串，需要先转成 dict
        if isinstance(config, str):
            config = json.loads(config)

        # 3. 构建客户端参数
        client_config = {
            mcp.mcp_name: {
                "transport": mcp.transport,
                **config  # 将 config_json 里的内容直接解包到字典里
            }
        }

        client = MultiServerMCPClient(client_config)

        # 4. 获取 tools
        tools = await client.get_tools()
        return tools