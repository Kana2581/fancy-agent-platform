from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class AgentWebhook(TimestampMixin, Base):
    __tablename__ = "agent_webhooks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    agent_id = Column(Integer, nullable=False)
    name = Column(String(64), nullable=False)
    slug = Column(String(24), nullable=False, unique=True, index=True)
    secret = Column(String(96), nullable=False)
    channel = Column(String(24), nullable=False, default="generic")
    telegram_bot_token = Column(String(128), nullable=True)
    dingtalk_app_secret = Column(String(256), nullable=True)
    discord_public_key = Column(String(128), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, nullable=False, default=0)
    persistent_session_id = Column(String(64), nullable=True)
