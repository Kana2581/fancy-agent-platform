# app/api/mcp_router.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.services.mcp_service import MCPService
from app.schemas.mcp_schema import MCPCreate, MCPUpdate, MCPOut
from app.schemas.tool_schema import ToolOut
from app.utils.langchain.tool_util import parse_tools
from app.deps.service import get_mcp_service
from app.deps.user import get_current_user

router = APIRouter(prefix="/mcps", tags=["MCP"])


@router.post("", response_model=MCPOut)
async def create_mcp(
    data: MCPCreate,
    service: MCPService = Depends(get_mcp_service),
    user_id: int = Depends(get_current_user),
):
    data_dict = data.model_dump()
    data_dict.update({"user_id": user_id})
    return await service.create_mcp(data_dict)


@router.get("/{mcp_id}", response_model=MCPOut)
async def get_mcp(
    mcp_id: int,
    service: MCPService = Depends(get_mcp_service),
    user_id: int = Depends(get_current_user),
):
    mcp = await service.get_mcp(mcp_id)
    # user_id is None means system-level shared MCP, readable by anyone
    if not mcp or (mcp.user_id is not None and mcp.user_id != user_id):
        raise HTTPException(status_code=404, detail="MCP not found")
    return mcp


@router.get("/{mcp_id}/tools", response_model=List[ToolOut])
async def get_mcp_tools(
    mcp_id: int,
    service: MCPService = Depends(get_mcp_service),
    user_id: int = Depends(get_current_user),
):
    mcp = await service.get_mcp(mcp_id)
    if not mcp or (mcp.user_id is not None and mcp.user_id != user_id):
        raise HTTPException(status_code=404, detail="MCP not found")
    tools = await service.extract_mcp(mcp_id)
    if not tools:
        raise HTTPException(status_code=404, detail="MCP not found")
    return parse_tools(tools)


@router.get("", response_model=List[MCPOut])
async def list_mcps(
    user_id: int = Depends(get_current_user),
    offset: int = 0,
    limit: int = 100,
    service: MCPService = Depends(get_mcp_service),
):
    return await service.list_mcps_by_user(user_id, offset, limit)


@router.put("/{mcp_id}", response_model=MCPOut)
async def update_mcp(
    mcp_id: int,
    data: MCPUpdate,
    service: MCPService = Depends(get_mcp_service),
    user_id: int = Depends(get_current_user),
):
    mcp = await service.get_mcp(mcp_id)
    if not mcp or (mcp.user_id is not None and mcp.user_id != user_id):
        raise HTTPException(status_code=404, detail="MCP not found")
    updated = await service.update_mcp(mcp_id, data)
    return updated


@router.delete("/{mcp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp(
    mcp_id: int,
    service: MCPService = Depends(get_mcp_service),
    user_id: int = Depends(get_current_user),
):
    mcp = await service.get_mcp(mcp_id)
    if not mcp or (mcp.user_id is not None and mcp.user_id != user_id):
        raise HTTPException(status_code=404, detail="MCP not found")
    await service.delete_mcp(mcp_id)
