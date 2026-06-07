from typing import List

from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.scheduled_task import ScheduledTask


class ScheduledTaskMapper(BaseMapper[ScheduledTask]):
    model = ScheduledTask

    async def get_by_user_id(self, user_id: int) -> List[ScheduledTask]:
        stmt = select(ScheduledTask).where(ScheduledTask.user_id == user_id).order_by(ScheduledTask.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_enabled_tasks(self) -> List[ScheduledTask]:
        result = await self.db.execute(
            select(ScheduledTask)
            .where(ScheduledTask.is_enabled == True)
            .order_by(ScheduledTask.updated_at.asc(), ScheduledTask.id.asc())
        )
        return list(result.scalars().all())
