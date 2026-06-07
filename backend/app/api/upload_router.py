from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db
from app.deps.user import get_current_user
from app.schemas.chat_file_schema import ChatFileUploadRequest, ChatFileResponse
from app.services.file_upload_service import FileUploadService

router = APIRouter(prefix="/files", tags=["files"])

@router.post("", response_model=ChatFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    session_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FileUploadService(db)
    return await service.upload(
        file,
        user_id=current_user,
        req=ChatFileUploadRequest(session_id=session_id),
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FileUploadService(db)
    await service.delete(file_id, user_id=current_user)
    return {"message": "删除成功"}