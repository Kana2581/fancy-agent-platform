from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.generated_image_mapper import GeneratedImageMapper
from app.models.generated_image import GeneratedImage
from app.schemas.generated_image_schema import GeneratedImageOut, GeneratedImagePageOut


class GeneratedImageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = GeneratedImageMapper(db=db)

    async def create(self, data: Dict[str, Any]) -> GeneratedImage:
        record = await self.mapper.create_from_dict(data)
        await self.db.commit()
        return record

    async def list_by_user(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> GeneratedImagePageOut:
        offset = (page - 1) * page_size
        total = await self.mapper.count_by_user(user_id)
        items = await self.mapper.list_by_filters(
            {"user_id": user_id}, offset=offset, limit=page_size
        )
        return GeneratedImagePageOut(
            items=[GeneratedImageOut.model_validate(i) for i in items],
            total=total,
        )

    async def get(self, record_id: int, user_id: int) -> Optional[GeneratedImage]:
        record = await self.mapper.get_by_id(record_id)
        if not record or record.user_id != user_id:
            return None
        return record

    async def delete(self, record_id: int, user_id: int) -> bool:
        record = await self.mapper.get_by_id(record_id)
        if not record or record.user_id != user_id:
            return False
        result = await self.mapper.delete_by_id(record_id)
        await self.db.commit()
        return result
