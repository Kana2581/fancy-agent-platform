# app/api/llm_router.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.services.llm_service import LLMService
from app.schemas.llm_schema import LLMCreate, LLMUpdate, LLMOut, LLMTestRequest, LLMTestResult
from app.deps.service import get_llm_service
from app.deps.user import get_current_user
router = APIRouter(prefix="/llm", tags=["LLM Models"])


@router.post("/test", response_model=LLMTestResult)
async def test_llm_connection(
    data: LLMTestRequest,
    service: LLMService = Depends(get_llm_service),
    user_id: int = Depends(get_current_user),
):
    success, message = await service.test_llm(data, user_id)
    return LLMTestResult(success=success, message=message)


@router.post("", response_model=LLMOut)
async def create_llm(
    data: LLMCreate,
    service: LLMService = Depends(get_llm_service),
    user_id: int = Depends(get_current_user)
):
    data_dict = data.model_dump()
    data_dict.update({"user_id": user_id})
    return await service.create_llm(data_dict)


@router.get("/{llm_id}", response_model=LLMOut)
async def get_llm(
    llm_id: int,
    service: LLMService = Depends(get_llm_service),
    user_id: int = Depends(get_current_user),
):
    llm = await service.get_llm(llm_id)
    if not llm or llm.user_id != user_id:
        raise HTTPException(status_code=404, detail="LLM model not found")
    return llm


@router.get("", response_model=List[LLMOut])
async def list_llms(
    offset: int = 0,
    limit: int = 100,
    user_id: int = Depends(get_current_user),
    service: LLMService = Depends(get_llm_service)
):
    return await service.list_llms_by_user(user_id, offset, limit)


@router.put("/{llm_id}", response_model=LLMOut)
async def update_llm(
    llm_id: int,
    data: LLMUpdate,
    service: LLMService = Depends(get_llm_service),
    user_id: int = Depends(get_current_user),
):
    llm = await service.get_llm(llm_id)
    if not llm or llm.user_id != user_id:
        raise HTTPException(status_code=404, detail="LLM model not found")
    updated = await service.update_llm(llm_id, data)
    return updated


@router.delete("/{llm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm(
    llm_id: int,
    service: LLMService = Depends(get_llm_service),
    user_id: int = Depends(get_current_user),
):
    llm = await service.get_llm(llm_id)
    if not llm or llm.user_id != user_id:
        raise HTTPException(status_code=404, detail="LLM model not found")
    await service.delete_llm(llm_id)
