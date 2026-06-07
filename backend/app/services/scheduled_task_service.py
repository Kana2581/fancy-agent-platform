import asyncio
from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger
from app.deps.db import get_db_session
from app.mappers.scheduled_task_execution_mapper import ScheduledTaskExecutionMapper
from app.mappers.scheduled_task_mapper import ScheduledTaskMapper
from app.mappers.user_email_agent_mapper import UserEmailAgentMapper
from app.mappers.user_mapper import UserMapper
from app.models.scheduled_task import ScheduledTask
from app.models.scheduled_task_execution import ScheduledTaskExecution
from app.schemas.dto.langchian import ValidAgent
from app.schemas.scheduled_task_schema import ScheduledTaskCreate, ScheduledTaskUpdate
from app.services.agent_service import AgentService
from app.utils.langchain.agent_util import get_langchian_agent

logger = get_logger(__name__)

# 调度容差：允许调度器触发有少量偏差（5 秒）
SCHEDULE_JITTER = timedelta(seconds=5)


@dataclass(frozen=True)
class DueTaskWindow:
    scheduled_for: datetime
    next_run_at: datetime


def _get_task_timezone(tz: str) -> ZoneInfo:
    return ZoneInfo(tz)


def _to_utc_naive(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_naive_to_local(dt: datetime, tz: str) -> datetime:
    return dt.replace(tzinfo=timezone.utc).astimezone(_get_task_timezone(tz))


def _build_local_datetime(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    tz: str,
) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=_get_task_timezone(tz))


def _parse_schedule_time(schedule_time: str) -> tuple[int, int]:
    hour, minute = schedule_time.split(":")
    return int(hour), int(minute)


def _require_schedule_day(schedule_type: str, schedule_day: Optional[int]) -> int:
    if schedule_type in {"weekly", "monthly"} and schedule_day is None:
        raise ValueError(f"{schedule_type} 任务必须提供 schedule_day")
    return schedule_day or 0


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    absolute_month = year * 12 + (month - 1) + delta
    return absolute_month // 12, absolute_month % 12 + 1


def _get_latest_monthly_candidate(
    schedule_day: int,
    hour: int,
    minute: int,
    tz: str,
    reference_local: datetime,
) -> datetime:
    year = reference_local.year
    month = reference_local.month

    while True:
        days_in_month = monthrange(year, month)[1]
        if schedule_day <= days_in_month:
            candidate = _build_local_datetime(year, month, schedule_day, hour, minute, tz)
            if candidate <= reference_local:
                return candidate
        year, month = _shift_month(year, month, -1)


def _get_next_monthly_candidate(
    schedule_day: int,
    hour: int,
    minute: int,
    tz: str,
    reference_local: datetime,
) -> datetime:
    year = reference_local.year
    month = reference_local.month

    while True:
        days_in_month = monthrange(year, month)[1]
        if schedule_day <= days_in_month:
            candidate = _build_local_datetime(year, month, schedule_day, hour, minute, tz)
            if candidate > reference_local:
                return candidate
        year, month = _shift_month(year, month, 1)


def get_latest_scheduled_run_at(
    schedule_type: str,
    schedule_time: str,
    schedule_day: Optional[int],
    tz: str,
    reference_utc: datetime,
) -> datetime:
    hour, minute = _parse_schedule_time(schedule_time)
    reference_local = _utc_naive_to_local(reference_utc, tz)

    if schedule_type == "daily":
        candidate = reference_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > reference_local:
            candidate -= timedelta(days=1)
        return _to_utc_naive(candidate)

    if schedule_type == "weekly":
        target_weekday = _require_schedule_day(schedule_type, schedule_day)
        days_back = (reference_local.weekday() - target_weekday) % 7
        candidate = (
            reference_local - timedelta(days=days_back)
        ).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > reference_local:
            candidate -= timedelta(days=7)
        return _to_utc_naive(candidate)

    if schedule_type == "monthly":
        target_day = _require_schedule_day(schedule_type, schedule_day)
        candidate = _get_latest_monthly_candidate(target_day, hour, minute, tz, reference_local)
        return _to_utc_naive(candidate)

    raise ValueError(f"不支持的 schedule_type: {schedule_type}")


