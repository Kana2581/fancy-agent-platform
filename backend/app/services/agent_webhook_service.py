import secrets
import string
from datetime import datetime
from typing import List, Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db_session
from app.mappers.agent_webhook_mapper import AgentWebhookMapper
from app.models.agent_webhook import AgentWebhook
from app.schemas.agent_webhook_schema import AgentWebhookCreate, AgentWebhookUpdate

_SLUG_ALPHABET = string.ascii_lowercase + string.digits


def _generate_slug(length: int = 16) -> str:
    return "".join(secrets.choice(_SLUG_ALPHABET) for _ in range(length))


def _generate_secret() -> str:
    return secrets.token_urlsafe(48)


class AgentWebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mapper = AgentWebhookMapper(db)

    async def create(self, user_id: int, data: AgentWebhookCreate) -> AgentWebhook:
        # 极小概率撞 slug，重试几次
        for _ in range(5):
            slug = _generate_slug()
            existing = await self.mapper.get_by_slug(slug)
            if existing is None:
                break
        else:
            raise RuntimeError("无法生成唯一的 webhook slug")

        payload = {
            "user_id": user_id,
            "agent_id": data.agent_id,
            "name": data.name,
            "slug": slug,
            "secret": _generate_secret(),
            "channel": data.channel,
            "telegram_bot_token": data.telegram_bot_token,
            "dingtalk_app_secret": data.dingtalk_app_secret,
            "discord_public_key": data.discord_public_key,
            "enabled": True,
            "trigger_count": 0,
        }
        res = await self.mapper.create_from_dict(payload)
        await self.db.commit()
        return res

    async def get(self, webhook_id: int) -> Optional[AgentWebhook]:
        return await self.mapper.get_by_id(webhook_id)

    async def list_by_user(self, user_id: int) -> List[AgentWebhook]:
        return await self.mapper.list_by_user(user_id)

    async def update(self, webhook_id: int, data: AgentWebhookUpdate) -> Optional[AgentWebhook]:
        res = await self.mapper.update_by_id(
            webhook_id, data.model_dump(exclude_unset=True)
        )
        await self.db.commit()
        return res

    async def regenerate_secret(self, webhook_id: int) -> Optional[AgentWebhook]:
        res = await self.mapper.update_by_id(webhook_id, {"secret": _generate_secret()})
        await self.db.commit()
        return res

    async def delete(self, webhook_id: int) -> bool:
        res = await self.mapper.delete_by_id(webhook_id)
        await self.db.commit()
        return res


async def record_trigger(webhook_id: int) -> None:
    """独立 session 写入触发计数与时间，避免与公开触发路由的主 session 耦合。"""
    async with get_db_session() as db:
        await db.execute(
            update(AgentWebhook)
            .where(AgentWebhook.id == webhook_id)
            .values(
                last_triggered_at=datetime.now(),
                trigger_count=AgentWebhook.trigger_count + 1,
            )
        )
        await db.commit()
