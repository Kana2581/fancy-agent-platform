from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps.service import get_agent_image_tool_service, get_agent_service
from app.deps.user import get_current_user
from app.services.agent_image_tool_service import AgentImageToolService
from app.services.agent_service import AgentService

router = APIRouter(prefix="/agents/{agent_id}/image-tools", tags=["agent-image-tools"])


class ToolIdsBody(BaseModel):
    tool_ids: List[int]


async def _require_agent_owner(
    agent_id: int,
    user_id: int,
    agent_service: AgentService,
):
    agent = await agent_service.get_agent(agent_id)
    if not agent or agent.user_id != user_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/", response_model=List[int])
async def list_agent_image_tools(
    agent_id: int,
    service: AgentImageToolService = Depends(get_agent_image_tool_service),
    agent_service: AgentService = Depends(get_agent_service),
    user_id: int = Depends(get_current_user),
):
    await _require_agent_owner(agent_id, user_id, agent_service)
    return await service.list_tools_for_agent(agent_id)


@router.post("/", response_model=dict)
async def sync_agent_image_tools(
    agent_id: int,
    body: ToolIdsBody,
    service: AgentImageToolService = Depends(get_agent_image_tool_service),
    agent_service: AgentService = Depends(get_agent_service),
    user_id: int = Depends(get_current_user),
):
    """同步 agent 绑定的图像生成工具（diff 后增删，传空数组则清空）。"""
    await _require_agent_owner(agent_id, user_id, agent_service)
    await service.bind_tools(agent_id, body.tool_ids)
    return {"synced": body.tool_ids}


@router.delete("/", response_model=dict)
async def unbind_agent_image_tools(
    agent_id: int,
    body: ToolIdsBody,
    service: AgentImageToolService = Depends(get_agent_image_tool_service),
    agent_service: AgentService = Depends(get_agent_service),
    user_id: int = Depends(get_current_user),
):
    await _require_agent_owner(agent_id, user_id, agent_service)
    count = await service.unbind_tools(agent_id, body.tool_ids)
    return {"deleted": count}
