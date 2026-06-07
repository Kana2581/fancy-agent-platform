from sqlalchemy import Column, Integer, String, Text, UniqueConstraint

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class UserMemory(Base, TimestampMixin):
    __tablename__ = "user_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    key = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    memory_type = Column(String(20), nullable=False, default="normal")  # "core" | "normal"

    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_memory_key"),)
