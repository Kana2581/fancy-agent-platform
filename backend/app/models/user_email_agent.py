from sqlalchemy import Column, Integer, String, Boolean, UniqueConstraint

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class UserEmailAgent(Base, TimestampMixin):
    __tablename__ = "user_email_agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    agent_id = Column(Integer, nullable=False)
    session_id = Column(String(36), nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_email_agent_user_id"),
    )
