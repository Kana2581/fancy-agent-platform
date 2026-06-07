from fastapi import APIRouter, Depends, HTTPException, status

from app.deps.service import get_generated_image_service
from app.deps.user import get_current_user
from app.schemas.generated_image_schema import GeneratedImageOut, GeneratedImagePageOut
from app.services.generated_image_service import GeneratedImageService

router = APIRouter(prefix="/generated-images", tags=["Generated Images"])


@router.get("", response_model=GeneratedImagePageOut)
async def list_generated_images(
    page: int = 1,
    page_size: int = 20,
    service: GeneratedImageService = Depends(get_generated_image_service),
    user_id: int = Depends(get_current_user),
):
    return await service.list_by_user(user_id, page, page_size)


@router.get("/{record_id}", response_model=GeneratedImageOut)
async def get_generated_image(
    record_id: int,
    service: GeneratedImageService = Depends(get_generated_image_service),
    user_id: int = Depends(get_current_user),
):
    record = await service.get(record_id, user_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generated_image(
    record_id: int,
    service: GeneratedImageService = Depends(get_generated_image_service),
    user_id: int = Depends(get_current_user),
):
    deleted = await service.delete(record_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Record not found")
