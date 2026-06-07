from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime


class ImageToolCreate(BaseModel):
    name: str
    description: Optional[str] = None
    provider: Optional[str]
    api_key: str = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    default_size: Optional[str] = "1024x1024"
    default_quality: Optional[str] = None
    default_style: Optional[str] = None
    extra_params: Optional[dict] = None
    support_img2img: bool = False


class ImageToolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    default_size: Optional[str] = None
    default_quality: Optional[str] = None
    default_style: Optional[str] = None
    extra_params: Optional[dict] = None
    support_img2img: Optional[bool] = None


class ImageToolOut(ImageToolCreate):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    # None ⇒ adapter 走 default_size；显式传值则覆盖
    width: Optional[int] = None
    height: Optional[int] = None
    extra: dict = {}


class Img2ImgRefRequest(BaseModel):
    prompt: str
    image_url: Optional[str] = None
    object_key: Optional[str] = None
    negative_prompt: str = ""
    width: Optional[int] = None
    height: Optional[int] = None
    extra: dict = {}

    @model_validator(mode="after")
    def validate_reference(self):
        if not (self.image_url or self.object_key):
            raise ValueError("image_url or object_key is required")
        return self


class GenerateResponse(BaseModel):
    image_url: str
    revised_prompt: Optional[str] = None
