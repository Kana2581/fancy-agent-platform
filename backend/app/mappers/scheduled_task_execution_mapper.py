from typing import List, Tuple

from sqlalchemy import select, func

from app.mappers.base_mapper import BaseMapper
from app.models.scheduled_task_execution import ScheduledTaskExecution


class ScheduledTaskExecutionMapper(BaseMapper[ScheduledTaskExecution]):
    model = ScheduledTaskExecution

    async def list_by_task_id(
        self, task_id: int, page: int = 1, page_size: int = 20
    ) -> Tuple[List[ScheduledTaskExecution], int]:
        count_stmt = select(func.count()).where(ScheduledTaskExecution.task_id == task_id)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = (
            select(ScheduledTaskExecution)
            .where(ScheduledTaskExecution.task_id == task_id)
            .order_by(ScheduledTaskExecution.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total
