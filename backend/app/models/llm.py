from sqlalchemy import (
    Column,
    Integer,
    String,

)
from sqlalchemy.orm import relationship

from app.core.crypto import EncryptedString
from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class LLM(Base,TimestampMixin):
    __tablename__ = "llms"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")

    user_id = Column(
        Integer,
        nullable=False,
        index=True,
        comment="所属用户ID"
    )

    provider = Column(
        String(100),
        nullable=False,
        comment="模型提供商"
    )

    model_name = Column(
        String(100),
        nullable=False,
        comment="模型名称"
    )

    base_url = Column(
        String(255),
        nullable=True,
        comment="模型基础URL"
    )

    api_key = Column(
        EncryptedString(),
        nullable=True,
        comment="API Key（落库加密）"
    )
    agents = relationship("Agent", back_populates="llm")  # 反向关联

