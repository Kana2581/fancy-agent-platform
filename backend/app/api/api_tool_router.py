import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.deps.service import get_api_tool_service
from app.deps.user import get_current_user
from app.schemas.api_tool_schema import ApiToolCreate, ApiToolOut, ApiToolUpdate
from app.services.api_tool_service import ApiToolService

router = APIRouter(prefix="/api-tools", tags=["API Tools"])


class TestRequest(BaseModel):
    params: dict = {}


@router.post("", response_model=ApiToolOut)
async def create_api_tool(
    data: ApiToolCreate,
    service: ApiToolService = Depends(get_api_tool_service),
    user_id: int = Depends(get_current_user),
):
    payload = data.model_dump()
    payload["user_id"] = user_id
    return await service.create_tool(payload)


@router.get("", response_model=List[ApiToolOut])
async def list_api_tools(
    offset: int = 0,
    limit: int = 100,
    service: ApiToolService = Depends(get_api_tool_service),
    user_id: int = Depends(get_current_user),
):
    return await service.list_tools_by_user(user_id, offset, limit)


@router.get("/{tool_id}", response_model=ApiToolOut)
async def get_api_tool(
    tool_id: int,
    service: ApiToolService = Depends(get_api_tool_service),
    user_id: int = Depends(get_current_user),
):
    tool = await service.get_tool(tool_id)
    if not tool or tool.user_id != user_id:
        raise HTTPException(status_code=404, detail="API tool not found")
    return tool


@router.put("/{tool_id}", response_model=ApiToolOut)
async def update_api_tool(
    tool_id: int,
    data: ApiToolUpdate,
    service: ApiToolService = Depends(get_api_tool_service),
    user_id: int = Depends(get_current_user),
):
    tool = await service.get_tool(tool_id)
    if not tool or tool.user_id != user_id:
        raise HTTPException(status_code=404, detail="API tool not found")
    return await service.update_tool(tool_id, data)


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_tool(
    tool_id: int,
    service: ApiToolService = Depends(get_api_tool_service),
    user_id: int = Depends(get_current_user),
):
    tool = await service.get_tool(tool_id)
    if not tool or tool.user_id != user_id:
        raise HTTPException(status_code=404, detail="API tool not found")
    await service.delete_tool(tool_id)


@router.post("/{tool_id}/test")
async def test_api_tool(
    tool_id: int,
    body: TestRequest,
    service: ApiToolService = Depends(get_api_tool_service),
    user_id: int = Depends(get_current_user),
):
    tool = await service.get_tool(tool_id)
    if not tool or tool.user_id != user_id:
        raise HTTPException(status_code=404, detail="API tool not found")
    config = {
        "name": tool.name,
        "description": tool.description,
        "url": tool.url,
        "method": tool.method,
        "headers": tool.headers or {},
        "param_location": tool.param_location,
        "fixed_params": tool.fixed_params or {},
        "tool_params": tool.tool_params or [],
        "response_extract": tool.response_extract or [],
        "response_max_chars": tool.response_max_chars,
    }

    from app.utils.langchain.http_tool_factory import build_tool_from_config
    try:
        lc_tool = build_tool_from_config(config)

        result = await asyncio.to_thread(
            lc_tool.invoke,
            {
                "type": "tool_call",
                "name": lc_tool.name,
                "args": body.params,
                "id": "test_call",
            },
        )
        return {"success": True, "result": result.content}
    except Exception as e:
        return {"success": False, "error": str(e)}
