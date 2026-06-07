from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.scheduled_task_schema import ScheduledTaskCreate, ScheduledTaskUpdate
from app.services.scheduled_task_service import ScheduledTaskService


class TestScheduledTaskService:
    async def test_create_sets_next_run_without_last_run(self, async_session: AsyncSession):
        service = ScheduledTaskService(async_session)

        task = await service.create(
            1,
            ScheduledTaskCreate(
                agent_id=1,
                name="daily-report",
                instruction="run",
                schedule_type="daily",
                schedule_time="09:00",
                timezone="Asia/Shanghai",
            ),
        )

        assert task.last_run_at is None
        assert task.next_run_at is not None

    async def test_update_schedule_preserves_last_run_and_recomputes_next_run(self, async_session: AsyncSession):
        service = ScheduledTaskService(async_session)
        task = await service.create(
            1,
            ScheduledTaskCreate(
                agent_id=1,
                name="daily-report",
                instruction="run",
                schedule_type="daily",
                schedule_time="09:00",
                timezone="Asia/Shanghai",
            ),
        )
        task.last_run_at = datetime(2026, 5, 31, 1, 0, 0)
        await async_session.commit()

        updated = await service.update(
            task.id,
            1,
            ScheduledTaskUpdate(schedule_time="10:00"),
        )

        assert updated is not None
        assert updated.last_run_at == datetime(2026, 5, 31, 1, 0, 0)
        assert updated.next_run_at is not None

    async def test_enabling_task_recomputes_next_run_without_resetting_last_run(self, async_session: AsyncSession):
        service = ScheduledTaskService(async_session)
        task = await service.create(
            1,
            ScheduledTaskCreate(
                agent_id=1,
                name="weekly-report",
                instruction="run",
                schedule_type="weekly",
                schedule_time="09:00",
                schedule_day=0,
                timezone="Asia/Shanghai",
            ),
        )
        task.is_enabled = False
        task.last_run_at = datetime(2026, 5, 26, 1, 0, 0)
        task.next_run_at = None
        await async_session.commit()

        updated = await service.update(
            task.id,
            1,
            ScheduledTaskUpdate(is_enabled=True),
        )

        assert updated is not None
        assert updated.is_enabled is True
        assert updated.last_run_at == datetime(2026, 5, 26, 1, 0, 0)
        assert updated.next_run_at is not None
