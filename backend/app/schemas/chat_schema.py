from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, model_validator
from pydantic import field_validator

from app.services.storage.url_signer import build_storage_url, rewrite_image_urls_in_text


class ChatRequest(BaseModel):
    parent_id: Optional[str] = None
    content: Optional[str] = None
    id: Optional[str] = None
    file_ids:Optional[List[int]] = None
    @field_validator("id", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

class SimpleFile(BaseModel):
    id: int
    content_type:Optional[str]
    url:Optional[str]
    @model_validator(mode="before")
    @classmethod
    def build_url(cls, data):
        if isinstance(data, dict):
            if not data.get("url") and data.get("object_key"):
                data["url"] = build_storage_url(data["object_key"])
        else:
            # ORM对象
            if not getattr(data, "url", None) and getattr(data, "object_key", None):
                data.url = build_storage_url(data.object_key)
        return data

class ChatResponse(BaseModel):
    id: str
    content: str|List|dict
    type: str
    name: Optional[str] = None
    parent_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    files:Optional[List[SimpleFile]] = None
    usage_metadata: Optional[Dict[str, Any]] = None
    approval_status: Optional[str] = None

    @model_validator(mode="after")
    def _resign_inline_images(self):
        # 历史消息 content 里内联的图片 URL 可能是过期的预签名 URL，
        # 返回前端前按 object_key 重新签名（public 模式幂等、无副作用）。
        if isinstance(self.content, str) and self.content:
            self.content = rewrite_image_urls_in_text(self.content)
        return self

class CompressRequest(BaseModel):
    message_id: Optional[str] = None


class ApproveToolRequest(BaseModel):
    message_id: str
    approved: bool




