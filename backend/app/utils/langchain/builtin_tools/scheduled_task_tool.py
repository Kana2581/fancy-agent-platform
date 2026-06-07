import json
from typing import List, Literal, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.deps.db import get_db_session
from app.schemas.scheduled_task_schema import ScheduledTaskCreate, ScheduledTaskUpdate
from app.services.scheduled_task_service import ScheduledTaskService


class CreateScheduledTaskInput(BaseModel):
    name: str = Field(description="任务名称")
    instruction: str = Field(description="发给 Agent 的指令内容")
    schedule_type: Literal["daily", "weekly", "monthly"] = Field(description="执行频率：daily 每天 / weekly 每周 / monthly 每月")
    schedule_time: str = Field(description="执行时间，格式 HH:MM，例如 09:00")
    schedule_day: Optional[int] = Field(default=None, description="weekly 时为星期几（0=周一…6=周日），monthly 时为几号（1-31），daily 时不填")
    timezone: str = Field(default="Asia/Shanghai", description="时区，默认 Asia/Shanghai")


class UpdateScheduledTaskInput(BaseModel):
    task_id: int = Field(description="要修改的任务 ID")
    name: Optional[str] = Field(default=None, description="新的任务名称")
    instruction: Optional[str] = Field(default=None, description="新的指令内容")
    schedule_type: Optional[Literal["daily", "weekly", "monthly"]] = Field(default=None, description="新的执行频率")
    schedule_time: Optional[str] = Field(default=None, description="新的执行时间 HH:MM")
    schedule_day: Optional[int] = Field(default=None, description="新的 schedule_day")
    timezone: Optional[str] = Field(default=None, description="新的时区")
    is_enabled: Optional[bool] = Field(default=None, description="是否启用")


def build_scheduled_task_tools(user_id: int, agent_id: int) -> List[BaseTool]:
    class ListScheduledTasksTool(BaseTool):
        name: str = "list_scheduled_tasks"
        description: str = "列出当前用户的所有定时任务，返回任务 ID、名称、执行频率、时间、是否启用等信息"
        args_schema: Type[BaseModel] = BaseModel

        async def _arun(self, **kwargs) -> str:
            async with get_db_session() as db:
                tasks = await ScheduledTaskService(db).list(user_id)
                result = [
                    {
                        "id": t.id,
                        "name": t.name,
                        "agent_id": t.agent_id,
                        "schedule_type": t.schedule_type,
                        "schedule_time": t.schedule_time,
                        "schedule_day": t.schedule_day,
                        "timezone": t.timezone,
                        "is_enabled": t.is_enabled,
                        "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
                        "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
                        "instruction": t.instruction,
                    }
                    for t in tasks
                ]
                return json.dumps(result, ensure_ascii=False)

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class CreateScheduledTaskTool(BaseTool):
        name: str = "create_scheduled_task"
        description: str = "创建一个新的定时任务，指定指令内容和调度计划（agent 自动为当前 agent）"
        args_schema: Type[BaseModel] = CreateScheduledTaskInput

        async def _arun(
            self,
            name: str,
            instruction: str,
            schedule_type: str,
            schedule_time: str,
            schedule_day: Optional[int] = None,
            timezone: str = "Asia/Shanghai",
        ) -> str:
            async with get_db_session() as db:
                data = ScheduledTaskCreate(
                    agent_id=agent_id,
                    name=name,
                    instruction=instruction,
                    schedule_type=schedule_type,
                    schedule_time=schedule_time,
                    schedule_day=schedule_day,
                    timezone=timezone,
                )
                task = await ScheduledTaskService(db).create(user_id, data)
                return json.dumps(
                    {
                        "id": task.id,
                        "name": task.name,
                        "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
                    },
                    ensure_ascii=False,
                )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class UpdateScheduledTaskTool(BaseTool):
        name: str = "update_scheduled_task"
        description: str = "修改已有定时任务，可更新名称、指令、调度计划或启用状态"
        args_schema: Type[BaseModel] = UpdateScheduledTaskInput

        async def _arun(
            self,
            task_id: int,
            name: Optional[str] = None,
            instruction: Optional[str] = None,
            schedule_type: Optional[str] = None,
            schedule_time: Optional[str] = None,
            schedule_day: Optional[int] = None,
            timezone: Optional[str] = None,
            is_enabled: Optional[bool] = None,
        ) -> str:
            async with get_db_session() as db:
                data = ScheduledTaskUpdate(
                    name=name,
                    instruction=instruction,
                    schedule_type=schedule_type,
                    schedule_time=schedule_time,
                    schedule_day=schedule_day,
                    timezone=timezone,
                    is_enabled=is_enabled,
                )
                task = await ScheduledTaskService(db).update(task_id, user_id, data)
                if not task:
                    return json.dumps({"error": f"未找到 ID 为 {task_id} 的任务"}, ensure_ascii=False)
                return json.dumps(
                    {
                        "id": task.id,
                        "name": task.name,
                        "is_enabled": task.is_enabled,
                        "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
                    },
                    ensure_ascii=False,
                )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    return [ListScheduledTasksTool(), CreateScheduledTaskTool(), UpdateScheduledTaskTool()]
