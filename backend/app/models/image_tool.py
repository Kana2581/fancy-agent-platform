from sqlalchemy import Column, Integer, String, Text, Boolean, JSON

from app.core.crypto import EncryptedString
from app.core.database import Base
from app.models.timestamp_model import TimestampMixin


class ImageTool(Base, TimestampMixin):
    __tablename__ = "image_tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    provider = Column(String(50), nullable=False)        # "openai" | "stability"
    api_key = Column(EncryptedString(), nullable=False)
    base_url = Column(String(500), nullable=True)        # 代理/兼容端点
    model = Column(String(100), nullable=True)           # dall-e-3 / stable-diffusion-xl-...
    default_size = Column(String(50), nullable=True)     # 1024x1024
    default_quality = Column(String(50), nullable=True)  # openai: standard|hd
    default_style = Column(String(50), nullable=True)    # openai: vivid|natural
    extra_params = Column(JSON, nullable=True)           # steps/cfg_scale 等 SD 专属参数
    support_img2img = Column(Boolean, default=False)
