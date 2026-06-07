from sqlalchemy import Column, Integer, String, UniqueConstraint

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class TelegramConversation(TimestampMixin, Base):
    __tablename__ = "telegram_conversations"
    __table_args__ = (
        UniqueConstraint(
            "webhook_id",
            "chat_id",
            "message_thread_id",
            name="uq_telegram_conversations_scope",
        ),
    )

    id = Column(Integer, primary_key=True)
    webhook_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(String(64), nullable=False, index=True)
    message_thread_id = Column(String(64), nullable=False, default="")
    session_id = Column(String(64), nullable=False)
