from sqlalchemy import Column, Integer, String, Text, Boolean

from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class GeneratedImage(Base, TimestampMixin):
    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    image_tool_id = Column(Integer, nullable=True)   # 工具删除后历史仍保留
    provider = Column(String(50), nullable=False)    # openai / stability / siliconflow
    model_name = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    revised_prompt = Column(Text, nullable=True)     # API 返回的修订提示词
    object_key = Column(String(500), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    is_img2img = Column(Boolean, default=False)
