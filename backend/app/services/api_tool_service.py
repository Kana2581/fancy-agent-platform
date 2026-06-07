from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.api_tool_mapper import ApiToolMapper
from app.models.api_tool import ApiTool
from app.schemas.api_tool_schema import ApiToolUpdate


class ApiToolService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = ApiToolMapper(db)

    async def create_tool(self, data: Dict[str, Any]) -> ApiTool:
        res = await self.mapper.create_from_dict(data)
        await self.db.commit()
        return res

    async def get_tool(self, tool_id: int) -> Optional[ApiTool]:
        return await self.mapper.get_by_id(tool_id)

    async def list_tools_by_user(
        self, user_id: int, offset: int = 0, limit: int = 100
    ) -> List[ApiTool]:
        return await self.mapper.list_by_filters(
            filters={"user_id": user_id}, offset=offset, limit=limit
        )

    async def update_tool(self, tool_id: int, data: ApiToolUpdate) -> Optional[ApiTool]:
        res = await self.mapper.update_by_id(
            tool_id, data.model_dump(exclude_unset=True)
        )
        await self.db.commit()
        return res

    async def delete_tool(self, tool_id: int) -> bool:
        res = await self.mapper.delete_by_id(tool_id)
        await self.db.commit()
        return res
