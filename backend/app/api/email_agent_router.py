from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.deps.db import get_db
from app.deps.user import get_current_user
from app.mappers.user_mapper import UserMapper
from app.schemas.user_email_agent_schema import (
    UserEmailAgentCreate,
    UserEmailAgentUpdate,
    UserEmailAgentOut,
)
from app.services.email_polling_service import send_notification_email
from app.services.user_email_agent_service import UserEmailAgentService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/email-agent", tags=["email-agent"])


@router.get("", response_model=UserEmailAgentOut)
async def get_email_agent(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserEmailAgentService(db)
    config = await service.get_by_user_id(user_id)
    if not config:
        raise HTTPException(status_code=404, detail="未配置邮件 Agent")
    return config


@router.post("", response_model=UserEmailAgentOut)
async def create_email_agent(
    data: UserEmailAgentCreate,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserEmailAgentService(db)
    existing = await service.get_by_user_id(user_id)
    if existing:
        raise HTTPException(status_code=400, detail="已存在邮件 Agent 配置，请使用 PUT 更新")
    result = await service.create(user_id=user_id, agent_id=data.agent_id)

    user = await UserMapper(db).get_by_id(user_id)
    if user and user.email:
        background_tasks.add_task(
            send_notification_email,
            user.email,
            "邮件 Agent 配置成功",
            f"您好，\n\n您已成功配置邮件 Agent（Agent ID: {data.agent_id}）。\n"
            f"今后您可以直接发邮件与该 Agent 对话，系统会自动为您回复。\n\n— Fancy Agent",
        )

    return result


@router.put("", response_model=UserEmailAgentOut)
async def update_email_agent(
    data: UserEmailAgentUpdate,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserEmailAgentService(db)
    obj = await service.update(user_id=user_id, data=data.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="未找到邮件 Agent 配置")

    user = await UserMapper(db).get_by_id(user_id)
    if user and user.email:
        background_tasks.add_task(
            send_notification_email,
            user.email,
            "邮件 Agent 配置已更新",
            f"您好，\n\n您的邮件 Agent 配置已成功更新。\n"
            f"如有疑问请登录 Fancy Agent 平台查看。\n\n— Fancy Agent",
        )

    return obj


@router.delete("")
async def delete_email_agent(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserEmailAgentService(db)
    success = await service.delete(user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="未找到邮件 Agent 配置")
    return {"success": True}
