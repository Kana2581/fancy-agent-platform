from typing import Optional
from sqlalchemy import select, func, desc
from app.mappers.base_mapper import BaseMapper
from app.models.session import Session


class SessionMapper(BaseMapper[Session]):
    model = Session
    pk_name = "id"

    async def list_with_search(
        self,
        user_id: int,
        agent_id: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Session], int]:
        base = select(self.model).where(self.model.user_id == user_id)
        if agent_id is not None:
            base = base.where(self.model.agent_id == agent_id)
        if keyword:
            base = base.where(self.model.title.ilike(f"%{keyword}%"))

        total = (await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )).scalar_one()

        rows = (await self.db.execute(
            base.order_by(desc(self.model.updated_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
        )).scalars().all()

        return list(rows), total