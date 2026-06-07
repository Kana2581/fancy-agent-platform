from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.deps.service import get_help_document_service
from app.deps.user import get_current_user
from app.schemas.help_document_schema import HelpDocumentOut, HelpDocumentSummaryOut
from app.services.help_document_service import HelpDocumentService


router = APIRouter(prefix="/help-docs", tags=["Help Documents"])


@router.get("", response_model=List[HelpDocumentSummaryOut])
async def list_help_documents(
    q: Optional[str] = None,
    category: Optional[str] = None,
    doc_type: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    service: HelpDocumentService = Depends(get_help_document_service),
    _: int = Depends(get_current_user),
):
    return await service.list_documents(
        q=q,
        category=category,
        doc_type=doc_type,
        offset=offset,
        limit=limit,
    )


@router.get("/{slug}", response_model=HelpDocumentOut)
async def get_help_document(
    slug: str,
    service: HelpDocumentService = Depends(get_help_document_service),
    _: int = Depends(get_current_user),
):
    doc = await service.get_by_slug(slug)
    if not doc:
        raise HTTPException(status_code=404, detail="Help document not found")
    return doc
