from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.help_document_mapper import HelpDocumentMapper
from app.models.help_document import HelpDocument


class HelpDocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = HelpDocumentMapper(db)

    async def list_documents(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        doc_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[HelpDocument]:
        return await self.mapper.list_active(
            q=q,
            category=category,
            doc_type=doc_type,
            offset=offset,
            limit=limit,
        )

    async def get_by_slug(self, slug: str) -> Optional[HelpDocument]:
        return await self.mapper.get_by_slug(slug)

    async def upsert_document(self, data: Dict[str, Any]) -> HelpDocument:
        doc = await self.mapper.upsert_by_slug(data)
        await self.db.commit()
        return doc
