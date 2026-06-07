from sqlalchemy import Column, String
from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class MessageApproval(Base, TimestampMixin):
    """1-to-1 with an AI ChatMessage that has pending tool calls."""
    __tablename__ = "message_approval"

    message_id = Column(String(64), primary_key=True)
    # "pending" | "approved" | "rejected"
    status = Column(String(16), nullable=False, default="pending")
