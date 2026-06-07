from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class MCP(Base,TimestampMixin):
    __tablename__ = "mcps"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 绑定用户，NULL 表示系统内置
    user_id = Column(Integer, nullable=True, index=True)

    # MCP 逻辑名称，如 tavily_mcp
    mcp_name = Column(String(100), nullable=False)

    # transport: http / stdio / websocket
    transport = Column(String(50), nullable=False)

    # JSON 字符串，存 url / env / 其他参数
    config_json = Column(JSON, nullable=True)

    # 是否系统内置
    is_builtin = Column(Boolean, nullable=False, default=False)

    # 是否启用
    is_enabled = Column(Boolean, nullable=False, default=True)

    agents = relationship(
        "AgentMCP", back_populates="mcp", cascade="all, delete-orphan"
    )
