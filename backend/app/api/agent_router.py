from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.services.agent_service import AgentService
from app.services.agent_mcp_service import AgentMCPService
from app.schemas.agent_schema import AgentCreate, AgentUpdate, AgentOut, AgentFullOut
from app.deps.service import get_agent_service, get_agent_mcp_service
from app.deps.user import get_current_user

router = APIRouter(prefix="/agents", tags=["agents"])


# ================= 查询 =================
@router.get("/{agent_id}", response_model=AgentFullOut)
async def get_agent(
    agent_id: int,
    service: AgentService = Depends(get_agent_service),
    user_id: int = Depends(get_current_user),
):
    agent = await service.get_full_agent(agent_id, user_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/", response_model=List[AgentOut])
async def list_agents(
    offset: int = 0,
    limit: int = 100,
    service: AgentService = Depends(get_agent_service),
    user_id: int = Depends(get_current_user),
):
    return await service.list_agents({"user_id": user_id}, offset=offset, limit=limit)


# ================= 新增 =================
@router.post("/", response_model=AgentOut)
async def create_agent(
    agent_in: AgentCreate,
    agent_service: AgentService = Depends(get_agent_service),
    agent_mcp_service: AgentMCPService = Depends(get_agent_mcp_service),
    user_id: int = Depends(get_current_user),
):
    data = agent_in.model_dump(exclude={"mcp_ids"})
    data["user_id"] = user_id
    agent = await agent_service.create_agent(data)
    mcp_ids = None
    if agent_in.mcp_ids:
        mcp_ids = await agent_mcp_service.bind_mcps(agent.id, agent_in.mcp_ids)
    agent_out = AgentOut.model_validate(agent)
    agent_out.mcp_ids = mcp_ids
    return agent_out


# ================= 更新 =================
@router.put("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: int,
    agent_in: AgentUpdate,
    service: AgentService = Depends(get_agent_service),
    agent_mcp_service: AgentMCPService = Depends(get_agent_mcp_service),
    user_id: int = Depends(get_current_user),
):
    agent = await service.get_agent(agent_id)
    if not agent or agent.user_id != user_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = await service.update_agent(agent_id, agent_in.model_dump(exclude_unset=True, exclude={"mcp_ids"}))
    if agent_in.mcp_ids is not None:
        await agent_mcp_service.bind_mcps(agent.id, agent_in.mcp_ids)
    return AgentOut.model_validate(agent)


# ================= 删除 =================
@router.delete("/{agent_id}", response_model=dict)
async def delete_agent(
    agent_id: int,
    service: AgentService = Depends(get_agent_service),
    user_id: int = Depends(get_current_user),
):
    agent = await service.get_agent(agent_id)
    if not agent or agent.user_id != user_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    success = await service.delete_agent(agent_id)
    return {"success": success}
