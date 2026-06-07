from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.deps.db import get_db
from app.deps.user import get_current_user
from app.schemas.scheduled_task_schema import (
    ScheduledTaskCreate,
    ScheduledTaskExecutionPageOut,
    ScheduledTaskOut,
    ScheduledTaskUpdate,
)
from app.services.scheduled_task_service import ScheduledTaskService

router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])


@router.get("", response_model=List[ScheduledTaskOut])
async def list_tasks(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ScheduledTaskService(db).list(user_id)


@router.post("", response_model=ScheduledTaskOut)
async def create_task(
    data: ScheduledTaskCreate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ScheduledTaskService(db).create(user_id, data)


@router.put("/{task_id}", response_model=ScheduledTaskOut)
async def update_task(
    task_id: int,
    data: ScheduledTaskUpdate,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await ScheduledTaskService(db).update(task_id, user_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return result


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await ScheduledTaskService(db).delete(task_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True}


@router.post("/{task_id}/run")
async def run_task_now(
    task_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await ScheduledTaskService(db).run_now(task_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True}


@router.get("/{task_id}/executions", response_model=ScheduledTaskExecutionPageOut)
async def list_executions(
    task_id: int,
    page: int = 1,
    page_size: int = 20,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, total = await ScheduledTaskService(db).list_executions(task_id, user_id, page, page_size)
    return ScheduledTaskExecutionPageOut(items=items, total=total)
