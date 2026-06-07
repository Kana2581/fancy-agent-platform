from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, model_validator
from pydantic import field_validator

from app.core.config import settings


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
        OSS_BASE_URL=settings.OSS_URL
        if isinstance(data, dict):
            if not data.get("url") and data.get("object_key"):
                data["url"] = f"{OSS_BASE_URL}/{data['object_key']}"
        else:
            # ORM对象
            if not getattr(data, "url", None) and getattr(data, "object_key", None):
                data.url = f"{OSS_BASE_URL}/{data.object_key}"
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

class CompressRequest(BaseModel):
    message_id: Optional[str] = None


class ApproveToolRequest(BaseModel):
    message_id: str
    approved: bool




