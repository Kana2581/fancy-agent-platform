from sqlalchemy import Column, Integer, String, ForeignKey, Text,Boolean

from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class Agent(Base,TimestampMixin):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    avatar = Column(String(255))
    model_id = Column(Integer, ForeignKey("llms.id"), nullable=False)
    description = Column(Text)
    system_prompt = Column(Text)
    max_token_size = Column(Integer,default=4096)
    human_in_the_loop = Column(Boolean,nullable=False, default=False)
    # 关系
    llm = relationship("LLM", back_populates="agents")
    mcps = relationship(
        "AgentMCP", back_populates="agent"
    )