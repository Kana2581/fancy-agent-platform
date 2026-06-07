from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps.service import get_agent_webhook_service
from app.deps.user import get_current_user
from app.schemas.agent_webhook_schema import (
    AgentWebhookCreate,
    AgentWebhookOut,
    AgentWebhookOutWithSecret,
    AgentWebhookUpdate,
)
from app.services.agent_webhook_service import AgentWebhookService

router = APIRouter(prefix="/agent-webhooks", tags=["AgentWebhooks"])


@router.post("", response_model=AgentWebhookOutWithSecret)
async def create_webhook(
    data: AgentWebhookCreate,
    service: AgentWebhookService = Depends(get_agent_webhook_service),
    user_id: int = Depends(get_current_user),
):
    return await service.create(user_id, data)


@router.get("", response_model=List[AgentWebhookOut])
async def list_webhooks(
    service: AgentWebhookService = Depends(get_agent_webhook_service),
    user_id: int = Depends(get_current_user),
):
    return await service.list_by_user(user_id)


@router.get("/{webhook_id}", response_model=AgentWebhookOut)
async def get_webhook(
    webhook_id: int,
    service: AgentWebhookService = Depends(get_agent_webhook_service),
    user_id: int = Depends(get_current_user),
):
    hook = await service.get(webhook_id)
    if not hook or hook.user_id != user_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return hook


@router.put("/{webhook_id}", response_model=AgentWebhookOut)
async def update_webhook(
    webhook_id: int,
    data: AgentWebhookUpdate,
    service: AgentWebhookService = Depends(get_agent_webhook_service),
    user_id: int = Depends(get_current_user),
):
    hook = await service.get(webhook_id)
    if not hook or hook.user_id != user_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return await service.update(webhook_id, data)


@router.post("/{webhook_id}/regenerate-secret", response_model=AgentWebhookOutWithSecret)
async def regenerate_secret(
    webhook_id: int,
    service: AgentWebhookService = Depends(get_agent_webhook_service),
    user_id: int = Depends(get_current_user),
):
    hook = await service.get(webhook_id)
    if not hook or hook.user_id != user_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return await service.regenerate_secret(webhook_id)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: int,
    service: AgentWebhookService = Depends(get_agent_webhook_service),
    user_id: int = Depends(get_current_user),
):
    hook = await service.get(webhook_id)
    if not hook or hook.user_id != user_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await service.delete(webhook_id)
