from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class SessionShare(TimestampMixin, Base):
    __tablename__ = "session_shares"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    slug = Column(String(24), nullable=False, unique=True, index=True)
    created_by = Column(Integer, nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    expires_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, nullable=False, default=0)
