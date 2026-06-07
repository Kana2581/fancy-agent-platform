from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps.user import get_current_user
from app.deps.service import get_agent_builtin_tool_service
from app.services.agent_builtin_tool_service import AgentBuiltinToolService
from app.utils.langchain.builtin_tools import BUILTIN_TOOL_CATALOG

router = APIRouter(
    prefix="/agents/{agent_id}/builtin-tools",
    tags=["agent-builtin-tools"],
)

builtin_catalog_router = APIRouter(
    prefix="/builtin-tools",
    tags=["builtin-tools"],
)


class SyncBuiltinToolsBody(BaseModel):
    tool_types: List[str]


@router.get("/", response_model=List[str])
async def list_agent_builtin_tools(
    agent_id: int,
    service: AgentBuiltinToolService = Depends(get_agent_builtin_tool_service),
    _: str = Depends(get_current_user),
):
    return await service.list_tool_types_for_agent(agent_id)


@router.post("/", response_model=List[str])
async def sync_agent_builtin_tools(
    agent_id: int,
    body: SyncBuiltinToolsBody,
    service: AgentBuiltinToolService = Depends(get_agent_builtin_tool_service),
    _: str = Depends(get_current_user),
):
    return await service.sync_tools(agent_id, body.tool_types)


@builtin_catalog_router.get("/")
async def list_builtin_tool_catalog():
    return BUILTIN_TOOL_CATALOG
