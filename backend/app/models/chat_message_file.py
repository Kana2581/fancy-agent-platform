from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class ChatMessageFile(Base, TimestampMixin):
    __tablename__ = "chat_message_file"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    message_id = Column(
        String(36),
        nullable=False,
        index=True
    )

    file_id = Column(
        Integer,
        ForeignKey("chat_file.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    __table_args__ = (
        UniqueConstraint("message_id", "file_id", name="uq_message_file"),
    )