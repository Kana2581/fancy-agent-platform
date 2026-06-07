import uuid
from sqlalchemy import (
    Column,
    String,
    JSON, Integer, CHAR,
)


from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_message"

    id = Column(
        CHAR(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id = Column(Integer, nullable=False)

    session_id = Column(
        CHAR(36),
        nullable=False
    )

    parent_id = Column(
        CHAR(64),
        nullable=True
    )

    type = Column(String(32), nullable=False)

    # 新增 content 字段
    content = Column(JSON)

    artifact = Column(JSON)

    tool_calls = Column(JSON)

    tool_call_id = Column(String(64))

    name = Column(String(255))

    message_group_id = Column(String(64))

    usage_metadata = Column(JSON, nullable=True)



