from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class PromptTemplate(Base, TimestampMixin):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")

    user_id = Column(
        Integer,
        nullable=False,
        index=True,
        comment="所属用户ID"
    )

    name = Column(
        String(100),
        nullable=False,
        comment="模板名称"
    )

    description = Column(
        String(500),
        nullable=True,
        comment="模板描述"
    )

    content = Column(
        Text,
        nullable=False,
        comment="模板内容"
    )

    category = Column(
        String(50),
        nullable=True,
        comment="分类标签"
    )
