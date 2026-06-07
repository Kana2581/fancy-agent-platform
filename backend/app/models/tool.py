from sqlalchemy import Column, Integer, String, Text, JSON, UniqueConstraint

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class Tool(Base, TimestampMixin):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, autoincrement=True)

    mcp_id = Column(Integer, nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # ✅ 改成 JSON
    args_schema = Column(JSON, nullable=True)

