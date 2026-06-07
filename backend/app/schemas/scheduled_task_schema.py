from datetime import datetime
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel


class ScheduledTaskCreate(BaseModel):
    agent_id: int
    name: str
    instruction: str
    schedule_type: Literal["daily", "weekly", "monthly"]
    schedule_time: str          # HH:MM
    schedule_day: Optional[int] = None
    timezone: str = "Asia/Shanghai"


class ScheduledTaskUpdate(BaseModel):
    agent_id: Optional[int] = None
    name: Optional[str] = None
    instruction: Optional[str] = None
    schedule_type: Optional[Literal["daily", "weekly", "monthly"]] = None
    schedule_time: Optional[str] = None
    schedule_day: Optional[int] = None
    timezone: Optional[str] = None
    is_enabled: Optional[bool] = None


class ScheduledTaskOut(BaseModel):
    id: int
    user_id: int
    agent_id: int
    name: str
    instruction: str
    schedule_type: str
    schedule_time: str
    schedule_day: Optional[int]
    timezone: str
    is_enabled: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduledTaskExecutionOut(BaseModel):
    id: int
    task_id: int
    status: str
    result: Optional[str]
    email_sent: bool
    error: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduledTaskExecutionPageOut(BaseModel):
    items: List[ScheduledTaskExecutionOut]
    total: int
