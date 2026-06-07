from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select

from app.mappers.base_mapper import BaseMapper
from app.models.help_document import HelpDocument


class HelpDocumentMapper(BaseMapper):
    model = HelpDocument

    async def get_by_slug(self, slug: str) -> Optional[HelpDocument]:
        result = await self.db.execute(
            select(HelpDocument).where(
                HelpDocument.slug == slug,
                HelpDocument.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_active(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        doc_type: Optional[str] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[HelpDocument]:
        stmt = select(HelpDocument).where(HelpDocument.is_active.is_(True))
        if category:
            stmt = stmt.where(HelpDocument.category == category)
        if doc_type:
            stmt = stmt.where(HelpDocument.doc_type == doc_type)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                or_(
                    HelpDocument.title.ilike(pattern),
                    HelpDocument.summary.ilike(pattern),
                    HelpDocument.content.ilike(pattern),
                )
            )
        stmt = stmt.order_by(HelpDocument.sort_order.asc(), HelpDocument.id.asc())
        result = await self.db.execute(stmt.offset(offset).limit(limit))
        return result.scalars().all()

    async def upsert_by_slug(self, data: Dict[str, Any]) -> HelpDocument:
        doc = await self.get_any_by_slug(data["slug"])
        if doc:
            return await self._update_entity(doc, data)
        return await self.create_from_dict(data)

    async def get_any_by_slug(self, slug: str) -> Optional[HelpDocument]:
        result = await self.db.execute(
            select(HelpDocument).where(HelpDocument.slug == slug)
        )
        return result.scalar_one_or_none()
