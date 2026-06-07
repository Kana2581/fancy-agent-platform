from typing import List, Optional

from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.session_share import SessionShare


class SessionShareMapper(BaseMapper[SessionShare]):
    model = SessionShare

    async def get_by_slug(self, slug: str) -> Optional[SessionShare]:
        result = await self.db.execute(
            select(SessionShare).where(SessionShare.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: str) -> List[SessionShare]:
        return await self.list_by_filters(filters={"session_id": session_id}, limit=100)
