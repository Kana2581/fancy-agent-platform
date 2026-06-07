from typing import List, Optional

from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.agent_webhook import AgentWebhook


class AgentWebhookMapper(BaseMapper[AgentWebhook]):
    model = AgentWebhook

    async def get_by_slug(self, slug: str) -> Optional[AgentWebhook]:
        result = await self.db.execute(
            select(AgentWebhook).where(AgentWebhook.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> List[AgentWebhook]:
        return await self.list_by_filters(filters={"user_id": user_id}, limit=500)
