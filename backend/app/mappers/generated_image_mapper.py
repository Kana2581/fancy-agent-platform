from sqlalchemy import select, func

from app.mappers.base_mapper import BaseMapper
from app.models.generated_image import GeneratedImage


class GeneratedImageMapper(BaseMapper[GeneratedImage]):
    model = GeneratedImage

    async def count_by_user(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(GeneratedImage).where(GeneratedImage.user_id == user_id)
        )
        return result.scalar() or 0
