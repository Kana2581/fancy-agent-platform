from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.deps.db import get_db
from app.deps.user import get_current_user
from app.schemas.session_share_schema import (
    SessionShareCreate,
    SessionShareOut,
    SharedSessionView,
)
from app.services.session_share_service import SessionShareService, get_public_view
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["SessionShares"])


def _get_service(db: AsyncSession = Depends(get_db)) -> SessionShareService:
    return SessionShareService(db)


@router.post("/sessions/{session_id}/shares", response_model=SessionShareOut)
async def create_share(
    session_id: str,
    data: SessionShareCreate,
    user_id: int = Depends(get_current_user),
    service: SessionShareService = Depends(_get_service),
):
    try:
        return await service.create(session_id, user_id, data)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/sessions/{session_id}/shares", response_model=List[SessionShareOut])
async def list_shares(
    session_id: str,
    user_id: int = Depends(get_current_user),
    service: SessionShareService = Depends(_get_service),
):
    return await service.list_by_session(session_id, user_id)


@router.delete("/session-shares/{share_id}", status_code=204)
async def revoke_share(
    share_id: int,
    user_id: int = Depends(get_current_user),
    service: SessionShareService = Depends(_get_service),
):
    ok = await service.revoke(share_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Share not found")


# Public route — no auth
@router.get("/share/{slug}", response_model=SharedSessionView)
async def view_shared_session(slug: str):
    view = await get_public_view(slug)
    if not view:
        raise HTTPException(status_code=410, detail="Share link is invalid or expired")
    return view
