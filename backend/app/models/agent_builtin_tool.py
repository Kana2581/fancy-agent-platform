from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint

from app.core.database import Base


class AgentBuiltinTool(Base):
    __tablename__ = "agents_builtin_tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_type = Column(String(64), nullable=False)  # "web_search" | "web_fetch"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("agent_id", "tool_type", name="uq_agent_builtin_tool"),)
