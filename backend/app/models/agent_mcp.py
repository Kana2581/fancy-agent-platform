from sqlalchemy import (
    Column, Integer,  ForeignKey, DateTime
)

from sqlalchemy.orm import relationship


from app.core.database import Base
from datetime import datetime, timezone

# =========================
# agents_mcps 关系表
# =========================
class AgentMCP(Base):
    __tablename__ = "agents_mcps"

    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    mcp_id = Column(Integer, ForeignKey("mcps.id"), nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    agent = relationship("Agent", back_populates="mcps")
    mcp = relationship("MCP", back_populates="agents")


