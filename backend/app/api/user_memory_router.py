from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps.service import get_user_memory_service
from app.deps.user import get_current_user
from app.schemas.user_memory_schema import UserMemoryCreate, UserMemoryOut
from app.services.user_memory_service import UserMemoryService

router = APIRouter(prefix="/memories", tags=["User Memories"])


@router.post("", response_model=UserMemoryOut)
async def save_memory(
    data: UserMemoryCreate,
    user_id: int = Depends(get_current_user),
    service: UserMemoryService = Depends(get_user_memory_service),
):
    return await service.save(user_id, data)


@router.get("", response_model=List[UserMemoryOut])
async def list_memories(
    memory_type: Optional[str] = None,
    category: Optional[str] = None,
    user_id: int = Depends(get_current_user),
    service: UserMemoryService = Depends(get_user_memory_service),
):
    return await service.list_by_user(user_id, memory_type=memory_type, category=category)


@router.get("/{key}", response_model=UserMemoryOut)
async def get_memory(
    key: str,
    user_id: int = Depends(get_current_user),
    service: UserMemoryService = Depends(get_user_memory_service),
):
    memory = await service.get(user_id, key)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    key: str,
    user_id: int = Depends(get_current_user),
    service: UserMemoryService = Depends(get_user_memory_service),
):
    deleted = await service.delete(user_id, key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
