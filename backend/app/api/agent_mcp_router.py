from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.services.agent_mcp_service import AgentMCPService
from app.services.agent_service import AgentService
from app.deps.service import get_agent_mcp_service, get_agent_service
from app.deps.user import get_current_user

router = APIRouter(prefix="/agents/{agent_id}/mcps", tags=["agent-mcps"])


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
async def list_mcps(
    agent_id: int,
    service: AgentMCPService = Depends(get_agent_mcp_service),
    agent_service: AgentService = Depends(get_agent_service),
    user_id: int = Depends(get_current_user),
):
    await _require_agent_owner(agent_id, user_id, agent_service)
    return await service.list_mcps_for_agent(agent_id)


@router.post("/", response_model=List[int])
async def bind_mcps(
    agent_id: int,
    mcp_ids: List[int] = [],
    service: AgentMCPService = Depends(get_agent_mcp_service),
    agent_service: AgentService = Depends(get_agent_service),
    user_id: int = Depends(get_current_user),
):
    await _require_agent_owner(agent_id, user_id, agent_service)
    binds = await service.bind_mcps(agent_id, mcp_ids)
    return [b for b in binds] if binds else []


@router.delete("/", response_model=dict)
async def unbind_mcps(
    agent_id: int,
    mcp_ids: List[int] = [],
    service: AgentMCPService = Depends(get_agent_mcp_service),
    agent_service: AgentService = Depends(get_agent_service),
    user_id: int = Depends(get_current_user),
):
    await _require_agent_owner(agent_id, user_id, agent_service)
    count = await service.unbind_mcps(agent_id, mcp_ids)
    return {"deleted": count}
