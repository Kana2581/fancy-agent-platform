# app/api/v1/session.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.session_schema import (
    SessionCreate,
    SessionUpdate,
    SessionOut,
    SessionPageOut,
)
from app.services.session_service import SessionService
from app.deps.service import get_session_service
from app.deps.user import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut)
async def create_session(
    data: SessionCreate,
    service: SessionService = Depends(get_session_service),
    user_id: int = Depends(get_current_user),
):
    return await service.create(user_id=user_id, **data.model_dump())


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
    user_id: int = Depends(get_current_user),
):
    session = await service.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("", response_model=SessionPageOut)
async def list_sessions(
    user_id: int = Depends(get_current_user),
    agent_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: SessionService = Depends(get_session_service),
):
    items, total = await service.list(
        user_id=user_id,
        agent_id=agent_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return SessionPageOut(items=items, total=total)


@router.put("/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: str,
    data: SessionUpdate,
    service: SessionService = Depends(get_session_service),
    user_id: int = Depends(get_current_user),
):
    session = await service.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    updated = await service.update(session_id, data)
    return updated


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
    user_id: int = Depends(get_current_user),
):
    session = await service.get(session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    await service.delete(session_id)
    return {"success": True}