def get_next_scheduled_run_at(
    schedule_type: str,
    schedule_time: str,
    schedule_day: Optional[int],
    tz: str,
    reference_utc: datetime,
) -> datetime:
    hour, minute = _parse_schedule_time(schedule_time)
    reference_local = _utc_naive_to_local(reference_utc, tz)

    if schedule_type == "daily":
        candidate = reference_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= reference_local:
            candidate += timedelta(days=1)
        return _to_utc_naive(candidate)

    if schedule_type == "weekly":
        target_weekday = _require_schedule_day(schedule_type, schedule_day)
        days_ahead = (target_weekday - reference_local.weekday()) % 7
        candidate = (
            reference_local + timedelta(days=days_ahead)
        ).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= reference_local:
            candidate += timedelta(days=7)
        return _to_utc_naive(candidate)

    if schedule_type == "monthly":
        target_day = _require_schedule_day(schedule_type, schedule_day)
        candidate = _get_next_monthly_candidate(target_day, hour, minute, tz, reference_local)
        return _to_utc_naive(candidate)

    raise ValueError(f"不支持的 schedule_type: {schedule_type}")


def compute_next_run(
    schedule_type: str,
    schedule_time: str,
    schedule_day: Optional[int],
    tz: str,
    *,
    reference_utc: Optional[datetime] = None,
) -> datetime:
    reference = reference_utc or datetime.now(timezone.utc).replace(tzinfo=None)
    return get_next_scheduled_run_at(schedule_type, schedule_time, schedule_day, tz, reference)


def get_due_task_window(
    task: ScheduledTask,
    window_end: datetime,
) -> Optional[DueTaskWindow]:
    scheduled_for = get_latest_scheduled_run_at(
        task.schedule_type,
        task.schedule_time,
        task.schedule_day,
        task.timezone,
        window_end,
    )
    lower_bound = task.last_run_at or task.updated_at or task.created_at
    if lower_bound and scheduled_for <= lower_bound:
        return None

    next_run_at = get_next_scheduled_run_at(
        task.schedule_type,
        task.schedule_time,
        task.schedule_day,
        task.timezone,
        scheduled_for,
    )
    return DueTaskWindow(scheduled_for=scheduled_for, next_run_at=next_run_at)


class ScheduledTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = ScheduledTaskMapper(db)
        self.exec_mapper = ScheduledTaskExecutionMapper(db)

    async def list(self, user_id: int) -> List[ScheduledTask]:
        return await self.mapper.get_by_user_id(user_id)

    async def get(self, task_id: int, user_id: int) -> Optional[ScheduledTask]:
        task = await self.mapper.get_by_id(task_id)
        if task and task.user_id == user_id:
            return task
        return None

    async def create(self, user_id: int, data: ScheduledTaskCreate) -> ScheduledTask:
        next_run = compute_next_run(
            data.schedule_type,
            data.schedule_time,
            data.schedule_day,
            data.timezone,
        )
        task = await self.mapper.create_from_dict({
            "user_id": user_id,
            "agent_id": data.agent_id,
            "name": data.name,
            "instruction": data.instruction,
            "schedule_type": data.schedule_type,
            "schedule_time": data.schedule_time,
            "schedule_day": data.schedule_day,
            "timezone": data.timezone,
            "is_enabled": True,
            "next_run_at": next_run,
        })
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update(self, task_id: int, user_id: int, data: ScheduledTaskUpdate) -> Optional[ScheduledTask]:
        task = await self.get(task_id, user_id)
        if not task:
            return None

        updates = data.model_dump(exclude_unset=True)
        schedule_fields = {"schedule_type", "schedule_time", "schedule_day", "timezone"}
        schedule_changed = bool(schedule_fields & updates.keys())
        enabled_changed_to_true = updates.get("is_enabled") is True and not task.is_enabled

        if schedule_changed or enabled_changed_to_true:
            schedule_type = updates.get("schedule_type", task.schedule_type)
            schedule_time = updates.get("schedule_time", task.schedule_time)
            schedule_day = updates.get("schedule_day", task.schedule_day)
            tz = updates.get("timezone", task.timezone)
            updates["next_run_at"] = compute_next_run(
                schedule_type,
                schedule_time,
                schedule_day,
                tz,
            )

        updated = await self.mapper.update_by_id(task_id, updates)
        await self.db.commit()
        await self.db.refresh(updated)
        return updated

    async def delete(self, task_id: int, user_id: int) -> bool:
        task = await self.get(task_id, user_id)
        if not task:
            return False
        result = await self.mapper.delete_by_id(task_id)
        await self.db.commit()
        return result

    async def list_executions(
        self, task_id: int, user_id: int, page: int = 1, page_size: int = 20
    ) -> Tuple[List[ScheduledTaskExecution], int]:
        task = await self.get(task_id, user_id)
        if not task:
            return [], 0
        return await self.exec_mapper.list_by_task_id(task_id, page, page_size)

    async def run_now(self, task_id: int, user_id: int) -> bool:
        task = await self.get(task_id, user_id)
        if not task:
            return False
        asyncio.create_task(_execute_single_task(task))
        return True


# ── Background execution ────────────────────────────────────────────────────

