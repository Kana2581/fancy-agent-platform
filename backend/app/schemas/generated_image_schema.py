from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, computed_field

from app.core.config import settings


class GeneratedImageOut(BaseModel):
    id: int
    user_id: int
    image_tool_id: Optional[int] = None
    provider: str
    model_name: str
    prompt: str
    revised_prompt: Optional[str] = None
    object_key: str
    width: Optional[int] = None
    height: Optional[int] = None
    is_img2img: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def image_url(self) -> str:
        oss_url = getattr(settings, "OSS_URL", "http://localhost:8000")
        return f"{oss_url.rstrip('/')}/{self.object_key}"

    @computed_field
    @property
    def thumbnail_url(self) -> str:
        oss_url = getattr(settings, "OSS_URL", "http://localhost:8000")
        return f"{oss_url.rstrip('/')}/{self.object_key}.thumb.webp"


class GeneratedImagePageOut(BaseModel):
    items: List[GeneratedImageOut]
    total: int
