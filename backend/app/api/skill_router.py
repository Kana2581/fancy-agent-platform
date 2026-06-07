from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps.service import get_skill_service
from app.deps.user import get_current_user
from app.models.skill import SKILL_SCOPE_SYSTEM, SKILL_SCOPE_USER
from app.schemas.skill_schema import SkillCreate, SkillOut, SkillUpdate
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["Skills"])


@router.post("", response_model=SkillOut)
async def create_skill(
    data: SkillCreate,
    service: SkillService = Depends(get_skill_service),
    user_id: int = Depends(get_current_user),
):
    data_dict = data.model_dump()
    data_dict["user_id"] = user_id
    # 普通用户不能通过 API 创建 system 级技能
    if data_dict.get("scope") == SKILL_SCOPE_SYSTEM:
        raise HTTPException(status_code=403, detail="不允许通过此接口创建 system 级技能")
    try:
        return await service.create_skill(data_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[SkillOut])
async def list_skills(
    offset: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    scope: Optional[str] = Query(None, description="过滤 scope: user/system/session/all；默认仅返回 user"),
    user_id: int = Depends(get_current_user),
    service: SkillService = Depends(get_skill_service),
):
    if scope == "all":
        return await service.list_layered(user_id, session_id=None, category=category)
    if scope == SKILL_SCOPE_SYSTEM:
        return await service.list_by_user(0, offset, limit, category, scope=SKILL_SCOPE_SYSTEM)
    return await service.list_by_user(
        user_id, offset, limit, category, scope=scope or SKILL_SCOPE_USER
    )


@router.get("/{skill_id}", response_model=SkillOut)
async def get_skill(
    skill_id: int,
    service: SkillService = Depends(get_skill_service),
    user_id: int = Depends(get_current_user),
):
    skill = await service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill.scope != SKILL_SCOPE_SYSTEM and skill.user_id != user_id:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.put("/{skill_id}", response_model=SkillOut)
async def update_skill(
    skill_id: int,
    data: SkillUpdate,
    service: SkillService = Depends(get_skill_service),
    user_id: int = Depends(get_current_user),
):
    skill = await service.get_skill(skill_id)
    if not skill or skill.user_id != user_id:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill.scope == SKILL_SCOPE_SYSTEM:
        raise HTTPException(status_code=403, detail="系统级技能不可修改")
    return await service.update_skill(skill_id, data)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: int,
    service: SkillService = Depends(get_skill_service),
    user_id: int = Depends(get_current_user),
):
    skill = await service.get_skill(skill_id)
    if not skill or skill.user_id != user_id:
        raise HTTPException(status_code=404, detail="Skill not found")
    if skill.scope == SKILL_SCOPE_SYSTEM:
        raise HTTPException(status_code=403, detail="系统级技能不可删除")
    await service.delete_skill(skill_id)