async def execute_due_tasks():
    """Called by APScheduler every N seconds to fire due tasks."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    check_interval = timedelta(seconds=settings.SCHEDULED_TASK_CHECK_INTERVAL)
    window_end = now + SCHEDULE_JITTER

    try:
        due_tasks: list[ScheduledTask] = []

        async with get_db_session() as db:
            mapper = ScheduledTaskMapper(db)
            tasks = await mapper.get_enabled_tasks()
            skipped_count = 0

            logger.info(
                f"[定时任务] 扫描启用任务 {len(tasks)} 条 | "
                f"窗口结束: {window_end.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            for task in tasks:
                due_window = get_due_task_window(task, window_end)
                if due_window is None:
                    skipped_count += 1
                    continue

                logger.info(
                    f"[定时任务] 命中任务 id={task.id} name={task.name} | "
                    f"scheduled_for={due_window.scheduled_for.strftime('%Y-%m-%d %H:%M:%S')} UTC | "
                    f"old_last_run_at={task.last_run_at.strftime('%Y-%m-%d %H:%M:%S') if task.last_run_at else 'None'} UTC | "
                    f"new_next_run_at={due_window.next_run_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                )

                await mapper.update_by_id(task.id, {
                    "last_run_at": due_window.scheduled_for,
                    "next_run_at": due_window.next_run_at,
                })
                task.last_run_at = due_window.scheduled_for
                task.next_run_at = due_window.next_run_at
                due_tasks.append(task)

            logger.info(
                f"[定时任务] 规则命中 {len(due_tasks)} 条 | "
                f"跳过 {skipped_count} 条 | "
                f"检查间隔 {check_interval.total_seconds():.0f} 秒"
            )

            if not due_tasks:
                return

            await db.commit()

        await asyncio.gather(*[_execute_single_task(task) for task in due_tasks])

    except Exception as e:
        logger.error(f"execute_due_tasks 失败: {e}", exc_info=True)


async def _execute_single_task(task: ScheduledTask):
    from app.services.email_polling_service import send_notification_email

    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    execution_id: Optional[int] = None

    try:
        async with get_db_session() as db:
            agent_data = await AgentService(db).get_full_agent(task.agent_id, task.user_id)
        if not agent_data:
            raise ValueError(f"Agent {task.agent_id} 不存在或不属于用户 {task.user_id}")

        async with get_db_session() as db:
            exec_obj = await ScheduledTaskExecutionMapper(db).create_from_dict({
                "task_id": task.id,
                "status": "running",
                "email_sent": False,
                "started_at": started_at,
            })
            await db.commit()
            await db.refresh(exec_obj)
            execution_id = exec_obj.id

        agent = await get_langchian_agent(ValidAgent.model_validate(agent_data))
        result = await agent.ainvoke({"messages": [HumanMessage(content=task.instruction)]})
        messages = result.get("messages", [])
        ai_reply = next(
            (m for m in reversed(messages) if getattr(m, "type", "") == "ai"),
            None,
        )
        reply_text = (
            ai_reply.content if ai_reply and isinstance(ai_reply.content, str)
            else str(ai_reply.content) if ai_reply
            else ""
        )

        email_sent = False
        async with get_db_session() as db:
            user = await UserMapper(db).get_by_id(task.user_id)
            email_agent_config = await UserEmailAgentMapper(db).get_by_user_id(task.user_id)

        if user and user.email and email_agent_config and email_agent_config.is_enabled:
            email_sent = await send_notification_email(
                to_email=user.email,
                subject=f"[定时任务] {task.name}",
                body=reply_text,
            )

        async with get_db_session() as db:
            await ScheduledTaskExecutionMapper(db).update_by_id(execution_id, {
                "status": "success",
                "result": reply_text,
                "email_sent": email_sent,
                "completed_at": datetime.now(timezone.utc).replace(tzinfo=None),
            })
            await db.commit()

        logger.info(f"定时任务 {task.id} ({task.name}) 执行成功")

    except Exception as e:
        logger.error(f"定时任务 {task.id} 执行失败: {e}", exc_info=True)
        if execution_id:
            try:
                async with get_db_session() as db:
                    await ScheduledTaskExecutionMapper(db).update_by_id(execution_id, {
                        "status": "failed",
                        "error": str(e),
                        "completed_at": datetime.now(timezone.utc).replace(tzinfo=None),
                    })
                    await db.commit()
            except Exception as ex:
                logger.error(f"更新执行记录失败: {ex}", exc_info=True)
        else:
            try:
                async with get_db_session() as db:
                    await ScheduledTaskExecutionMapper(db).create_from_dict({
                        "task_id": task.id,
                        "status": "failed",
                        "email_sent": False,
                        "error": str(e),
                        "started_at": started_at,
                        "completed_at": datetime.now(timezone.utc).replace(tzinfo=None),
                    })
                    await db.commit()
            except Exception:
                pass
