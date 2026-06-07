from sqlalchemy import Column, Integer, String, Boolean


from app.core.database import Base
from app.models.timestamp_model import TimestampMixin

class Session(Base,TimestampMixin):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        Integer,
        nullable=False,
    )
    agent_id = Column(
        Integer,
        nullable=False,
    )

    title = Column(String(255))

    is_active = Column(Boolean, nullable=False, default=True)
    auto_title_generated = Column(Boolean, nullable=False, default=False, server_default="0")
