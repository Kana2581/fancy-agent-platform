from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.services.prompt_template_service import PromptTemplateService
from app.schemas.prompt_template_schema import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateOut,
)
from app.deps.service import get_prompt_template_service
from app.deps.user import get_current_user

router = APIRouter(prefix="/prompt-templates", tags=["Prompt Templates"])


@router.post("", response_model=PromptTemplateOut)
async def create_prompt_template(
    data: PromptTemplateCreate,
    service: PromptTemplateService = Depends(get_prompt_template_service),
    user_id: int = Depends(get_current_user),
):
    data_dict = data.model_dump()
    data_dict.update({"user_id": user_id})
    return await service.create_prompt_template(data_dict)


@router.get("", response_model=List[PromptTemplateOut])
async def list_prompt_templates(
    offset: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    user_id: int = Depends(get_current_user),
    service: PromptTemplateService = Depends(get_prompt_template_service),
):
    return await service.list_by_user(user_id, offset, limit, category)


@router.get("/{template_id}", response_model=PromptTemplateOut)
async def get_prompt_template(
    template_id: int,
    service: PromptTemplateService = Depends(get_prompt_template_service),
    user_id: int = Depends(get_current_user),
):
    template = await service.get_prompt_template(template_id)
    if not template or template.user_id != user_id:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return template


@router.put("/{template_id}", response_model=PromptTemplateOut)
async def update_prompt_template(
    template_id: int,
    data: PromptTemplateUpdate,
    service: PromptTemplateService = Depends(get_prompt_template_service),
    user_id: int = Depends(get_current_user),
):
    template = await service.get_prompt_template(template_id)
    if not template or template.user_id != user_id:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return await service.update_prompt_template(template_id, data)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt_template(
    template_id: int,
    service: PromptTemplateService = Depends(get_prompt_template_service),
    user_id: int = Depends(get_current_user),
):
    template = await service.get_prompt_template(template_id)
    if not template or template.user_id != user_id:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    await service.delete_prompt_template(template_id)
