from datetime import datetime, timezone

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class AgentApiTool(Base):
    __tablename__ = "agents_api_tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    api_tool_id = Column(Integer, ForeignKey("api_tools.id"), nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
