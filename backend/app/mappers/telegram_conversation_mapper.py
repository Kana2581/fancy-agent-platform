from typing import Optional

from sqlalchemy import select

from app.mappers.base_mapper import BaseMapper
from app.models.telegram_conversation import TelegramConversation


class TelegramConversationMapper(BaseMapper[TelegramConversation]):
    model = TelegramConversation

    async def get_by_scope(
        self,
        webhook_id: int,
        chat_id: str,
        message_thread_id: str = "",
    ) -> Optional[TelegramConversation]:
        result = await self.db.execute(
            select(TelegramConversation).where(
                TelegramConversation.webhook_id == webhook_id,
                TelegramConversation.chat_id == chat_id,
                TelegramConversation.message_thread_id == message_thread_id,
            )
        )
        return result.scalar_one_or_none()
