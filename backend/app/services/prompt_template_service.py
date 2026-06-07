from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.prompt_template_mapper import PromptTemplateMapper
from app.schemas.prompt_template_schema import PromptTemplateUpdate
from app.models.prompt_template import PromptTemplate


class PromptTemplateService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = PromptTemplateMapper(db)

    async def create_prompt_template(self, data: dict) -> PromptTemplate:
        res = await self.mapper.create_from_dict(data)
        await self.db.commit()
        return res

    async def get_prompt_template(self, template_id: int) -> Optional[PromptTemplate]:
        return await self.mapper.get_by_id(template_id)

    async def list_by_user(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> List[PromptTemplate]:
        filters = {"user_id": user_id}
        if category:
            filters["category"] = category
        return await self.mapper.list_by_filters(
            filters=filters,
            offset=offset,
            limit=limit,
        )

    async def update_prompt_template(
        self, template_id: int, data: PromptTemplateUpdate
    ) -> Optional[PromptTemplate]:
        res = await self.mapper.update_by_id(
            template_id,
            data.model_dump(exclude_unset=True)
        )
        await self.db.commit()
        return res

    async def delete_prompt_template(self, template_id: int) -> bool:
        res = await self.mapper.delete_by_id(template_id)
        await self.db.commit()
        return res
